"""Pure-stdlib adversarial E66 frozen receipt gates; no raw MAT data."""
import unittest,math
from scripts.audit_e66_frozen_receipts import classify,check_numeric_trajectory

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
    def mock_trajectory(self):
        series=[{"time_s":float(i),"model_V":3.6+0.001*i,
                 "measured_V":3.55+0.001*i} for i in range(500)]
        return dict(trajectory=series,experimental={"duration_s":499.0},
            voltage_RMSE_V=.05,voltage_bias_V=.05,voltage_max_error_V=.05,
            coverage_fraction=1.0)
    def test_recalculate_exact_saved_voltage_metrics(self):
        self.assertEqual(check_numeric_trajectory(self.mock_trajectory())["status"],"PASS")
    def test_reject_reported_rmse_not_supported_by_saved_trace(self):
        r=self.mock_trajectory()
        r["voltage_RMSE_V"]=0.001
        q=check_numeric_trajectory(r)
        self.assertEqual(q["status"],"FAIL")
        self.assertIn("voltage_RMSE_V",q["differences"])
    def test_reject_missing_trajectory_even_if_claimed_pass(self):
        r=self.mock_trajectory();r.pop("trajectory")
        self.assertEqual(check_numeric_trajectory(r)["status"],"FAIL")
    def test_reject_early_termination_falsely_claimed_complete(self):
        r=self.mock_trajectory();r["experimental"]["duration_s"]=1000.
        self.assertEqual(check_numeric_trajectory(r)["status"],"FAIL")
        self.assertIn("coverage_fraction",check_numeric_trajectory(r)["differences"])
    def test_reject_nonmonotone_trajectory(self):
        r=self.mock_trajectory();r["trajectory"][5]["time_s"]=r["trajectory"][4]["time_s"]
        self.assertEqual(check_numeric_trajectory(r)["status"],"FAIL")
if __name__=="__main__":unittest.main()
