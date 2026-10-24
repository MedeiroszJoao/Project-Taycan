"""Read-only SHA-512 verifier for the TUM m1774217 ZIP. No extracted raw data."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile


def audit(path: Path) -> dict:
    sha256 = hashlib.sha256()
    with path.open('rb') as fp:
        for chunk in iter(lambda: fp.read(2 * 1024 * 1024), b''):
            sha256.update(chunk)
    with ZipFile(path) as z:
        lines = z.read('m1774217_001/checksum.sha512').decode('utf-8').splitlines()
        expected = {}
        for line in lines:
            digest, name = line.strip().split(None, 1)
            if len(digest) != 128:
                raise ValueError('Invalid expected SHA-512 length')
            expected[name.lstrip('*').replace('\\', '/')] = digest.lower()
        members = [i for i in z.infolist() if i.filename.endswith('.csv')]
        match = 0
        headers = set()
        for member in members:
            suffix = member.filename.removeprefix('m1774217_001/')
            h = hashlib.sha512()
            with z.open(member) as stream:
                first = stream.readline()
                h.update(first)
                for chunk in iter(lambda: stream.read(2*1024*1024),b''):
                    h.update(chunk)
            if expected.get(suffix) != h.hexdigest():
                raise ValueError(f'SHA-512 mismatch or manifest missing: {suffix}')
            match += 1
            headers.add(first)
        if len(expected) != len(members):
            raise ValueError('Manifest CSV count does not match ZIP CSV count')
    return {'archive_name':path.name,'archive_bytes':path.stat().st_size,
            'sha256':sha256.hexdigest(),'csv_files':len(members),
            'sha512_verified':match,'distinct_headers':len(headers),
            'status':'INTEGRITY_ONLY_NOT_PHYSICAL_VALIDATION'}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('zip',type=Path)
    args=parser.parse_args()
    print(json.dumps(audit(args.zip),indent=2))
