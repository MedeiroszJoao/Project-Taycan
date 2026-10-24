"""Analytic M01/I01 extra-loss mapping for the *toy candidate*, not frozen Stage 4.

No source of held-out data is read. This mathematical identity depends on the
candidate's *chosen loss-injection model*, not on Taycan measurements.
"""
from __future__ import annotations
import json,hashlib,sys,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/simulator'))
from candidate_sim import model_energy_consistent as phys
from scripts.duty_cycle_candidate import build_duty_inputs

ENERGY_PROFILES={'NOMINAL_6H':47.8046875,'SHIFT_REGEN_COLD_6H':31.5625}


def analytic_mapping():
    p=phys.ModelConfig()
    entries=[];core={}
    for profile in ENERGY_PROFILES:
        t=build_duty_inputs(dt_s=5.,charge_power_kw=ENERGY_PROFILES[profile],profile_id=profile)
        # Temperature evolution and differential-motor temperature observability do
        # not enter this particular M01 or I01 *loss parameterization*.
        base_motor_loss_J=sum(p.motor_copper_coeff_w_per_nm2*(v*v)*5. for v in t.torque_nm)
        full_motor_extra_J=base_motor_loss_J*(p.motor_loss_fault_multiplier-1.)
        full_inverter_extra_J=p.inverter_fault_extra_W*len(t.torque_nm)*5.
        core[profile]={'full_m01_extra_J':full_motor_extra_J,'full_i01_extra_J':full_inverter_extra_J,
                       'ratio_i01_severity_per_m01_severity':full_motor_extra_J/full_inverter_extra_J,
                       'total_duration_s':len(t.torque_nm)*5,'charge_power_used_kw':ENERGY_PROFILES[profile]}
        for mapping in ('winding_proxy','uninformative'):
            for severity in (.25,.5,1.):
                requested=full_motor_extra_J*severity/full_inverter_extra_J
                chosen=min(1.,max(0.,requested))
                target=full_motor_extra_J*severity
                achieved=full_inverter_extra_J*chosen
                mismatch=abs(target-achieved)/max(abs(target),abs(achieved),1e-12)*100
                entries.append({'profile_id':profile,'diff_motor_t_mapping':mapping,'m01_severity':severity,
                                'i01_severity_used':chosen,'delta_E_motor_J':target,
                                'delta_E_inverter_J':achieved,'mismatch_pct':mismatch,
                                'match_status':'MATCHED' if mismatch<=1 else 'INFEASIBLE'})
    return {'classification':'DEVELOPMENT_ONLY_NOT_STAGE4_M01_I01_ENERGY_MATCH_RECEIPT',
            'assumptions':'constant k torque^2 motor copper fault and constant-W inverter fault; not evidence of separability in real EV',
            'seeds_and_data':'no validation/test; analytic formula on assumed six-hour torque waveform only',
            'candidate_source_sha256':hashlib.sha256((ROOT/'src/simulator/candidate_sim/model_energy_consistent.py').read_bytes()).hexdigest(),
            'profile_parameters':core,'entries':entries}


def validate_full_horizon_finite_differences(result):
    # One 100% M01 and its energy-matched I01 per profile, each against same
    # physically simulated H00 reference; the other severities are exactly
    # linear by the injection parameterization, not independently scored.
    audits=[]
    for profile,power in ENERGY_PROFILES.items():
        trace=build_duty_inputs(dt_s=5.,charge_power_kw=power,profile_id=profile)
        cold=profile=='SHIFT_REGEN_COLD_6H'
        p=phys.ModelConfig(seed=505,dt_s=5,steps=4320,initial_soc=.6,sensor_noise=False,
                           coolant_C=10 if cold else 25,init_module_C=16 if cold else 31,
                           auxiliary_amplitude_W=0)
        def run(f):
            return phys.simulate(f,p,torque_trace_nm=trace.torque_nm,
                      rpm_trace_rpm=trace.rpm,external_charge_trace_W=trace.charge_W)
        base=run(phys.Fault('H00',severity=0))
        motor=run(phys.Fault('M01',severity=1))
        calibrated=next(x for x in result['entries'] if x['profile_id']==profile and x['m01_severity']==1.)
        inv=run(phys.Fault('I01',severity=calibrated['i01_severity_used']))
        dm=sum((m['power_motor_loss_W']-b['power_motor_loss_W'])*5 for m,b in zip(motor.truth,base.truth))
        di=sum((i['power_inverter_loss_W']-b['power_inverter_loss_W'])*5 for i,b in zip(inv.truth,base.truth))
        mismatch=100*abs(dm-di)/max(abs(dm),abs(di),1e-9)
        if mismatch>1e-7 or abs(dm-calibrated['delta_E_motor_J'])>1e-5:
            raise AssertionError('calibrated energy mismatch: '+str((profile,dm,di,mismatch)))
        audits.append({'profile':profile,'E_M01_extra_J':dm,'E_I01_extra_J':di,'mismatch_pct':mismatch,
                       'H00_final_soc_pct':base.truth[-1]['mean_hidden_soc']*100,
                       'M01_final_soc_pct':motor.truth[-1]['mean_hidden_soc']*100,
                       'I01_final_soc_pct':inv.truth[-1]['mean_hidden_soc']*100,
                       'note':'matching injected loss energy does not equalize post-loss current, thermal pathways, or observed features'})
    result['full_6h_reference_checks']=audits
    return result

if __name__=='__main__':
    data=validate_full_horizon_finite_differences(analytic_mapping())
    dest=ROOT/'results/m01_i01_energy_match_development_only.json'
    dest.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'status':data['classification'],'entries':len(data['entries']),
        'ratio':{k:v['ratio_i01_severity_per_m01_severity'] for k,v in data['profile_parameters'].items()},
        'check':data['full_6h_reference_checks']},indent=2))
