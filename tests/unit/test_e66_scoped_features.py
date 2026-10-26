import unittest
from scripts.audit_e66_extended_validation import module_features

class ScopedModuleFeatureTests(unittest.TestCase):
    def test_constant_power_energy_and_masks(self):
        f=module_features([0,1,2],[24,24,24],[10,10,10])
        self.assertAlmostEqual(f['F20_integrated_observed_HV_kWh'],480/3600000)
        self.assertEqual(f['F21_negative_DC_power_fraction'],0)
        self.assertEqual(sum(f['mask_F%02d'%i]==0 for i in range(1,29)),2)

    def test_charge_sign_is_negative_power(self):
        f=module_features([0,1,2],[24,24,24],[-10,-10,-10])
        self.assertLess(f['F20_integrated_observed_HV_kWh'],0)
        self.assertEqual(f['F21_negative_DC_power_fraction'],1)

    def test_counters_never_synthesized(self):
        f=module_features([0,1],[24,24],[10,10])
        for code,name in [('F14','net_Ah_counter_minus_BMS_integral_Ah'),('F28','net_kWh_counter_minus_BMS_DC_integral_kWh')]:
            self.assertIsNone(f[code+'_'+name])
            self.assertEqual(f['mask_'+code],1)
