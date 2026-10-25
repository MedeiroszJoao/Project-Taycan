"""Authorized25C HPPC/GITT discrimination; no fitting or raw-data publication."""
import os
os.environ['PYBAMM_DISABLE_TELEMETRY']='true'
os.environ['OMP_NUM_THREADS']='1'
import io,json,hashlib,zipfile,sys,time,argparse,subprocess
from pathlib import Path
import numpy as np
from scipy.io import loadmat
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
OUT=ROOT/'results/e66_pulse_discrimination';REC=ROOT/'results/tmp/e66_causal/receipts/e66_calibration';ARCHIVE=ROOT.parent/'project_sources/09-doi-10.5683-sp3-7jp3nm.zip'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def clean_exact_duplicates(t,i,v,T):
 if not all(np.all(np.isfinite(x)) for x in [t,i,v,T]) or np.any(np.diff(t)<0):raise ValueError("nonfinite/nonmonotonic")
 dup=np.flatnonzero(np.diff(t)==0)
 if any(np.any(x[dup]!=x[dup+1]) for x in [i,v,T]):raise ValueError("conflicting repeated timestamps")
 keep=np.r_[True,np.diff(t)>0]
 return [x[keep] for x in [t,i,v,T]],int(len(dup))

def read(which):
 spec=json.loads((OUT/'PROTOCOL.json').read_text());name=next(x for x in spec['files'] if x.endswith('_'+which+'.mat'))
 z=zipfile.ZipFile(ARCHIVE);c=zipfile.ZipFile(io.BytesIO(z.read('1-Cell Data.zip')));blob=c.read(name);m=loadmat(io.BytesIO(blob),simplify_cells=True)['meas']
 t=np.asarray(m['Time'],float);i=-np.asarray(m['Current'],float);v=np.asarray(m['Voltage'],float);T=np.asarray(m['Battery_Temp_degC'],float)
 if not all(np.all(np.isfinite(x)) for x in [t,i,v,T]) or np.any(np.diff(t)<0):raise ValueError('invalidclock/nonfinite')
 dup=np.flatnonzero(np.diff(t)==0);conflict=dup[np.logical_or.reduce([x[dup]!=x[dup+1] for x in [i,v,T]])];conflict_times=t[conflict].copy()
 first=np.r_[True,np.diff(t)>0];last=np.r_[np.diff(t)>0,True]
 tf=t[first];i_first=i[first];i_last=i[last]
 qdiff=np.r_[0,np.cumsum(((i_first[1:]+i_first[:-1])-(i_last[1:]+i_last[:-1]))*.5*np.diff(tf)/3600)]
 soc_ambiguity=float(np.max(abs(qdiff))/61.259778569358865)
 removed=len(dup);t,i,v,T=[x[first] for x in [t,i,v,T]]
 return t,i,v,T,{'source':name,'sha256':hashlib.sha256(blob).hexdigest(),'samples':len(t),'duplicate_rows_collapsed':removed,'conflicting_timestamps':len(conflict),'SOC_first_last_sensitivity_max_fraction':soc_ambiguity,'_conflict_times':conflict_times,'duration_s':float(t[-1]-t[0])}
