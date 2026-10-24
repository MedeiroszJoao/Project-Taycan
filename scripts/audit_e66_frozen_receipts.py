"""Audit already-generated E66 B fit/freeze/evaluation JSON. NO fit, solver, raw data.

This script does not load raw E66 MATLAB payloads or call PyBaMM and does not
access any historic reserved Stage4 episode. If Work's receipts are absent,
fail closed. Historical 1C failure cannot be rewritten as PASS.
"""
from __future__ import annotations
import argparse,hashlib,json,math
from pathlib import Path
NAME="E66_FROZEN_EVALUATION_RECEIPT_AUDIT"
def hash_path(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def check_numeric_trajectory(row, relative_tol=1e-8):
    """Recalculate reported voltage metrics from saved 500-point evaluation.

    Returns an explicit failure for missing or incompatible trajectory. Never
    reconstructs absent records from nominal metrics or hidden test data.
    """
    values=row.get("trajectory")
    if not isinstance(values,list) or len(values)!=500:
        return dict(status="FAIL",error="ARCHIVED_500_POINT_TRAJECTORY_MISSING_OR_WRONG_LENGTH")
    try:
        ts=[float(x["time_s"]) for x in values]
        model=[float(x["model_V"]) for x in values]
        actual=[float(x["measured_V"]) for x in values]
    except (TypeError,ValueError,KeyError):
        return dict(status="FAIL",error="INVALID_TRAJECTORY_RECORD_SCHEMA")
    if not all(math.isfinite(v) for v in ts+model+actual):
        return dict(status="FAIL",error="NONFINITE_TRAJECTORY")
    if abs(ts[0])>1e-8 or any(t2<=t1 for t1,t2 in zip(ts,ts[1:])):
        return dict(status="FAIL",error="NONMONOTONE_OR_NONZERO_START")
    errors=[a-b for a,b in zip(model,actual)]
    metrics=dict(voltage_RMSE_V=math.sqrt(math.fsum(e*e for e in errors)/len(errors)),
        voltage_bias_V=math.fsum(errors)/len(errors),
        voltage_max_error_V=max(map(abs,errors)))
    duration=row.get("experimental",{}).get("duration_s")
    if not isinstance(duration,(float,int)) or not math.isfinite(duration) or duration<=0:
        return dict(status="FAIL",error="EXPERIMENT_DURATION_MISSING")
    metrics["coverage_fraction"]=ts[-1]/duration
    disagreements={}
    for key,expected in metrics.items():
        registered=row.get(key)
        if not isinstance(registered,(int,float)) or not math.isfinite(registered):
            disagreements[key]="REPORTED_VALUE_MISSING_OR_NONFINITE"
        elif not math.isclose(float(registered),expected,rel_tol=relative_tol,abs_tol=1e-8):
            disagreements[key]=dict(reported=registered,recomputed=expected)
    return dict(status="PASS" if not disagreements else "FAIL",
        error=None if not disagreements else "TRAJECTORY_METRICS_CONTRADICTION",
        differences=disagreements,recomputed=metrics,
        points=len(values),last_time_s=ts[-1])

def classify(row,criteria):
    result={"file":row.get("file"),"model":row.get("model"),"status":"FAIL",
            "reasons":[],"error_reported":row.get("error")}
    if row.get("error") or row.get("gate")=="ERROR":
        result["reasons"].append("SOLVER_ERROR")
    keys={"voltage_RMSE_V":"voltage_RMSE_V",
          "voltage_max_error_V":"voltage_max_abs_error_V",
          "coverage_fraction":"coverage_fraction_min"}
    for metric,limit_name in keys.items():
        value=row.get(metric)
        if not isinstance(value,(float,int)) or not math.isfinite(value):
            result["reasons"].append(metric+"_UNAVAILABLE");continue
        limit=criteria[limit_name]
        if metric=="coverage_fraction":
            if value < limit:result["reasons"].append("LOW_COVERAGE")
        elif value > limit:
            result["reasons"].append(metric+"_THRESHOLD_EXCEEDED")
    refinement=row.get("numerical_refinement_max_V")
    if not isinstance(refinement,(int,float)) or not math.isfinite(refinement):
        result["reasons"].append("REFINEMENT_UNAVAILABLE")
    elif refinement>criteria["numerical_refinement_V_max"]:
        result["reasons"].append("REFINEMENT_THRESHOLD_EXCEEDED")
    if row.get("numerical_gate")!="PASS":
        result["reasons"].append("NUMERICAL_GATE_NOT_PASS")
    if row.get("gate")!="PASS":
        result["reasons"].append("EMPIRICAL_GATE_NOT_PASS")
    result["status"]="PASS" if not result["reasons"] else "FAIL"
    result["reported_metrics"]={k:row.get(k) for k in (
      "voltage_RMSE_V","voltage_max_error_V","voltage_bias_V",
      "coverage_fraction","numerical_refinement_max_V","gate","numerical_gate",
      "termination")}
    return result

def audit(directory,source_path,report_path):
    directory=Path(directory)
    mapping={"spec":directory/"PROSPECTIVE.json",
             "fit":directory/"FIT_RESULT.json",
             "freeze":directory/"GENERATOR_B_FREEZE.json",
             "evaluation":directory/"EVALUATION.json"}
    for k,path in mapping.items():
        if not path.is_file():raise FileNotFoundError("WORK_RECEIPT_NOT_PUBLISHED:"+str(path))
    receipts={k:json.loads(path.read_text(encoding="utf-8")) for k,path in mapping.items()}
    spec,fit,freeze,evaluation=(receipts[x] for x in ("spec","fit","freeze","evaluation"))
    reasons=[]
    code_source_hash=hash_path(source_path) if Path(source_path).is_file() else None
    hashes={
      "source_recorded":freeze.get("source_sha256"),
      "source_verifiable_from_GitHub":code_source_hash,
      "fit_recorded":freeze.get("fit_result_sha256"),
      "fit_actual":hash_path(mapping["fit"]),
      "prereg_recorded":freeze.get("prospective_sha256"),
      "prereg_actual":hash_path(mapping["spec"]),
      "freeze_sha256":hash_path(mapping["freeze"]),
      "evaluation_source_hash":evaluation.get("freeze_sha256")}
    for a,b,key in (
      ("source_recorded","source_verifiable_from_GitHub","SOURCE"),
      ("fit_recorded","fit_actual","FIT_RESULT"),
      ("prereg_recorded","prereg_actual","PROSPECTIVE"),
      ("freeze_sha256","evaluation_source_hash","FREEZE_IN_EVALUATION")):
        if not hashes[a] or not hashes[b] or hashes[a]!=hashes[b]:
            reasons.append(key+"_HASH_MISMATCH_OR_MISSING")
    if freeze.get("parameters") != fit.get("parameters"):
        reasons.append("FIT_FREEZE_PARAMETERS_DIFFER")
    if freeze.get("evaluation_files") != spec.get("evaluation"):
        reasons.append("EVALUATION_DESIGN_DIFFER")
    if freeze.get("criteria") != spec.get("evaluation_criteria"):
        reasons.append("CRITERIA_DIFFER")
    if freeze.get("before_evaluation") is not True:
        reasons.append("BEFORE_EVALUATION_CLAIM_MISSING")
    # Declaration alone cannot independently verify real chronological freezing.
    chronological_freeze_external_proof=False
    c=spec.get("evaluation_criteria",{})
    required={"voltage_RMSE_V","voltage_max_abs_error_V",
        "coverage_fraction_min","numerical_refinement_V_max"}
    if not required.issubset(c) or any(not isinstance(c[z],(int,float)) for z in required):
        raise ValueError("PREREG_CRITERIA_INVALID")
    records=evaluation.get("results",[])
    expected={(file,mod) for file in spec.get("evaluation",[])
               for mod in ("SPMe","DFN")}
    actual={(r.get("file"),r.get("model")) for r in records}
    if len(expected)!=4 or len(records)!=4 or expected!=actual:
        reasons.append("MISSING_DUPLICATE_OR_WRONG_EVAL_PAIR")
    classified=[classify(row,c) for row in records]
    numeric_consistency=[dict(file=row.get("file"),model=row.get("model"),
        check=check_numeric_trajectory(row)) for row in records]
    if any(x["check"]["status"]!="PASS" for x in numeric_consistency):
        reasons.append("ARCHIVED_TRAJECTORY_METRIC_INCONSISTENCY_OR_MISSING")
    counts={"PASS":sum(x["status"]=="PASS" for x in classified),
            "FAIL":sum(x["status"]=="FAIL" for x in classified)}
    evidence=dict(
       classification=NAME,
       analysis="READ_ONLY_POST_FREEZE_RECEIPT_AUDIT_NOT_A_NEW_FIT",
       verifies_freeze_historical_timestamp=False,
       freeze_reported_before_evaluation=freeze.get("before_evaluation",False),
       independent_chronology_proven=chronological_freeze_external_proof,
       local_hashes=hashes,
       receipt_integrity="PASS" if not reasons else "FAIL",
       receipt_failures=reasons,
       models=models if (models:=sorted(set(x.get("model","") for x in records))) else [],
       evaluations=classified,
       trajectory_integrity=numeric_consistency,
       n_reports=len(records),
       gate_counts=counts,
       all_eval_pass=counts["PASS"]==4 and not reasons,
       explicitly_unresolved=[
         "Numerical mesh+solver tolerance changed together; not isolatable in original refinement result",
         "Same cell repeated protocols, not independent units",
         "Original Work solver logs and recorded evaluation timing required",
         "Nothing here validates pack thermal performance or fault diagnosis",
       ],
       historical_stage4_reserved_cases_read=0)
    report_path=Path(report_path);report_path.parent.mkdir(parents=True,exist_ok=True)
    report_path.write_text(json.dumps(evidence,indent=2,allow_nan=False)+"\n")
    print(json.dumps({k:v for k,v in evidence.items() if k!="evaluations"},indent=2))
    for e in classified:print(json.dumps(e))
    if reasons:raise SystemExit("FREEZE_OR_RECEIPT_INTEGRITY_FAIL")
    return evidence

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--receipts",type=Path,required=True)
    p.add_argument("--source",type=Path,default=Path("scripts/fit_e66_generator_b.py"))
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args();audit(a.receipts,a.source,a.out)
