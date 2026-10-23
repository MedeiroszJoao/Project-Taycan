"""Prospective Stage4A activity-gated M01/I01 loss matching, by construction.

This is an algebraic identity of assumed injection laws, NOT real fault equivalence.
"""
import math,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/"src"),str(ROOT/"src/simulator")]
from candidate_sim import model_4a_activity_gated as phys
from scripts.duty_cycle_candidate import build_duty_inputs

class ActivityGatedEnergyMatch(unittest.TestCase):
 def test_matched_injected_energy_in_12_prospective_combinations(self):
  cfg=phys.ModelConfig()
  expected={"NOMINAL_6H":.09882981940668557,
            "SHIFT_REGEN_COLD_6H":.10643684785638745}
  n=0
  for profile in expected:
   d=build_duty_inputs(dt_s=5.,charge_power_kw=0.,profile_id=profile)
   active=[abs(t)>1e-9 and abs(r)>1e-9 for t,r in zip(d.torque_nm,d.rpm)]
   self.assertEqual(sum(active),2592)
   self.assertTrue(all(not active[i] for i,m in enumerate(d.mode) if m in ("rest","charge")))
   m01_unit=sum(cfg.motor_copper_coeff_w_per_nm2*(cfg.motor_loss_fault_multiplier-1)*t*t*5
                for t in d.torque_nm)
   i01_unit=sum(cfg.inverter_fault_extra_W*5 for is_active in active if is_active)
   ratio=m01_unit/i01_unit
   self.assertAlmostEqual(ratio,expected[profile],places=12)
   for mapping in ("winding_proxy","uninformative"):
    for sev_m in (.25,.5,1.):
     with self.subTest(profile=profile,mapping=mapping,sev_m=sev_m):
      sev_i=ratio*sev_m
      self.assertLessEqual(sev_i,1.)
      self.assertAlmostEqual(m01_unit*sev_m,i01_unit*sev_i,delta=1e-7)
      n+=1
  self.assertEqual(n,12)
 def test_old_always_on_mapping_not_equivalent(self):
  for profile in ("NOMINAL_6H","SHIFT_REGEN_COLD_6H"):
   d=build_duty_inputs(dt_s=5.,charge_power_kw=0.,profile_id=profile)
   active=sum(abs(t)>1e-9 and abs(r)>1e-9 for t,r in zip(d.torque_nm,d.rpm))
   self.assertEqual(active/len(d.mode),.6)
   self.assertAlmostEqual(len(d.mode)/active,5/3)
if __name__=="__main__":unittest.main()
