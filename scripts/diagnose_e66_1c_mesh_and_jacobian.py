"""Retrospective E66 mesh convergence and fixed-step Jacobian sensitivity.

INPUT receipts are *POSTHOC RECONSTRUCTED*, never original Work freeze.
No fit, no evaluation of virgin heldout. All physical parameters frozen.
"""
from __future__ import annotations
import argparse,copy,hashlib,json,math,platform,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.diagnose_e66_1c_frozen_numerics import (
    verify_original_receipts,simulate_fixed,predictive_metrics,
    compare_records,verify_baseline_archived)
from scripts.fit_e66_generator_b import get_inputs,simulate
from scripts.audit_e66_frozen_receipts import hash_path
MESHES=(20,40,80,160)
TOL=dict(rtol=1e-8,atol=1e-9)
FIT_STEPS=(.001,.001,.001)
PAIRS=((20,40),(40,80),(80,160))

def _fit_jacobian(freeze,fit,archive,files):
    import numpy as np
    curves=get_inputs(archive,files)
    if len(curves)!=2:raise ValueError("TWO_ORIGINAL_FIT_CURVES_REQUIRED")
    p=np.array(fit["parameters"],float)
    q=fit["effective_capacity_Ah"]
    mats=[];diagnostics=[]
    # No optimizer run here. Each derivative uses explicit absolute physical step.
    for dataset in curves:
        t,v,term=simulate(dataset,p,q,mesh=40,fit=True)
        expected_duration=.9*dataset["t"][-1]
        if t[-1]<expected_duration-1e-5 or len(t)!=150:
            raise RuntimeError("FIT_CURVE_REFERENCE_PREMATURE_STOP")
        cols=[]
        for param,delta in enumerate(FIT_STEPS):
            x=p.copy();x[param]+=delta
            times,volts,_=simulate(dataset,x,q,mesh=40,fit=True)
            if len(times)!=len(t) or np.max(np.abs(times-t))>1e-5:
                raise RuntimeError("FIT_CURVE_SENSITIVITY_INCONSISTENT_TIMEGRID")
            col=(volts-v)/delta
            if not np.all(np.isfinite(col)):raise RuntimeError("NONFINITE_FIT_JAC_COLUMN")
            cols.append(col)
        matrix=np.column_stack(cols)
        mats.append(matrix)
        diagnostics.append(dict(file=dataset["name"],n=int(len(t)),
            voltage_sensitivity_column_norms=[float(np.linalg.norm(c)) for c in cols]))
    matrix=np.vstack(mats)
    s=np.linalg.svd(matrix,compute_uv=False)
    rank=int(np.linalg.matrix_rank(matrix))
    return dict(method="ABSOLUTE_FORWARD_DIFFERENCE_ON_ORIGINAL_2_FIT_CURVES_ONLY",
        param_names=["positive_ocp_offset_V","positive_ocp_stoich_slope_V",
                     "effective_M50_contact_resistance_ohm"],
        frozen_parameter_vector=p.tolist(),steps_absolute=FIT_STEPS,
        jacobian_shape=list(matrix.shape),
        numerical_rank=rank,singular_values=s.tolist(),
        contact_column_norm=float(np.linalg.norm(matrix[:,2])),
        source_optimizer_recorded_rank=fit["jacobian_rank"],
        source_optimizer_recorded_singular_values=fit["conditional_jacobian_singular_values"],
        source_optimizer_contact_R_at_boundary=bool(abs(p[2])<1e-10),
        any_claim_of_global_structural_identifiability=False,
        dataset_sensitivity_details=diagnostics)

