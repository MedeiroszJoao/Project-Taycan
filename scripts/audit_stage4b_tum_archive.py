#!/usr/bin/env python3
"""Read-only provenance/structure audit for public TUM Taycan archive.

No extraction, no data interpretation, no model fitting. No file uploads.
Run only after the ZIP is present in Work's filesystem.
"""
import argparse
import collections
import hashlib
import json
import os
import stat
import zipfile
from pathlib import Path, PurePosixPath

SOURCE = {
    "provider": "Technical University of Munich / mediaTUM",
    "title": "CAN Data of a Porsche Taycan during Real-world Driving Scenarios",
    "doi": "10.14459/2025mp1774217",
    "landing_page": "https://mediatum.ub.tum.de/1774217",
    "expected_filename": "m1774217_001.zip",
    "reported_measurements": 92,
    "vehicle": "2022 Taycan base RWD, Performance Battery Plus 93.4 kWh, "
               "NOT 2022 Taycan 4S AWD 79.2 kWh",
    "source_characterization": "external domain-shift evidence, not target calibration",
}

def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def audit(path: Path, *, include_sha256: bool = False, verify_crc: bool = False) -> dict:
    if not path.is_file() or not zipfile.is_zipfile(path):
        raise ValueError("missing or invalid ZIP archive")
    suspicious = []
    ext_counts = collections.Counter()
    files = []
    names = set()
    total_uncompressed = 0
    total_compressed = 0
    with zipfile.ZipFile(path) as archive:
        for item in archive.infolist():
            name = item.filename
            pure = PurePosixPath(name)
            suffix = pure.suffix.lower() or "(no extension)"
            ext_counts[suffix] += not item.is_dir()
            unix_mode = (item.external_attr >> 16)
            is_link = stat.S_ISLNK(unix_mode)
            bad_name = (name.startswith("/") or "\\" in name or
                ".." in pure.parts or ":" in name or not name)
            if is_link or bad_name or name in names:
                suspicious.append({"member": name, "reason":
                                   "link/unsafe path/duplicate filename"})
            names.add(name)
            total_uncompressed += item.file_size
            total_compressed += item.compress_size
            if item.flag_bits & 1:
                suspicious.append({"member": name, "reason": "encrypted"})
            if item.file_size > 0 and item.compress_size == 0:
                suspicious.append({"member": name, "reason": "zero compressed size"})
            elif item.compress_size > 0 and item.file_size/item.compress_size > 1000:
                suspicious.append({"member": name, "reason": "compression ratio >1000"})
            if not item.is_dir():
                files.append({"name": name, "uncompressed_bytes": item.file_size,
                              "compressed_bytes": item.compress_size,
                              "crc32_zip_header": f"{item.CRC:08x}"})
        if verify_crc and not suspicious:
            failed = archive.testzip()
            if failed:
                raise ValueError(f"CRC mismatch for {failed}")
    result = {
        "status": "STRUCTURE_ONLY_NO_MEASUREMENTS_PARSED",
        "source": SOURCE,
        "archive_path_basename": path.name,
        "archive_bytes": path.stat().st_size,
        "sha256_archive": digest(path) if include_sha256 else None,
        "zip_testzip_passed": bool(verify_crc and not suspicious),
        "member_count": len(names),
        "file_count": len(files),
        "total_uncompressed_bytes": total_uncompressed,
        "total_compressed_bytes": total_compressed,
        "extensions": dict(sorted(ext_counts.items())),
        "unsafe_members": suspicious[:30],
        "member_listing": files,
        "can_signal_table_verified": False,
        "unit_or_sampling_verified": False,
        "vehicle_configuration_matched_to_target": False,
    }
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--sha256",action="store_true",
                   help="Compute archive hash by streaming bytes, no extraction")
    p.add_argument("--verify-crc",action="store_true",
                   help="Read compressed members and verify CRC; may take time")
    args = p.parse_args()
    report = audit(args.archive,include_sha256=args.sha256,verify_crc=args.verify_crc)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    summary={k:report[k] for k in ("status","archive_bytes","sha256_archive","member_count",
                  "file_count","extensions","unsafe_members","zip_testzip_passed")}
    print(json.dumps(summary,indent=2,ensure_ascii=False))
    if report["unsafe_members"]:
        raise SystemExit("Unsafe ZIP members present: do not extract")
if __name__=="__main__":main()
