"""Conditional one-parameter fit, guarded freeze, nonblind transfer evaluation."""
import os
os.environ['OMP_NUM_THREADS']='1';os.environ['PYBAMM_DISABLE_TELEMETRY']='true'
import sys,json,hashlib,time,subprocess,platform
from pathlib import Path
import numpy as np
from scipy.optimize import minimize_scalar
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import e66_pulse_discrimination as pulse
from scripts.fit_e66_generator_b import get_inputs
OUT=ROOT/'results/e66_kinetic_calibration';REC=pulse.REC

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,d):Path(p).write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def params(k,soc,T):
 import pybamm
 f=json.loads((REC/'FIT_RESULT.json').read_text());p=pybamm.ParameterValues('Chen2020');p.set_initial_stoichiometries(soc,inplace=True)
 fn=p['Positive electrode OCP [V]'];a,b,r=f['parameters']
 def corrected(sto):return fn(sto)+a+b*(sto-.5)
 p.update({'Positive electrode OCP [V]':corrected,'Contact resistance [Ohm]':r,'Initial temperature [K]':T+273.15,'Ambient temperature [K]':T+273.15,'Lower voltage cut-off [V]':2.5,'Upper voltage cut-off [V]':4.5})
 for side in ['Negative','Positive']:
  key=side+' electrode exchange-current density [A.m-2]';fun=p[key]
  def scaled(c_e,c_s_surf,c_s_max,T,fun=fun):return k*fun(c_e,c_s_surf,c_s_max,T)
  p.update({key:scaled})
 return p

def run_model(p,grid,kind,mesh):
 import pybamm
 m=getattr(pybamm.lithium_ion,kind)(options={'thermal':'isothermal','contact resistance':'true'})
 sim=pybamm.Simulation(m,parameter_values=p,var_pts={key:mesh for key in ['x_n','x_s','x_p','r_n','r_p']},solver=pybamm.IDAKLUSolver(rtol=1e-7,atol=1e-8));s=sim.solve([0,float(grid[-1])]);good=grid<=s.t[-1];g=grid[good];v=np.asarray(s['Voltage [V]'](g)).reshape(-1)
 return g,v,float(np.asarray(s['Battery open-circuit voltage [V]'](0)).reshape(-1)[0]),float(s.t[-1])/float(grid[-1]),str(s.termination)

def simulate(k,dataset,index,kind='SPMe',mesh=40):
 import pybamm
 if dataset in ['HPPC','GITT']:
  f,grid,actual=pulse.extract(dataset)[0][index];dur=f['duration_s'];end=dur+f['available_post_s'];p=params(k,f['soc_proxy'],f['initial_T_C']);I=f['current_A']/(61.259778569358865/5)
  p.update({'Current function [A]':pybamm.Interpolant(np.array([0.,dur-.001,dur,end]),np.array([I,I,0,0]),pybamm.t)})
  g,v,ocv,coverage,term=run_model(p,grid,kind,mesh);pred=v-ocv;actual=actual[:len(g)];loaded=g<dur-.1
 else:
  spec=json.loads((REC/'PROSPECTIVE.json').read_text());d=get_inputs(pulse.ARCHIVE,[spec['evaluation'][index]])[0];p=params(k,1,float(d['T'][0]));p.update({'Current function [A]':pybamm.Interpolant(d['t'],d['i']/(61.259778569358865/5),pybamm.t)})
  grid=np.linspace(0,d['t'][-1],500);g,pred,ocv,coverage,term=run_model(p,grid,kind,mesh);actual=np.interp(g,d['t'],d['v']);loaded=np.ones(len(g),bool)
 error=pred-actual
 def rm(x):return float(np.sqrt(np.mean(x*x))) if len(x) else None
 return {'status':'COMPLETED','k':k,'dataset':dataset,'index':index,'model':kind,'mesh':mesh,'RMSE_V':rm(error),'loaded_RMSE_V':rm(error[loaded]),'rest_RMSE_V':rm(error[~loaded]),'max_error_V':float(np.max(abs(error))),'bias_V':float(np.mean(error)),'coverage':coverage,'termination':term,'model_times_s':g.tolist(),'model_V':pred.tolist(),'loaded_MSE':float(np.mean(error[loaded]**2)),'gate':'PASS' if rm(error)<=.05 and np.max(abs(error))<=.15 and coverage>=.95 else 'FAIL'}

