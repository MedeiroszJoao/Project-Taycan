"""Unit tests for the read-only Stage 3/4 archive recovery utility.

These tests use synthetic ZIP fixtures, not a recovered vehicle simulator.
Run: python -m unittest discover -s tests/unit -p 'test_stage4_archive_recovery.py'
"""
from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from scripts.recover_frozen_stage3_from_archives import (
    Candidate, RecoveryError, inspect_archive, safe_member, select_model, select_observer
)

class ArchiveRecoveryTests(unittest.TestCase):
    def test_read_matching_frozen_model_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "stage3.zip"
            source = b"# frozen simulator fixture\n"
            with ZipFile(archive, "w") as z:
                z.writestr("taycan_sim/model.py", source)
                z.writestr("taycan_sim/notes.txt", "ignored")
            model_list, obs_list = inspect_archive(archive)
            self.assertEqual(len(model_list), 1)
            self.assertEqual(len(obs_list), 0)
            selected = select_model(model_list, hashlib.sha256(source).hexdigest())
            self.assertEqual(selected.content, source)

    def test_reject_model_with_wrong_frozen_checksum(self):
        c = Candidate("stage3.zip", "taycan_sim/model.py", "f" * 64, b"bad")
        with self.assertRaises(RecoveryError):
            select_model([c], "0" * 64)

    def test_reject_conflicting_observation_layer_variants(self):
        a = Candidate("first.zip", "observation_layer.py", "0" * 64, b"one")
        b = Candidate("second.zip", "observation_layer.py", "1" * 64, b"two")
        with self.assertRaisesRegex(RecoveryError, "Conflicting"):
            select_observer([a, b])

    def test_accept_byte_identical_observer_copies(self):
        a = Candidate("first.zip", "observation_layer.py", "a" * 64, b"x")
        b = Candidate("second.zip", "observation_layer.py", "a" * 64, b"x")
        self.assertEqual(select_observer([a, b]), a)

    def test_reject_zip_slip(self):
        for name in ("../taycan_sim/model.py", "/tmp/model.py", "folder\\model.py"):
            self.assertFalse(safe_member(name), name)
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "malicious.zip"
            with ZipFile(archive, "w") as z:
                z.writestr("../taycan_sim/model.py", b"bad")
            with self.assertRaisesRegex(RecoveryError, "Unsafe ZIP member"):
                inspect_archive(archive)

if __name__ == "__main__":
    unittest.main()
