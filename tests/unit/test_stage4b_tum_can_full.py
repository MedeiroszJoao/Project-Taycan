"""Read-only TUM CSV audit: synthetic fixtures, no real recordings in repository."""
import tempfile
import unittest
from pathlib import Path
from scripts.audit_stage4b_tum_can_full import parse_num,analyze_csv,EXPECTED_HEADER

class TestTUMCANFullAudit(unittest.TestCase):
    def test_nan_and_infinity_cannot_count_as_measurements(self):
        for x in ("","NaN"," nan ","Infinity","inf","-inf","n/a","none","null"):
            self.assertIsNone(parse_num(x))
        self.assertEqual(parse_num(" -1.42000000000007 "),-1.42000000000007)

    def test_missing_coverage_timing_and_envelope(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/"synthetic.csv"
            path.write_text("time,hv_soc,hv_current,hv_voltage,vehicle_speed\n"
                "0,60,-1.4,800,0\n"
                "0.1,,2.3,800,10\n"
                "0.2,101,NaN,-30,20\n")
            r=analyze_csv(path)
            self.assertEqual(r["rows"],3)
            self.assertEqual(r["dt_seconds_modes"][0][0],0.1)
            self.assertEqual(r["channel_stats"]["hv_soc"]["valid"],2)
            self.assertAlmostEqual(r["channel_stats"]["hv_soc"]["coverage"],2/3)
            self.assertEqual(r["soc_outside_0_100"],1)
            self.assertEqual(r["voltage_nonpositive"],1)
            self.assertEqual(r["nonincreasing_time_steps"],0)
            self.assertEqual(r["duration_s"],0.2)
            self.assertEqual(len(r["source_sha256"]),64)

    def test_nonmonotonic_time_is_explicit(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/"synthetic.csv"
            path.write_text("time,hv_soc\n0,50\n0.1,51\n0.1,52\n")
            r=analyze_csv(path)
            self.assertEqual(r["nonincreasing_time_steps"],1)
if __name__=="__main__":
    unittest.main()
