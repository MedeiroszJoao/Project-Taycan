"""Adversarial fault-energy activity sensitivity, never official scoring."""
from __future__ import annotations
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src/simulator"))
from scripts.audit_stage4_m01_i01_modes import inspect_profile  # noqa: E402
from candidate_sim import model_energy_consistent as physical  # noqa: E402


class InverterModeSensitivityTests(unittest.TestCase):
    def test_research_duty_has_forty_percent_stationary_time(self):
        for profile in ("NOMINAL_6H", "SHIFT_REGEN_COLD_6H"):
            with self.subTest(profile=profile):
                x = inspect_profile(profile)
                self.assertEqual(x["stationary_duration_s"], 8640)
                self.assertEqual(x["active_duration_s"], 12960)
                self.assertAlmostEqual(
                    x["stationary_fraction_of_I01_matched_loss"], 0.4, places=12
                )

    def test_current_I01_candidate_injects_loss_while_stationary(self):
        p = physical.ModelConfig(
            seed=505, initial_soc=.6, dt_s=5, steps=2,
            auxiliary_amplitude_W=0, sensor_noise=False,
        )
        zero_torque = [0.0, 0.0]
        zero_rpm = [0.0, 0.0]
        nominal = physical.simulate(
            physical.Fault("H00", severity=0), p,
            torque_trace_nm=zero_torque, rpm_trace_rpm=zero_rpm,
        )
        inverter = physical.simulate(
            physical.Fault("I01", severity=1.0), p,
            torque_trace_nm=zero_torque, rpm_trace_rpm=zero_rpm,
        )
        for a, b in zip(nominal.truth, inverter.truth):
            self.assertEqual(a["power_mechanical_W"], 0)
            self.assertEqual(b["power_mechanical_W"], 0)
            self.assertAlmostEqual(
                b["power_inverter_loss_W"] - a["power_inverter_loss_W"],
                1600.0, delta=1e-10,
            )

    def test_gated_counterfactual_requires_five_thirds_severity(self):
        for profile in ("NOMINAL_6H", "SHIFT_REGEN_COLD_6H"):
            with self.subTest(profile=profile):
                x = inspect_profile(profile)
                self.assertAlmostEqual(
                    x["I01_matched_severity_activity_gated"]
                    / x["I01_matched_severity_always_on"],
                    5/3, places=12,
                )
                self.assertAlmostEqual(
                    x["I01_matched_severity_always_on"]
                    * x["I01_full_injection_energy_at_severity_1_J"],
                    x["M01_injected_extra_energy_J"], delta=1e-6,
                )
                self.assertAlmostEqual(
                    x["I01_matched_severity_activity_gated"]
                    * x["I01_gated_energy_at_severity_1_J"],
                    x["M01_injected_extra_energy_J"], delta=1e-6,
                )

    def test_severity_bounds_and_illustrative_nominal_values(self):
        x=inspect_profile("NOMINAL_6H")
        self.assertAlmostEqual(
            x["I01_matched_severity_always_on"], 0.059297892,
            delta=1e-6,
        )
        self.assertAlmostEqual(
            x["I01_matched_severity_activity_gated"], 0.09882982,
            delta=1e-6,
        )
        for wrong in (0, 1.01, -0.2):
            with self.assertRaises(ValueError):
                inspect_profile("NOMINAL_6H", wrong)


if __name__ == "__main__":
    unittest.main()
