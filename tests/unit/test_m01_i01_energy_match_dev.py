"""Analytic toy-model energy map tests (development only, NOT official receipts)."""
from pathlib import Path
import math,sys,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'src/simulator'))
from scripts.m01_i01_energy_match_development import analytic_mapping
from scripts.duty_cycle_candidate import build_duty_inputs
from candidate_sim import model_energy_consistent as m

class MatchedEnergyTests(unittest.TestCase):
    def test_complete_registered_mapping_grid_shape(self):
        r=analytic_mapping()
        self.assertEqual(len(r['entries']),12)
        ks={(e['profile_id'],e['diff_motor_t_mapping'],e['m01_severity']) for e in r['entries']}
        self.assertEqual(len(ks),12)
        self.assertEqual({e['match_status'] for e in r['entries']},{'MATCHED'})

    def test_map_has_no_lookahead_or_observation_coupling(self):
        r=analytic_mapping()
        for p in r['profile_parameters']:
            a=[e for e in r['entries'] if e['profile_id']==p and e['diff_motor_t_mapping']=='winding_proxy']
            b=[e for e in r['entries'] if e['profile_id']==p and e['diff_motor_t_mapping']=='uninformative']
            self.assertEqual([e['i01_severity_used'] for e in a],[e['i01_severity_used'] for e in b])
            for x in a:
                self.assertGreater(x['i01_severity_used'],0.)
                self.assertLessEqual(x['i01_severity_used'],1.)
                self.assertLess(x['mismatch_pct'],1e-9)

    def test_expected_loss_formula_against_2_step_physics(self):
        p=m.ModelConfig(steps=2,dt_s=5,initial_soc=.6,sensor_noise=False)
        torques=[-90,105];rpms=[2500,2500]
        h=m.simulate(m.Fault('H00',severity=0),p,torque_trace_nm=torques,rpm_trace_rpm=rpms)
        motor=m.simulate(m.Fault('M01',severity=.5),p,torque_trace_nm=torques,rpm_trace_rpm=rpms)
        inv=m.simulate(m.Fault('I01',severity=.2),p,torque_trace_nm=torques,rpm_trace_rpm=rpms)
        for i in range(2):
            deltaM=motor.truth[i]['power_motor_loss_W']-h.truth[i]['power_motor_loss_W']
            deltaI=inv.truth[i]['power_inverter_loss_W']-h.truth[i]['power_inverter_loss_W']
            self.assertAlmostEqual(deltaM,.5*p.motor_copper_coeff_w_per_nm2*torques[i]**2,delta=1e-9)
            self.assertAlmostEqual(deltaI,.2*p.inverter_fault_extra_W,delta=1e-9)

    def test_precommitted_torque_input_has_exact_time_grid(self):
        for profile in ('NOMINAL_6H','SHIFT_REGEN_COLD_6H'):
            d=build_duty_inputs(dt_s=5,charge_power_kw=0,profile_id=profile)
            self.assertEqual(len(d.torque_nm),4320)
            self.assertEqual(sum(x=='regeneration' for x in d.mode),864)
            self.assertTrue(all(t<0 for t,x in zip(d.torque_nm,d.mode) if x=='regeneration'))

if __name__=='__main__': unittest.main()