def extract(which):
 t,i,v,T,meta=read(which);active=np.abs(i)>5;starts=np.flatnonzero(np.diff(active.astype(int),prepend=0)==1);ends=np.flatnonzero(np.diff(active.astype(int),append=0)==-1)
 q=np.r_[0,np.cumsum((i[1:]+i[:-1])*.5*np.diff(t)/3600)];pulses=[];candidates=0;conflicts=meta.pop("_conflict_times");excluded=0
 for a,b in zip(starts,ends):
  if a==0 or b+1>=len(t):continue
  current=float(np.median(i[a:b+1]));duration=float(t[b+1]-t[a]);soc=float(1-q[a]/61.259778569358865)
  if current<=5 or not .2<=soc<=.8:continue
  if which=='HPPC' and not(55<=current<=75 and 8<=duration<=12):continue
  if which=='GITT' and duration<60:continue
  candidates+=1;pre=a-1
  while pre>0 and abs(i[pre-1])<=1:pre-=1
  post=b+1
  while post+1<len(t) and abs(i[post+1])<=1:post+=1
  before=t[a-1]-t[pre];after=t[post]-t[b+1]
  if before<300 or after<60:continue
  if np.any((conflicts>=t[a]-300)&(conflicts<=min(t[post],t[b+1]+300))):excluded+=1;continue
  base=float(np.median(v[(t>=t[a]-5)&(t<t[a])]))
  rel=t[a:post+1]-t[a];vv=v[a:post+1]-base;last=min(300,float(after));end=duration+last
  grid=np.unique(np.r_[np.linspace(0,duration,100),duration+np.array([.1,1,5,10,30,60,120,300])]);grid=grid[(grid<=end)&(grid>=0)]
  val=np.interp(grid,rel,vv);at=lambda sec:float(np.interp(sec,rel,vv)) if sec<=rel[-1] else None
  drop=-at(min(duration-.1,10));recovery={str(s):at(duration+s) for s in [1,30,60,300] if s<=after}
  features={'index':len(pulses),'start_time_s':float(t[a]),'duration_s':duration,'current_A':current,'soc_proxy':soc,'initial_T_C':float(T[a]),'pre_rest_s':float(before),'post_rest_s':float(after),'available_post_s':last,'apparent_R_1s_ohm':-at(1)/current,'apparent_R_10s_ohm':drop/current,'relaxation_deltaV_after_s':recovery,'recovery_fraction_60s':(at(duration+60)+drop)/drop if drop>0 else None,'pre_rest_last60s_voltage_range_V':float(np.ptp(v[(t>=t[a]-60)&(t<t[a])])),'max_selected_dt_s':float(np.max(np.diff(t[a:post+1])))}
  pulses.append((features,grid,val));
  if len(pulses)==8:break
 meta.update(eligible_after_filter=len(pulses),current_duration_soc_candidates_encountered=candidates,pulses_excluded_conflicting_clock=excluded,selection='first8eligiblechronological',independent_cells=1)
 return pulses,meta

def solve(pulse,candidate,mesh=20):
 import pybamm
 f,grid,actual=pulse;fit=json.loads((REC/'FIT_RESULT.json').read_text());p=pybamm.ParameterValues('Chen2020');p.set_initial_stoichiometries(f['soc_proxy'],inplace=True)
 fn=p['Positive electrode OCP [V]'];a,b,r=fit['parameters']
 def corrected(sto):return fn(sto)+a+b*(sto-.5)
 dur=f['duration_s'];end=dur+f['available_post_s'];current=f['current_A']/(fit['effective_capacity_Ah']/5)
 p.update({'Positive electrode OCP [V]':corrected,'Contact resistance [Ohm]':r,'Initial temperature [K]':f['initial_T_C']+273.15,'Ambient temperature [K]':f['initial_T_C']+273.15,'Lower voltage cut-off [V]':2.5,'Upper voltage cut-off [V]':4.5,'Current function [A]':pybamm.Interpolant(np.array([0.,dur-.001,dur,end]),np.array([current,current,0.,0.]),pybamm.t)})
 if candidate=='kinetics_both_x2':
  for side in ['Negative','Positive']:
   key=side+' electrode exchange-current density [A.m-2]';fun=p[key]
   def doubled(c_e,c_s_surf,c_s_max,T,fun=fun):return 2*fun(c_e,c_s_surf,c_s_max,T)
   p.update({key:doubled})
 if candidate=='diffusivity_both_x2':
  for side in ['Negative','Positive']:
   key=side+' particle diffusivity [m2.s-1]';p.update({key:2*p[key]})
 m=pybamm.lithium_ion.SPMe(options={'thermal':'isothermal','contact resistance':'true'})
 sim=pybamm.Simulation(m,parameter_values=p,var_pts={k:mesh for k in ['x_n','x_s','x_p','r_n','r_p']},solver=pybamm.IDAKLUSolver(rtol=1e-7,atol=1e-8));sol=sim.solve([0,end]);good=grid<=float(sol.t[-1]);gg=grid[good]
 ocv=float(np.asarray(sol['Battery open-circuit voltage [V]'](0)).reshape(-1)[0]);model=np.asarray(sol['Voltage [V]'](gg)).reshape(-1)-ocv;error=model-actual[good]
 def rm(mask):return float(np.sqrt(np.mean(error[mask]**2))) if np.any(mask) else None
 return {'status':'COMPLETED','candidate':candidate,'mesh':mesh,'pulse':f,'RMSE_deltaV_V':rm(np.ones(len(gg),bool)),'RMSE_loaded_V':rm(gg<dur-.1),'RMSE_rest_V':rm(gg>dur),'coverage':float(sol.t[-1])/end,'model_deltas':model.tolist(),'model_times_s':gg.tolist(),'warning':'initialuniformSOC inferredfromcoulombcount; measuredpre-restbaseline subtracted, notOCVfit; remainingpolarizationunknown'}

