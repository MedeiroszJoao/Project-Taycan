#!/usr/bin/env python3
"""Read-only Stage4B external TUM 1774217 inventory from provider public rsync.

No copying of protected archives, no publishing raw CAN data, no model fitting.
The public mediaTUM record advertises 93 files / 408 MB and credentials:
https://mediatum.ub.tum.de/1774217
"""
from __future__ import annotations
import argparse,csv,hashlib,json,os,re,subprocess,tempfile
from pathlib import Path

SOURCE="rsync://m1774217.001@dataserv.ub.tum.de/m1774217.001/"
DOI="10.14459/2025mp1774217.001"
LIST_LINE=re.compile(r"^(\S{10,})\s+([\d,]+)\s+\S+\s+\S+\s+(.+)$")
TEXT_SUFFIX={".csv",".txt",".tsv",".json",".md"}
MAX_SINGLE=2_000_000
MAX_TOTAL=8_000_000

def rsync(args, env):
    return subprocess.run(["rsync","--no-motd","--timeout=35","--contimeout=15",*args],
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,
        text=True,timeout=110,check=False)

def list_archive(env):
    proc=rsync(["--list-only","--recursive",SOURCE],env)
    if proc.returncode:
        raise RuntimeError("TUM rsync listing unavailable: exit="+str(proc.returncode)+
            " "+proc.stderr[-500:])
    entries=[]
    other=[]
    for line in proc.stdout.splitlines():
        m=LIST_LINE.match(line.strip())
        if not m:
            if line.strip():other.append(line.strip()[:300])
            continue
        mode,size,name=m.groups()
        if mode.startswith("d"):continue
        name=name.strip()
        if name.startswith("/") or ".." in Path(name).parts or "\\" in name:
            raise RuntimeError("unsafe path in authoritative file listing")
        entries.append(dict(path=name,size_bytes=int(size.replace(",",""))))
    if not entries:raise RuntimeError("provider file listing was nonempty but unparseable")
    return entries,other

def probe_small(entries, env):
    candidates=[x for x in entries
      if 0<x["size_bytes"]<=MAX_SINGLE
      and Path(x["path"]).suffix.lower() in TEXT_SUFFIX]
    candidates.sort(key=lambda x:(0 if "readme" in x["path"].lower() else 1,
                                   x["size_bytes"],x["path"]))
    samples=[]
    transferred=0
    with tempfile.TemporaryDirectory() as temp:
        folder=Path(temp)
        for row in candidates[:12]:
            size=row["size_bytes"]
            if transferred+size>MAX_TOTAL:break
            name=row["path"]
            dst=folder/(str(len(samples))+"_"+Path(name).name)
            proc=rsync([SOURCE+name,str(dst)],env)
            if proc.returncode or not dst.exists():
                samples.append(dict(path=name,status="TRANSFER_FAILED",
                                    error=proc.stderr[-240:]))
                continue
            transferred+=dst.stat().st_size
            with dst.open("rb") as fh:
                first=fh.read(65536)
            is_text=not b"\x00" in first
            sample=dict(path=name,status="FETCHED_READ_ONLY",
                bytes=dst.stat().st_size,sha256=hashlib.sha256(dst.read_bytes()).hexdigest(),
                likely_text=is_text,first_64kb_sha256=hashlib.sha256(first).hexdigest())
            if is_text:
                text=first.decode("utf-8",errors="replace")
                nonempty=[line for line in text.splitlines() if line.strip()]
                sample["header_lines"]=[x[:500] for x in nonempty[:3]]
                if name.lower().endswith((".csv",".tsv")) and nonempty:
                    sep=";" if nonempty[0].count(";")>nonempty[0].count(",") else (
                        "\t" if "\t" in nonempty[0] else ",")
                    try:
                        columns=next(csv.reader([nonempty[0]],delimiter=sep))
                    except csv.Error:
                        columns=[]
                    sample["separator"]=repr(sep)
                    sample["column_count"]=len(columns)
                    sample["columns"]=columns[:120]
            samples.append(sample)
    return samples,transferred

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--list-only",action="store_true")
    args=p.parse_args()
    env=os.environ.copy()
    # Password is published verbatim by TUM; not a ChatGPT/user account secret.
    env["RSYNC_PASSWORD"]="m1774217.001"
    report=dict(dataset="TUM_PORSCHE_TAYCAN_CAN_REALWORLD",
        doi=DOI,record="https://mediatum.ub.tum.de/1774217",
        source=SOURCE,status="BLOCKED",raw_data_republished=False,
        original_target_mismatch="base Taycan RWD 93.4kWh vs 4S AWD 79.2kWh")
    try:
        entries,unparsed=list_archive(env)
        report.update(status="INVENTORIED",file_count=len(entries),
          total_bytes=sum(x["size_bytes"] for x in entries),
          files=entries,listing_unparsed_lines=unparsed[:30])
        if not args.list_only:
            report["small_text_probes"],report["probe_total_bytes"]=probe_small(entries,env)
            report["status"]="INVENTORIED_AND_LIMITED_PROBED"
    except Exception as exc:
        report["error"]=str(exc)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k not in
            ("files","small_text_probes","listing_unparsed_lines")},indent=2))
    for s in report.get("small_text_probes",[]):
        print(json.dumps({k:v for k,v in s.items() if k in
            ("path","status","bytes","columns","column_count","header_lines")},ensure_ascii=False))
    if report["status"]=="BLOCKED":raise SystemExit(2)

if __name__=="__main__":
    main()
