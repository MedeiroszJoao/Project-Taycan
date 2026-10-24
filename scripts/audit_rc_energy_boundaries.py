"""Prospective exploratory falsification, no Stage 4 scored episodes or fitting."""
from __future__ import annotations
import json, hashlib, math, os, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/simulator'))
from candidate_sim import model as old, model_energy_consistent as revised


def compute():
    # waveform given in continuous physical time: same input for every dt.
    torque=lambda t: 40+110*math.sin(2*math.pi*t/200)+11*math.cos(2*math.pi*t/31)
    reference={}
    for dt in (1.,2.5,5.,10.):
        steps=int(900/dt)
        cfg=revised.ModelConfig(seed=777,initial_soc=.6,dt_s=dt,steps=steps,sensor_noise=False,
            auxiliary_mean_W=1200,auxiliary_amplitude_W=0,
            group_soc_spread=0,branch_soc_spread=0)
        trace=[torque(i*dt) for i in range(steps)]
        orig=old.simulate(p=old.ModelConfig(**vars(cfg)),torque_trace_nm=trace)
        strict=revised.simulate(p=cfg,torque_trace_nm=trace)
        heat=sum(x['module_heat_generation_J_step'] for x in strict.truth)
        rc=sum(x['rc_dissipation_J_step'] for x in strict.truth)
        dq=sum(x['rc_capacitor_storage_delta_J_step'] for x in strict.truth)
        work=sum(x['rc_input_work_J_step'] for x in strict.truth)
        errors=[abs(x['rc_input_work_J_step']-x['rc_dissipation_J_step']-x['rc_capacitor_storage_delta_J_step']) for x in strict.truth]
        reference[str(dt)]={'steps':steps,'dt_s':dt,
            'final_mean_soc_original_pct':orig.truth[-1]['mean_hidden_soc']*100,
            'final_mean_soc_strict_pct':strict.truth[-1]['mean_hidden_soc']*100,
            'final_motor_temperature_C_strict':strict.truth[-1]['motor_winding_C'],
            'original_final_module_mean_T_C':orig.observations[-1]['TAYCAN_BMS_T_AVG'],
            'strict_final_module_mean_T_C':strict.observations[-1]['TAYCAN_BMS_T_AVG'],
            'original_initial_module_mean_T_C':orig.observations[0]['TAYCAN_BMS_T_AVG'],
            'strict_initial_module_mean_T_C':strict.observations[0]['TAYCAN_BMS_T_AVG'],
            'strict_total_rc_heat_J':rc,'strict_total_rc_energy_change_J':dq,
            'strict_total_rc_input_work_J':work,'strict_total_generated_module_heat_J':heat,
            'max_step_rc_energy_identity_error_J':max(errors),
            'max_step_dc_power_closure_W':max(abs(x['power_dc_W']-x['power_requested_dc_W']) for x in strict.truth)}
    # Numerical no-current single-RC reference = exact dissipation, not I*pol heat.
    v0=.15;R=.00025;tau=75;dt=5
    v1,q,stored,work=revised._rc_exact_step(v0,0.,R,tau,dt)
    reference_relax={'initial_polarization_V':v0,'current_A':0,
        'dt_s':dt,'R1_ohm':R,'tau_s':tau,'heat_R1_J':q,
        'stored_energy_delta_J':stored,'electrical_work_J':work}
    # Log the boundary failure instead of trying to calibrate after holdout.
    invalid=revised.ModelConfig(initial_soc=.985,dt_s=20,steps=120,sensor_noise=False,
        group_soc_spread=0,branch_soc_spread=0,
        driver_torque_baseline=0,driver_torque_swing=0,driver_torque_fast_swing=0,
        external_charge_power_W=180000)
    failure=None
    try:revised.simulate(p=invalid,torque_trace_nm=[0.]*invalid.steps)
    except ValueError as ex:failure=str(ex)
    assert failure and 'SOC_BOUNDARY_VIOLATION' in failure
    return {'classification':'EXPLORATORY_NOT_STAGE4_SCORED',
        'original_sha256':hashlib.sha256((ROOT/'src/simulator/taycan_sim/model.py').read_bytes()).hexdigest(),
        'bidirectional_candidate_sha256':hashlib.sha256((ROOT/'src/simulator/candidate_sim/model.py').read_bytes()).hexdigest(),
        'energy_strict_candidate_sha256':hashlib.sha256((ROOT/'src/simulator/candidate_sim/model_energy_consistent.py').read_bytes()).hexdigest(),
        'boundary_violation_example':failure,'single_branch_zero_current_relaxation':reference_relax,
        'steady_900s_signed_torque_refinement':reference,
        'limitations':['DC power equation closes algebraically; this is not whole-vehicle thermodynamic conservation',
          'RC exact within each step assuming constant current and RC parameters; R1 changes between steps',
          'SOC clipping replaced by fail-closed rejection; no charge limiting/taper/regen curtailed implemented',
          'B04 leakage heat expression inherited; sign and chemical energy accounting not validated',
          'external DC injection is an ideal stress boundary, not a Porsche charger/drive operating mode',
          'same seeds generate initial branch heterogeneity; dt convergence alone is insufficient for external validity']}

if __name__=='__main__':
    r=compute();o=ROOT/'results/energy_consistency_adversarial.json';o.write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n');
    print(json.dumps({'status':r['classification'],'example':r['boundary_violation_example'],
         'results':{k:{'temp_old':v['original_final_module_mean_T_C'],'temp_new':v['strict_final_module_mean_T_C'],
         'rc_dissip_J':v['strict_total_rc_heat_J'],'RC_energy_residual_J':v['max_step_rc_energy_identity_error_J']} for k,v in r['steady_900s_signed_torque_refinement'].items()}},indent=2))
