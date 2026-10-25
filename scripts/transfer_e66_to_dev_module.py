"""Guarded 6s2p sentinel transfer; only development module payloads are read."""
import os,sys,json,io,zipfile,tempfile,subprocess,hashlib
from pathlib import Path
os.environ['OMP_NUM_THREADS']='1';os.environ['PYBAMM_DISABLE_TELEMETRY']='true'
import numpy as np
from scipy.optimize import brentq
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import calibrate_e66_kinetics as c
from scripts import recalibrate_e66_ocp_offset as o
from scripts.audit_stage4b_e66_dev_only import DEV
OUT=ROOT/'results/e66_module_transfer';FIELDS=['RecordingTime','AVL_Current','AVL_Voltage','AhAccu_Charge','AhAccu_Discharge'];THERM=['A1','A2','A3','B1','C1','D1','E1','E2','E3']
def trim_terminal_padding(d):
 if len(d['RecordingTime'])>1 and all(not np.isfinite(d[k][-1]) for k in FIELDS):
  return {k:v[:-1] for k,v in d.items()},1
 return d,0

def read(name):
 if name not in DEV:raise ValueError('not development allowlist')
 import matio,pandas as pd
 with zipfile.ZipFile(c.pulse.ARCHIVE) as z:
  raw=z.read('4-Module Data.zip')
 if hashlib.sha256(raw).hexdigest()!='a5628a9d56d2e097158620346c3f69b5ff5c6269bb2770f643e91f397abcac7e':raise ValueError('module hash')
 with zipfile.ZipFile(io.BytesIO(raw)) as z:blob=z.read(next(n for n in z.namelist() if Path(n).name==name))
 with tempfile.NamedTemporaryFile(suffix='.mat') as f:
  f.write(blob);f.flush();a=matio.load_from_mat(f.name,raw_data=False)['meas']
 tables={k:a[k].flat[0] for k in FIELDS+THERM if k in a.dtype.names};base=tables['RecordingTime']
 if any(not isinstance(v,pd.DataFrame) or len(v)!=len(base) or not v.index.equals(base.index) or v.shape[1]!=1 for v in tables.values()):raise ValueError('unaligned tables')
 d={k:pd.to_numeric(v.iloc[:,0],errors='coerce').to_numpy(dtype=float) for k,v in tables.items()};d,removed=trim_terminal_padding(d);t=d['RecordingTime']
 if not all(np.all(np.isfinite(d[k])) for k in FIELDS) or np.any(np.diff(t)<=0):raise ValueError('nonfinite/clock')
 d['source_sha256']=hashlib.sha256(blob).hexdigest();d['terminal_padding_removed']=removed;return d

def parameters(soc,T):
 f=json.loads((o.OUT/'GENERATOR_B_FREEZE.json').read_text());p=c.params(f['parent_k'],soc,T);fn=p['Positive electrode OCP [V]']
 def shifted(sto):return fn(sto)+f['additive_ocp_offset_V']
 p.update({'Positive electrode OCP [V]':shifted});return p

def ocv(soc,T):
 p=parameters(soc,T);vs=[]
 for side in ['Negative','Positive']:
  x=p[f'Initial concentration in {side.lower()} electrode [mol.m-3]']/p[f'Maximum concentration in {side.lower()} electrode [mol.m-3]'];v=p[f'{side} electrode OCP [V]'](x);vs.append(float(v.evaluate()) if hasattr(v,'evaluate') else float(v))
 return vs[1]-vs[0]

