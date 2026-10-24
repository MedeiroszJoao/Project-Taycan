"""No real E66 records: verify factor isolation and failure on truncated trajectories."""
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch

from scripts.diagnose_e66_1c_frozen_numerics import (
 CONFIGS,PAIRS,verify_original_receipts,compare_records,verify_baseline_archived)

try:
 import numpy as np
 HAVE_NUMPY=True
except ImportError:
 HAVE_NUMPY=False

@unittest.skipUnless(HAVE_NUMPY,"NumPy test in dedicated E66 numerical CI only")
class E66FrozenFactorialGuards(unittest.TestCase):
 def rec(self,achieved=100.0):
    return dict(summary=dict(target_duration_s=100.0,
       achieved_duration_s=achieved,coverage_fraction=achieved/100,
       complete_full_horizon=achieved>=100.0),sol=object())

 def test_four_fixed_factors(self):
    self.assertEqual(len(CONFIGS),4)
    a,b,c,d=(CONFIGS[k] for k in (
       "A_FROZEN","B_MESH_ONLY","C_TOL_ONLY","D_BOTH_ORIGINAL_COMPARATOR"))
    self.assertEqual(a["rtol"],b["rtol"])
    self.assertEqual(a["atol"],b["atol"])
    self.assertEqual(a["mesh"],c["mesh"])
    self.assertEqual(c["rtol"],d["rtol"])
    self.assertEqual(c["atol"],d["atol"])
    self.assertEqual(b["mesh"],d["mesh"])
    self.assertEqual(len(PAIRS),5)

 def test_identical_prefix_from_short_solver_must_not_pass(self):
    with patch("scripts.diagnose_e66_1c_frozen_numerics._voltage",
               side_effect=lambda _s,t:np.zeros(len(t))):
        r=compare_records(self.rec(70),self.rec(100))
    self.assertEqual(r["max_abs_difference_V"],0)
    self.assertTrue(r["tolerance_5mV_met_on_common_prefix"])
    self.assertFalse(r["eligible_as_full_numerical_convergence_evidence"])
    self.assertLess(r["common_duration_coverage"],.95)

 def test_full_horizon_can_be_compared(self):
    with patch("scripts.diagnose_e66_1c_frozen_numerics._voltage",
               side_effect=lambda _s,t:np.zeros(len(t))):
        r=compare_records(self.rec(100),self.rec(100))
    self.assertTrue(r["eligible_as_full_numerical_convergence_evidence"])
    self.assertEqual(r["compared_count"],500)

 def test_baseline_repro_mismatch_fails(self):
    original=[dict(time_s=float(t),model_V=3.6)
              for t in np.linspace(0,100,500)]
    with patch("scripts.diagnose_e66_1c_frozen_numerics._voltage",
               side_effect=lambda _s,t:np.full(len(t),3.5)):
        r=verify_baseline_archived(self.rec(100),dict(trajectory=original))
    self.assertEqual(r["status"],"FAIL")
    self.assertGreater(r["max_V_difference_V"],1e-5)

 def test_missing_work_json_stops(self):
    with tempfile.TemporaryDirectory() as td:
        with self.assertRaises(FileNotFoundError):
            verify_original_receipts(Path(td),Path(td)/"missing_data.zip")
if __name__=="__main__":unittest.main()
