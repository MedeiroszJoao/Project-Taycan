"""Bounded E66 terminal-response calibration; Chen-derived effective surrogate.
No module/temperature holdouts, historical manifest episodes or classifier inputs.
"""
import os
os.environ['PYBAMM_DISABLE_TELEMETRY']='true'
import argparse,hashlib,io,json,platform,time,zipfile,sys
from pathlib import Path
import numpy as np
from scipy.io import loadmat
from scipy.optimize import least_squares
from importlib.metadata import version
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/e66_calibration'
def sha(b):return hashlib.sha256(b).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def segment(blob):
 m=loadmat(io.BytesIO(blob),simplify_cells=True)['meas']
 t=np.asarray(m['Time'],float);i=-np.asarray(m['Current'],float);v=np.asarray(m['Voltage'],float);T=np.asarray(m['Battery_Temp_degC'],float)
 valid=np.isfinite(t)&np.isfinite(i)&np.isfinite(v)&np.isfinite(T)&(i>1)&(v>2)&(v<5)
 # First contiguous high-current discharge, never concatenate charge/rest cycles.
 ix=np.flatnonzero(valid)
 if len(ix)<10:raise ValueError('no valid discharge')
 cut=np.flatnonzero(np.diff(ix)>1);ix=ix[:cut[0]+1] if len(cut) else ix
 t=t[ix]-t[ix[0]];i=i[ix];v=v[ix];T=T[ix]
 if np.any(np.diff(t)<=0):raise ValueError('nonmonotonic time')
 return {'t':t,'i':i,'v':v,'T':T,'source_sha256':sha(blob),'rows':len(t),'capacity_Ah':float(np.trapezoid(i,t)/3600),'duration_s':float(t[-1]),'current_median_A':float(np.median(i)),'initial_temperature_C':float(T[0]),'temperature_range_C':[float(T.min()),float(T.max())]}
def simulate(d,x,q,kind='SPMe',mesh=20,fit=False):
 import pybamm
 p=pybamm.ParameterValues('Chen2020');p.set_initial_stoichiometries(1,inplace=True)
 ocp=p['Positive electrode OCP [V]'];a,b,r=map(float,x)
 def corrected(sto):return ocp(sto)+a+b*(sto-.5)
 p.update({'Positive electrode OCP [V]':corrected,'Contact resistance [Ohm]':r,'Ambient temperature [K]':d['T'][0]+273.15,'Initial temperature [K]':d['T'][0]+273.15,'Lower voltage cut-off [V]':2.5,'Upper voltage cut-off [V]':4.5,'Current function [A]':pybamm.Interpolant(d['t'],d['i']/(q/5),pybamm.t)})
 duration=float(d['t'][-1])*(.9 if fit else 1)
 model=getattr(pybamm.lithium_ion,kind)(options={'thermal':'isothermal','contact resistance':'true'})
 sim=pybamm.Simulation(model,parameter_values=p,var_pts={k:mesh for k in ['x_n','x_s','x_p','r_n','r_p']},solver=pybamm.IDAKLUSolver(rtol=1e-6 if mesh==20 else 1e-8,atol=1e-7 if mesh==20 else 1e-9))
 sol=sim.solve([0,duration]);grid=np.linspace(0,min(duration,float(sol.t[-1])),150 if fit else 500)
 return grid,np.asarray(sol['Voltage [V]'](grid)).reshape(-1),str(sol.termination)
def get_inputs(archive,names):
 z=zipfile.ZipFile(archive);c=zipfile.ZipFile(io.BytesIO(z.read('1-Cell Data.zip')))
 return [dict(segment(c.read(n)),name=n) for n in names]
