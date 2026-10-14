"""Unit tests for Stage 4 counter/sample alignment.

The H00/BMS_I fixture below is deterministic synthetic observation data, not a
physical-model run. The frozen Stage 3 counters begin accumulating at row 1,
while row 0 establishes the cumulative-counter baseline.
"""
from __future__ import annotations

import unittest

from scripts.run_stage4_experiments import feature_matrix


def h00_bms_i_observed_rows() -> list[dict[str, float]]:
    """Construct H00 observations with counter_source=BMS_I and nonzero I[0]."""
    dt_s = 5.0
    voltages = [720.0, 718.0, 721.0, 719.0]
    currents = [46.3, 23.5, -14.25, 9.75]
    ah_dis = ah_chg = kwh_dis = kwh_chg = 0.0
    rows: list[dict[str, float]] = []
    for i, (voltage, current) in enumerate(zip(voltages, currents)):
        if i >= 1:
            step_ah = current * dt_s / 3600.0
            step_kwh = voltage * current * dt_s / 3600000.0
            ah_dis += max(step_ah, 0.0)
            ah_chg += max(-step_ah, 0.0)
            kwh_dis += max(step_kwh, 0.0)
            kwh_chg += max(-step_kwh, 0.0)
        rows.append({
            "time_s": i * dt_s,
            "dt_s": dt_s,
            "TAYCAN_HVBAT_VOLT": voltage,
            "TAYCAN_BMS_I": current,
            "TAYCAN_HVBAT_CURRENT": current,
            "TAYCAN_HVBAT_TOT_AH_DCHRG": ah_dis,
            "TAYCAN_HVBAT_TOT_AH_CHRG": ah_chg,
            "TAYCAN_HVBAT_TOT_KWH_DCHRG": kwh_dis,
            "TAYCAN_HVBAT_TOT_KWH_CHRG": kwh_chg,
        })
    return rows


class CounterAlignmentTests(unittest.TestCase):
    def test_h00_bms_i_f14_f28_are_zero_to_1e_minus_9(self) -> None:
        # The nonzero first sample catches the original off-by-one bug.
        rows = h00_bms_i_observed_rows()
        self.assertNotEqual(rows[0]["TAYCAN_BMS_I"], 0.0)
        with self.subTest(hypothesis="H00", counter_source="BMS_I"):
            features, _ = feature_matrix("H00_BMS_I_COUNTER_TEST", rows, 5.0,
                                         counter_timing_verified=True)
            self.assertLess(abs(features["F14_net_Ah_counter_minus_BMS_integral_Ah"]), 1e-9)
            self.assertLess(abs(features["F28_net_kWh_counter_minus_BMS_DC_integral_kWh"]), 1e-9)
            self.assertEqual(features["mask_F14"], 0)
            self.assertEqual(features["mask_F28"], 0)

    def test_unverified_timing_masks_both_counter_features(self) -> None:
        features, _ = feature_matrix("H00_BMS_I_UNVERIFIED", h00_bms_i_observed_rows(), 5.0,
                                     counter_timing_verified=False)
        self.assertIsNone(features["F14_net_Ah_counter_minus_BMS_integral_Ah"])
        self.assertIsNone(features["F28_net_kWh_counter_minus_BMS_DC_integral_kWh"])
        self.assertEqual(features["mask_F14"], 1)
        self.assertEqual(features["mask_F28"], 1)


if __name__ == "__main__":
    unittest.main()
