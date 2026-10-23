"""All 12 diagnoses, exploratory 120-step train-only candidate integration.

NOT the formal Stage 4 12-episode six-hour smoke or any scored episode.
"""
from __future__ import annotations
import csv,json,math,sys,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'src/simulator'))
from candidate_sim import model as phys
from observation.observation_layer_candidate import transform_observed_rows,auxiliary_trace_candidate,APPROVED_OBD_IDS
from scripts.run_stage4_experiments import make_observation_config,feature_matrix,FEATURE_NAMES,MASK_NAMES,HYPOTHESES


def run():
    prereg=json.loads((ROOT/'experiments/stage_04_data_validation/REVISION_PREREG_ADDENDUM.json').read_text())
    with (ROOT/'experiments/stage_04_data_validation/STAGE4_EPISODE_MANIFEST.csv').open(newline='') as f:
        manifest=list(csv.DictReader(f))
    outcomes=[]
    for hypothesis in HYPOTHESES:
        row=next(x for x in manifest if x['hypothesis']==hypothesis and x['split']=='train')
        config=make_observation_config(row,prereg)
        steps=120; dt=5.0
        torque=[25+100*math.sin(i*dt/40)+14*math.cos(i*dt/15) for i in range(steps)]
        aux=auxiliary_trace_candidate(config,dt,steps)
        physics=phys.ModelConfig(seed=config['seeds']['physics'],steps=steps,dt_s=dt,initial_soc=.60,
            sensor_noise=False,acquisition_mode=config['acquisition_mode'],counter_source=config['counter_source'],
            diff_motor_t_mapping=config['diff_motor_t_mapping'],auxiliary_amplitude_W=0)
        sim=phys.simulate(phys.Fault(hypothesis,severity=float(row['severity']) if hypothesis!='H00' else 0),physics,
            torque_trace_nm=torque,auxiliary_trace_W=aux)
        observed,meta=transform_observed_rows(sim.observations,config,dt)
        assert all((set(a)-{'time_s','dt_s'})<=APPROVED_OBD_IDS for a in observed)
        features,diagnostics=feature_matrix(row['episode_id']+'_EXPLORATORY',observed,dt,counter_timing_verified=True)
        missing=[n for n in FEATURE_NAMES if features[n] is None]
        residual=max(abs(r['power_requested_dc_W']-r['power_dc_W']) for r in sim.truth)
        negative_loss=sum(int(r['power_inverter_loss_W']<0 or r['power_gearbox_loss_W']<0) for r in sim.truth)
        assert not negative_loss and residual<1e-7
        outcome={'hypothesis':hypothesis,'manifest_train_row':row['episode_id'],
            'severity':float(row['severity']) if hypothesis!='H00' else 0,
            'samples':steps,'dt_s':dt,'feature_names':len(FEATURE_NAMES),'mask_names':len(MASK_NAMES),
            'missing_features':missing,'missing_masks_raised':sum(features[k] for k in MASK_NAMES),
            'max_abs_power_balance_residual_W':residual,'negative_loss_steps':negative_loss,
            'F06_A':features['F06_mean_current_diff_A'],
            'F14_Ah':features['F14_net_Ah_counter_minus_BMS_integral_Ah'],
            'F28_kWh':features['F28_net_kWh_counter_minus_BMS_DC_integral_kWh'],
            'acquisition_mode':config['acquisition_mode'],'counter_source':config['counter_source'],
            'soc_initial_configured_pct':60.,'soc_final_hidden_pct':100*sim.truth[-1]['mean_hidden_soc'],
            'sensor_clippings':meta['soc_clipped_group_samples']}
        outcomes.append(outcome)
    out={'classification':'RESEARCH_PROBE_ONLY_NO_OFFICIAL_STAGE4_EPISODES',
        'note':'12 hypotheses use unique TRAIN-manifest nuisance seeds, a custom signed torque waveform, 120 x 5s. No score, no learning, no profile/charge calibration, no validation/test inputs.',
        'candidate_physics_sha256':hashlib.sha256((ROOT/'src/simulator/candidate_sim/model.py').read_bytes()).hexdigest(),
        'observation_candidate_sha256':hashlib.sha256((ROOT/'src/observation/observation_layer_candidate.py').read_bytes()).hexdigest(),
        'cases':outcomes}
    dest=ROOT/'results'/'candidate_12_hypothesis_probe.json'
    dest.write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    return out

if __name__=='__main__':
    r=run()
    print(json.dumps({'cases':len(r['cases']),'total_missing_features':sum(len(c['missing_features']) for c in r['cases']),
    'missing_cases':[(c['hypothesis'],c['missing_features']) for c in r['cases'] if c['missing_features']],
    'worst_balance_abs_W':max(c['max_abs_power_balance_residual_W'] for c in r['cases']),
    'negative_loss_steps':sum(c['negative_loss_steps'] for c in r['cases'])},indent=2))
