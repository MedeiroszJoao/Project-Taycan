"""Declared nuisance perturbations of fixed kinetic candidate; no fitting."""
import json,sys,subprocess,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import calibrate_e66_kinetics as c
OUT=c.OUT

def main():
 f=json.loads((OUT/'GENERATOR_B_FREEZE.json').read_text())
 if f['signature']!=c.signature() or f['fit_sha256']!=c.sha(OUT/'FIT_RESULT.json'):raise ValueError('freeze drift')
 rows=[]
 for ds,dt in [(-.02,0),(.02,0),(0,-5),(0,5)]:
  path=OUT/f'stress_soc{ds}_T{dt}.json'
  try:
   r=subprocess.run([sys.executable,__file__,'worker',str(ds),str(dt)],capture_output=True,text=True,timeout=90)
   if r.returncode:raise RuntimeError(r.stderr[-1000:])
   row=json.loads(r.stdout)
  except Exception as e:row={'status':'ERROR','error':str(e)}
  row.update(soc_shift=ds,T_shift_K=dt);c.dump(path,row);rows.append(row);print(ds,dt,row['status'],row.get('RMSE_V'),flush=True)
 c.dump(OUT/'PHYSICAL_STRESS.json',{'freeze_sha256':c.sha(OUT/'GENERATOR_B_FREEZE.json'),'protocol_sha256':c.sha(OUT/'ADVERSARIAL_PROTOCOL.json'),'results':rows})

if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='worker':
  ds,dt=map(float,sys.argv[2:]);fn=c.params
  def changed(k,soc,T):return fn(k,soc+ds,T+dt)
  c.params=changed;f=json.loads((OUT/'GENERATOR_B_FREEZE.json').read_text());print(json.dumps(c.simulate(f['k'],'GITT',0)))
 else:main()
