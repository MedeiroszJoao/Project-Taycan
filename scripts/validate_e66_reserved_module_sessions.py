"""Explicitly released two-session validation. Four final blind files prohibited."""
import os,sys,json,zipfile,io,tempfile,subprocess,hashlib
from pathlib import Path
import numpy as np
from scipy.optimize import brentq
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import e66_module_observation_adapter as a
m=a.m;OUT=ROOT/'results/e66_module_reserved_validation';FILES=['20240207_1.5C_CP_Loss.mat','20240313_1.5C_Test (MCCC).mat']
def select_charge(I):
 for j in range(65,len(I)-30):
  if I[j]>10 and np.all(abs(I[j-65:j-5])<=1) and np.max(I[j:j+10])>.8*198 and np.mean(I[j:j+30]>10)>=.9:return j-5
 raise ValueError('qualified MCCC onset not found')
def read(name):
 if name not in FILES:raise ValueError('outside explicit validation allowlist')
 import matio,pandas as pd
 with zipfile.ZipFile(m.c.pulse.ARCHIVE) as z:raw=z.read('4-Module Data.zip')
 if hashlib.sha256(raw).hexdigest()!='a5628a9d56d2e097158620346c3f69b5ff5c6269bb2770f643e91f397abcac7e':raise ValueError('archivehash')
 with zipfile.ZipFile(io.BytesIO(raw)) as z:b=z.read(next(n for n in z.namelist() if Path(n).name==name))
 with tempfile.NamedTemporaryFile(suffix='.mat') as f:
  f.write(b);f.flush();s=matio.load_from_mat(f.name,raw_data=False)['meas']
 keys=m.FIELDS+m.THERM+['BMS_Voltage'];tables={k:s[k].flat[0] for k in keys if k in s.dtype.names};base=tables['RecordingTime']
 if any(not isinstance(v,pd.DataFrame) or len(v)!=len(base) or not v.index.equals(base.index) or v.shape[1]!=1 for v in tables.values()):raise ValueError('unaligned tables')
 d={k:pd.to_numeric(v.iloc[:,0],errors='coerce').to_numpy(dtype=float) for k,v in tables.items()};d,removed=m.trim_terminal_padding(d)
 if any(not np.all(np.isfinite(d[k])) for k in m.FIELDS+['BMS_Voltage']) or np.any(np.diff(d['RecordingTime'])<=0):raise ValueError('nonfinite/clock')
 d['source_sha256']=hashlib.sha256(b).hexdigest();d['terminal_padding_removed']=removed;return d

def window(index):
 d=read(FILES[index]);t=d['RecordingTime'];I=d['AVL_Current'];start=a.select_start(I,1.5) if index==0 else select_charge(I);ix=np.flatnonzero((t>=t[start])&(t<=t[start]+300))
 if start<5 or np.any(abs(I[start-5:start])>1) or t[ix[-1]]-t[start]<300 or np.max(np.diff(t[ix]))>2:raise ValueError('invalid precondition/window')
 T=float(np.nanmean([d[k][start-5:start] for k in m.THERM if k in d]));v0=float(np.mean(d['BMS_Voltage'][start-5:start])/6)
 if not np.isfinite(T):raise ValueError('missing temperature')
 soc=brentq(lambda z:m.ocv(z,T)-v0,0,1,xtol=1e-10);meta={'name':FILES[index],'sha256':d['source_sha256'],'rows':len(t),'terminal_padding_removed':d['terminal_padding_removed'],'window_start_s':float(t[start]),'initial_SOC':soc,'initial_cell4_surface_temperature_C':T,'initial_BMS_mean_cell_voltage_V':v0,'module_AVL_current_range_A':[float(np.min(I[ix])),float(np.max(I[ix]))],'cell4_surface_temperature_range_C':[float(np.nanmin([d[k][ix] for k in m.THERM if k in d])),float(np.nanmax([d[k][ix] for k in m.THERM if k in d]))]}
 return t[ix]-t[start],I[ix],d['AVL_Voltage'][ix],d['BMS_Voltage'][ix],meta

