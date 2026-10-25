"""Numerical inventory/bounds controls of virtual Chen-derived candidate."""
import json,sys,subprocess
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import calibrate_e66_kinetics as c

def worker(soc):
 import pybamm
 k=json.loads((c.OUT/'GENERATOR_B_FREEZE.json').read_text())['k'];p=c.params(k,soc,25);I=65/(61.259778569358865/5)
 p.update({'Current function [A]':pybamm.Interpolant(np.array([0,9.999,10,310]),np.array([I,I,0,0]),pybamm.t)})
 sim=pybamm.Simulation(pybamm.lithium_ion.SPMe(options={'thermal':'isothermal','contact resistance':'true'}),parameter_values=p,var_pts={key:40 for key in ['x_n','x_s','x_p','r_n','r_p']},solver=pybamm.IDAKLUSolver(rtol=1e-7,atol=1e-8));s=sim.solve([0,310]);t=np.unique(np.r_[np.linspace(0,310,500),9.999,10]);li=np.asarray(s['Total lithium [mol]'](t));relative=float(np.max(abs(li-li.flat[0]))/abs(li.flat[0]));q=float(s['Discharge capacity [A.h]'](310));expected=I*9.9995/3600;bounds={}
 for side in ['Negative','Positive']:
  a=np.asarray(s[side+' particle stoichiometry'].entries);bounds[side]=[float(np.min(a)),float(np.max(a))]
 finite=bool(np.all(np.isfinite(s['Voltage [V]'](t))))
 return {'status':'COMPLETED','soc':soc,'relative_lithium_drift':relative,'discharge_capacity_error_Ah':q-expected,'stoichiometry_bounds':bounds,'finite_voltage':finite,'gate':'PASS' if relative<=1e-6 and abs(q-expected)<=1e-6 and finite and all(a>=-1e-8 and b<=1+1e-8 for a,b in bounds.values()) else 'FAIL'}
if __name__=='__main__':
 if len(sys.argv)>1:print(json.dumps(worker(float(sys.argv[1]))))
 else:
  f=json.loads((c.OUT/'GENERATOR_B_FREEZE.json').read_text())
  if f['signature']!=c.signature():raise ValueError('freeze drift')
  rows=[]
  for soc in [.2,.6,.8]:
   try:
    p=subprocess.run([sys.executable,__file__,str(soc)],capture_output=True,text=True,timeout=90)
    if p.returncode:raise RuntimeError(p.stderr[-1000:])
    r=json.loads(p.stdout)
   except Exception as e:r={'status':'ERROR','soc':soc,'error':str(e)}
   rows.append(r);c.dump(c.OUT/'INVENTORY_CONTROLS.json',{'scope':'virtual model numerical conservation, not measured E66 lithium inventory or thermal balance','freeze_sha256':c.sha(c.OUT/'GENERATOR_B_FREEZE.json'),'results':rows});print(soc,r,flush=True)