def job(k,dataset,index,kind='SPMe',mesh=40):
 key=hashlib.sha256(json.dumps([float(k),dataset,index,kind,mesh,sha(__file__)]).encode()).hexdigest()[:16];path=OUT/('job_'+key+'.json')
 if path.exists():return json.loads(path.read_text())
 cmd=[sys.executable,__file__,'worker',str(k),dataset,str(index),kind,str(mesh)]
 try:
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=90);(OUT/('job_'+key+'.log')).write_text(p.stderr)
  if p.returncode:raise RuntimeError(p.stderr[-1200:])
  r=json.loads(p.stdout)
 except Exception as e:r={'status':'ERROR','k':k,'dataset':dataset,'index':index,'model':kind,'mesh':mesh,'error':str(e)}
 dump(path,r);return r

def signature():
 import importlib.metadata as m
 return {'script_sha256':sha(__file__),'pulse_script_sha256':sha(pulse.__file__),'protocol_sha256':sha(OUT/'PROTOCOL.json'),'base_fit_sha256':sha(REC/'FIT_RESULT.json'),'archive_sha256':sha(pulse.ARCHIVE),'versions':{x:m.version(x) for x in ['pybamm','numpy','scipy','pybammsolvers','casadi']},'python':platform.python_version()}

def fit():
 if (OUT/'GENERATOR_B_FREEZE.json').exists():raise ValueError('already frozen')
 sig=signature();dump(OUT/'FIT_START.json',sig);history=[]
 def obj(logk):
  k=float(np.exp(logk));rr=[job(k,'HPPC',i) for i in range(3)]
  if any(r['status']!='COMPLETED' or r['coverage']<.999 for r in rr):raise RuntimeError('fit solve failed, abort')
  mse=float(np.mean([r['loaded_MSE'] for r in rr]));history.append({'k':k,'MSE':mse,'per_pulse_MSE':[r['loaded_MSE'] for r in rr]});dump(OUT/'FIT_HISTORY.json',history);print('fit',k,mse,flush=True);return mse
 profiles=[]
 for k in [.5,1,1.5,2,3,4,6,8]:obj(np.log(k));profiles.append(history[-1])
 fit=minimize_scalar(obj,bounds=(np.log(.5),np.log(8)),method='bounded',options={'xatol':.01,'maxiter':20})
 result={'k':float(np.exp(fit.x)),'success':bool(fit.success),'MSE':float(fit.fun),'nfev':fit.nfev,'profiles':profiles,'conditional_pulse_grid_optima':[min(profiles,key=lambda r:r['per_pulse_MSE'][i])['k'] for i in range(3)],'leave_one_pulse_out_grid_optima':[min(profiles,key=lambda r:sum(v for j,v in enumerate(r['per_pulse_MSE']) if j!=i))['k'] for i in range(3)],'uncertainty':'conditional profile only, not a CI; three correlated pulses from one cell'}
 dump(OUT/'FIT_RESULT.json',result)
 if not fit.success:raise RuntimeError('optimizer not converged; no freeze')
 dump(OUT/'GENERATOR_B_FREEZE.json',{'signature':sig,'fit_sha256':sha(OUT/'FIT_RESULT.json'),'k':result['k'],'scope':'effective Chen-derived joint kinetic multiplier; not identified E66 electrode physics','before_new_predictions':True,'evaluation_exposure':'nonblind, previous empirical/voltage inspection','status':'RESEARCH_FROZEN_NOT_APPROVED'})

def evaluate():
 f=json.loads((OUT/'GENERATOR_B_FREEZE.json').read_text())
 if f['signature']!=signature() or f['fit_sha256']!=sha(OUT/'FIT_RESULT.json'):raise ValueError('freeze drift')
 k=f['k'];jobs=[('GITT',i,m,40) for i in range(6) for m in ['SPMe','DFN']]+[('DISCHARGE',i,m,40) for i in range(2) for m in ['SPMe','DFN']]+[('HPPC',1,'SPMe',40),('HPPC',1,'SPMe',80),('GITT',0,'SPMe',80)]
 rows=[]
 for d,i,m,n in jobs:
  r=job(k,d,i,m,n);rows.append(r);dump(OUT/'EVALUATION.json',{'freeze_sha256':sha(OUT/'GENERATOR_B_FREEZE.json'),'results':rows,'historical_reserved_access':0,'module_reserved_access':0});print(d,i,m,n,r['status'],r.get('RMSE_V'),flush=True)

if __name__=='__main__':
 mode=sys.argv[1]
 if mode=='worker':print(json.dumps(simulate(float(sys.argv[2]),sys.argv[3],int(sys.argv[4]),sys.argv[5],int(sys.argv[6])),allow_nan=False))
 elif mode=='fit':fit()
 elif mode=='evaluate':evaluate()
 else:raise ValueError(mode)
