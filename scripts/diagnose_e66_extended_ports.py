"""Post-hoc error decomposition against two measured voltage ports; no fitting."""
import sys,json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import e66_extended_validation as e

def main():
    rows=json.loads((e.OUT/'EVALUATION.json').read_text())['results'];out=[]
    probe=json.loads((e.OUT/'temperature_probe/EVALUATION.json').read_text())['results'];probe_audit=[]
    f=json.loads((e.v.a.OUT/'ADAPTER_FREEZE.json').read_text())
    for i in range(2):
        t,I,va,vb,_,_,_=e.window(i)
        port=(va-vb-f['offset_V']-f['R_effective_ohm']*I)/6
        for r in [r for r in probe if r['index']==i and r['status']=='COMPLETED']:
            error=(np.asarray(r['predicted_AVL_module_V'])-np.interp(r['times_s'],t,va))/6
            rm=float(np.sqrt(np.mean(error**2)));mx=float(np.max(abs(error)))
            if abs(rm-r['RMSE_V'])>1e-10 or abs(mx-r['max_error_V'])>1e-10:raise ValueError('temperature probe metric mismatch')
            probe_audit.append({'index':i,'model':r['model'],'RMSE_V':rm,'maximum_V':mx,'coverage':r['coverage'],
                                'voltage_threshold_status':'PASS' if rm<=.05 and mx<=.15 and r['coverage']>=.95 else 'FAIL',
                                'not_thermal_validation':True})
        for r in [r for r in rows if r['index']==i and r['status']=='COMPLETED']:
            g=np.asarray(r['times_s']);pred=np.asarray(r['predicted_AVL_module_V']);cur=np.interp(g,t,I)
            avl_error=(pred-np.interp(g,t,va))/6
            bms_prediction=pred-f['offset_V']-f['R_effective_ohm']*cur
            bms_error=(bms_prediction-np.interp(g,t,vb))/6
            gap=float(np.max(abs(avl_error-(bms_error-np.interp(g,t,port)))))
            if gap>1e-10:raise ValueError('voltage port identity failed')
            out.append({'index':i,'model':r['model'],'mesh':r['mesh'],'AVL_error_bias_V':float(avl_error.mean()),
                        'BMS_RMSE_V':float(np.sqrt(np.mean(bms_error**2))),'paired_port_residual_RMSE_V':float(np.sqrt(np.mean(port**2))),
                        'paired_port_residual_bias_V':float(port.mean()),'algebraic_identity_max_gap_V':gap})
    e.v.m.c.dump(e.OUT/'PORT_DIAGNOSTIC.json',{'posthoc':True,'no_refitting':True,'results':out,
                                           'warning':'BMS secondary target is not substituted for primary AVL; voltage-port relation is empirical, not a proved contact resistance'})
    if len(probe_audit)!=4:raise ValueError('incomplete temperature probe')
    e.v.m.c.dump(e.OUT/'temperature_probe/AUDIT.json',{'posthoc':True,'results':probe_audit,'thermal_prediction_validated':False})

if __name__=='__main__':main()
