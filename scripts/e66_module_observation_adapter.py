"""Fit only paired measurement-port relation; fixed electrochemical generator."""
import sys,json,zipfile,io,tempfile,subprocess
from pathlib import Path
import numpy as np
from scipy.optimize import brentq
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import transfer_e66_to_dev_module as m
OUT=ROOT/'results/e66_module_observation_adapter'
FILES=['20240209_0.7C_CP_Loss.mat','20240209_1C_CP_Loss.mat','20240323_1.2C_CP_Loss.mat'];RATES=[.7,1,1.2]
def select_start(I,rate):
 threshold=.8*132*rate
 for a in range(5,len(I)-25):
  if I[a]<-10 and np.all(abs(I[a-5:a])<=1) and np.min(I[a:a+12])<-threshold and np.max(I[a+8:a+25])>threshold:return a
 raise ValueError('alternating protocol not found')
def data(index):
 import matio,pandas as pd
 name=FILES[index];d=m.read(name)
 with zipfile.ZipFile(m.c.pulse.ARCHIVE) as z:
  with zipfile.ZipFile(io.BytesIO(z.read('4-Module Data.zip'))) as q:b=q.read(next(n for n in q.namelist() if Path(n).name==name))
 with tempfile.NamedTemporaryFile(suffix='.mat') as f:
  f.write(b);f.flush();a=matio.load_from_mat(f.name,raw_data=False)['meas']
 v=pd.to_numeric(a['BMS_Voltage'].flat[0].iloc[:,0],errors='coerce').to_numpy(dtype=float)
 if d['terminal_padding_removed']:v=v[:-1]
 if len(v)!=len(d['RecordingTime']) or not np.all(np.isfinite(v)):raise ValueError('BMS voltage alignment')
 d['BMS_Voltage']=v;return d

def window(index):
 d=data(index);t=d['RecordingTime'];I=d['AVL_Current'];a=select_start(I,RATES[index]);ix=np.flatnonzero((t>=t[a])&(t<=t[a]+300))
 if t[ix[-1]]-t[a]<300 or np.max(np.diff(t[ix]))>2:raise ValueError('incomplete window')
 T=float(np.nanmean([d[k][a-5:a] for k in m.THERM if k in d]));v0=float(np.mean(d['BMS_Voltage'][a-5:a])/6);soc=brentq(lambda s:m.ocv(s,T)-v0,0,1,xtol=1e-10)
 meta={'name':FILES[index],'source_sha256':d['source_sha256'],'activation_time_s':float(t[a]),'initial_SOC_from_BMS_voltage':soc,'initial_cell4_mean_surface_temperature_C':T,'initial_BMS_mean_cell_voltage_V':v0,'initial_AVL_mean_cell_voltage_V':float(np.mean(d['AVL_Voltage'][a-5:a])/6),'module_AVL_current_range_A':[float(np.min(I[ix])),float(np.max(I[ix]))]}
 return t[ix]-t[a],I[ix],d['AVL_Voltage'][ix],d['BMS_Voltage'][ix],meta

def signature():return {'script_sha256':m.c.sha(__file__),'protocol_sha256':m.c.sha(OUT/'PROTOCOL.json'),'cell_freeze_sha256':m.c.sha(m.o.OUT/'GENERATOR_B_FREEZE.json'),'module_interface_script_sha256':m.c.sha(m.__file__)}
def fit():
 if (OUT/'ADAPTER_FREEZE.json').exists():raise ValueError('existing freeze')
 t,I,va,vb,meta=window(0);beta=np.linalg.lstsq(np.column_stack([np.ones(len(I)),I]),va-vb,rcond=None)[0]
 if abs(beta[0])>.5 or not 0<=beta[1]<=.02:raise ValueError('adapter outside bounds')
 m.c.dump(OUT/'ADAPTER_FREEZE.json',{'signature':signature(),'offset_V':float(beta[0]),'R_effective_ohm':float(beta[1]),'fit_metadata':meta,'fit_rows':len(I),'fit_observables':'paired measured AVL-BMS voltage and current only; no B model residuals','exposure':'exploratory development files','before_new_predictions':True})
def solve(index,kind):
 import pybamm
 f=json.loads((OUT/'ADAPTER_FREEZE.json').read_text());t,I,va,vb,meta=window(index);p=m.parameters(meta['initial_SOC_from_BMS_voltage'],meta['initial_cell4_mean_surface_temperature_C']);p.update({'Current function [A]':pybamm.Interpolant(t,-I/2/(61.259778569358865/5),pybamm.t)})
 g,v,_,coverage,term=m.c.run_model(p,np.linspace(0,t[-1],301),kind,40);ii=np.interp(g,t,I);pred_avl=6*v+f['offset_V']+f['R_effective_ohm']*ii;e=(pred_avl-np.interp(g,t,va))/6;eb=v-np.interp(g,t,vb)/6;q=np.r_[0,np.cumsum((I[1:]+I[:-1])*.5*np.diff(t)/3600)];soc=meta['initial_SOC_from_BMS_voltage']+q/(2*61.259778569358865)
 rm=float(np.sqrt(np.mean(e*e)));mx=float(np.max(abs(e)));domain=bool(np.min(soc)>=0 and np.max(soc)<=1)
 return {'status':'COMPLETED','name':FILES[index],'index':index,'model':kind,'metadata':meta,'AVL_RMSE_V_per_mean_cell':rm,'AVL_max_error_V_per_mean_cell':mx,'BMS_RMSE_V_per_mean_cell':float(np.sqrt(np.mean(eb*eb))),'coverage':coverage,'coulomb_SOC_range':[float(np.min(soc)),float(np.max(soc))],'nominal_SOC_domain_gate':'PASS' if domain else 'FAIL','gate':'PASS' if rm<=.05 and mx<=.15 and coverage>=.95 and domain else 'FAIL','termination':term,'model_times_s':g.tolist(),'predicted_BMS_module_V':(6*v).tolist(),'predicted_AVL_module_V':pred_avl.tolist()}
def run():
 f=json.loads((OUT/'ADAPTER_FREEZE.json').read_text())
 if f['signature']!=signature():raise ValueError('freeze drift')
 rows=[]
 for i in range(3):
  for kind in ['SPMe','DFN']:
   try:
    p=subprocess.run([sys.executable,__file__,'worker',str(i),kind],capture_output=True,text=True,timeout=90)
    if p.returncode:raise RuntimeError(p.stderr[-1200:])
    r=json.loads(p.stdout)
   except Exception as e:r={'status':'ERROR_OR_INELIGIBLE','index':i,'name':FILES[i],'model':kind,'error':str(e)}
   rows.append(r);m.c.dump(OUT/'EVALUATION.json',{'freeze_sha256':m.c.sha(OUT/'ADAPTER_FREEZE.json'),'results':rows,'reserved_numeric_access':0});print(i,kind,r['status'],r.get('AVL_RMSE_V_per_mean_cell'),r.get('gate'),flush=True)
if __name__=='__main__':
 if sys.argv[1]=='fit':fit()
 elif sys.argv[1]=='run':run()
 elif sys.argv[1]=='worker':print(json.dumps(solve(int(sys.argv[2]),sys.argv[3])))
