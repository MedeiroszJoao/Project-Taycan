"""Stage 4 preregistration/manifest integrity gates; no physical simulation run.

The dataset is already sealed. These tests only read existing data files and
verify their byte hashes, schema, seeds, and deterministic nuisance draws.
"""
from __future__ import annotations

import collections
import hashlib
import unittest

from scripts import run_stage4_experiments as r


class Stage4SealedInputsTests(unittest.TestCase):
    def test_sealed_inputs_byte_hashes(self) -> None:
        for name, path in (
            ("prereg", r.PREREG_PATH),
            ("amendment", r.AMENDMENT_PATH),
            ("manifest", r.MANIFEST_PATH),
        ):
            self.assertTrue(path.is_file(), f"Missing {name}: {path}")
            self.assertEqual(r.sha256_file(path), r.EXPECTED[f"{name}_sha256"])
            data = path.read_bytes()
            git_blob = hashlib.sha1(
                f"blob {len(data)}\0".encode("ascii") + data
            ).hexdigest()
            self.assertEqual(git_blob, r.EXPECTED[f"{name}_git_blob_sha1"])
        freeze = r.STAGE4 / "freeze.json"
        self.assertTrue(freeze.is_file())
        self.assertEqual(r.sha256_file(freeze), r.EXPECTED["freeze_sha256"])

    def test_manifest_all_rows_validate_without_model(self) -> None:
        manifest, prereg, amendment = r.load_manifest()
        self.assertEqual(len(manifest), 2232)
        self.assertEqual(
            dict(collections.Counter(row["split"] for row in manifest)),
            {"train": 720, "validation": 360, "test": 1152},
        )
        self.assertEqual(len(r.FEATURES), 28)
        self.assertEqual(len(set(r.FEATURE_NAMES)), 28)
        self.assertEqual(len(set(r.MASK_NAMES)), 28)
        self.assertNotIn("TAYCAN_HVBAT_SOC_DISP", r.BASE_OBSERVED_CHANNELS)
        self.assertIn("manifest", amendment)
        self.assertIn("split_policy", prereg)

    def test_all_nuisance_rows_reproduce_from_seed(self) -> None:
        manifest, prereg, _ = r.load_manifest()
        for row in manifest:
            with self.subTest(episode=row["episode_id"]):
                config = r.make_observation_config(row, prereg, verify_draws=True)
                self.assertEqual(config["counter_source"], row["counter_source"])
                self.assertEqual(config["seeds"]["nuisance"], int(row["seed_nuisance"]))


if __name__ == "__main__":
    unittest.main()
