"""Development-derived endpoint offset, with re-initialization; exploratory only."""
import json,sys
import numpy as np
from scipy.optimize import brentq
from scripts import e66_b2_development as b

def run(q):
 import pybamm
 anchors=json.loads((b.OUT/'RELAXED_ANCHORS.json').read_text())['results']
 anchor=next(r for r in anchors if r['name']==b.NAME)['anchors'][0]
 delta=anchor['BMS_tail_V']-b.m.ocv(1,anchor['temperature_C'])
 t,I,actual,z,T,sha,start=b.data();v0=b.m.ocv(z,T)
 z=brentq(lambda z:b.m.ocv(z,T)+delta-v0,0,1)
 p=b.m.parameters(z,T);fn=p['Positive electrode OCP [V]']
 p.update({'Positive electrode OCP [V]':lambda sto:fn(sto)+delta,'Current function [A]':pybamm.Interpolant(t,-I/2/(q/5),pybamm.t)})
 g,v,_,coverage,term=b.m.c.run_model(p,np.arange(1801.),'SPMe',40)
 f=json.loads((b.a.OUT/'ADAPTER_FREEZE.json').read_text());pred=6*v+f['offset_V']+f['R_effective_ohm']*np.interp(g,t,I);err=(pred-np.interp(g,t,actual))/6
 row=dict(q=q,delta_V=delta,initial_SOC=z,RMSE_V=float(np.sqrt(np.mean(err**2))),max_error_V=float(np.max(abs(err))),coverage=coverage,termination=term,development_only=True,not_validated=True)
 (b.OUT/f'endpoint_probe_{q}.json').write_text(json.dumps(row,indent=2));print(row)
if __name__=='__main__':run(float(sys.argv[1]))
