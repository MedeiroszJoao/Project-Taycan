import unittest
import numpy as np
from scripts.e66_extended_validation import a_law, ModelConfig

class ExtendedReplayTests(unittest.TestCase):
    def test_zero_current_keeps_voltage_and_soc(self):
        t=np.arange(101.); v,z=a_law(t,np.zeros(101),3.8,30,0)
        np.testing.assert_allclose(v,3.8,atol=1e-12)
        np.testing.assert_allclose(z,z[0],atol=1e-12)

    def test_discharge_matches_exact_constant_current_solution(self):
        t=np.arange(101.); p=ModelConfig(); current=10.
        v,z=a_law(t,np.full(101,-2*current),3.8,25,0)
        expected=3.8-p.ocv_span_v*current*t/(3600*p.capacity_ah_cell)-current*p.r0_ohm_cell-current*p.r1_ohm_cell*(1-np.exp(-t/p.rc_tau_s))
        np.testing.assert_allclose(v,expected,atol=1e-12)
        self.assertLess(z[-1],z[0])

    def test_charge_uses_opposite_sign(self):
        v,z=a_law(np.arange(101.),np.full(101,20.),3.8,25,0)
        self.assertGreater(v[0],3.8)
        self.assertGreater(z[-1],z[0])

    def test_domain_violation_is_not_clamped(self):
        _,z=a_law(np.array([0.,3600.]),np.array([1000.,1000.]),3.8,25,0)
        self.assertGreater(z[-1],1)
