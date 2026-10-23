#!/usr/bin/env python3
"""Recover Stage 3/4 source bytes from original project ZIPs, without rewriting physics.

Default: read-only audit. --extract copies only the exact frozen model.py
(SHA-256 locked) and an unmodified observation_layer.py into src/taycan_sim/.
A different model hash is a hard failure. Existing mismatched files are never
overwritten. This script does NOT execute simulations or authorize Stage 4.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_MODEL = "af4e576cf824d30ee6aa9b2fd1f2c18d576fd269027df67c43c5e7647266ff4e"
EXPECTED_FREEZE = "5822c3e43e6f4634c7ca60d0aabb6f38afe5cecece99883833ee1c4d12dc5df8"
FREEZE_PATH = ROOT / "experiments" / "stage_04_data_validation" / "freeze.json"
MAX_MEMBER_BYTES = 4 * 1024 * 1024
ARCHIVE_NAMES = (
    "taycan_etapa3_codigo_testes.zip",
    "taycan_etapa4_codigo_dados.zip",
    "taycan_etapa4_dados_reais_e_codigo.zip",
)
SEARCH_DIRS = (Path("/mnt/data/recovered"), Path("/mnt/data"), ROOT / "archives")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def default_archives() -> list[Path]:
    return [directory / name for directory in SEARCH_DIRS for name in ARCHIVE_NAMES
            if (directory / name).is_file()]


def inspect_archives(archives: list[Path]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    status: dict[str, Any] = {"found_archives": [], "missing_archives": [],
                               "zip_errors": [], "candidates": []}
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in archives:
        key = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        if not path.is_file():
            status["missing_archives"].append(str(path))
            continue
        status["found_archives"].append({
            "path": str(path), "archive_sha256": digest(path.read_bytes()),
            "size_bytes": path.stat().st_size,
        })
        try:
            with zipfile.ZipFile(path) as z:
                damaged = z.testzip()
                if damaged is not None:
                    raise ValueError(f"ZIP member CRC failure: {damaged}")
                for item in z.infolist():
                    if item.is_dir():
                        continue
                    basename = Path(item.filename.replace("\\", "/")).name
                    if basename not in ("model.py", "observation_layer.py", "freeze.json"):
                        continue
                    if item.file_size > MAX_MEMBER_BYTES:
                        status["zip_errors"].append(f"Member too large: {path}: {item.filename}")
                        continue
                    data = z.read(item)
                    entry = {
                        "basename": basename, "member": item.filename, "archive": str(path),
                        "size_bytes": len(data), "sha256": digest(data), "_bytes": data,
                    }
                    candidates.append(entry)
                    status["candidates"].append({k: v for k, v in entry.items() if k != "_bytes"})
        except (OSError, zipfile.BadZipFile, ValueError, RuntimeError) as exc:
            status["zip_errors"].append(f"{path}: {exc}")
    return status, candidates


def choose(candidates: list[dict[str, Any]], name: str,
           required_hash: str | None = None) -> dict[str, Any] | None:
    subset = [candidate for candidate in candidates if candidate["basename"] == name]
    if required_hash:
        subset = [candidate for candidate in subset if candidate["sha256"] == required_hash]
    distinct = {candidate["sha256"] for candidate in subset}
    if len(distinct) != 1:
        return None
    return subset[0]


def checked_write(destination: Path, data: bytes) -> str:
    """Write atomically if absent; preserve existing identical file, reject differences."""
    if destination.exists():
        if digest(destination.read_bytes()) != digest(data):
            raise ValueError(f"Refusing overwrite of different bytes: {destination}")
        return "existing_identical"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as handle:
        tmp = Path(handle.name)
        try:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
    try:
        # No overwrite of existing different content, even if created meanwhile.
        if destination.exists():
            tmp.unlink(missing_ok=True)
            if digest(destination.read_bytes()) == digest(data):
                return "existing_identical"
            raise ValueError(f"Concurrent different file appeared: {destination}")
        tmp.rename(destination)
    finally:
        tmp.unlink(missing_ok=True)
    return "written"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archives", nargs="+", type=Path,
                        help="Explicit ZIP paths; defaults to original project archive names")
    parser.add_argument("--observer-sha256",
                        help="Required to disambiguate multiple different observation_layer.py files")
    parser.add_argument("--extract", action="store_true",
                        help="Write verified source files and a recovery receipt (default: audit only)")
    args = parser.parse_args()

    archives = args.archives if args.archives is not None else default_archives()
    status, candidates = inspect_archives(archives)
    model = choose(candidates, "model.py", EXPECTED_MODEL)
    observer = choose(candidates, "observation_layer.py", args.observer_sha256)
    freeze = {"path": str(FREEZE_PATH), "sha256": None, "verified": False}
    if FREEZE_PATH.is_file():
        freeze["sha256"] = digest(FREEZE_PATH.read_bytes())
        freeze["verified"] = freeze["sha256"] == EXPECTED_FREEZE
    status["freeze_repo"] = freeze

    model_candidates = [x for x in candidates if x["basename"] == "model.py"]
    obs_candidates = [x for x in candidates if x["basename"] == "observation_layer.py"]
    status["model_frozen_hash_verified"] = model is not None
    status["observation_layer_unique"] = observer is not None
    status["model_candidate_count"] = len(model_candidates)
    status["observation_candidate_count"] = len(obs_candidates)
    if observer is not None and args.observer_sha256 is None:
        status["observation_hash_status"] = "measured_now; no previously sealed hash"
    elif observer is not None:
        status["observation_hash_status"] = "matches caller supplied hash"
    else:
        status["observation_hash_status"] = "missing or ambiguous"
    status["selected"] = {
        key: ({k: v for k, v in selected.items() if k != "_bytes"} if selected else None)
        for key, selected in (("model", model), ("observation_layer", observer))
    }
    ready = model is not None and observer is not None and freeze["verified"]
    status["ready_to_extract"] = ready
    if not ready:
        status["remediation"] = (
            "Read-only block: locate a ZIP containing the exact frozen model hash, "
            "a unique observation_layer.py, and the repository's verified freeze.json."
        )
    elif args.extract:
        target = ROOT / "src" / "taycan_sim"
        writes = {
            "model.py": checked_write(target / "model.py", model["_bytes"]),
            "observation_layer.py": checked_write(target / "observation_layer.py", observer["_bytes"]),
        }
        status["writes"] = writes
        status["after_write_model_hash_verified"] = (
            digest((target / "model.py").read_bytes()) == EXPECTED_MODEL
        )
        if not status["after_write_model_hash_verified"]:
            raise RuntimeError("Unexpected post-write model hash mismatch")
        receipt = ROOT / "results" / "stage_04" / "archive_recovery_receipt.json"
        receipt.parent.mkdir(parents=True, exist_ok=True)
        # Write receipt only after artifact verification. Never include binary payload.
        receipt.write_text(json.dumps(status, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
        status["receipt"] = str(receipt)
    print(json.dumps(status, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
