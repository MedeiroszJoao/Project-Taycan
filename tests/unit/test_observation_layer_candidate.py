"""Only the exploratory observation candidate; NEVER a recovered Stage 4 layer."""
from __future__ import annotations

import csv
import json
import math
import sys
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'src' / 'simulator'))
sys.path.insert(0, str(ROOT))
from observation.observation_layer_candidate import (  # noqa: E402
    transform_observed_rows, auxiliary_trace_candidate, exact_ou_transition,
    CURRENT, RPM_CHANNELS,
)
from taycan_sim import ModelConfig, Fault, simulate  # noqa: E402
from scripts.run_stage4_experiments import make_observation_config, feature_matrix, FEATURE_NAMES, MASK_NAMES  # noqa: E402


class ObservationCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest = ROOT / 'experiments/stage_04_data_validation/STAGE4_EPISODE_MANIFEST.csv'
        prereg = ROOT / 'experiments/stage_04_data_validation/REVISION_PREREG_ADDENDUM.json'
        with manifest.open(newline='') as fp:
            cls.episode = next(csv.DictReader(fp))
        cls.prereg = json.loads(prereg.read_text())
        cls.cfg = make_observation_config(cls.episode, cls.prereg)
        cls.dt_s = 5.0
        cls.base = simulate(Fault('H00'), ModelConfig(seed=cls.cfg['seeds']['physics'], sensor_noise=False,
                      steps=60, dt_s=cls.dt_s, initial_soc=.60,
                      acquisition_mode=cls.cfg['acquisition_mode'],counter_source=cls.cfg['counter_source'])).observations

    def test_manifest_nuisance_config_and_output_reproducible(self):
        a, meta = transform_observed_rows(self.base, self.cfg, self.dt_s)
        b, _ = transform_observed_rows([dict(reversed(list(row.items()))) for row in self.base], self.cfg, self.dt_s)
        self.assertEqual(a, b)
        self.assertEqual(meta['num_steps'], len(self.base))
        self.assertEqual(meta['auxiliary_energy_coupling'].split(';')[0], 'NOT_IMPLEMENTED')

    def test_auxiliary_is_separate_stream_and_changes_only_on_aux_seed(self):
        cfg = self.cfg
        first = auxiliary_trace_candidate(cfg, self.dt_s, len(self.base))
        changed = {**cfg, 'seeds': {**cfg['seeds'], 'aux': cfg['seeds']['aux'] + 1}}
        self.assertNotEqual(first, auxiliary_trace_candidate(changed, self.dt_s, len(self.base)))
        self.assertEqual(transform_observed_rows(self.base, cfg, self.dt_s)[0],
                         transform_observed_rows(self.base, changed, self.dt_s)[0])
        changed_obs = {**cfg, 'seeds': {**cfg['seeds'], 'observer': cfg['seeds']['observer'] + 1}}
        self.assertEqual(first, auxiliary_trace_candidate(changed_obs, self.dt_s, len(self.base)))
        self.assertNotEqual(transform_observed_rows(self.base, cfg, self.dt_s)[0],
                            transform_observed_rows(self.base, changed_obs, self.dt_s)[0])

    def test_noise_disabled_exact_baseline_except_explicit_counter_timings(self):
        c = {**self.cfg, 'sensor_noise_enabled': False}
        rows, _ = transform_observed_rows(self.base, c, self.dt_s)
        for old, new in zip(self.base,rows):
            for k in ('TAYCAN_BMS_SOC','TAYCAN_HVBAT_VOLT', *RPM_CHANNELS, *CURRENT):
                self.assertEqual(old[k],new[k])

    def test_shared_currents_share_one_draw_independent_separate(self):
        c = {**self.cfg, 'acquisition_mode': 'shared'}
        shared,_=transform_observed_rows(self.base,c,self.dt_s)
        self.assertTrue(all(row[CURRENT[0]]==row[CURRENT[1]] for row in shared))
        indep,_=transform_observed_rows(self.base,{**c,'acquisition_mode':'independent'},self.dt_s)
        self.assertTrue(any(abs(row[CURRENT[0]]-row[CURRENT[1]])>1e-6 for row in indep))

    def test_persistent_bias_and_no_double_white(self):
        c={**self.cfg,'rpm_white_sigma_rpm':0.0,'torque_white_sigma_Nm':0.0,
            'rpm_persistent_bias_by_channel_rpm': {k:7.0 for k in RPM_CHANNELS},
            'torque_persistent_bias_by_channel_Nm': {'TAYCAN_EM_TORQ_1':3.0,'TAYCAN_EM_TORQ_2':-3.0}}
        out,_=transform_observed_rows(self.base,c,self.dt_s)
        for old,new in zip(self.base,out):
            self.assertAlmostEqual(new['TAYCAN_EM_RPM_1']-old['TAYCAN_EM_RPM_1'],7.0)
            self.assertAlmostEqual(new['TAYCAN_EM_TORQ_2']-old['TAYCAN_EM_TORQ_2'],-3.0)

    def test_f14_f28_alignment_and_28_features_28_masks(self):
        observed,_=transform_observed_rows(self.base,self.cfg,self.dt_s)
        feat,diag=feature_matrix('PROBE_ONLY',observed,self.dt_s,counter_timing_verified=True)
        self.assertEqual(len(FEATURE_NAMES),28)
        self.assertEqual(len(MASK_NAMES),28)
        self.assertTrue(all(k in feat for k in [*FEATURE_NAMES,*MASK_NAMES]))
        self.assertLess(abs(feat['F14_net_Ah_counter_minus_BMS_integral_Ah']),1e-9)
        self.assertLess(abs(feat['F28_net_kWh_counter_minus_BMS_DC_integral_kWh']),1e-9)
        self.assertEqual(feat['mask_F14'],0)
        self.assertEqual(feat['mask_F28'],0)

    def test_hv_current_counter_is_not_oracle_and_exposes_f14_difference(self):
        c={**self.cfg,'counter_source':'HVBAT_CURRENT','acquisition_mode':'independent'}
        observed,_=transform_observed_rows(self.base,c,self.dt_s)
        feat,_=feature_matrix('PROBE_ONLY',observed,self.dt_s,counter_timing_verified=True)
        self.assertGreater(abs(feat['F14_net_Ah_counter_minus_BMS_integral_Ah']),1e-8)
        self.assertNotEqual(feat['mask_F14'],1)

    def test_truth_counter_and_latent_truth_rejected(self):
        c={**self.cfg,'counter_source':'truth'}
        with self.assertRaises(ValueError):
            transform_observed_rows(self.base,c,self.dt_s)
        bad=list(self.base)
        bad[0]={**bad[0], 'fault_label':'B06'}
        with self.assertRaises(ValueError):
            transform_observed_rows(bad,self.cfg,self.dt_s)

    def test_exact_ou_dt_and_bounds(self):
        phi=.97;sigma=.05
        a,sd=exact_ou_transition(phi,sigma,5.0)
        self.assertAlmostEqual(a,phi**5,12)
        self.assertGreater(sd,0)
        self.assertLess(sd,sigma*math.sqrt(5.0))
        with self.assertRaises(ValueError):
            exact_ou_transition(1.001,sigma,5.0)

    def test_nonfinite_input_fails_closed(self):
        bad=[dict(r) for r in self.base]
        bad[1]['TAYCAN_HVBAT_VOLT']=float('nan')
        with self.assertRaises(ValueError):
            transform_observed_rows(bad,self.cfg,self.dt_s)

if __name__=='__main__':unittest.main()
