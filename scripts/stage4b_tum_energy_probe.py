#!/usr/bin/env python3
"""Stage4B TUM empirical CAN battery/motor accounting. No model-A fit or labels.

Only 12 predeclared SHA256-sorted-by-path recordings of 92 total, on one
RWD car. Downloads to temporary disk; no raw CAN re-hosted or retained.
"""
from __future__ import annotations
import argparse,collections,csv,hashlib,json,math,os,statistics,subprocess,tempfile
from pathlib import Path
from scripts.inspect_stage4b_tum_public_rsync import SOURCE,list_archive
from scripts.audit_stage4b_tum_can_full import parse_num,hash_file,remote_copy

DT_MAX=1.0
WINDOW_S=600.0
MIN_SOC_PP=1.0
MIN_COVERAGE=0.80
MAX_FILE=65_000_000
N_SELECT=12

def select(frame):
    f=[x for x in frame if x["path"].lower().endswith(".csv")]
    assert len(f)==92,"source listing no longer contains 92 recordings"
    return sorted(f,key=lambda x:hashlib.sha256(x["path"].encode()).hexdigest())[:N_SELECT]

def _positive_median(vals):
    return statistics.median(vals) if vals else None

def _analyze(path:Path,name:str):
    stats=collections.Counter()
    binned={}
    prev=None
    time_min=None;time_max=None
    E_net=0.0;E_abs=0.0;Q_net=0.0;Q_abs=0.0;Mech_net=0.0
    paired_total=0.0
    voltage_mean_sum=0.;voltage_n=0
    with path.open(newline="",encoding="utf-8-sig",errors="replace") as f:
        reader=csv.DictReader(f)
        need={"time","hv_current","hv_voltage","hv_soc","motor_torque","motor_speed"}
        if not need.issubset(set(reader.fieldnames or [])):
            raise ValueError("missing required columns")
        for row in reader:
            stats["rows"]+=1
            t=parse_num(row["time"])
            i=parse_num(row["hv_current"])
            v=parse_num(row["hv_voltage"])
            soc=parse_num(row["hv_soc"])
            rpm=parse_num(row["motor_speed"])
            torque=parse_num(row["motor_torque"])
            if t is None:
                stats["time_missing"]+=1;prev=None;continue
            if time_min is None:time_min=t
            time_max=t
            if v is not None and v>0:
                voltage_mean_sum+=v;voltage_n+=1
            if soc is not None and not(0<=soc<=100):
                stats["invalid_soc"]+=1;soc=None
            if v is not None and not(0<v<=1500):
                stats["invalid_hv_voltage"]+=1;v=None
            if i is None:stats["current_missing"]+=1
            if v is None:stats["voltage_missing_or_invalid"]+=1
            if soc is None:stats["soc_missing_or_invalid"]+=1
            if rpm is None or torque is None:stats["mechanical_missing"]+=1
            window=int((t-(time_min or 0))//WINDOW_S)
            win=binned.setdefault(window,dict(start=None,end=None,q=0.,coverage_s=0.,
                                               span_first=t,span_last=t,
                                               usable_pair_count=0))
            win["span_last"]=t
            if soc is not None:
                if win["start"] is None:win["start"]=soc
                win["end"]=soc
            if prev is not None:
                dt=t-prev["t"]
                if dt<=0:
                    stats["nonincreasing_pairs"]+=1
                elif dt>DT_MAX:
                    stats["gap_gt_1s_pairs"]+=1
                else:
                    stats["valid_time_pairs"]+=1
                    if all(z is not None for z in (i,prev["i"])):
                        current_integral=.5*(i+prev["i"])*dt
                        Q_net+=current_integral/3600.
                        Q_abs+=(abs(i)+abs(prev["i"]))*dt/7200.
                        # Do not integrate one interval across multiple 600s bins.
                        if int((prev["t"]-(time_min or 0))//WINDOW_S)==window:
                            win["q"]+=current_integral/3600.
                            win["coverage_s"]+=dt
                            win["usable_pair_count"]+=1
                            stats["current_pairs"]+=1
                    else:stats["missing_current_pairs"]+=1
                    if all(z is not None for z in (i,prev["i"],v,prev["v"])):
                        pe=.5*(v*i+prev["v"]*prev["i"])*dt/3.6e6
                        E_net+=pe
                        E_abs+=(abs(v*i)+abs(prev["v"]*prev["i"]))*dt/7.2e6
                        paired_total+=dt
                        stats["voltage_current_pairs"]+=1
                    else:stats["voltage_current_missing_pairs"]+=1
                    if all(z is not None for z in (torque,rpm,prev["torque"],prev["rpm"])):
                        Mech_net+=(torque*rpm+prev["torque"]*prev["rpm"])*math.pi/60*dt/3.6e6
                        stats["mechanical_pairs"]+=1
                    else:stats["mechanical_missing_pairs"]+=1
            prev=dict(t=t,i=i,v=v,soc=soc,rpm=rpm,torque=torque)
    windows=[]
    for k,w in sorted(binned.items()):
        span=w["span_last"]-w["span_first"]
        dsoc=(w["end"]-w["start"]) if w["end"] is not None and w["start"] is not None else None
        coverage=(w["coverage_s"]/span) if span>0 else 0.
        eligible=bool(dsoc is not None and abs(dsoc)>=MIN_SOC_PP
                      and coverage>=MIN_COVERAGE)
        q=w["q"]
        effective=100*abs(q)/abs(dsoc) if eligible else None
        windows.append(dict(index=k,duration_s=span,delta_soc_pp=dsoc,
            current_ah_signed=q,current_coverage=coverage,eligible=eligible,
            effective_capacity_Ah_abs=effective,sign_agreement=(
            math.copysign(1,dsoc)==math.copysign(1,q)) if eligible and q!=0 else None))
    eligible=[w for w in windows if w["eligible"]]
    corr_concordant=sum(w["sign_agreement"] is True for w in eligible)
    corr_opposite=sum(w["sign_agreement"] is False for w in eligible)
    return dict(filename=name,status="PASS",sha256=hash_file(path),bytes=path.stat().st_size,
        rows=stats["rows"],time_first_s=time_min,time_last_s=time_max,
        duration_s=(time_max-time_min if time_min is not None else None),
        net_terminal_signed_kWh=E_net,
        absolute_terminal_kWh=E_abs,
        net_current_Ah_signed=Q_net,absolute_current_Ah=Q_abs,
        net_single_motor_mechanical_kWh=Mech_net,
        voltage_average_V=voltage_mean_sum/voltage_n if voltage_n else None,
        valid_voltage_current_time_s=paired_total,
        pair_and_data_counts=dict(stats),
        ten_minute_windows_total=len(windows),ten_minute_windows_eligible=len(eligible),
        eligible_same_sign=corr_concordant,eligible_opposite_sign=corr_opposite,
        effective_Ah_window_median=_positive_median([x["effective_capacity_Ah_abs"]
                            for x in eligible if x["effective_capacity_Ah_abs"] is not None]),
        windows=windows)

def run(out:Path):
    env=os.environ.copy()
    env["RSYNC_PASSWORD"]="m1774217.001"  # published by TUM in public dataset page
    frame,_=list_archive(env)
    chosen=select(frame)
    report=dict(classification="UNSEALED_EXTERNAL_REAL_CAN_DIAGNOSTIC",
        precommit="docs/decisions/STAGE4B_TUM_ENERGY_PROBE_PROSPECTIVE_2026-10-24.md",
        dataset_doi="10.14459/2025mp1774217.001",
        model_A_calibrated=False,model_B_frozen=False,
        one_vehicle_repeated_12_sessions=True,
        sample_rule="lowest_SHA256_of_relative_filepath_12_of_92",
        source="rsync_public_TUM",measurement_unit_conventions="PROVISIONAL",
        raw_data_republished=False,compared_faults=False,
        selected_paths=[x["path"] for x in chosen],report=[],errors=[])
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        for pos,x in enumerate(chosen):
            destination=Path(directory)/(str(pos)+".csv")
            try:
                if x["size_bytes"]>MAX_FILE:raise ValueError("file exceeds cap")
                remote_copy(x["path"],destination,env)
                if destination.stat().st_size!=x["size_bytes"]:
                    raise ValueError("source byte count changed")
                r=_analyze(destination,x["path"])
                report["report"].append(r)
            except Exception as exc:
                report["errors"].append(dict(path=x["path"],reason=
                    type(exc).__name__+": "+str(exc)[:250]))
            finally:
                if destination.exists():destination.unlink()
            out.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
            print("TUM ENERGY DIAG",pos+1,"/",len(chosen),"failed",len(report["errors"]),flush=True)
    xs=report["report"]
    elig=sum(x["ten_minute_windows_eligible"] for x in xs)
    report["summary"]=dict(processed=len(xs),failed=len(report["errors"]),
        total_rows=sum(x["rows"] for x in xs),recordings_with_voltage_current_pairs=sum(
        x["pair_and_data_counts"].get("voltage_current_pairs",0)>0 for x in xs),
        eligible_SOC_windows=elig,
        agreeing_eligible_SOC_windows=sum(x["eligible_same_sign"] for x in xs),
        opposing_eligible_SOC_windows=sum(x["eligible_opposite_sign"] for x in xs),
        per_recording_capacity_Ah_medians=[dict(file=x["filename"],
              Ah=x["effective_Ah_window_median"],windows=x["ten_minute_windows_eligible"])
              for x in xs],vehicle_replicates=1,
        inference="exploratory_within_one_RWD_vehicle_not_Taycan_4S_fault_accuracy")
    report["status"]="COMPLETED" if len(xs)==N_SELECT and not report["errors"] else "INCOMPLETE"
    out.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k in
      ("status","summary","selected_paths")},indent=2),flush=True)
    if report["status"]!="COMPLETED":raise SystemExit(3)

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True)
    run(p.parse_args().out)
