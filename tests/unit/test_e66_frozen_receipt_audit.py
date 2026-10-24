"""Pure-stdlib adversarial E66 frozen receipt gates; no raw MAT data."""
import unittest
from scripts.audit_e66_frozen_receipts import classify

CRIT={"voltage_RMSE_V":0.05,
      "voltage_max_abs_error_V":0.15,
      "coverage_fraction_min":0.95,
      "numerical_refinement_V_max":0.005}
def row(**changes):
    data=dict(file="synthetic_test_not_real.mat",model="SPMe",
        voltage_RMSE_V=.046,voltage_max_error_V=.12,
        coverage_fraction=1.0,numerical_refinement_max_V=.002,
        gate="PASS",numerical_gate="PASS")
    data.update(changes)
    return data
class E66FrozenReceiptClassificationTests(unittest.TestCase):
    def test_pass_only_when_all_four_gates_present(self):
        self.assertEqual(classify(row(),CRIT)["status"],"PASS")
    def test_one_c_failure_cannot_be_promoted(self):
        r=classify(row(voltage_RMSE_V=.085,gate="FAIL"),CRIT)
        self.assertEqual(r["status"],"FAIL")
        self.assertIn("voltage_RMSE_V_THRESHOLD_EXCEEDED",r["reasons"])
    def test_refinement_gate_is_separately_binding(self):
        r=classify(row(numerical_refinement_max_V=.009,numerical_gate="FAIL"),CRIT)
        self.assertIn("REFINEMENT_THRESHOLD_EXCEEDED",r["reasons"])
    def test_missing_refinement_fails_closed(self):
        r=classify(row(numerical_refinement_max_V=None),CRIT)
        self.assertIn("REFINEMENT_UNAVAILABLE",r["reasons"])
    def test_short_solver_run_cannot_pass(self):
        r=classify(row(coverage_fraction=.7,gate="FAIL"),CRIT)
        self.assertIn("LOW_COVERAGE",r["reasons"])
if __name__=="__main__":unittest.main()
