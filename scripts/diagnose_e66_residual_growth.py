"""Post-hoc residual localization; no fitting or access to final blind files."""
import json, hashlib
import numpy as np
from scripts import e66_extended_validation as e

def main():
    source=e.OUT/'EVALUATION.json'
    rows=json.loads(source.read_text())['results']; result=[]
    for i in range(2):
        t,current,avl,bms,meta,_,_=e.window(i)
        for r in rows:
            if r['index']!=i or r['mesh']!=40: continue
            g=np.asarray(r['times_s']); err=(np.asarray(r['predicted_AVL_module_V'])-np.interp(g,t,avl))/6
            assert abs(np.sqrt(np.mean(err**2))-r['RMSE_V'])<1e-10
            bins=[]
            for start in range(0,1800,300):
                mask=(g>=start)&(g<start+300)
                bins.append(dict(start_s=start,end_exclusive_s=start+300,n=int(mask.sum()),RMSE_mV=float(np.sqrt(np.mean(err[mask]**2))*1000),bias_mV=float(err[mask].mean()*1000)))
            result.append(dict(session=i,model=r['model'],bins=bins,oracle_constant_offset_minimum_RMSE_mV=float(np.std(err)*1000),warning='Oracle bound uses evaluation residuals; not an admissible calibration or validation.'))
    out=dict(posthoc=True,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),final_blind_files_opened=0,results=result)
    (e.OUT/'RESIDUAL_GROWTH_DIAGNOSTIC.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))
if __name__=='__main__': main()
