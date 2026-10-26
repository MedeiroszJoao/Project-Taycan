"""Recompute extended errors and exercise real feature extractor on module analogues."""
import sys,json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import e66_extended_validation as e
from scripts import run_stage4_experiments as runner

def module_features(times, voltage, current):
    # Adapter exists only for this scoped extractor test. No synthetic vehicle rows published.
    rows=[{'time_s':float(t),'TAYCAN_HVBAT_VOLT':float(v),'TAYCAN_BMS_I':float(i)} for t,v,i in zip(times,voltage,current)]
    f,_=runner.feature_matrix('MODULE_ANALOGUE_NOT_VEHICLE',rows,1.,False)
    available={code for code,_ in runner.FEATURES if f['mask_'+code]==0}
    if available!={'F20','F21'}:raise ValueError('unsupported feature became available')
    return f

def main():
    if json.loads((e.OUT/'FREEZE.json').read_text())!=e.signature():raise ValueError('freeze drift')
    receipt=json.loads((e.OUT/'EVALUATION.json').read_text());rows=receipt['results']
    expected={(i,k,40) for i in range(2) for k in ['SPMe','DFN']}|{(i,'SPMe',80) for i in range(2)}
    keys=[(r['index'],r['model'],r['mesh']) for r in rows]
    if len(keys)!=6 or set(keys)!=expected:raise ValueError('case set mismatch')
    checks=[];features=[];refinement=[]
    for i in range(2):
        t,I,va,_,meta,_,_=e.window(i)
        charge=np.r_[0,np.cumsum((I[:-1]+I[1:])*np.diff(t)/7200)]
        soc=meta['initial_SOC']+charge/(2*61.259778569358865)
        for r in [r for r in rows if r['index']==i and r['status']=='COMPLETED']:
            g=np.asarray(r['times_s']);pred=np.asarray(r['predicted_AVL_module_V']);actual=np.interp(g,t,va);current=-np.interp(g,t,I)
            error=(pred-actual)/6;rm=float(np.sqrt(np.mean(error**2)));mx=float(np.max(abs(error)))
            if abs(rm-r['RMSE_V'])>1e-10 or abs(mx-r['max_error_V'])>1e-10:raise ValueError('metric mismatch')
            if not np.allclose(r['SOC_proxy_range'],[soc.min(),soc.max()],atol=1e-10,rtol=0):raise ValueError('SOC mismatch')
            passed=rm<=.05 and mx<=.15 and r['coverage']>=.95 and soc.min()>=0 and soc.max()<=1
            if r['gate']!=('PASS' if passed else 'FAIL'):raise ValueError('gate mismatch')
            checks.append({'index':i,'model':r['model'],'mesh':r['mesh'],'RMSE_mV':rm*1000,'maximum_mV':mx*1000,'gate':r['gate']})
            measured=module_features(g,actual,current);modeled=module_features(g,pred,current)
            features.append({'index':i,'model':r['model'],'mesh':r['mesh'],'measured':measured,'modeled':modeled,
                             'F20_absolute_difference_kWh':abs(modeled['F20_integrated_observed_HV_kWh']-measured['F20_integrated_observed_HV_kWh']),
                             'warning':'F21 shares measured input current; agreement is expected, not independent predictive evidence. Module energy is not pack energy.'})
        pair={r['mesh']:r for r in rows if r['index']==i and r['model']=='SPMe' and r['status']=='COMPLETED'}
        if len(pair)==2:
            a,b=pair[40],pair[80];g=np.asarray(a['times_s']);use=g<=b['times_s'][-1]
            gap=float(np.max(abs(np.asarray(a['predicted_AVL_module_V'])[use]-np.interp(g[use],b['times_s'],b['predicted_AVL_module_V'])))/6)
            full=a['coverage']>=.95 and b['coverage']>=.95
            refinement.append({'index':i,'maximum_gap_mV':gap*1000,'gate':'PASS' if gap<=.005 and full else 'FAIL','common_interval_only':not full})
    complete=len(checks)==6 and len(refinement)==2
    decision='FAIL' if any(r['gate']=='FAIL' for r in checks+refinement) else ('PASS_LIMITED' if complete else 'INCONCLUSIVE')
    e.v.m.c.dump(e.OUT/'AUDIT.json',{'decision':decision,'preregistration_commit':'ae05470813fa0be1be71ab9f99df179cc4ef03e9','checks':checks,'refinement':refinement,
                                   'scope':'nonblind extension, one module, initial temperature fixed','final_blind_numeric_access':0,'historical_reserved_access':0})
    e.v.m.c.dump(e.OUT/'FEATURE_TRANSFER.json',{'scope':'module-level analogues only; not vehicle feature validation','available_features':2,'masked_features':26,'results':features})
    print(decision)

if __name__=='__main__':main()