def run(receipts,archive,out):
    import pybamm
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
    report=dict(classification="RETROSPECTIVE_POSTHOC_E66_MESH_JACOBIAN_ONLY",
       original_Work_FIT_FREEZE_recovered=False,
       original_Work_1C_FAIL_preserved=True,no_refit_or_parameter_update=True,
       original_1152_stage4_test_rows_used=0,
       status="BLOCKED",source_data_archive_uploaded=False,
       numeric_comparisons=[],solver_results=[],errors=[])
    try:
        spec,fit,freeze,ev,one_c,paths=verify_original_receipts(
            receipts,archive)
        if pybamm.__version__!="26.4.2":
            raise RuntimeError("PYBAMM_26_4_2_REQUIRED")
        receipt_marker=Path(receipts).parent/"POSTHOC_PROVENANCE.json"
        if not receipt_marker.is_file():
            raise RuntimeError("POSTHOC_PROVENANCE_ORIGIN_MISSING")
        origin=json.loads(receipt_marker.read_text())
        if origin.get("classification")!="POSTHOC_RECONSTRUCTED_AFTER_1C_OUTCOMES_KNOWN":
            raise RuntimeError("ATTEMPT_TO_USE_UNLABELED_ORIGINAL_WORK_FREEZE")
        if origin.get("official_inner_md5")!="734d8c3c262d7dcbd4eaf1b6b366e079":
            raise RuntimeError("PUBLISHER_SOURCE_PROVENANCE_DRIFT")
        for fn,key in (("FIT_RESULT.json","fit_result_sha256"),
                       ("GENERATOR_B_FREEZE.json","freeze_sha256"),
                       ("EVALUATION.json","eval_sha256")):
            rec=origin.get("reconstruction_receipt_sha256",{}).get(fn)
            actual=hash_path(Path(receipts)/fn)
            if rec!=actual:
                raise RuntimeError("RECONSTRUCTED_"+fn+"_SHA_MISMATCH")
        report["source_sha256"]=hash_path(ROOT/"scripts/fit_e66_generator_b.py")
        report["reconstructed_freeze_sha256"]=hash_path(Path(receipts)/"GENERATOR_B_FREEZE.json")
        report["raw_inner_public_sha256"]=origin["official_inner_sha256"]
        report["outer_wrapper_sha256"]=hash_path(archive)
        report["pybamm_version"]=pybamm.__version__
        report["python_version"]=platform.python_version()
        measurements=get_inputs(archive,[one_c])
        if len(measurements)!=1:
            raise RuntimeError("EXPECTED_ONLY_1C_EXPOSED_CELL")
        data=measurements[0]
        report["1C_source"]=data["name"]
        report["baseline_source_evaluation"]=[{
          k:rec.get(k) for k in ("file","model","voltage_RMSE_V",
                                  "voltage_max_error_V","numerical_refinement_max_V",
                                  "gate","numerical_gate")}
          for rec in ev["results"] if rec.get("file")==one_c]
        report["status"]="IN_PROGRESS"
        for model in ("SPMe","DFN"):
            cases={}
            for mesh in MESHES:
                try:
                    record=simulate_fixed(data,fit,model,dict(mesh=mesh,**TOL))
                    cases[mesh]=record
                    report["solver_results"].append(dict(model=model,mesh=mesh,
                         **record["summary"],
                         predictive=predictive_metrics(record,data)))
                    print("MESH_SOLVED",model,mesh,flush=True)
                except Exception as e:
                    report["errors"].append(dict(model=model,mesh=mesh,
                         error=type(e).__name__+": "+str(e)[:320]))
            for n1,n2 in PAIRS:
                if n1 in cases and n2 in cases:
                    p=compare_records(cases[n1],cases[n2])
                    report["numeric_comparisons"].append(dict(
                         model=model,mesh_a=n1,mesh_b=n2,
                         **p,passes_fixed_5mV_full_horizon=bool(
                            p["eligible_as_full_numerical_convergence_evidence"] and
                            p["max_abs_difference_V"]<=.005)))
            out.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
        report["fixed_step_jacobian"]=_fit_jacobian(freeze,fit,archive,spec["fit"])
        report["status"]=("DIAGNOSTICS_COMPLETE_NOT_VALIDATION"
            if len(report["solver_results"])==8 and
               len(report["numeric_comparisons"])==6 and
               not report["errors"] else "PARTIAL_OR_FAILED")
    except Exception as e:
        report["errors"].append(dict(stage="PREREQUISITES_OR_ANALYSIS",
            error=type(e).__name__+": "+str(e)[:470]))
        report["status"]="FAILED_OR_BLOCKED"
    out.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print("MESH_AND_JACOBIAN",json.dumps({k:v for k,v in report.items()
        if k not in ("solver_results",)},indent=2,allow_nan=False),flush=True)
    if report["status"]!="DIAGNOSTICS_COMPLETE_NOT_VALIDATION":
        raise SystemExit(3)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--receipts",type=Path,required=True)
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args();run(a.receipts,a.archive,a.out)
