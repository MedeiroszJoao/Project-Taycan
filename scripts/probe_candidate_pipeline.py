"""Exploratory only: do NOT treat as Stage 4 runner or scored protocol output.

A candidate physical model (different SHA) is combined with the new synthetic
observation candidate. Uses only preregistered TRAIN rows to exercise interface.
No frozen files are changed, no validation/test outcomes inspected.
"""
from __future__ import annotations
import csv, json, math, sys, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'src/simulator'))
from candidate_sim import model as phys
from observation.observation_layer_candidate import transform_observed_rows, auxiliary_trace_candidate
from scripts.run_stage4_experiments import make_observation_config,feature_matrix,FEATURE_NAMES,MASK_NAMES


def run_probes():
    prereg=json.loads((ROOT/'experiments/stage_04_data_validation/REVISION_PREREG_ADDENDUM.json').read_text())
    with (ROOT/'experiments/stage_04_data_validation/STAGE4_EPISODE_MANIFEST.csv').open(newline='') as fp:
        rows=list(csv.DictReader(fp))
    report={'classification':'EXPLORATORY_NONSCORING_NOT_STAGE4','model_sha256': hashlib.sha256((ROOT/'src/simulator/candidate_sim/model.py').read_bytes()).hexdigest(),
            'frozen_model_sha256':hashlib.sha256((ROOT/'src/simulator/taycan_sim/model.py').read_bytes()).hexdigest(),
            'observation_layer_candidate_sha256':hashlib.sha256((ROOT/'src/observation/observation_layer_candidate.py').read_bytes()).hexdigest(),
            'probes':[]}
    for name in ('H00','B06'):
        row=next(r for r in rows if r['split']=='train' and r['hypothesis']==name)
        config=make_observation_config(row,prereg)
        steps=120;dt=5
        torque_trace=[25+100*math.sin(i*dt/40)+14*math.cos(i*dt/15) for i in range(steps)]
        aux=auxiliary_trace_candidate(config,dt,steps)
        modelcfg=phys.ModelConfig(steps=steps,dt_s=dt,seed=config['seeds']['physics'], initial_soc=.60,
                                 sensor_noise=False,counter_source=config['counter_source'],
                                 acquisition_mode=config['acquisition_mode'],
                                 diff_motor_t_mapping=config['diff_motor_t_mapping'],auxiliary_amplitude_W=0)
        sim=phys.simulate(phys.Fault(name,severity=0.0 if name=='H00' else float(row['severity'])),modelcfg,
                          torque_trace_nm=torque_trace,auxiliary_trace_W=aux)
        observed,detail=transform_observed_rows(sim.observations,config,dt)
        assert not any('truth' in k or k.startswith('real_') for x in observed for k in x)
        features,diagnostics=feature_matrix(row['episode_id']+'_EXPLORATORY',observed,dt,counter_timing_verified=True)
        assert all(k in features for k in FEATURE_NAMES+MASK_NAMES)
        power_residual=max(abs(t['power_dc_W']-t['power_requested_dc_W']) for t in sim.truth)
        negative_losses=sum(t['power_inverter_loss_W']<0 or t['power_gearbox_loss_W']<0 for t in sim.truth)
        result={
            'source_manifest_episode_id':row['episode_id'], 'hypothesis':name,
            'sample_count':steps,'dt_s':dt,'time_span_s':(steps-1)*dt,
            'profile':'custom_signed_torque_exploration_NOT_NOMINAL_6H',
            'auxiliary_physically_coupled_in_candidate':True,
            'counter_source':config['counter_source'], 'acquisition_mode':config['acquisition_mode'],
            'feature_count':len(FEATURE_NAMES),'mask_count':len(MASK_NAMES),
            'num_missing_features':sum(features[k] is None for k in FEATURE_NAMES),
            'F14_Ah':features['F14_net_Ah_counter_minus_BMS_integral_Ah'],
            'F28_kWh':features['F28_net_kWh_counter_minus_BMS_DC_integral_kWh'],
            'F06_current_diff_A':features['F06_mean_current_diff_A'],
            'power_balance_max_abs_W':power_residual,
            'negative_dissipative_losses_step_count':negative_losses,
            'physical_SOC_first':sim.truth[0]['mean_hidden_soc'],
            'physical_SOC_last':sim.truth[-1]['mean_hidden_soc'],
            'measurement_clip_count':detail['soc_clipped_group_samples'],
            'not_stage4_approval':True
        }
        assert negative_losses==0 and power_residual<1e-6
        report['probes'].append(result)
    out=ROOT/'results/candidate_pipeline_probe.json'
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return report

if __name__=='__main__':
    print(json.dumps(run_probes(),indent=2,ensure_ascii=False))
