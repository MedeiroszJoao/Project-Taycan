"""Exploratory development-only six-hour H00 bracket search.

NOT the frozen runner algorithm: it uses a NEW, currently unapproved explicit
charge-block and parked-RPM trace. It must never write Stage 4 calibration
receipts consumed by the official runner. It does not use validation/test rows.
"""
from __future__ import annotations
import json,math,time,hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/simulator'))
from candidate_sim import model_energy_consistent as phys
from scripts.duty_cycle_candidate import build_duty_inputs

def run_one(profile:str,kw:float, seed:int=505):
    trace=build_duty_inputs(dt_s=5,charge_power_kw=kw,profile_id=profile)
    cold=profile=='SHIFT_REGEN_COLD_6H'
    p=phys.ModelConfig(seed=seed,dt_s=5,steps=len(trace.mode),initial_soc=.60,sensor_noise=False,
            coolant_C=10 if cold else 25, init_module_C=16 if cold else 31,
            auxiliary_amplitude_W=0)
    try:
        s=phys.simulate(phys.Fault('H00',severity=0),p,
           torque_trace_nm=trace.torque_nm,rpm_trace_rpm=trace.rpm,
           external_charge_trace_W=trace.charge_W)
    except ValueError as e:
        return {'profile':profile,'power_kw':kw,'status':'INVALID','reason':str(e)}
    soc=[r['mean_hidden_soc']*100 for r in s.truth]
    low=[r['min_hidden_branch_soc']*100 for r in s.truth]
    high=[r['max_hidden_branch_soc']*100 for r in s.truth]
    initial=100*p.initial_soc
    return {'profile':profile,'power_kw':kw,'status':'OK' if min(soc)>=30 and max(soc)<=80 else 'WINDOW_VIOLATION',
        'soc_initial_configured_pp':initial,'soc_final_pp':soc[-1],'residual_pp':soc[-1]-initial,
        'mean_soc_min_pp':min(soc),'mean_soc_max_pp':max(soc),
        'min_branch_soc_pp':min(low),'max_branch_soc_pp':max(high),
        'integrated_dc_charging_energy_kWh':sum(trace.charge_W)*5/3_600_000,
        'max_rc_energy_identity_error_J':max(abs(r['rc_input_work_J_step']-r['rc_dissipation_J_step']-r['rc_capacitor_storage_delta_J_step']) for r in s.truth),
        'max_power_residual_W':max(abs(r['power_requested_dc_W']-r['power_dc_W']) for r in s.truth)}

def run():
    outputs=[]
    for prof,lo,hi in [('NOMINAL_6H',40.,49.),('SHIFT_REGEN_COLD_6H',16.,32.)]:
        print('PROFILE',prof,flush=True)
        a,b=run_one(prof,lo),run_one(prof,hi)
        if a['status']=='INVALID' or b['status']=='INVALID' or a['residual_pp']*b['residual_pp']>=0:
            raise RuntimeError(f'exploratory bracket invalid {prof}: {a} {b}')
        trace=[a,b]
        for i in range(1,9):
            mid=(lo+hi)/2
            e=run_one(prof,mid)
            e['iteration']=i
            trace.append(e)
            if e['status']=='INVALID':
                raise RuntimeError('candidate bracket hit inadmissible state, cannot continue')
            if e['residual_pp']*a['residual_pp']>0:
                lo=mid;a=e
            else:
                hi=mid;b=e
            print(' ',i,prof,round(mid,6),'SOC',round(e['soc_final_pp'],6),'range',
               round(e['mean_soc_min_pp'],4),round(e['mean_soc_max_pp'],4),flush=True)
        best=min([r for r in trace if r['status']=='OK'],key=lambda r:abs(r['residual_pp']))
        outputs.append({'profile':prof,'best_exploratory':best,'bisection_iterations':8,
                        'interval_at_end_kW':[lo,hi],'trace':trace})
    return {'classification':'EXPLORATORY_H00_ONLY_NOT_OFFICIAL_STAGE4_CALIBRATION',
        'has_seen_validation_or_test_outcomes':False,'charge_duty':'12_minutes_charge_per_60min_6h',
        'warning':'Bracket [40,49] / [16,32] informed by earlier exploratory outcomes, NOT PRECOMMITTED; MUST NOT supply this receipt to sealed runner.',
        'source_hash':hashlib.sha256((ROOT/'src/simulator/candidate_sim/model_energy_consistent.py').read_bytes()).hexdigest(),
        'profiles':outputs}

if __name__=='__main__':
    result=run();dest=ROOT/'results/calibration_6h_duty_development_only.json'
    dest.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print('FINISHED',str(dest),flush=True)
