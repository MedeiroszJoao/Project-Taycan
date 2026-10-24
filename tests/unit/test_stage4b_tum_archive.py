"""Unit regression for read-only stage4B TUM archive inventory."""
import tempfile
import unittest
import zipfile
from pathlib import Path
from scripts.audit_stage4b_tum_archive import audit, SOURCE

class TestTUMArchiveAudit(unittest.TestCase):
    def test_safe_zip_structure_and_digest(self):
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/"m1774217_001.zip"
            with zipfile.ZipFile(f,"w",compression=zipfile.ZIP_DEFLATED) as z:
                z.writestr("test/run_01.csv","time,current_A\n0,1\n")
                z.writestr("README.txt","synthetic unit fixture")
            r=audit(f,include_sha256=True,verify_crc=True)
            self.assertEqual(r["file_count"],2)
            self.assertEqual(r["extensions"],{".csv":1,".txt":1})
            self.assertFalse(r["unsafe_members"])
            self.assertTrue(r["zip_testzip_passed"])
            self.assertEqual(len(r["sha256_archive"]),64)
            self.assertFalse(r["can_signal_table_verified"])
            self.assertFalse(r["vehicle_configuration_matched_to_target"])

    def test_reject_path_traversal(self):
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/"test.zip"
            with zipfile.ZipFile(f,"w") as z:
                z.writestr("../unsafe.csv","synthetic fixture")
            r=audit(f)
            self.assertTrue(r["unsafe_members"])

    def test_source_is_not_target_vehicle(self):
        self.assertEqual(SOURCE["reported_measurements"],92)
        self.assertIn("RWD",SOURCE["vehicle"])
        self.assertIn("NOT",SOURCE["vehicle"])

if __name__=="__main__":
    unittest.main()