def run(which):
 protocol=json.loads((OUT/'PROTOCOL.json').read_text())
 if sha(ARCHIVE)!=protocol['outer_sha256']:raise ValueError('archivehash')
 # Candidate/algorithm freeze before reading new-session GITT outcomes.
 freeze={'protocol_sha256':sha(OUT/'PROTOCOL.json'),'script_sha256':sha(__file__),'fit_sha256':sha(REC/'FIT_RESULT.json'),'candidates':protocol['candidates'],'no_parameter_fit':True,'GITT_scope':'empiricalrelaxationaudit only; notpredictionvalidation unlessactuallysimulated'}
 fp=OUT/'CANDIDATE_FREEZE.json'
 if fp.exists() and json.loads(fp.read_text())!=freeze:raise ValueError('freeze drift')
 if not fp.exists():dump(fp,freeze)
 pulses,meta=extract(which);dump(OUT/f'{which}_EMPIRICAL.json',{'metadata':meta,'pulses':[x[0] for x in pulses]})
 if which=='GITT':print(json.dumps(meta));return
 jobs=[(k,c,20) for k in range(len(pulses)) for c in protocol['candidates']]
 if pulses:jobs += [(len(pulses)//2,c,40) for c in protocol['candidates']]
 rows=[]
 for k,c,mesh in jobs:
  path=OUT/f'pulse{k}_{c}_{mesh}.json'
  if path.exists():r=json.loads(path.read_text())
  else:
   start=time.monotonic()
   try:
    q=subprocess.run([sys.executable,__file__,'worker','--index',str(k),'--candidate',c,'--mesh',str(mesh)],capture_output=True,text=True,timeout=60,cwd=ROOT)
    (OUT/f'pulse{k}_{c}_{mesh}.log').write_text(q.stderr)
    if q.returncode:raise RuntimeError(q.stderr[-500:])
    r=json.loads(q.stdout);r['elapsed_s']=time.monotonic()-start
   except subprocess.TimeoutExpired:r={'status':'TIMEOUT','index':k,'candidate':c,'mesh':mesh}
   except Exception as e:r={'status':'ERROR','index':k,'candidate':c,'mesh':mesh,'error':str(e)}
   r['freeze_sha256']=sha(fp);dump(path,r)
  if r.get('freeze_sha256')!=sha(fp):raise ValueError('checkpointdrift')
  rows.append(r);dump(OUT/'HPPC_RESULTS.json',{'metadata':meta,'results':rows,'new_fitted_parameters':0});print(k,c,mesh,r['status'],r.get('RMSE_deltaV_V'),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['HPPC','GITT','worker']);p.add_argument('--index',type=int);p.add_argument('--candidate');p.add_argument('--mesh',type=int,default=20);a=p.parse_args()
 if a.mode=='worker':print(json.dumps(solve(extract('HPPC')[0][a.index],a.candidate,a.mesh),allow_nan=False))
 else:run(a.mode)
