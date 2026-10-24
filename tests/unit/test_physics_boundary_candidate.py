"""Proof-of-concept unit tests; do not count as pre-registered Stage 4 tests."""
import hashlib, importlib.util, math, sys, unittest
from pathlib import Path
from dataclasses import replace
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT / 'src' / 'simulator'))
from candidate_sim import model as candidate

ORIGINAL_PATH=ROOT / 'src/simulator/taycan_sim/model.py'
spec=importlib.util.spec_from_file_location('taycan_sim_original_frozen',ORIGINAL_PATH)
original=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=original
spec.loader.exec_module(original)

class BoundaryTests(unittest.TestCase):
    def test_frozen_original_is_untouched(self):
        expected='af4e576cf824d30ee6aa9b2fd1f2c18d576fd269027df67c43c5e7647266ff4e'
        self.assertEqual(hashlib.sha256(ORIGINAL_PATH.read_bytes()).hexdigest(),expected)

    def test_zero_input_exact_regression(self):
        for fault_id in ('H00','B06','M01','I01'):
            a=original.simulate(original.Fault(fault_id), original.ModelConfig(steps=24,seed=151,sensor_noise=True))
            b=candidate.simulate(candidate.Fault(fault_id), candidate.ModelConfig(steps=24,seed=151,sensor_noise=True))
            self.assertEqual(a.observations,b.observations)
            for old,new in zip(a.truth,b.truth):
                for key in old:
                    self.assertEqual(old[key],new[key],(fault_id,key))

    def test_charging_negative_current_and_soc_increase(self):
        params=candidate.ModelConfig(steps=180,dt_s=5,initial_soc=.6,
          sensor_noise=False,driver_torque_baseline=0.,driver_torque_swing=0.,
          driver_torque_fast_swing=0.,external_charge_power_W=40000.)
        s=candidate.simulate(p=params)
        self.assertTrue(all(x['real_pack_current_A']<0 for x in s.truth))
        self.assertGreater(s.truth[-1]['mean_hidden_soc'],s.truth[0]['mean_hidden_soc'])
        self.assertGreater(s.observations[-1]['TAYCAN_HVBAT_TOT_AH_CHRG'],0)
        self.assertEqual(s.observations[-1]['TAYCAN_HVBAT_TOT_AH_DCHRG'],0)
        self.assertTrue(all(r['power_charge_to_dc_bus_W']==40000 for r in s.truth))
        self.check_energy(s)

    def check_energy(self,s):
        for t in s.truth:
            estimate=(t['power_mechanical_W']+t['power_motor_loss_W']+
              t['power_inverter_loss_W']+t['power_gearbox_loss_W']+
              t['power_auxiliary_W']-t['power_charge_to_dc_bus_W'])
            self.assertAlmostEqual(estimate,t['power_requested_dc_W'],places=6)
            self.assertLess(abs(t['power_dc_W']-estimate),max(1e-4,abs(estimate)*1e-9))
            self.assertGreaterEqual(t['power_inverter_loss_W'],0)
            self.assertGreaterEqual(t['power_gearbox_loss_W'],0)

    def test_regen_signed_losses_and_torque_scale_before_copper(self):
        cfg=candidate.ModelConfig(steps=100,dt_s=2,initial_soc=.6,sensor_noise=False,
              external_charge_power_W=0,regeneration_torque_scale=1.5,
              traction_torque_scale=.85)
        raw=[(-95 if i%2==0 else 95) for i in range(cfg.steps)]
        s=candidate.simulate(p=cfg,torque_trace_nm=raw)
        self.assertTrue(any(x['real_pack_current_A']<0 for x in s.truth))
        self.assertTrue(any(x['real_pack_current_A']>0 for x in s.truth))
        self.assertAlmostEqual(s.observations[0]['TAYCAN_EM_TORQ_1']/cfg.front_torque_fraction,-95*1.5)
        self.assertAlmostEqual(s.observations[1]['TAYCAN_EM_TORQ_1']/cfg.front_torque_fraction,95*.85)
        self.check_energy(s)
        # Original model has negative inverter/gear losses in reverse mode.
        op=original.ModelConfig(steps=2,sensor_noise=False,driver_torque_baseline=-95,
                    driver_torque_swing=0,driver_torque_fast_swing=0)
        broken=original.simulate(p=op)
        self.assertLess(broken.truth[0]['power_inverter_loss_W'],0)
        self.assertLess(broken.truth[0]['power_gearbox_loss_W'],0)

    def test_cold_boundary(self):
        warm=candidate.simulate(p=candidate.ModelConfig(steps=45,sensor_noise=False,coolant_C=25,init_module_C=31))
        cold=candidate.simulate(p=candidate.ModelConfig(steps=45,sensor_noise=False,coolant_C=10,init_module_C=16))
        self.assertLess(cold.observations[0]['TAYCAN_BMS_T_AVG'],warm.observations[0]['TAYCAN_BMS_T_AVG'])
        self.check_energy(cold)

    def test_invalid_trace_and_power_fail(self):
        with self.assertRaises(ValueError):
            candidate.ModelConfig(external_charge_power_W=-200)
        with self.assertRaises(ValueError):
            candidate.simulate(p=candidate.ModelConfig(steps=5),torque_trace_nm=[0,1])
        with self.assertRaises(ValueError):
            candidate.simulate(p=candidate.ModelConfig(steps=5),torque_trace_nm=[0,1,float('nan'),0,0])

if __name__=='__main__':unittest.main(verbosity=2)
