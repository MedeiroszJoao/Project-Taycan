"""Development-only MCCC diagnostic. Frozen B is never modified."""
import sys,json
import numpy as np
from scipy.optimize import brentq
from scripts import e66_module_observation_adapter as a
m=a.m; OUT=m.ROOT/'results/e66_b2_development'
NAME='20240314_1C_Test (MCCC).mat'
def data():
 a.FILES=[NAME];d=a.data(0);t=d['RecordingTime'];I=d['AVL_Current']
 starts=[j-5 for j in range(65,len(I)-1800) if I[j]>10 and np.all(abs(I[j-65:j-5])<=1) and np.max(I[j:j+10])>.8*132 and np.mean(I[j:j+30]>10)>=.9]
 if not starts:raise ValueError('no eligible onset')
 start=starts[0];ix=np.flatnonzero((t>=t[start])&(t<=t[start]+1800))
 if len(ix)<1801:raise ValueError('incomplete window')
 T=float(np.mean([d[k][start-5:start] for k in m.THERM]));v0=float(np.mean(d['BMS_Voltage'][start-5:start])/6);z=brentq(lambda z:m.ocv(z,T)-v0,0,1)
 return t[ix]-t[start],I[ix],d['AVL_Voltage'][ix],z,T,d['source_sha256'],float(t[start])
def run(q):
 import pybamm
 t,I,actual,z,T,sha,start=data();p=m.parameters(z,T)
 p.update({'Current function [A]':pybamm.Interpolant(t,-I/2/(q/5),pybamm.t)})
 g,v,_,coverage,term=m.c.run_model(p,np.arange(1801.),'SPMe',40)
 f=json.loads((a.OUT/'ADAPTER_FREEZE.json').read_text());pred=6*v+f['offset_V']+f['R_effective_ohm']*np.interp(g,t,I);err=(pred-np.interp(g,t,actual))/6
 row=dict(capacity_Ah=q,source_sha256=sha,start_s=start,initial_SOC=z,temperature_C=T,RMSE_V=float(np.sqrt(np.mean(err**2))),max_error_V=float(np.max(abs(err))),coverage=coverage,termination=term,segments=[float(np.sqrt(np.mean(err[(g>=k)&(g<k+300)]**2))) for k in range(0,1800,300)],times_s=g.tolist(),prediction_AVL_V=pred.tolist())
 (OUT/f'capacity_{q}.json').write_text(json.dumps(row,indent=2));print({k:v for k,v in row.items() if k not in ['times_s','prediction_AVL_V']},flush=True)
if __name__=='__main__':run(float(sys.argv[1]))