def window(name):
 d=read(name);t=d['RecordingTime'];I=d['AVL_Current'];active=np.flatnonzero(abs(I)>10)
 if not len(active):raise ValueError('no active current')
 a=int(active[0])
 if a<5 or np.any(abs(I[a-5:a])>1):raise ValueError('insufficient initial quiet samples')
 end=min(t[a]+300,t[-1]);ix=np.flatnonzero((t>=t[a])&(t<=end))
 if t[ix[-1]]-t[a]<60 or np.max(np.diff(t[ix]))>2:raise ValueError('short/gapped sentinel')
 initialT=float(np.nanmean(np.array([d[k][a-5:a] for k in THERM if k in d])));initialV=float(np.mean(d['AVL_Voltage'][a-5:a])/6)
 if not np.isfinite(initialT):raise ValueError('missing initial temperature')
 z=brentq(lambda soc:ocv(soc,initialT)-initialV,.05,.95,xtol=1e-10)
 # Signed counter and current are compared over the same complete record, not used as voltage targets.
 q=np.r_[0,np.cumsum((I[1:]+I[:-1])*.5*np.diff(t)/3600)];counter=d['AhAccu_Charge']+d['AhAccu_Discharge'];counter=counter-counter[0]
 corr=float(np.corrcoef(q,counter)[0,1]) if np.std(q)>1e-6 and np.std(counter)>1e-6 else None
 if corr is None or corr<.9:raise ValueError('counter sign/timing check')
 temps=np.array([d[k][ix] for k in THERM if k in d]);meta={'name':name,'sha256':d['source_sha256'],'rows':len(t),'terminal_padding_removed':d['terminal_padding_removed'],'activation_time_s':float(t[a]),'duration_s':float(t[ix[-1]]-t[a]),'initial_SOC_from_pre_voltage':z,'initial_mean_surface_T_C':initialT,'initial_mean_cell_V':initialV,'surface_T_range_C':[float(np.nanmin(temps)),float(np.nanmax(temps))],'counter_integral_correlation':corr,'counter_integral_RMSE_Ah':float(np.sqrt(np.mean((q-counter)**2))),'current_module_range_A':[float(np.min(I[ix])),float(np.max(I[ix]))]}
 return t[ix]-t[a],-I[ix]/2,d['AVL_Voltage'][ix]/6,meta

def simulate(name,kind):
 import pybamm
 t,I,v,meta=window(name);p=parameters(meta['initial_SOC_from_pre_voltage'],meta['initial_mean_surface_T_C']);p.update({'Current function [A]':pybamm.Interpolant(t,I/(61.259778569358865/5),pybamm.t)})
 grid=np.linspace(0,t[-1],301);g,pred,_,coverage,term=c.run_model(p,grid,kind,40);e=pred-np.interp(g,t,v);rmse=float(np.sqrt(np.mean(e*e)));mx=float(np.max(abs(e)))
 return {'status':'COMPLETED','name':name,'model':kind,'metadata':meta,'RMSE_mean_cell_V':rmse,'max_error_mean_cell_V':mx,'coverage':coverage,'termination':term,'gate':'PASS' if rmse<=.05 and mx<=.15 and coverage>=.95 else 'FAIL','model_times_s':g.tolist(),'model_mean_cell_V':pred.tolist()}

def signature():return {'script_sha256':c.sha(__file__),'amendment_sha256':c.sha(OUT/'TERMINAL_PADDING_AMENDMENT.json'),'protocol_sha256':c.sha(OUT/'PROTOCOL.json'),'cell_freeze_sha256':c.sha(o.OUT/'GENERATOR_B_FREEZE.json'),'development_allowlist':sorted(DEV),'reserved_numeric_access':0}
def run():
 f=signature();path=OUT/'TRANSFER_FREEZE.json'
 if path.exists() and json.loads(path.read_text())!=f:raise ValueError('transfer drift')
 if not path.exists():c.dump(path,f)
 if json.loads((o.OUT/'GENERATOR_B_FREEZE.json').read_text())['signature']!=o.signature():raise ValueError('cell freeze drift')
 rows=[]
 for name in sorted(DEV):
  for kind in ['SPMe','DFN']:
   try:
    p=subprocess.run([sys.executable,__file__,'worker',name,kind],capture_output=True,text=True,timeout=90)
    if p.returncode:raise RuntimeError(p.stderr[-1400:])
    r=json.loads(p.stdout)
   except Exception as e:r={'status':'ERROR_OR_INELIGIBLE','name':name,'model':kind,'error':str(e)}
   rows.append(r);c.dump(OUT/'EVALUATION.json',{'freeze_sha256':c.sha(path),'results':rows,'reserved_numeric_access':0});print(name,kind,r['status'],r.get('RMSE_mean_cell_V'),flush=True)
if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='worker':print(json.dumps(simulate(sys.argv[2],sys.argv[3])))
 elif len(sys.argv)>1 and sys.argv[1]=='freeze':c.dump(OUT/'TRANSFER_FREEZE.json',signature())
 else:run()
