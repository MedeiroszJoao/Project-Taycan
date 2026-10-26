"""Post-hoc explanatory probe: measured surface T is an imposed input, never a prediction."""
import sys,json,subprocess
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import e66_extended_validation as e
OUT=e.OUT/'temperature_probe'

def signature():
    return {'script_sha256':e.v.m.c.sha(__file__),'extended_freeze_sha256':e.v.m.c.sha(e.OUT/'FREEZE.json'),
            'design':'post-hoc after1800s MCCC failure; all2sessions x2models mesh40, measured mean of9cell4thermocouples imposed as temperature; no fit; no thermal validation claim'}

def solve(index,kind):
    import pybamm
    e.v.guards()
    if json.loads((OUT/'FREEZE.json').read_text())!=signature():raise ValueError('probe drift')
    t,I,va,_,meta,d,ix=e.window(index)
    temp=np.mean(np.array([d[k][ix] for k in e.v.m.THERM]),axis=0)
    if not np.all(np.isfinite(temp)):raise ValueError('missing thermocouples, no repair')
    p=e.v.m.parameters(meta['initial_SOC'],meta['initial_cell4_surface_temperature_C'])
    p.update({'Current function [A]':pybamm.Interpolant(t,-I/2/(61.259778569358865/5),pybamm.t),
              'Ambient temperature [K]':pybamm.Interpolant(t,temp+273.15,pybamm.t)})
    g,voltage,_,coverage,termination=e.v.m.c.run_model(p,np.arange(1801.),kind,40)
    f=json.loads((e.v.a.OUT/'ADAPTER_FREEZE.json').read_text());pred=6*voltage+f['offset_V']+f['R_effective_ohm']*np.interp(g,t,I)
    error=(pred-np.interp(g,t,va))/6
    return {'status':'COMPLETED','index':index,'model':kind,'coverage':coverage,'RMSE_V':float(np.sqrt(np.mean(error**2))),
            'max_error_V':float(np.max(abs(error))),'termination':termination,'temperature_input_range_C':[float(temp.min()),float(temp.max())],
            'thermal_validation':False,'times_s':g.tolist(),'predicted_AVL_module_V':pred.tolist()}

def main():
    rows=[]
    for i in range(2):
        for k in ['SPMe','DFN']:
            try:
                p=subprocess.run([sys.executable,__file__,'worker',str(i),k],capture_output=True,text=True,timeout=240)
                (OUT/f'{i}_{k}.log').write_text(p.stderr)
                if p.returncode:raise RuntimeError(p.stderr[-1600:])
                r=json.loads(p.stdout)
            except Exception as ex:r={'status':'ERROR','index':i,'model':k,'error':str(ex)}
            rows.append(r);e.v.m.c.dump(OUT/'EVALUATION.json',{'freeze_sha256':e.v.m.c.sha(OUT/'FREEZE.json'),'scope':'posthoc conditional voltage diagnostic, measured surface temperature is not core temperature or predicted temperature','results':rows})
            print(i,k,r['status'],r.get('RMSE_V'),flush=True)

if __name__=='__main__':
    if sys.argv[1]=='freeze':OUT.mkdir(exist_ok=True);e.v.m.c.dump(OUT/'FREEZE.json',signature())
    elif sys.argv[1]=='run':main()
    else:print(json.dumps(solve(int(sys.argv[2]),sys.argv[3])))