def signature():return {'script_sha256':m.c.sha(__file__),'protocol_sha256':m.c.sha(OUT/'PROTOCOL.json'),'adapter_freeze_sha256':m.c.sha(a.OUT/'ADAPTER_FREEZE.json'),'adapter_script_sha256':m.c.sha(a.__file__),'cell_freeze_sha256':m.c.sha(m.o.OUT/'GENERATOR_B_FREEZE.json'),'module_script_sha256':m.c.sha(m.__file__),'validation_allowlist':FILES}
def guards():
 if json.loads((OUT/'VALIDATION_FREEZE.json').read_text())!=signature():raise ValueError('validation freeze drift')
 if json.loads((a.OUT/'ADAPTER_FREEZE.json').read_text())['signature']!=a.signature():raise ValueError('adapter drift')
 if json.loads((m.o.OUT/'GENERATOR_B_FREEZE.json').read_text())['signature']!=m.o.signature():raise ValueError('cell drift')
def solve(i,kind,mesh):
 import pybamm
 guards();f=json.loads((a.OUT/'ADAPTER_FREEZE.json').read_text());t,I,va,vb,meta=window(i);p=m.parameters(meta['initial_SOC'],meta['initial_cell4_surface_temperature_C']);p.update({'Current function [A]':pybamm.Interpolant(t,-I/2/(61.259778569358865/5),pybamm.t)})
 g,v,_,coverage,term=m.c.run_model(p,np.linspace(0,t[-1],301),kind,mesh);pred=6*v+f['offset_V']+f['R_effective_ohm']*np.interp(g,t,I);e=(pred-np.interp(g,t,va))/6;eb=v-np.interp(g,t,vb)/6;q=np.r_[0,np.cumsum((I[1:]+I[:-1])*.5*np.diff(t)/3600)];soc=meta['initial_SOC']+q/(2*61.259778569358865);rm=float(np.sqrt(np.mean(e*e)));mx=float(np.max(abs(e)));domain=bool(np.min(soc)>=0 and np.max(soc)<=1)
 return {'status':'COMPLETED','index':i,'name':FILES[i],'model':kind,'mesh':mesh,'metadata':meta,'AVL_RMSE_V_per_mean_cell':rm,'AVL_max_error_V_per_mean_cell':mx,'BMS_RMSE_V_per_mean_cell':float(np.sqrt(np.mean(eb*eb))),'coverage':coverage,'coulomb_SOC_range':[float(np.min(soc)),float(np.max(soc))],'gate':'PASS' if rm<=.05 and mx<=.15 and coverage>=.95 and domain else 'FAIL','termination':term,'model_times_s':g.tolist(),'predicted_AVL_module_V':pred.tolist(),'predicted_BMS_module_V':(6*v).tolist()}
def run():
 guards();rows=[]
 for i,kind,mesh in [(i,k,40) for i in range(2) for k in ['SPMe','DFN']]+[(0,'SPMe',80),(1,'SPMe',80)]:
  try:
   p=subprocess.run([sys.executable,__file__,'worker',str(i),kind,str(mesh)],capture_output=True,text=True,timeout=120 if mesh==80 else 90)
   (OUT/f'{i}_{kind}_{mesh}.log').write_text(p.stderr)
   if p.returncode:raise RuntimeError(p.stderr[-1600:])
   r=json.loads(p.stdout)
  except Exception as e:r={'status':'ERROR_OR_INELIGIBLE','index':i,'name':FILES[i],'model':kind,'mesh':mesh,'error':str(e)}
  rows.append(r);m.c.dump(OUT/'EVALUATION.json',{'freeze_sha256':m.c.sha(OUT/'VALIDATION_FREEZE.json'),'results':rows,'final_blind_files_numeric_access':0,'historical_reserved_access':0,'validation_files_numeric_access':len({x['name'] for x in rows})});print(i,kind,mesh,r['status'],r.get('AVL_RMSE_V_per_mean_cell'),r.get('gate'),flush=True)
if __name__=='__main__':
 if sys.argv[1]=='freeze':m.c.dump(OUT/'VALIDATION_FREEZE.json',signature())
 elif sys.argv[1]=='run':run()
 elif sys.argv[1]=='worker':print(json.dumps(solve(int(sys.argv[2]),sys.argv[3],int(sys.argv[4]))))
