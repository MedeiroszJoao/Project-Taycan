"""Adversarial regression tests for conditional Jacobian diagnostics."""
import importlib.util
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
try:
 import numpy as np
 from scripts.e66_absolute_jacobian_audit import svd_report
 AVAILABLE=True
except ImportError:AVAILABLE=False
@unittest.skipUnless(AVAILABLE,'numpy/scipy scientific dependencies unavailable')
class AbsoluteJacobianDiagnostics(unittest.TestCase):
 def test_normalized_rank_invariant_to_parameter_units(self):
  x=np.column_stack([np.ones(20),np.linspace(-1,1,20),np.arange(20)%2])
  a=svd_report(x);b=svd_report(x*np.array([1e3,.001,100]))
  self.assertEqual(a['rank_unit_column_threshold_1e_3'],3)
  np.testing.assert_allclose(a['singular_values_unit_column'],b['singular_values_unit_column'],atol=1e-12)
 def test_zero_contact_column_not_silently_full_rank(self):
  x=np.column_stack([np.ones(20),np.arange(20),np.zeros(20)])
  a=svd_report(x);self.assertEqual(a['rank_default'],2);self.assertIsNone(a['condition_unit_column'])
 def test_analytic_contact_direction_and_absolute_step_at_boundary(self):
  current=np.array([.25,1.7]);r=2.6387202740172146e-16;voltage=np.array([4.,3.5])
  for h in [.001,.0001]:
   derivative=((voltage-current*(r+h))-(voltage-current*r))/h
   np.testing.assert_allclose(derivative,-current,atol=1e-10)
  relative=((voltage-current*(r+r*.001))-(voltage-current*r))/(r*.001)
  np.testing.assert_array_equal(relative,np.zeros(2))
if __name__=='__main__':unittest.main()
