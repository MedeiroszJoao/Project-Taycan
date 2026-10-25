import unittest
import numpy as np
from scripts.e66_module_observation_adapter import select_start


class AdapterSelectionTests(unittest.TestCase):
    def test_preparation_is_skipped(self):
        current = np.zeros(300)
        current[20:40] = -66
        current[100:110] = -158.4
        current[110:120] = 158.4
        self.assertEqual(select_start(current, 1.2), 100)

    def test_lower_rate_not_accepted_as_1p5c(self):
        current = np.zeros(100)
        current[20:30] = -132
        current[30:40] = 132
        with self.assertRaises(ValueError):
            select_start(current, 1.5)

    def test_positive_charge_is_not_alternating_onset(self):
        current = np.zeros(100)
        current[20:40] = 198
        with self.assertRaises(ValueError):
            select_start(current, 1.5)

    def test_quiet_baseline_required(self):
        current = np.full(100, 5.)
        current[20:30] = -198
        current[30:40] = 198
        with self.assertRaises(ValueError):
            select_start(current, 1.5)
