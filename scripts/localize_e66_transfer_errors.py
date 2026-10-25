import json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import calibrate_e66_kinetics as c
spec=json.loads((c.REC/'PROSPECTIVE.json').read_text());data=c.get_inputs(c.pulse.ARCHIVE,spec['fit']+spec['evaluation']);rows=[]
for filename,offset in [('FIT_REGRESSION.json',0),('BASELINE_FIT_REFERENCE.json',0),('EVALUATION.json',2)]:
 for r in json.loads((c.OUT/filename).read_text())['results']:
  if r['status']!='COMPLETED' or filename=='EVALUATION.json' and r['dataset']!='DISCHARGE':continue
  d=data[offset+r['index']];t=np.array(r['model_times_s']);error=np.array(r['model_V'])-np.interp(t,d['t'],d['v']);frac=t/d['t'][-1];j=int(np.argmax(abs(error)));bins=[]
  for lo,hi in [(0,.25),(.25,.5),(.5,.75),(.75,.9),(.9,1.00001)]:
   a=error[(frac>=lo)&(frac<hi)];bins.append({'duration_fraction':[lo,min(hi,1)],'RMSE_V':float(np.sqrt(np.mean(a*a))),'bias_V':float(np.mean(a)),'max_abs_V':float(np.max(abs(a)))})
  if abs(float(np.sqrt(np.mean(error*error)))-r['RMSE_V'])>1e-10:raise ValueError('metric mismatch')
  rows.append({'source':filename,'index':r['index'],'model':r['model'],'peak_error_duration_fraction':float(frac[j]),'peak_error_V':float(error[j]),'bins':bins})
c.dump(c.OUT/'ERROR_LOCALIZATION.json',{'scope':'post-result localization, no retuning or altered gates','results':rows})
