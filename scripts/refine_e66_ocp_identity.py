import sys,json,subprocess
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import calibrate_e66_kinetics as c
from scripts import recalibrate_e66_ocp_offset as o

def fine(p,grid,kind,mesh):
 import pybamm
 m=getattr(pybamm.lithium_ion,kind)(options={'thermal':'isothermal','contact resistance':'true'})
 s=pybamm.Simulation(m,parameter_values=p,var_pts={key:mesh for key in ['x_n','x_s','x_p','r_n','r_p']},solver=pybamm.IDAKLUSolver(rtol=1e-9,atol=1e-10)).solve([0,float(grid[-1])]);g=grid[grid<=s.t[-1]]
 return g,np.asarray(s['Voltage [V]'](g)).reshape(-1),float(np.asarray(s['Battery open-circuit voltage [V]'](0)).reshape(-1)[0]),float(s.t[-1])/float(grid[-1]),str(s.termination)
if __name__=='__main__':
 f=json.loads((o.OUT/'GENERATOR_B_FREEZE.json').read_text())
 if f['signature']!=o.signature():raise ValueError('freeze drift')
 if len(sys.argv)>1:
  c.run_model=fine;r=c.simulate(f['parent_k'],'DISCHARGE',1,'DFN') if sys.argv[1]=='parent' else o.worker('DISCHARGE',1,'DFN');print(json.dumps(r))
 else:
  rows={}
  for mode in ['parent','corrected']:
   try:
    p=subprocess.run([sys.executable,__file__,mode],capture_output=True,text=True,timeout=90)
    if p.returncode:raise RuntimeError(p.stderr[-1000:])
    r=json.loads(p.stdout)
   except Exception as e:r={'status':'ERROR','error':str(e)}
   rows[mode]=r;c.dump(o.OUT/'TIGHT_IDENTITY_SOLVES.json',rows);print(mode,r['status'],flush=True)
  if all(r['status']=='COMPLETED' for r in rows.values()):
   a,b=rows['parent'],rows['corrected'];gap=float(np.max(abs(np.array(b['model_V'])-a['model_V']-f['additive_ocp_offset_V'])));out={'max_identity_gap_V':gap,'gate':'PASS' if gap<=1e-6 else 'FAIL','rtol':1e-9,'atol':1e-10,'original_loose_identity_gate':'FAIL','corrected_voltage_gate':b['gate']}
  else:out={'gate':'INCONCLUSIVE','original_loose_identity_gate':'FAIL'}
  c.dump(o.OUT/'TIGHT_IDENTITY_VERDICT.json',out);print(out)
