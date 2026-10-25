"""Training-only OCP offset recalibration, explicitly exploratory follow-up."""
import sys,json,subprocess,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import calibrate_e66_kinetics as c
OUT=ROOT/'results/e66_ocp_recalibration'
def signature():return {'script_sha256':c.sha(__file__),'protocol_sha256':c.sha(OUT/'PROTOCOL.json'),'parent_freeze_sha256':c.sha(c.OUT/'GENERATOR_B_FREEZE.json'),'training_predictions_sha256':c.sha(c.OUT/'FIT_REGRESSION.json'),'parent_script_sha256':c.sha(c.__file__)}
def fit():
 if (OUT/'GENERATOR_B_FREEZE.json').exists():raise ValueError('already frozen')
 parent=json.loads((c.OUT/'GENERATOR_B_FREEZE.json').read_text())
 if parent['signature']!=c.signature():raise ValueError('parent drift')
 train=json.loads((c.OUT/'FIT_REGRESSION.json').read_text())['results']
 if len(train)!=2 or any(r['status']!='COMPLETED' or r['coverage']<.999 for r in train):raise ValueError('training incomplete')
 delta=-float(np.mean([r['bias_V'] for r in train]))
 if abs(delta)>.1:raise ValueError('offset bound')
 f={'signature':signature(),'parent_k':parent['k'],'additive_ocp_offset_V':delta,'derivation':'negative equal-curve mean of C20/C3 development residual biases','evaluation_exposure':'exploratory nonblind, predecessor evaluated before this follow-up','status':'FROZEN_RESEARCH_CANDIDATE_NOT_APPROVED','before_followup_predictions':True}
 c.dump(OUT/'GENERATOR_B_FREEZE.json',f);print(json.dumps(f))
def worker(ds,i,kind):
 from unittest.mock import patch
 f=json.loads((OUT/'GENERATOR_B_FREEZE.json').read_text());fn=c.params
 def shifted(k,soc,T):
  p=fn(k,soc,T);ocp=p['Positive electrode OCP [V]']
  def corrected(sto):return ocp(sto)+f['additive_ocp_offset_V']
  p.update({'Positive electrode OCP [V]':corrected});return p
 with patch.object(c,'params',shifted):
  if ds=='TRAIN':
   get=c.get_inputs;spec=json.loads((c.REC/'PROSPECTIVE.json').read_text())
   with patch.object(c,'get_inputs',lambda archive,names:get(archive,[spec['fit'][i]])):r=c.simulate(f['parent_k'],'DISCHARGE',i,kind)
   r['dataset']='TRAIN'
  else:r=c.simulate(f['parent_k'],ds,i,kind)
 return r

def evaluate():
 f=json.loads((OUT/'GENERATOR_B_FREEZE.json').read_text())
 if f['signature']!=signature():raise ValueError('freeze drift')
 parent=json.loads((c.OUT/'EVALUATION.json').read_text())['results'];train=json.loads((c.OUT/'FIT_REGRESSION.json').read_text())['results'];rows=[]
 jobs=[('TRAIN',i,'SPMe') for i in range(2)]+[('DISCHARGE',i,m) for i in range(2) for m in ['SPMe','DFN']]+[('HPPC',1,'SPMe'),('GITT',0,'SPMe')]
 for ds,i,m in jobs:
  try:
   p=subprocess.run([sys.executable,__file__,'worker',ds,str(i),m],capture_output=True,text=True,timeout=90)
   (OUT/f'{ds}_{i}_{m}.log').write_text(p.stderr)
   if p.returncode:raise RuntimeError(p.stderr[-1000:])
   r=json.loads(p.stdout);base=next(x for x in (train if ds=='TRAIN' else parent) if x['index']==i and x['model']==m and x['mesh']==40 and (ds=='TRAIN' or x['dataset']==ds))
   t=np.array(r['model_times_s']);expected=np.interp(t,base['model_times_s'],base['model_V'])+(f['additive_ocp_offset_V'] if ds in ['TRAIN','DISCHARGE'] else 0)
   gap=float(np.max(abs(np.array(r['model_V'])-expected)));r['gauge_identity_max_error_V']=gap;r['gauge_identity_gate']='PASS' if gap<=1e-6 else 'FAIL'
  except Exception as e:r={'status':'ERROR','dataset':ds,'index':i,'model':m,'error':str(e)}
  rows.append(r);c.dump(OUT/'EVALUATION.json',{'freeze_sha256':c.sha(OUT/'GENERATOR_B_FREEZE.json'),'results':rows});print(ds,i,m,r['status'],r.get('RMSE_V'),r.get('max_error_V'),r.get('gauge_identity_max_error_V'),flush=True)
if __name__=='__main__':
 if sys.argv[1]=='fit':fit()
 elif sys.argv[1]=='evaluate':evaluate()
 elif sys.argv[1]=='worker':print(json.dumps(worker(sys.argv[2],int(sys.argv[3]),sys.argv[4])))