def summarize(d):return {k:v for k,v in d.items() if k not in ('t','i','v','T')}
def run(archive):
 import pybamm
 spec=json.loads((OUT/'PROSPECTIVE.json').read_text())
 if pybamm.__version__!='26.4.2':raise ValueError('version mismatch')
 if sha(archive.read_bytes())!=spec['source_archive_SHA256']:raise ValueError('archive mismatch')
 if (OUT/'GENERATOR_B_FREEZE.json').exists():raise ValueError('existing freeze; use evaluation command, do not refit')
 fits=get_inputs(archive,spec['fit']);q=fits[0]['capacity_Ah'];history=[];start=time.monotonic()
 def objective(x):
  errs=[]
  for d in fits:
   try:
    t,v,term=simulate(d,x,q,fit=True)
    expected=np.interp(t,d['t'],d['v']);e=v-expected
    coverage=t[-1]/(.9*d['t'][-1])
    if coverage<.999:e=e+(1-coverage)*2
   except Exception as exc:
    e=np.ones(150)*10;term=type(exc).__name__+': '+str(exc)
   errs.extend(e)
  history.append({'parameters':list(map(float,x)),'rmse_V':float(np.sqrt(np.mean(np.array(errs)**2))),'termination':term})
  dump(OUT/'FIT_HISTORY.json',history)
  return np.asarray(errs)
 fit=least_squares(objective,[0,0,.001],bounds=([-.3,-1,0],[.3,1,.1]),max_nfev=25,diff_step=1e-3,xtol=1e-6,ftol=1e-6,gtol=1e-6)
 singular=np.linalg.svd(fit.jac,compute_uv=False);rank=int(np.linalg.matrix_rank(fit.jac))
 result={'parameters':list(map(float,fit.x)),'effective_capacity_Ah':q,'virtual_parallel_scale':q/5,'conditional_jacobian_singular_values':singular.tolist(),'jacobian_condition':float(singular[0]/singular[-1]) if singular[-1]>0 else None,'jacobian_rank':rank,'least_squares_success':bool(fit.success),'termination':str(fit.message),'nfev':fit.nfev,'actual_solver_attempts':len(history)*len(fits),'fit_RMSE_V':float(np.sqrt(np.mean(fit.fun**2))),'elapsed_s':time.monotonic()-start,'fit_sources':[summarize(d) for d in fits],'interpretation':'effective terminal-curve calibration of Chen-derived current-normalized surrogate, not unique E66 electrode physics','covariance_CI':'not reported: residual time autocorrelation and singlecell invalidate iid covariance'}
 dump(OUT/'FIT_RESULT.json',result)
 freeze={'status':'FROZEN_RESEARCH_CANDIDATE_NOT_APPROVED_E66_PHYSICS','source_sha256':sha(Path(__file__).read_bytes()),'prospective_sha256':sha((OUT/'PROSPECTIVE.json').read_bytes()),'fit_result_sha256':sha((OUT/'FIT_RESULT.json').read_bytes()),'parameters':result['parameters'],'effective_capacity_Ah':q,'virtual_parallel_scale':q/5,'base':'Chen2020','models':['SPMe','DFN sensitivity'],'thermal':'isothermal; no thermal predictiveclaim','solver':'IDAKLU rtol1e-6 atol1e-7 mesh20','environment':{'python':platform.python_version(),**{k:version(k) for k in ['pybamm','pybammsolvers','numpy','scipy','casadi']}},'fit_files':result['fit_sources'],'evaluation_files':spec['evaluation'],'before_evaluation':True,'seeds':[],'limitations':spec['numeric_exposure'],'criteria':spec['evaluation_criteria']}
 dump(OUT/'GENERATOR_B_FREEZE.json',freeze)
 print(json.dumps(result),flush=True)
def evaluate(archive):
 f=json.loads((OUT/'GENERATOR_B_FREEZE.json').read_text());spec=json.loads((OUT/'PROSPECTIVE.json').read_text())
 for path,key in [(Path(__file__),'source_sha256'),(OUT/'PROSPECTIVE.json','prospective_sha256'),(OUT/'FIT_RESULT.json','fit_result_sha256')]:
  if sha(path.read_bytes())!=f[key]:raise ValueError('freeze mismatch '+str(path))
 if sha(archive.read_bytes())!=spec['source_archive_SHA256']:raise ValueError('archive mismatch')
 datasets=get_inputs(archive,f['evaluation_files']);reports=[]
 for d in datasets:
  for model in ['SPMe','DFN']:
   item={'file':d['name'],'model':model,'experimental':summarize(d)}
   try:
    t,v,term=simulate(d,f['parameters'],f['effective_capacity_Ah'],kind=model)
    expected=np.interp(t,d['t'],d['v']);error=v-expected
    coverage=t[-1]/d['t'][-1]
    item.update(voltage_RMSE_V=float(np.sqrt(np.mean(error**2))),voltage_bias_V=float(error.mean()),voltage_max_error_V=float(np.max(abs(error))),coverage_fraction=float(coverage),termination=term,trajectory=[{'time_s':float(tt),'model_V':float(vv),'measured_V':float(ee)} for tt,vv,ee in zip(t,v,expected)])
    item['gate']='PASS' if item['voltage_RMSE_V']<=.05 and item['voltage_max_error_V']<=.15 and coverage>=.95 else 'FAIL'
    tf,vf,_=simulate(d,f['parameters'],f['effective_capacity_Ah'],kind=model,mesh=40)
    common=t<=tf[-1];gap=float(np.max(abs(v[common]-np.interp(t[common],tf,vf))))
    item['numerical_refinement_max_V']=gap;item['numerical_gate']='PASS' if gap<=.005 else 'FAIL'
   except Exception as e:item.update(gate='ERROR',error=type(e).__name__+': '+str(e))
   reports.append(item);dump(OUT/'EVALUATION.json',{'freeze_sha256':sha((OUT/'GENERATOR_B_FREEZE.json').read_bytes()),'classification':'VALIDAÇÃO EXTERNA LIMITADA DE CURVA TERMINAL; UMA CÉLULA; NÃO CEGA','results':reports,'physical_temperature_prediction':'NOT_EXECUTED_ISOTHERMAL','historical_reserved_access':0})
 print(json.dumps([{k:v for k,v in r.items() if k!='trajectory'} for r in reports]),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['fit','evaluate']);p.add_argument('--archive',type=Path,default=ROOT.parent/'project_sources/09-doi-10.5683-sp3-7jp3nm.zip');a=p.parse_args();(run if a.mode=='fit' else evaluate)(a.archive)
