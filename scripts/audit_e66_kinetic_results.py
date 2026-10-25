"""Independent metric recomputation and declared sensor stress; no model refit."""
import json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import calibrate_e66_kinetics as c

def main():
 out=c.OUT;ev=json.loads((out/'EVALUATION.json').read_text());f=json.loads((out/'GENERATOR_B_FREEZE.json').read_text());fit=json.loads((out/'FIT_RESULT.json').read_text());pulses={ds:c.pulse.extract(ds)[0] for ds in ['HPPC','GITT']};spec=json.loads((c.REC/'PROSPECTIVE.json').read_text());dis=c.get_inputs(c.pulse.ARCHIVE,spec['evaluation']);rows=[]
 for r in ev['results']:
  if r['status']!='COMPLETED':rows.append({'dataset':r['dataset'],'index':r['index'],'status':'ERROR'});continue
  t=np.array(r['model_times_s']);v=np.array(r['model_V'])
  if r['dataset']=='DISCHARGE':d=dis[r['index']];actual=np.interp(t,d['t'],d['v'])
  else:
   features,grid,data=pulses[r['dataset']][r['index']];actual=np.interp(t,grid,data)
  err=v-actual;rmse=float(np.sqrt(np.mean(err**2)));gap=abs(rmse-r['RMSE_V']);
  if gap>1e-10:raise ValueError('metric recomputation mismatch')
  stresses={}
  for bias in [-.005,.005]:stresses[f'bias_{bias}V_RMSE']=float(np.sqrt(np.mean((err-bias)**2)))
  for delay in [-.1,.1]:
   shifted=t+delay;keep=(shifted>=t[0])&(shifted<=t[-1]);error=v[keep]-np.interp(shifted[keep],t,actual);stresses[f'delay_{delay}s_RMSE']=float(np.sqrt(np.mean(error**2)))
  rng=np.random.default_rng(1729);keep=rng.random(len(t))>=.2;stresses['missing20percent_RMSE']=float(np.sqrt(np.mean(err[keep]**2)));stresses['missing_retained']=int(sum(keep))
  rows.append({'dataset':r['dataset'],'index':r['index'],'model':r['model'],'mesh':r['mesh'],'status':'VERIFIED','RMSE_V':rmse,'max_error_V':r['max_error_V'],'coverage':r['coverage'],'gate':r['gate'],'stress':stresses})
 mesh=[]
 for r in ev['results']:
  if r['mesh']!=80:continue
  low=next(x for x in ev['results'] if x['dataset']==r['dataset'] and x['index']==r['index'] and x['model']==r['model'] and x['mesh']==40)
  row={'dataset':r['dataset'],'index':r['index']}
  if r['status']!='COMPLETED' or low['status']!='COMPLETED':row['gate']='INCONCLUSIVE'
  else:
   t=np.array(low['model_times_s']);mask=t<=r['model_times_s'][-1];delta=np.array(low['model_V'])[mask]-np.interp(t[mask],r['model_times_s'],r['model_V']);gap=float(np.max(abs(delta)));row.update(max_gap_V=gap,gate='PASS' if gap<=.005 and r['coverage']>=.95 else 'FAIL')
  mesh.append(row)
 differences=[]
 for r in ev['results']:
  if r['model']!='DFN' or r['status']!='COMPLETED':continue
  a=next(x for x in ev['results'] if x['dataset']==r['dataset'] and x['index']==r['index'] and x['model']=='SPMe' and x['mesh']==40)
  if a['status']!='COMPLETED':continue
  t=np.array(a['model_times_s']);mask=t<=r['model_times_s'][-1];d=np.array(a['model_V'])[mask]-np.interp(t[mask],r['model_times_s'],r['model_V']);differences.append({'dataset':r['dataset'],'index':r['index'],'SPMe_DFN_RMS_V':float(np.sqrt(np.mean(d*d))),'max_V':float(np.max(abs(d)))})
 c.dump(out/'INDEPENDENT_AUDIT.json',{'freeze_sha256':c.sha(out/'GENERATOR_B_FREEZE.json'),'fit_k':fit['k'],'metric_recomputation':'independent from saved model predictions and authorized measured data; all completed outputs checked','results':rows,'mesh':mesh,'SPMe_DFN':differences,'limits':'sensor stress uses observation-grid interpolation and conditional scenarios, not calibrated uncertainty or independent samples'})
 print('verified',len(rows),'mesh',mesh,flush=True)
if __name__=='__main__':main()
