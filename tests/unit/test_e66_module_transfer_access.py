import unittest
import numpy as np
from scripts.transfer_e66_to_dev_module import read,trim_terminal_padding,FIELDS
class ModuleAccessTests(unittest.TestCase):
 def test_reserved_rejected_before_decoder(self):
  from scripts.audit_stage4b_e66_dev_only import VALIDATION,BLIND
  for name in VALIDATION|BLIND:
   with self.subTest(name=name),self.assertRaisesRegex(ValueError,'not development allowlist'):read(name)
 def test_unknown_path_rejected(self):
  with self.assertRaisesRegex(ValueError,'not development allowlist'):read('../20240209_0.7C_CP_Loss.mat')
 def test_only_fully_empty_terminal_row_removed(self):
  d={k:np.array([1.,2.,np.nan]) for k in FIELDS};out,n=trim_terminal_padding(d)
  self.assertEqual(n,1)
  for k in FIELDS:np.testing.assert_equal(out[k],[1,2])
 def test_partial_or_interior_missing_rows_not_deleted(self):
  d={k:np.array([1.,np.nan,3.]) for k in FIELDS};_,n=trim_terminal_padding(d);self.assertEqual(n,0)
  d={k:np.array([1.,2.,np.nan]) for k in FIELDS};d[FIELDS[0]][-1]=3
  _,n=trim_terminal_padding(d);self.assertEqual(n,0)
if __name__=='__main__':unittest.main()
