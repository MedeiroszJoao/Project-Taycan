"""Verify the sealed Stage 4 input files, without requiring the physical backend."""
from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

from scripts.run_stage4_experiments import EXPECTED, ROOT, STAGE4, load_manifest, BASE_OBSERVED_CHANNELS

class Stage4ManifestSealTests(unittest.TestCase):
    def test_sealed_manifest_prereg_amendment_and_freeze_sha256(self) -> None:
        items = {
            "prereg_sha256": STAGE4 / "REVISION_PREREG_ADDENDUM.json",
            "amendment_sha256": STAGE4 / "STAGE4_APPEND_ONLY_AMENDMENT.json",
            "manifest_sha256": STAGE4 / "STAGE4_EPISODE_MANIFEST.csv",
            "freeze_sha256": STAGE4 / "freeze.json",
        }
        for expected_key, path in items.items():
            with self.subTest(path=str(path)):
                self.assertTrue(path.is_file(), str(path))
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), EXPECTED[expected_key])

    def test_manifest_full_contract_without_physical_backend(self) -> None:
        rows, prereg, amendment = load_manifest()
        self.assertEqual(len(rows), 2232)
        self.assertEqual({r["split"] for r in rows}, {"train", "validation", "test"})
        self.assertEqual(len({r["episode_id"] for r in rows}), len(rows))
        self.assertEqual(set(r["hypothesis"] for r in rows), {"H00", "B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B09", "M01", "I01"})
        self.assertIsInstance(prereg, dict)
        self.assertIsInstance(amendment, dict)

    def test_display_soc_not_permitted_as_observed_predictor(self) -> None:
        self.assertNotIn("TAYCAN_HVBAT_SOC_DISP", BASE_OBSERVED_CHANNELS)

if __name__ == "__main__":
    unittest.main()
