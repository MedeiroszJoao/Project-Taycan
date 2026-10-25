"""Post-result reference control: original k=1, no tuning, original fit curves."""
import json,sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import calibrate_e66_kinetics as c
from unittest.mock import patch

def worker(i):
 spec=json.loads((c.REC/'PROSPECTIVE.json').read_text());get=c.get_inputs
 with patch.object(c,'get_inputs',lambda archive,names:get(archive,[spec['fit'][i]])):
  r=c.simulate(1,'DISCHARGE',i)
 r['dataset']='BASELINE_C20_C3_REFERENCE';return r
if __name__=='__main__':
 if len(sys.argv)>1:print(json.dumps(worker(int(sys.argv[1]))))
 else:
  rows=[]
  for i in range(2):
   try:
    p=subprocess.run([sys.executable,__file__,str(i)],capture_output=True,text=True,timeout=90)
    if p.returncode:raise RuntimeError(p.stderr[-1000:])
    r=json.loads(p.stdout)
   except Exception as e:r={'status':'ERROR','index':i,'error':str(e)}
   rows.append(r);c.dump(c.OUT/'BASELINE_FIT_REFERENCE.json',{'scope':'post-result original-k reference, not preregistered success evidence','results':rows});print(i,r['status'],r.get('RMSE_V'),r.get('max_error_V'),flush=True)
