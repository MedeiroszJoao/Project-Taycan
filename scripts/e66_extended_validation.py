"""Fixed 1800s extension; already exposed sessions, no new blind claim or fit."""
import sys, json, subprocess
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'src/simulator')]
from scripts import validate_e66_reserved_module_sessions as v
from taycan_sim.model import ModelConfig
OUT = ROOT/'results/e66_extended_validation'

def signature():
    return {str(p.relative_to(ROOT)): v.m.c.sha(p) for p in [Path(__file__), OUT/'PROTOCOL.json', v.OUT/'VALIDATION_FREEZE.json', ROOT/'src/simulator/taycan_sim/model.py']}

def window(index):
    _, _, _, _, meta = v.window(index)
    d = v.read(v.FILES[index]); t = d['RecordingTime']; start = meta['window_start_s']
    ix = np.flatnonzero((t >= start) & (t <= start+1800))
    if len(ix)<2 or t[ix[-1]]-start<1800 or np.max(np.diff(t[ix]))>2:
        raise ValueError('complete 1800s window unavailable')
    return t[ix]-start, d['AVL_Current'][ix], d['AVL_Voltage'][ix], d['BMS_Voltage'][ix], meta, d, ix

def a_law(t, avl_current, initial_voltage, temperature, age):
    """Homogeneous isothermal 1RC reduction, exact RC step for held current."""
    p = ModelConfig(); q = p.capacity_ah_cell*(1-p.age_capacity_loss*age)
    r0 = p.r0_ohm_cell*(1+p.age_resistance_gain*age)*max(.5,1+p.resistance_cold_coeff_per_K*(p.resistance_reference_C-temperature))
    r1 = p.r1_ohm_cell*(1+p.age_resistance_gain*age)
    z = (initial_voltage-p.ocv_low_v-p.ocv_temp_coeff_v_per_K*(temperature-25))/p.ocv_span_v
    pol = 0.; voltages=[]; states=[]; current=-np.asarray(avl_current)/2
    for j in range(len(t)):
        states.append(z); voltages.append(p.ocv_low_v+p.ocv_span_v*z+p.ocv_temp_coeff_v_per_K*(temperature-25)-pol-current[j]*r0)
        if j+1<len(t):
            dt=t[j+1]-t[j]; decay=np.exp(-dt/p.rc_tau_s)
            pol=pol*decay+r1*current[j]*(1-decay)
            z-=current[j]*dt/(3600*q)
    return np.asarray(voltages), np.asarray(states)

def solve(index, kind, mesh):
    import pybamm
    v.guards()
    if json.loads((OUT/'FREEZE.json').read_text()) != signature(): raise ValueError('extended freeze drift')
    t,I,va,vb,meta,d,ix=window(index); f=json.loads((v.a.OUT/'ADAPTER_FREEZE.json').read_text())
    p=v.m.parameters(meta['initial_SOC'],meta['initial_cell4_surface_temperature_C'])
    p.update({'Current function [A]':pybamm.Interpolant(t,-I/2/(61.259778569358865/5),pybamm.t)})
    g,voltage,_,coverage,termination=v.m.c.run_model(p,np.arange(1801.),kind,mesh)
    predicted=6*voltage+f['offset_V']+f['R_effective_ohm']*np.interp(g,t,I)
    error=(predicted-np.interp(g,t,va))/6
    charge=np.r_[0,np.cumsum((I[:-1]+I[1:])*np.diff(t)/7200)]
    soc=meta['initial_SOC']+charge/(2*61.259778569358865)
    rm=float(np.sqrt(np.mean(error**2))); mx=float(np.max(abs(error)))
    segments=[]
    for a,b in [(0,300),(300,900),(900,1800)]:
        selected=(g>=a)&(g<=b)
        segments.append({'start_s':a,'end_s':b,'points':int(selected.sum()),'RMSE_V':float(np.sqrt(np.mean(error[selected]**2))) if selected.any() else None})
    return dict(index=index,model=kind,mesh=mesh,status='COMPLETED',metadata=meta,RMSE_V=rm,max_error_V=mx,coverage=coverage,termination=termination,
                SOC_proxy_range=[float(soc.min()),float(soc.max())],gate='PASS' if rm<=.05 and mx<=.15 and coverage>=.95 and soc.min()>=0 and soc.max()<=1 else 'FAIL',
                cell4_temperature_range_C=[float(np.nanmin([d[k][ix] for k in v.m.THERM])),float(np.nanmax([d[k][ix] for k in v.m.THERM]))],
                segments=segments,times_s=g.tolist(),predicted_AVL_module_V=predicted.tolist())

def compare_a():
    results=[]
    for i in range(2):
        t,I,va,vb,meta,_,_=window(i); f=json.loads((v.a.OUT/'ADAPTER_FREEZE.json').read_text())
        for age in [0,.15]:
            voltage,z=a_law(t,I,meta['initial_BMS_mean_cell_voltage_V'],meta['initial_cell4_surface_temperature_C'],age)
            pred=6*voltage+f['offset_V']+f['R_effective_ohm']*I; error=(pred-va)/6
            results.append({'index':i,'age':age,'RMSE_V':float(np.sqrt(np.mean(error**2))),'max_error_V':float(np.max(abs(error))),
                            'SOC_proxy_range':[float(z.min()),float(z.max())],'initialization':'invert A own linear OCV using same prebaseline BMS voltage; zero polarization',
                            'integration':'left-held measured current for exact RC step; no clamping; not full A backend'})
    v.m.c.dump(OUT/'A_COMPARISON.json',{'scope':'homogeneous isothermal A constitutive law only; same measured current and observation adapter as B','results':results})

def run():
    rows=[]
    for i,k,n in [(i,k,40) for i in range(2) for k in ['SPMe','DFN']]+[(i,'SPMe',80) for i in range(2)]:
        try:
            p=subprocess.run([sys.executable,__file__,'worker',str(i),k,str(n)],capture_output=True,text=True,timeout=240)
            (OUT/f'{i}_{k}_{n}.log').write_text(p.stderr)
            if p.returncode: raise RuntimeError(p.stderr[-1600:])
            row=json.loads(p.stdout)
        except Exception as e: row=dict(index=i,model=k,mesh=n,status='ERROR_OR_INELIGIBLE',error=str(e))
        rows.append(row);v.m.c.dump(OUT/'EVALUATION.json',{'freeze_sha256':v.m.c.sha(OUT/'FREEZE.json'),'results':rows,'exposure':'nonblind extension of two previously evaluated sessions','final_blind_numeric_access':0})
        print(i,k,n,row['status'],row.get('RMSE_V'),row.get('gate'),flush=True)
    compare_a()

if __name__=='__main__':
    if sys.argv[1]=='freeze':v.m.c.dump(OUT/'FREEZE.json',signature())
    elif sys.argv[1]=='run':run()
    elif sys.argv[1]=='worker':print(json.dumps(solve(int(sys.argv[2]),sys.argv[3],int(sys.argv[4]))))
