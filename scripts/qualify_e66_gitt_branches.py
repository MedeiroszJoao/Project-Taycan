"""Restricted two-branch quasi-OCV candidate; reject out-of-domain inference."""
import json,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/e66_gitt_branch_candidate'
def predict(points,z):
 a=np.array(sorted(points));x,y=a[:,0],a[:,1]
 if np.any(np.diff(x)<=0) or np.any(np.diff(y)<=0):raise ValueError('nonmonotone branch')
 if np.any(np.asarray(z)<x[0]) or np.any(np.asarray(z)>x[-1]):raise ValueError('outside branch support')
 return np.interp(z,x,y)
def main():
 source=ROOT/'results/e66_gitt_history_audit/RESULTS.json';a=json.loads(source.read_text())['anchors'];j=int(np.argmin([r['soc'] for r in a]));branches={'discharge':a[:j+1],'charge':a[j+1:]};out={}
 for name,rows in branches.items():
  pts=sorted([[r['soc'],r['V']] for r in rows]);errs=[]
  for k in range(1,len(pts)-1):errs.append(float(predict(pts[:k]+pts[k+1:],pts[k][0])-pts[k][1]))
  rm=float(np.sqrt(np.mean(np.array(errs)**2))*1000);mx=float(np.max(abs(np.array(errs)))*1000)
  out[name]=dict(points=pts,interior_LOO_errors_mV=[v*1000 for v in errs],RMSE_mV=rm,max_mV=mx,gate='PASS_INTERPOLATION_ONLY' if rm<=50 and mx<=150 else 'FAIL_INTERPOLATION',SOC_support=[pts[0][0],pts[-1][0]])
 result=dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),protocol_sha256=hashlib.sha256((OUT/'PROTOCOL.json').read_bytes()).hexdigest(),branches=out,independent_validation=False,dynamic_model=False,B2_approved=False)
 (OUT/'RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
 for n,r in out.items():print(n,r['RMSE_mV'],r['max_mV'],r['gate'])
 tests=0
 for z in [-.1,1.1]:
  try:predict([[0,3],[1,4]],z)
  except ValueError:tests+=1
  else:raise AssertionError('extrapolation accepted')
 assert predict([[0,3],[1,4]],.5)==3.5;tests+=1
 try:predict([[0,4],[1,3]],.5)
 except ValueError:tests+=1
 else:raise AssertionError('nonmonotone accepted')
 (OUT/'TESTS.json').write_text(json.dumps({'passed':tests,'scope':'interpolation and domain guards'},indent=2))
if __name__=='__main__':main()
