"""Adversarial tests for fail-closed recovery of frozen Stage 3 and Stage 4 sources.

All fixtures are synthetic; tests do not claim to have executed the real model.
"""
from __future__ import annotations

import hashlib
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts import recover_stage3_stage4_sources as recovery


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_zip(path: Path, members: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in members.items():
            archive.writestr(name, data)


class RecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.model = b"ORIGINAL MODEL SYNTHETIC FIXTURE\n"
        self.layer = b"ORIGINAL OBSERVATION LAYER SYNTHETIC FIXTURE\n"
        self.freeze = b"{\"synthetic_fixture\": true}\n"
        self.stage3 = self.root / "stage3.zip"
        self.stage4 = self.root / "stage4.zip"
        self.freeze_path = self.root / "freeze.json"
        self.freeze_path.write_bytes(self.freeze)
        self.output = self.root / "recovered"
        make_zip(self.stage3, {"package/taycan_sim/model.py": self.model})
        make_zip(self.stage4, {"experiment/taycan_sim/model.py": self.model,
                               "experiment/taycan_sim/observation_layer.py": self.layer,
                               "experiment/freeze.json": self.freeze})

    def recover_fixture(self) -> dict:
        with patch.object(recovery, "MODEL_SHA256", digest(self.model)), \
             patch.object(recovery, "FREEZE_SHA256", digest(self.freeze)):
            return recovery.recover(self.stage3, self.stage4,
                                    self.freeze_path, self.output)

    def test_byte_identical_sources_and_idempotent_receipt(self) -> None:
        first = self.recover_fixture()
        receipt_first = (self.output / "recovery_receipt.json").read_bytes()
        second = self.recover_fixture()
        self.assertEqual(first, second)
        self.assertEqual(receipt_first, (self.output / "recovery_receipt.json").read_bytes())
        self.assertEqual((self.output / "taycan_sim" / "model.py").read_bytes(), self.model)
        self.assertEqual((self.output / "observation_layer.py").read_bytes(), self.layer)

    def test_modified_model_is_rejected(self) -> None:
        make_zip(self.stage4, {"taycan_sim/model.py": b"MODIFIED",
                               "observation_layer.py": self.layer})
        with self.assertRaisesRegex(ValueError, "SHA-256 divergente"):
            self.recover_fixture()

    def test_conflicting_observation_layers_are_rejected(self) -> None:
        make_zip(self.stage4, {"observation_layer.py": self.layer,
                               "nested/observation_layer.py": b"CONFLICTING"})
        with self.assertRaisesRegex(ValueError, "Versões conflitantes"):
            self.recover_fixture()

    def test_missing_observation_layer_is_rejected(self) -> None:
        make_zip(self.stage4, {"irrelevant.txt": b"x"})
        with self.assertRaisesRegex(ValueError, "observation_layer.py"):
            self.recover_fixture()

    def test_wrong_freeze_is_rejected(self) -> None:
        self.freeze_path.write_bytes(b"BAD")
        with self.assertRaisesRegex(ValueError, "freeze.json"):
            self.recover_fixture()

    def test_refuses_to_overwrite_previous_model(self) -> None:
        (self.output / "taycan_sim").mkdir(parents=True)
        (self.output / "taycan_sim" / "model.py").write_bytes(b"UNRELATED")
        with self.assertRaisesRegex(ValueError, "Recusado sobrescrever"):
            self.recover_fixture()


if __name__ == "__main__":
    unittest.main()
