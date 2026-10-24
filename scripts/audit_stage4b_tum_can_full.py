#!/usr/bin/env python3
"""Stage4B: external real CAN data availability/QC, no fit, no class labels.

Reads public TUM 1774217 CSV recordings from provider's documented rsync.
Each CSV is deleted after a streaming feature-availability + numeric-range audit.
DO NOT commit, publish or use the raw telemetry as Taycan 4S calibration.
"""
from __future__ import annotations
import argparse, collections, csv, hashlib, json, math, os, re, subprocess, tempfile
from pathlib import Path
from scripts.inspect_stage4b_tum_public_rsync import SOURCE, DOI, list_archive

EXPECTED_HEADER = ("time","hv_soc","hv_current","hv_voltage","dcdc_aux",
    "hv_heater_current","hv_compressor_power","lv_power","vehicle_speed",
    "motor_speed","gearbox_speed","motor_torque","gear_selected",
    "gear_selected_neutral","accelerator_pedal","brake_pedal_activated",
    "steering_wheel_angle","temp_ambient","temp_interior","temp_battery_avg",
    "temp_battery_inlet","temp_battery_outlet","temp_stator","temp_inverter",
    "temp_gearbox","suspension_level","radiator_shutter_right",
    "radiator_shutter_left","spoiler_level")
MISSING={"","na","nan","null","none","n/a","-"}
MAX_FILE=65_000_000
QC_FIELDS=("time","hv_soc","hv_current","hv_voltage","vehicle_speed",
    "motor_speed","motor_torque","temp_battery_avg","temp_inverter")
SOURCE_LICENSE="CC BY 4.0 (provider record; attribute TUM Rosenberger/Lienkamp)"

def parse_num(value):
    x=str(value).strip()
    if x.lower() in MISSING:return None
    try:
        v=float(x)
        return v if math.isfinite(v) else None
    except (ValueError,OverflowError):
        return None

def hash_file(path):
    h=hashlib.sha256()
    with path.open("rb") as src:
        for data in iter(lambda: src.read(4*1024*1024),b""):
            h.update(data)
    return h.hexdigest()

def analyze_csv(path:Path, *,source_path=None):
    with path.open("r",encoding="utf-8-sig",errors="replace",newline="") as fh:
        # Expected plain-text published Taycan CAN tables; fail if malformed.
        rdr=csv.DictReader(fh)
        headers=rdr.fieldnames or []
        if not headers or len(headers)!=len(set(headers)):
            raise ValueError("invalid/duplicated header")
        if None in headers:raise ValueError("malformed CSV header")
        stats={name:dict(valid=0,missing=0,min=None,max=None,mean=0.0,M2=0.0)
               for name in headers}
        dt_counts=collections.Counter()
        bad_time=0;nonincreasing=0
        bad_soc=0;bad_voltage=0;count=0
        first_time=None;last_time=None;last_seen_time=None
        max_abs_voltage=0.
        for row in rdr:
            if None in row:
                raise ValueError("more data fields than header")
            count+=1
            for key in headers:
                v=parse_num(row.get(key,""))
                vstat=stats[key]
                if v is None:
                    vstat["missing"]+=1;continue
                n=vstat["valid"]+1
                delta=v-vstat["mean"]
                vstat["valid"]=n
                vstat["mean"]+=delta/n
                vstat["M2"]+=delta*(v-vstat["mean"])
                vstat["min"]=v if vstat["min"] is None else min(v,vstat["min"])
                vstat["max"]=v if vstat["max"] is None else max(v,vstat["max"])
            t=parse_num(row.get("time"))
            if t is None:
                bad_time+=1
            else:
                if first_time is None:first_time=t
                if last_seen_time is not None:
                    dt=t-last_seen_time
                    if dt<=0:nonincreasing+=1
                    elif len(dt_counts)<100 or round(dt,5) in dt_counts:
                        dt_counts[round(dt,5)]+=1
                last_seen_time=t;last_time=t
            soc=parse_num(row.get("hv_soc"))
            if soc is not None and not 0<=soc<=100:bad_soc+=1
            voltage=parse_num(row.get("hv_voltage"))
            if voltage is not None and voltage<=0:bad_voltage+=1
        if count<2:raise ValueError("not enough measured rows")
    compact={}
    for k,d in stats.items():
        n=d["valid"]
        compact[k]=dict(coverage=n/count,valid=n,missing=d["missing"],
             min=d["min"],max=d["max"],mean=d["mean"] if n else None,
             sample_sd=math.sqrt(max(0,d["M2"]/(n-1))) if n>=2 else None)
    return dict(
       filename=source_path or path.name,rows=count,columns=headers,
       dt_seconds_modes=dt_counts.most_common(5),valid_first_time=first_time,
       valid_last_time=last_time,duration_s=(last_time-first_time if last_time is not None
                        and first_time is not None else None),
       malformed_time_rows=bad_time,nonincreasing_time_steps=nonincreasing,
       soc_outside_0_100=bad_soc,voltage_nonpositive=bad_voltage,
       channel_stats=compact,source_sha256=hash_file(path),
       file_size_bytes=path.stat().st_size)

