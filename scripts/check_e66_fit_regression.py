import json,sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import calibrate_e66_kinetics as c

def worker(index):
 from unittest.mock import patch
 f=json.loads((c.OUT/'GENERATOR_B_FREEZE.json').read_text());get=c.get_inputs
 spec=json.loads((c.REC/'PROSPECTIVE.json').read_text())
 def training(archive,names):return get(archive,[spec['fit'][index]])
 with patch.object(c,'get_inputs',training):r=c.simulate(f['k'],'DISCHARGE',index)
 r['dataset']='C20_C3_DEVELOPMENT_REGRESSION';return r
if __name__=='__main__':
 if len(sys.argv)>1:print(json.dumps(worker(int(sys.argv[1]))))
 else:
  f=json.loads((c.OUT/'GENERATOR_B_FREEZE.json').read_text())
  if f['signature']!=c.signature():raise ValueError('freeze drift')
  rows=[]
  for i in range(2):
   try:
    p=subprocess.run([sys.executable,__file__,str(i)],capture_output=True,text=True,timeout=90)
    if p.returncode:raise RuntimeError(p.stderr[-1200:])
    r=json.loads(p.stdout)
   except Exception as e:r={'status':'ERROR','index':i,'error':str(e)}
   rows.append(r);c.dump(c.OUT/'FIT_REGRESSION.json',{'freeze_sha256':c.sha(c.OUT/'GENERATOR_B_FREEZE.json'),'results':rows});print(i,r['status'],r.get('RMSE_V'),flush=True)
