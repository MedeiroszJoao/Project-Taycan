"""Public real Porsche LG E66 6p2s module integrity and archive-only metadata QC.

No signal calibration, no PyBaMM fitting, no publication of raw measurements.
"""
from __future__ import annotations
import argparse,hashlib,json,stat,tempfile,urllib.request,zipfile
from pathlib import Path,PurePosixPath
URL="https://borealisdata.ca/api/access/datafile/837535"
DOI="10.5683/SP3/7JP3NM"
SIZE=5501501
MD5="619eb01774c04696e399d106639a342c"

def download(dest):
    req=urllib.request.Request(URL,headers={"User-Agent":"ProjectTaycan-Research-ReadOnly/1.0"})
    size=0;m=hashlib.md5();sha=hashlib.sha256()
    with urllib.request.urlopen(req,timeout=55) as r,dest.open("wb") as f:
        for block in iter(lambda:r.read(1024*1024),b""):
            size+=len(block)
            if size>SIZE+1:raise ValueError("larger than preregistered module archive")
            m.update(block);sha.update(block);f.write(block)
    if size!=SIZE or m.hexdigest()!=MD5:
        raise AssertionError("Borealis archive size or checksum mismatch")
    return dict(bytes=size,md5=m.hexdigest(),sha256=sha.hexdigest())

def inspect(source,hashes):
    if not zipfile.is_zipfile(source):raise ValueError("not a ZIP")
    files=[];unsafe=[];seen=set();extensions={}
    with zipfile.ZipFile(source) as z:
        for i in z.infolist():
            name=i.filename
            parts=PurePosixPath(name)
            mode=(i.external_attr>>16)
            reasons=[]
            if name in seen:reasons.append("duplicate_name")
            if name.startswith("/") or ".." in parts.parts or "\\" in name or ":" in name:
                reasons.append("unsafe_path")
            if stat.S_ISLNK(mode):reasons.append("symlink")
            if i.flag_bits&1:reasons.append("encrypted")
            if i.compress_size and i.file_size/i.compress_size>1000:
                reasons.append("ratio>1000")
            if reasons:
                unsafe.append({"name":name,"reasons":reasons})
            seen.add(name)
            if i.is_dir():continue
            ext=parts.suffix.lower()
            extensions[ext]=extensions.get(ext,0)+1
            sample=b""
            if not reasons:
                with z.open(i) as f:
                    sample=f.read(128)
            kind=("MATLAB_LEVEL5" if sample.startswith(b"MATLAB 5.0 MAT-file")
                  else "HDF5" if sample.startswith(b"\x89HDF\r\n\x1a\n")
                  else "UNKNOWN")
            files.append(dict(path=name,compressed_bytes=i.compress_size,
              bytes=i.file_size,crc32_header=f"{i.CRC:08x}",format_magic=kind,
              head_128_sha256=hashlib.sha256(sample).hexdigest()))
        if unsafe:raise ValueError("Zip rejected for unsafe contents: "+repr(unsafe[:5]))
        firstbad=z.testzip()
        if firstbad:raise ValueError("CRC mismatch in "+firstbad)
    return dict(status="PROVENANCE_AND_ARCHIVE_VALIDATED_NO_FIT",
      file_id=837535,DOI=DOI,source_url=URL,license="CC BY 4.0",
      measured_module="Porsche Taycan recovered module of LG E66 6p2s, tested at 30C",
      sha256=hashes["sha256"],md5=hashes["md5"],archive_bytes=hashes["bytes"],
      total_members=len(seen),file_members=len(files),
      compressed_total=sum(x["compressed_bytes"] for x in files),
      uncompressed_total=sum(x["bytes"] for x in files),
      formats=extensions,members=files,
      crc_full_pass=True,raw_published=False,
      any_signals_fit_to_model_B=False,
      cell_data_archive_downloaded=False,
      sealed_stage4_examples_read=0)

def main(out):
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/"module.zip"
        hashes=download(path)
        rec=inspect(path,hashes)
    out.write_text(json.dumps(rec,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({k:v for k,v in rec.items() if k not in ("members",)},indent=2))
    print("MEMBERS",json.dumps(rec["members"],ensure_ascii=False))
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",required=True,type=Path)
    main(p.parse_args().out)