def remote_copy(name,destination,env):
    p=subprocess.run(["rsync","--no-motd","--timeout=60","--contimeout=20",
            SOURCE+name,str(destination)],stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,text=True,env=env,timeout=300,check=False)
    if p.returncode:
        raise RuntimeError("rsync failed: exit "+str(p.returncode)+" "+p.stderr[-350:])

def full_audit(out:Path, *,max_files:int):
    env=os.environ.copy()
    env["RSYNC_PASSWORD"]="m1774217.001" # publicly documented by TUM
    inventory,ignored=list_archive(env)
    csv_items=[x for x in inventory if x["path"].lower().endswith(".csv")]
    csv_items.sort(key=lambda x:x["path"])
    if len(csv_items)!=92:raise ValueError("expected exactly 92 source CSV recordings; got "+
                                           str(len(csv_items)))
    if max_files==0 or max_files>92:
        raise ValueError("max-files must be 1..92")
    report=dict(status="IN_PROGRESS",dataset="TUM_REALWORLD_TAYCAN_1774217",
        provider="TUM Rosenberger and Lienkamp",licence=SOURCE_LICENSE,
        doi=DOI,landing_page="https://mediatum.ub.tum.de/1774217",
        total_source_files=len(inventory),csv_recordings_listed=len(csv_items),
        original_can_data_republished=False,not_target_taycan_4s=True,
        independence="one physical RWD vehicle, 92 repeated driving recordings",
        experimental_fault_labels_available=False,
        reports=[],errors=[],source_bytes=sum(x["size_bytes"] for x in csv_items))
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        directory=Path(tmp)
        for index,item in enumerate(csv_items[:max_files]):
            source_path=item["path"]
            try:
                if item["size_bytes"]>MAX_FILE:
                    raise RuntimeError("file exceeds predeclared single-file cap")
                local=directory/("scan_"+str(index)+".csv")
                remote_copy(source_path,local,env)
                if local.stat().st_size!=item["size_bytes"]:
                    raise RuntimeError("downloaded byte length differs from provider inventory")
                record=analyze_csv(local,source_path=source_path)
                record["status"]="PASS"
                report["reports"].append(record)
            except Exception as exc:
                report["errors"].append(dict(path=source_path,reason=
                    type(exc).__name__+": "+str(exc)[:350]))
            finally:
                local=directory/("scan_"+str(index)+".csv")
                if local.exists():local.unlink()
            if index%8==0:
                out.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+"\n")
                print("audited",index+1,"of",max_files,"errors",len(report["errors"]),flush=True)
    n=len(report["reports"])
    cols=collections.Counter()
    avail_per_column=collections.defaultdict(list)
    observations_per_column=collections.defaultdict(lambda:dict(valid=0,total=0))
    for rec in report["reports"]:
        for c,d in rec["channel_stats"].items():
            cols[c]+=1
            avail_per_column[c].append(d["coverage"])
            observations_per_column[c]["valid"]+=d["valid"]
            observations_per_column[c]["total"]+=rec["rows"]
    report["complete_source_coverage"]=len(csv_items)==n and len(report["errors"])==0
    report["status"]="COMPLETED_FULL" if report["complete_source_coverage"] else (
        "COMPLETED_SAMPLE" if n>0 else "FAILED")
    report["summary"]=dict(
      succeeded=n,failed=len(report["errors"]),requested=max_files,
      rows=sum(r["rows"] for r in report["reports"]),
      duration_total_s=sum(r["duration_s"] or 0 for r in report["reports"]),
      variable_per_recording_coverage={c:dict(n_recordings=len(vals),
           mean_fraction=sum(vals)/len(vals),
           n_recordings_with_any=sum(v>0 for v in vals),
           n_recordings_over_80pct=sum(v>=.8 for v in vals),
           fraction_of_all_sampled_rows=(observations_per_column[c]["valid"]/
                    observations_per_column[c]["total"]))
         for c,vals in sorted(avail_per_column.items())},
      structural_missingness="NOT_AT_RANDOM possible; do not discard sessions blindly",
      no_fault_labels=True,vehicle_level_transfer_to_AWD_79kWh="DOMAIN_SHIFT"
    )
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k in
        ("status","summary","errors","complete_source_coverage")},
        ensure_ascii=False,allow_nan=False)[:24000])
    if report["errors"] or n!=max_files:raise SystemExit(3)
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--max-files",type=int,default=92)
    args=p.parse_args()
    full_audit(args.out,max_files=args.max_files)
if __name__=="__main__":main()
