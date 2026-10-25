"""Fixed one-at-a-time post-hoc causal probes, never refits exposed 1C."""
import os
os.environ['PYBAMM_DISABLE_TELEMETRY']='true'
os.environ['OMP_NUM_THREADS']='1'
import argparse,hashlib,json,subprocess,sys,time,concurrent.futures,platform
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
OUT=ROOT/'results/e66_causal_audit/counterfactuals';REC=ROOT/'results/tmp/e66_causal/receipts/e66_calibration'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,o):p.write_text(json.dumps(o,indent=2,allow_nan=False)+'\n')
def worker(case,model,rate):
 import numpy as np,pybamm
 from scripts.fit_e66_generator_b import get_inputs
 if pybamm.__version__!='26.4.2':raise ValueError('version drift')
 fit=json.loads((REC/'FIT_RESULT.json').read_text());spec=json.loads((REC/'PROSPECTIVE.json').read_text())
 name=next(n for n in spec['evaluation'] if n.endswith('Dis_'+('0p5C' if rate=='.5' else '1C')+'.mat'))
 d=get_inputs(ROOT.parent/'project_sources/09-doi-10.5683-sp3-7jp3nm.zip',[name])[0]
 p=pybamm.ParameterValues('Chen2020');soc=.99 if case=='initial_soc_0p99' else 1.
 if case!='reinitialize_corrected_ocp':p.set_initial_stoichiometries(soc,inplace=True)
 ocp=p['Positive electrode OCP [V]'];a,b,r=fit['parameters']
 def corrected(sto):return ocp(sto)+a+b*(sto-.5)
 p.update({'Positive electrode OCP [V]':corrected})
 if case=='reinitialize_corrected_ocp':p.set_initial_stoichiometries(soc,inplace=True)
 q=65. if case=='capacity_nominal65' else fit['effective_capacity_Ah']
 T=float(d['T'][0])+273.15+(5 if case=='temperature_plus5' else 0)
 ambient=pybamm.Interpolant(d['t'],d['T']+273.15,pybamm.t) if case=='temperature_measured_oracle' else T
 p.update({'Contact resistance [Ohm]':r+(.001 if case=='contact_plus0p001' else 0),'Initial temperature [K]':T,'Ambient temperature [K]':ambient,'Lower voltage cut-off [V]':2.5,'Upper voltage cut-off [V]':4.5,'Current function [A]':pybamm.Interpolant(d['t'],d['i']/(q/5),pybamm.t)})
 if case=='diffusivity_both_x2':
  for side in ['Negative','Positive']:
   key=side+' particle diffusivity [m2.s-1]';p.update({key:2*p[key]})
 if case=='kinetics_both_x2':
  for side in ['Negative','Positive']:
   key=side+' electrode exchange-current density [A.m-2]';fn=p[key]
   def doubled(c_e,c_s_surf,c_s_max,T,fn=fn):return 2*fn(c_e,c_s_surf,c_s_max,T)
   p.update({key:doubled})
 m=getattr(pybamm.lithium_ion,model)(options={'thermal':'isothermal','contact resistance':'true'})
 sim=pybamm.Simulation(m,parameter_values=p,var_pts={k:20 for k in ['x_n','x_s','x_p','r_n','r_p']},solver=pybamm.IDAKLUSolver(rtol=1e-6,atol=1e-7))
 started=time.monotonic();s=sim.solve([0,float(d['t'][-1])]);end=float(s.t[-1]);t=np.linspace(0,d['t'][-1],500);t=t[t<=end+1e-8]
 v=np.array(s['Voltage [V]'](t)).reshape(-1);obs=np.interp(t,d['t'],d['v']);e=v-obs
 old=json.loads((REC/'EVALUATION.json').read_text());old=next(x for x in old['results'] if x['model']==model and x['file']==name)
 base=np.array([r['model_V'] for r in old['trajectory']])[:len(t)];gap=v-base
 result={'status':'COMPLETED','case':case,'model':model,'rate':rate,'file_sha256':d['source_sha256'],'elapsed_s':time.monotonic()-started,'coverage':end/d['t'][-1],'termination':str(s.termination),'RMSE_V':float(np.sqrt(np.mean(e*e))),'bias_V':float(np.mean(e)),'centered_RMSE_V':float(np.std(e)),'max_abs_error_V':float(np.max(abs(e))),'baseline_gap_max_V':float(np.max(abs(gap))),'baseline_gap_RMS_V':float(np.sqrt(np.mean(gap*gap))),'baseline_gap_mean_V':float(np.mean(gap)),'initial_terminal_V':float(v[0]),'initial_temperature_K':T,'capacity_normalizer_Ah':q,'parameters_optimized':False,'classification':'POSTHOC_DIAGNOSTIC_NOT_NEW_VALIDATION','source_SHA256':sha(__file__),'fit_SHA256':sha(REC/'FIT_RESULT.json'),'protocol_SHA256':sha(OUT/'PROTOCOL.json')}
 for key in ['Battery open-circuit voltage [V]','Surface open-circuit voltage [V]']:
  try:result['initial_OCV_V']=float(np.asarray(s[key](0)).reshape(-1)[0]);result['OCV_key']=key;break
  except KeyError:pass
 result['descriptive_original_error_gate']='PASS' if result['RMSE_V']<=.05 and result['max_abs_error_V']<=.15 and result['coverage']>=.95 else 'FAIL'
 if case=='baseline':result['archive_reproduction']='PASS' if result['baseline_gap_max_V']<=1e-4 else 'FAIL'
 return result

def runjob(job):
 case,model,rate=job;path=OUT/f'{model}_{rate}_{case}.json'
 if path.exists():
  r=json.loads(path.read_text())
  if r.get('source_SHA256')==sha(__file__) and r.get('protocol_SHA256')==sha(OUT/'PROTOCOL.json'):return r
 try:
  p=subprocess.run([sys.executable,__file__,'--worker',case,model,rate],cwd=ROOT,capture_output=True,text=True,timeout=120)
  (OUT/f'{model}_{rate}_{case}.log').write_text(p.stderr)
  if p.returncode:raise RuntimeError(p.stderr[-1500:])
  r=json.loads(p.stdout)
 except subprocess.TimeoutExpired:r={'status':'TIMEOUT','case':case,'model':model,'rate':rate,'limit_s':120}
 except Exception as e:r={'status':'ERROR','case':case,'model':model,'rate':rate,'error':str(e)}
 r.update(source_SHA256=sha(__file__),protocol_SHA256=sha(OUT/'PROTOCOL.json'));write(path,r);return r

def main():
 protocol=json.loads((OUT/'PROTOCOL.json').read_text());jobs=[(c,'SPMe',r) for c in protocol['cases'] for r in ['.5','1']]+[(c,'DFN','1') for c in protocol['DFN_1C_cases']]
 from importlib.metadata import version
 write(OUT/'ENVIRONMENT.json',{'python':platform.python_version(),**{k:version(k) for k in ['pybamm','pybammsolvers','numpy','scipy','casadi']}})
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  results=[]
  for r in pool.map(runjob,jobs):
   results.append(r);write(OUT/'RESULTS.json',{'results':results,'frozen_parameters_not_refit':True,'official_test_access':0});print(r['model'],r['rate'],r['case'],r['status'],r.get('RMSE_V'),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--worker',nargs=3);a=p.parse_args()
 if a.worker:
  try:print(json.dumps(worker(*a.worker),allow_nan=False))
  except Exception:raise
 else:main()
