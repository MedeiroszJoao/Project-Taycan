#!/usr/bin/env python3
"""Recover original Stage 3/4 sources from their archives without rebuilding them.

This utility does not execute a simulation, change a frozen file, or approve a
stage. It extracts only byte-for-byte verified Python sources.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from zipfile import BadZipFile, ZipFile

MODEL_SHA256 = "af4e576cf824d30ee6aa9b2fd1f2c18d576fd269027df67c43c5e7647266ff4e"
FREEZE_SHA256 = "5822c3e43e6f4634c7ca60d0aabb6f38afe5cecece99883833ee1c4d12dc5df8"
MAX_SOURCE_BYTES = 4_000_000


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def scan_archive(path: Path) -> list[dict]:
    if not path.is_file():
        raise ValueError(f"Arquivo não encontrado: {path}")
    matches: list[dict] = []
    with ZipFile(path, "r") as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            filename = member.filename.replace("\\", "/")
            basename = filename.rsplit("/", 1)[-1]
            if basename not in ("model.py", "observation_layer.py", "freeze.json"):
                continue
            if member.file_size > MAX_SOURCE_BYTES:
                raise ValueError(f"Arquivo-fonte grande demais: {path}:{filename}")
            data = archive.read(member)  # validates the ZIP member CRC
            matches.append({
                "archive": str(path),
                "member": filename,
                "basename": basename,
                "sha256": sha256(data),
                "size_bytes": len(data),
                "data": data,
            })
    return matches


def unique_bytes(candidates: list[dict], kind: str) -> dict:
    if not candidates:
        raise ValueError(f"Arquivo obrigatório não encontrado nos ZIPs: {kind}")
    hashes = {candidate["sha256"] for candidate in candidates}
    if len(hashes) != 1:
        descriptions = [(x["archive"], x["member"], x["sha256"]) for x in candidates]
        raise ValueError(f"Versões conflitantes de {kind}: {descriptions!r}")
    return candidates[0]


def preserve_exact(destination: Path, content: bytes) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if destination.read_bytes() != content:
            raise ValueError(f"Recusado sobrescrever arquivo com bytes diferentes: {destination}")
        return "already_identical"
    # Exclusive create prevents accidental replacement.
    with destination.open("xb") as stream:
        stream.write(content)
    return "created"


def recover(stage3_zip: Path, stage4_zip: Path, freeze_path: Path, output: Path) -> dict:
    stage3 = scan_archive(stage3_zip)
    stage4 = scan_archive(stage4_zip)
    all_members = stage3 + stage4
    frozen_models = [m for m in all_members if m["basename"] == "model.py"]
    if not frozen_models:
        raise ValueError("Nenhum model.py nos ZIPs; não é permitido fabricar substituto.")
    mismatched_models = [m for m in frozen_models if m["sha256"] != MODEL_SHA256]
    if mismatched_models:
        raise ValueError("ZIP contém model.py com SHA-256 divergente: " +
                         str([(x["archive"], x["member"], x["sha256"]) for x in mismatched_models]))
    model = unique_bytes(frozen_models, "model.py")
    layers = [m for m in stage4 if m["basename"] == "observation_layer.py"]
    layer = unique_bytes(layers, "observation_layer.py")
    freeze = freeze_path.read_bytes()
    if sha256(freeze) != FREEZE_SHA256:
        raise ValueError(f"freeze.json não coincide com SHA-256 congelado: {sha256(freeze)}")
    # The Stage 3 archive may contain unrelated historical freeze files.
    embedded_freezes = [m for m in stage4 if m["basename"] == "freeze.json"]
    for embedded in embedded_freezes:
        if embedded["sha256"] != FREEZE_SHA256:
            raise ValueError(f"freeze.json divergente no ZIP: {embedded['archive']}:{embedded['member']}")
    locations = [
        (model, output / "taycan_sim" / "model.py"),
        (layer, output / "observation_layer.py"),
    ]
    for item, destination in locations:
        preserve_exact(destination, item["data"])
    report = {
        "status": "SOURCES_RECOVERED_NOT_EXECUTED_NOT_APPROVED",
        "model_sha256_verified": True,
        "freeze_sha256_verified": True,
        "observation_layer_approved_hash_available": False,
        "counter_timing_verified": False,
        "stage3_zip": str(stage3_zip),
        "stage4_zip": str(stage4_zip),
        "freeze_json": str(freeze_path),
        "sources": [
            {"path": str(destination), "archive": item["archive"],
             "archive_member": item["member"], "sha256": item["sha256"],
             "size_bytes": item["size_bytes"]}
            for item, destination in locations
        ],
        "important": "Original observation-layer bytes recovered but no known approved SHA-256; review its code and Stage 3 compatibility before running.",
    }
    report_path = output / "recovery_receipt.json"
    receipt = (json.dumps(report, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    preserve_exact(report_path, receipt)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage3-zip", type=Path, required=True)
    parser.add_argument("--stage4-zip", type=Path, required=True)
    parser.add_argument("--freeze", type=Path, default=Path(
        "experiments/stage_04_data_validation/freeze.json"))
    parser.add_argument("--output", type=Path, default=Path("recovered-stage4"))
    args = parser.parse_args()
    try:
        report = recover(args.stage3_zip, args.stage4_zip, args.freeze, args.output)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0
    except (ValueError, OSError, BadZipFile) as exc:
        print(f"BLOQUEIO_RECUPERACAO: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
