"""Unit tests for archival-source recovery, using tiny synthetic ZIP fixtures.

These test the recovery mechanism, not the frozen physical model.
No public or synthetic substitute is accepted as the approved Stage 3 model.
"""
from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts import recover_frozen_stage3_stage4 as recovery


class ArchiveRecoveryTests(unittest.TestCase):
    def make_archive(self, parent: Path, name: str, members: dict[str, bytes]) -> Path:
        path = parent / name
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for member, data in members.items():
                z.writestr(member, data)
        return path

    def test_finds_file_by_basename_without_rewriting_bytes(self) -> None:
        model_bytes = b"# synthetic fixture only\n"
        obs_bytes = b"# synthetic observer fixture only\n"
        with tempfile.TemporaryDirectory() as temp:
            archive = self.make_archive(Path(temp), "source.zip", {
                "taycan_sim/model.py": model_bytes,
                "some/path/observation_layer.py": obs_bytes,
            })
            status, candidates = recovery.inspect_archives([archive])
            model = recovery.choose(candidates, "model.py", recovery.digest(model_bytes))
            observer = recovery.choose(candidates, "observation_layer.py")
            self.assertEqual(model["_bytes"], model_bytes)
            self.assertEqual(observer["_bytes"], obs_bytes)
            self.assertEqual(status["zip_errors"], [])

    def test_wrong_model_hash_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            archive = self.make_archive(Path(temp), "source.zip", {
                "taycan_sim/model.py": b"# NOT THE FROZEN MODEL\n",
            })
            _, candidates = recovery.inspect_archives([archive])
            self.assertIsNone(recovery.choose(candidates, "model.py", recovery.EXPECTED_MODEL))

    def test_ambiguous_observer_requires_explicit_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp)
            first = self.make_archive(parent, "1.zip", {"observation_layer.py": b"one\n"})
            second = self.make_archive(parent, "2.zip", {"observation_layer.py": b"two\n"})
            _, candidates = recovery.inspect_archives([first, second])
            self.assertIsNone(recovery.choose(candidates, "observation_layer.py"))
            chosen = recovery.choose(candidates, "observation_layer.py", recovery.digest(b"two\n"))
            self.assertEqual(chosen["_bytes"], b"two\n")

    def test_different_existing_file_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "model.py"
            self.assertEqual(recovery.checked_write(destination, b"old"), "written")
            self.assertEqual(recovery.checked_write(destination, b"old"), "existing_identical")
            with self.assertRaisesRegex(ValueError, "Refusing overwrite"):
                recovery.checked_write(destination, b"replacement")
            self.assertEqual(destination.read_bytes(), b"old")

    def test_corrupt_zip_reported_without_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "not-a-real.zip"
            path.write_bytes(b"invalid zip")
            status, candidates = recovery.inspect_archives([path])
            self.assertEqual(candidates, [])
            self.assertEqual(len(status["zip_errors"]), 1)


if __name__ == "__main__":
    unittest.main()
