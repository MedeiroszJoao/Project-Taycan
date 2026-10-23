#!/usr/bin/env python3
"""Recover previously generated Stage 3/4 Python artifacts without modifying them.

This is an archival extraction tool, NOT a physical-model implementation.
It refuses to accept any model.py whose SHA-256 differs from the approved Stage 3
freeze. It does not alter any preregistration, manifest, model or runner files.
Python 3.10+, standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import tempfile
from typing import NamedTuple
from zipfile import ZipFile, BadZipFile

MODEL_SHA256 = "af4e576cf824d30ee6aa9b2fd1f2c18d576fd269027df67c43c5e7647266ff4e"
FREEZE_SHA256 = "5822c3e43e6f4634c7ca60d0aabb6f38afe5cecece99883833ee1c4d12dc5df8"
MAX_SOURCE_BYTES = 8 * 1024 * 1024

class RecoveryError(Exception):
    pass

class Candidate(NamedTuple):
    archive: str
    member: str
    sha256: str
    content: bytes

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def safe_member(name: str) -> bool:
    if "\\" in name or name.startswith("/") or "\x00" in name:
        return False
    parts = PurePosixPath(name).parts
    return bool(parts) and all(p not in (".", "..") for p in parts)

def inspect_archive(archive_path: Path) -> tuple[list[Candidate], list[Candidate]]:
    if not archive_path.is_file():
        raise RecoveryError(f"NÃO CONSEGUI ACESSAR: {archive_path}")
    models, observers = [], []
    try:
        with ZipFile(archive_path) as z:
            for info in z.infolist():
                if info.is_dir():
                    continue
                if not safe_member(info.filename):
                    raise RecoveryError(f"Unsafe ZIP member in {archive_path}: {info.filename!r}")
                mode = info.external_attr >> 16
                if stat.S_IFMT(mode) == stat.S_IFLNK:
                    raise RecoveryError(f"ZIP symlink rejected in {archive_path}: {info.filename!r}")
                base = PurePosixPath(info.filename).name
                is_model = base == "model.py" and (
                    info.filename == "taycan_sim/model.py"
                    or info.filename.endswith("/taycan_sim/model.py")
                )
                is_observer = base == "observation_layer.py"
                if not (is_model or is_observer):
                    continue
                if info.file_size > MAX_SOURCE_BYTES:
                    raise RecoveryError(f"Source unexpectedly large: {archive_path}!{info.filename}")
                with z.open(info, "r") as handle:
                    content = handle.read(MAX_SOURCE_BYTES + 1)
                if len(content) > MAX_SOURCE_BYTES or len(content) != info.file_size:
                    raise RecoveryError(f"ZIP source size inconsistency: {archive_path}!{info.filename}")
                item = Candidate(str(archive_path), info.filename, sha256_bytes(content), content)
                (models if is_model else observers).append(item)
    except BadZipFile as e:
        raise RecoveryError(f"Archive damaged: {archive_path}: {e}") from e
    return models, observers

def select_model(candidates: list[Candidate], expected: str = MODEL_SHA256) -> Candidate:
    matches = [x for x in candidates if x.sha256 == expected]
    if not matches:
        observed = [{"archive": c.archive, "member": c.member, "sha256": c.sha256} for c in candidates]
        raise RecoveryError("Frozen model SHA-256 not found; do not replace the approved model. " + json.dumps(observed))
    return matches[0]

def select_observer(candidates: list[Candidate]) -> Candidate | None:
    if not candidates:
        return None
    hashes = {x.sha256 for x in candidates}
    if len(hashes) != 1:
        info = [{"archive": c.archive, "member": c.member, "sha256": c.sha256} for c in candidates]
        raise RecoveryError("Conflicting observation_layer.py variants; manual provenance audit required. " + json.dumps(info))
    return candidates[0]

def save_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="wb", dir=path.parent, delete=False) as temp:
        temp.write(content)
        temp.flush()
        os.fsync(temp.fileno())
        temp_name = temp.name
    try:
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)

def recover(stage3_zip: Path, stage4_zips: list[Path], freeze: Path,
            outdir: Path, write: bool = False) -> dict:
    if not freeze.is_file():
        raise RecoveryError(f"NÃO CONSEGUI ACESSAR: {freeze}")
    freeze_sha = sha256_bytes(freeze.read_bytes())
    if freeze_sha != FREEZE_SHA256:
        raise RecoveryError(f"FROZEN FREEZE HASH MISMATCH: {freeze_sha}; expected {FREEZE_SHA256}")
    models, observers = [], []
    archive_receipts = []
    for archive in [stage3_zip, *stage4_zips]:
        raw_sha = hashlib.sha256(archive.read_bytes()).hexdigest()
        m, o = inspect_archive(archive)
        models.extend(m)
        observers.extend(o)
        archive_receipts.append({"filename": str(archive), "sha256": raw_sha,
                                 "model_candidates": len(m), "observer_candidates": len(o)})
    model = select_model(models)
    observer = select_observer(observers)
    receipt = {
        "status": "MODEL_AND_OBSERVER_RECOVERED" if observer else "MODEL_ONLY_OBSERVER_UNRESOLVED",
        "frozen_stage3_model_sha256": model.sha256,
        "freeze_sha256": freeze_sha,
        "model_provenance": {"archive": model.archive, "member": model.member, "size_bytes": len(model.content)},
        "observer_provenance": None if observer is None else {
            "archive": observer.archive, "member": observer.member,
            "sha256": observer.sha256, "size_bytes": len(observer.content)},
        "archives": archive_receipts, "write_enabled": write,
        "note": "Do not classify as executed/tested; copying verified bytes is not an integration test.",
    }
    if write:
        # Never overwrite an existing artifact silently.
        planned = [(outdir / "taycan_sim" / "model.py", model.content)]
        if observer:
            planned.append((outdir / "observation_layer.py", observer.content))
        planned.append((outdir / "recovery_receipt.json",
                        (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8")))
        for path, content in planned:
            if path.exists() and path.read_bytes() != content:
                raise RecoveryError(f"Existing destination differs; refusing overwrite: {path}")
        for path, content in planned:
            if not path.exists():
                save_atomic(path, content)
        if sha256_bytes((outdir / "taycan_sim" / "model.py").read_bytes()) != MODEL_SHA256:
            raise RecoveryError("Post-write model checksum mismatch")
    return receipt

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage3-zip", type=Path, required=True)
    p.add_argument("--stage4-zip", type=Path, action="append", default=[])
    p.add_argument("--freeze", type=Path, default=Path("experiments/stage_04_data_validation/freeze.json"))
    p.add_argument("--outdir", type=Path, default=Path("recovery/stage4_verified"))
    p.add_argument("--write", action="store_true", help="Write verified byte-identical files to an isolated recovery folder")
    a = p.parse_args()
    try:
        result = recover(a.stage3_zip, a.stage4_zip, a.freeze, a.outdir, a.write)
    except (RecoveryError, OSError, BadZipFile) as exc:
        print(json.dumps({"status": "BLOQUEIO", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "MODEL_AND_OBSERVER_RECOVERED" else 3

if __name__ == "__main__":
    raise SystemExit(main())
