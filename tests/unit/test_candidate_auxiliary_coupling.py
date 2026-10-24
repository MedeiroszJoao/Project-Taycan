"""Candidate physical/observation coupling, NOT an official Stage 4 experiment."""
from pathlib import Path
import sys,unittest,dataclasses,math
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'src/simulator'))
from candidate_sim import model as candidate
from observation.observation_layer_candidate import auxiliary_trace_candidate

class CouplingTests(unittest.TestCase):
    def test_external_load_enters_battery_power_and_changes_soc(self):
        p=candidate.ModelConfig(steps=80,dt_s=5,initial_soc=.6,sensor_noise=False,auxiliary_mean_W=0,auxiliary_amplitude_W=0)
        lower=candidate.simulate(p=p,auxiliary_trace_W=[800.0]*p.steps)
        higher=candidate.simulate(p=p,auxiliary_trace_W=[4800.0]*p.steps)
        for a,b in zip(lower.truth,higher.truth):
            self.assertAlmostEqual(b['power_auxiliary_W']-a['power_auxiliary_W'],4000)
            self.assertAlmostEqual(b['power_requested_dc_W']-a['power_requested_dc_W'],4000)
            self.assertGreater(b['real_pack_current_A'],a['real_pack_current_A'])
            self.assertGreaterEqual(b['power_inverter_loss_W'],0)
            self.assertGreaterEqual(b['power_gearbox_loss_W'],0)
        self.assertLess(higher.truth[-1]['mean_hidden_soc'],lower.truth[-1]['mean_hidden_soc'])
        self.assertTrue(higher.metadata['auxiliary_trace_supplied'])

    def test_invalid_external_load_fails_closed(self):
        p=candidate.ModelConfig(steps=3,sensor_noise=False)
        for bad in ([1,2],[1,-2,3],[1,float('nan'),3]):
            with self.assertRaises(ValueError):
                candidate.simulate(p=p,auxiliary_trace_W=bad)

    def test_stochastic_auxiliary_trace_nonnegative_with_upper_cap(self):
        c={'counter_source':'BMS_I','acquisition_mode':'independent','diff_motor_t_mapping':'winding_proxy',
           'seeds':{'physics':1,'observer':2,'aux':3,'nuisance':4},
           'rpm_persistent_bias_by_channel_rpm':{k:0 for k in ('TAYCAN_EM_RPM_1','TAYCAN_EM_RPM_2','TAYCAN_ENG_MOTOR_RPM')},
           'torque_persistent_bias_by_channel_Nm':{k:0 for k in ('TAYCAN_EM_TORQ_1','TAYCAN_EM_TORQ_2')},
           'rpm_white_sigma_rpm':0,'torque_white_sigma_Nm':0,'soc_group_bias_sd_pp':0,
           'soc_innovation_pp_sqrt_s':0,'soc_phi_per_s':0.97,
           'aux_phi_per_s':0.9,'aux_white_sigma_W_sqrt_s':100,'aux_cap_W':500}
        a=auxiliary_trace_candidate(c,5,70)
        self.assertTrue(all(0<=x<=500 for x in a))
        self.assertEqual(a,auxiliary_trace_candidate(c,5,70))

if __name__=='__main__':unittest.main()
