import json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import recalibrate_e66_ocp_offset as o
from scripts import calibrate_e66_kinetics as c
f=json.loads((o.OUT/'GENERATOR_B_FREEZE.json').read_text())
assert f['signature']==o.signature()
spec=json.loads((c.REC/'PROSPECTIVE.json').read_text());data=c.get_inputs(c.pulse.ARCHIVE,spec['fit']+spec['evaluation']);rows=[]
for r in json.loads((o.OUT/'EVALUATION.json').read_text())['results']:
 if r['status']!='COMPLETED':rows.append({'dataset':r['dataset'],'status':'ERROR'});continue
 t=np.asarray(r['model_times_s']);pred=np.asarray(r['model_V'])
 if r['dataset'] in ['TRAIN','DISCHARGE']:
  d=data[r['index']+(2 if r['dataset']=='DISCHARGE' else 0)];actual=np.interp(t,d['t'],d['v'])
 else:
  _,grid,v=c.pulse.extract(r['dataset'])[0][r['index']];actual=np.interp(t,grid,v)
 e=pred-actual;rmse=float(np.sqrt(np.mean(e*e)));maximum=float(np.max(abs(e)))
 assert abs(rmse-r['RMSE_V'])<1e-10 and abs(maximum-r['max_error_V'])<1e-10
 stress=[]
 for b in [-.005,.005]:stress.append({'bias_V':b,'RMSE_V':float(np.sqrt(np.mean((e-b)**2))),'max_error_V':float(np.max(abs(e-b)))})
 timing=[]
 for delay in [-.1,.1]:
  shifted=t+delay;mask=(shifted>=t[0])&(shifted<=t[-1]);er=pred[mask]-np.interp(shifted[mask],t,actual);timing.append({'delay_s':delay,'RMSE_V':float(np.sqrt(np.mean(er*er)))})
 rng=np.random.default_rng(1729);keep=rng.random(len(t))>=.2;missing=float(np.sqrt(np.mean(e[keep]**2)))
 rows.append({'dataset':r['dataset'],'index':r['index'],'model':r['model'],'RMSE_V':rmse,'max_error_V':maximum,'coverage':r['coverage'],'gate':r['gate'],'gauge_identity_max_error_V':r['gauge_identity_max_error_V'],'gauge_identity_gate':r['gauge_identity_gate'],'measurement_bias_stress':stress,'timing_stress':timing,'missing20percent_RMSE_V':missing})
assert len(rows)==8
c.dump(o.OUT/'INDEPENDENT_AUDIT.json',{'freeze_sha256':c.sha(o.OUT/'GENERATOR_B_FREEZE.json'),'results':rows,'all_voltage_and_gauge_gates_pass':all(x.get('gate')=='PASS' and x.get('gauge_identity_gate')=='PASS' for x in rows),'scientific_scope':'exploratory terminal-voltage qualification, no new independent blind data'})
print(json.dumps(rows,indent=2))
