import unittest
import numpy as np
from scripts.validate_e66_reserved_module_sessions import read,select_charge
class ReservedBoundaryTests(unittest.TestCase):
 def test_final_blind_files_stay_rejected(self):
  from scripts.audit_stage4b_e66_dev_only import BLIND
  for name in BLIND:
   with self.subTest(name=name),self.assertRaisesRegex(ValueError,'outside explicit validation allowlist'):read(name)
 def test_preparation_current_is_not_main_charge(self):
  current=np.zeros(400);current[70:90]=66;current[200:]=198
  self.assertEqual(select_charge(current),195)
 def test_no_quiet_condition_is_rejected(self):
  with self.assertRaises(ValueError):select_charge(np.ones(400)*198)
 def test_charge_start_includes_five_ramp_samples(self):
  current=np.zeros(300);current[100:]=198
  self.assertEqual(select_charge(current),95)
if __name__=='__main__':unittest.main()
