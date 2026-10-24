#!/usr/bin/env python3
"""Post-hoc 2x2 numerical diagnostic on ORIGINAL FROZEN E66 1C evaluation ONLY.

Never recalibrates; no optimization, no module validation/blind access, no Stage4
historical holdout. Requires original Work receipts with exact SHA256.
"""
from __future__ import annotations
import argparse,hashlib,json,math,os,platform,sys,time
from pathlib import Path

os.environ["PYBAMM_DISABLE_TELEMETRY"]="true"
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.audit_e66_frozen_receipts import hash_path

# Prospective FIXED factorial diagnostic after the negative outcome was observed.
CONFIGS={
    "A_FROZEN":dict(mesh=20,rtol=1e-6,atol=1e-7),
    "B_MESH_ONLY":dict(mesh=40,rtol=1e-6,atol=1e-7),
    "C_TOL_ONLY":dict(mesh=20,rtol=1e-8,atol=1e-9),
    "D_BOTH_ORIGINAL_COMPARATOR":dict(mesh=40,rtol=1e-8,atol=1e-9),
}
PAIRS=(("A_FROZEN","B_MESH_ONLY"),("A_FROZEN","C_TOL_ONLY"),
       ("A_FROZEN","D_BOTH_ORIGINAL_COMPARATOR"),
       ("B_MESH_ONLY","D_BOTH_ORIGINAL_COMPARATOR"),
       ("C_TOL_ONLY","D_BOTH_ORIGINAL_COMPARATOR"))
MIN_SOLVER_COVERAGE=.95

def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def verify_original_receipts(folder,archive):
    folder=Path(folder)
    source=ROOT/"scripts/fit_e66_generator_b.py"
    paths={name:folder/name for name in (
        "PROSPECTIVE.json","FIT_RESULT.json","GENERATOR_B_FREEZE.json","EVALUATION.json")}
    for f in [source,archive,*paths.values()]:
        if not f.is_file():
            raise FileNotFoundError(f"BLOCKED_MISSING_ORIGINAL_WORK_RECEIPT_OR_DATA: {f}")
    spec,fit,freeze,ev=(_json(paths[k]) for k in paths)
    expected={
        "source_sha256":hash_path(source),
        "prospective_sha256":hash_path(paths["PROSPECTIVE.json"]),
        "fit_result_sha256":hash_path(paths["FIT_RESULT.json"])}
    for k,v in expected.items():
        if freeze.get(k)!=v:
            raise ValueError("FROZEN_SOURCE_OR_RECEIPT_HASH_DRIFT: "+k)
    if ev.get("freeze_sha256")!=hash_path(paths["GENERATOR_B_FREEZE.json"]):
        raise ValueError("WORK_EVALUATION_FREEZE_HASH_MISMATCH")
    if spec.get("source_archive_SHA256")!=hash_path(archive):
        raise ValueError("ORIGINAL_E66_DATA_ARCHIVE_HASH_MISMATCH")
    if fit.get("parameters")!=freeze.get("parameters"):
        raise ValueError("FREEZE_PARAMETERS_DO_NOT_MATCH_FIT")
    if freeze.get("criteria")!=spec.get("evaluation_criteria"):
        raise ValueError("PREDECLARED_CRITERIA_CHANGED")
    if freeze.get("evaluation_files")!=spec.get("evaluation"):
        raise ValueError("ORIGINAL_EVALUATION_FILES_CHANGED")
    eval_rows=ev.get("results",[])
    if len(eval_rows)!=4:
        raise ValueError("WORK_EVALUATION_INCOMPLETE")
    one_c=[x for x in spec.get("evaluation",[]) if x.endswith("Dis_1C.mat")]
    if len(one_c)!=1:
        raise ValueError("NO_SINGLE_PREDECLARED_1C_FILE")
    if sorted(x.get("model") for x in eval_rows if x.get("file")==one_c[0])!=["DFN","SPMe"]:
        raise ValueError("WORK_1C_MODEL_ROWS_INCOMPLETE")
    return spec,fit,freeze,ev,one_c[0],paths

def simulate_fixed(d,fit,kind,config):
    import numpy as np
    import pybamm
    # Mirrors physics and current scaling of FROZEN source; no model/source edits.
    p=pybamm.ParameterValues("Chen2020")
    p.set_initial_stoichiometries(1,inplace=True)
    ocp=p["Positive electrode OCP [V]"]
    offset,slope,contact=map(float,fit["parameters"])
    def corrected(sto):
        return ocp(sto)+offset+slope*(sto-.5)
    capacity=float(fit["effective_capacity_Ah"])
    if not capacity>0:raise ValueError("INVALID_FROZEN_EFFECTIVE_CAPACITY")
    p.update({"Positive electrode OCP [V]":corrected,
         "Contact resistance [Ohm]":contact,
         "Ambient temperature [K]":d["T"][0]+273.15,
         "Initial temperature [K]":d["T"][0]+273.15,
         "Lower voltage cut-off [V]":2.5,
         "Upper voltage cut-off [V]":4.5,
         "Current function [A]":pybamm.Interpolant(
             d["t"],d["i"]/(capacity/5),pybamm.t)})
    model=getattr(pybamm.lithium_ion,kind)(
        options={"thermal":"isothermal","contact resistance":"true"})
    n=config["mesh"]
    sim=pybamm.Simulation(
      model,parameter_values=p,
      var_pts={k:n for k in ["x_n","x_s","x_p","r_n","r_p"]},
      solver=pybamm.IDAKLUSolver(rtol=config["rtol"],atol=config["atol"]))
    target=float(d["t"][-1])
    t0=time.monotonic()
    sol=sim.solve([0,target])
    elapsed=time.monotonic()-t0
    final=float(sol.t[-1])
    if not math.isfinite(final) or final<0 or final>target+1:
        raise ValueError("INVALID_SOLVER_TIME")
    return dict(sol=sol,
       summary=dict(model=kind,mesh=n,rtol=config["rtol"],atol=config["atol"],
        target_duration_s=target,achieved_duration_s=final,
        coverage_fraction=final/target,termination=str(sol.termination),
        solver_wall_seconds=elapsed,
        threshold95pct_reached=final/target>=MIN_SOLVER_COVERAGE,
        complete_full_horizon=final>=target-1e-4))

def _voltage(sol,times):
    import numpy as np
    values=np.asarray(sol["Voltage [V]"](np.asarray(times,float))).reshape(-1)
    if not np.all(np.isfinite(values)):raise ValueError("NONFINITE_SOLVER_VOLTAGE")
    return values

def predictive_metrics(record,d):
    import numpy as np
    target=record["summary"]["target_duration_s"]
    end=record["summary"]["achieved_duration_s"]
    # Fixed full-horizon grid. No implicit extrapolation of early-terminated run.
    intended=np.linspace(0,target,500)
    mask=intended<=end+1e-8
    grid=intended[mask]
    if len(grid)<2:raise ValueError("INSUFFICIENT_OBSERVED_DOMAIN")
    v=_voltage(record["sol"],grid)
    actual=np.interp(grid,d["t"],d["v"])
    delta=v-actual
    thirds={}
    for name,lo,hi in (("first_third",0,1/3),("middle_third",1/3,2/3),
                       ("final_third",2/3,1.00001)):
        segment=(grid/target>=lo)&(grid/target<hi)
        errors=delta[segment]
        thirds[name]=(dict(n=int(errors.size),bias_V=float(np.mean(errors)),
            rms_V=float(np.sqrt(np.mean(errors**2))))
            if errors.size else None)
    return dict(n_evaluated=int(len(grid)),n_requested=500,
        duration_coverage_fraction=end/target,
        samples_coverage_fraction=float(len(grid)/500),
        terminated_before_full_horizon=end<target-1e-4,
        rmse_V=float(np.sqrt(np.mean(delta**2))),
        bias_V=float(np.mean(delta)),max_abs_V=float(np.max(np.abs(delta))),
        residual_by_horizon_thirds=thirds)

def compare_records(first,second):
    import numpy as np
    expected=first["summary"]["target_duration_s"]
    if abs(expected-second["summary"]["target_duration_s"])>1e-7:
        raise ValueError("MISMATCHED_PHYSICAL_TEST_LENGTH")
    full_grid=np.linspace(0,expected,500)
    domain_end=min(first["summary"]["achieved_duration_s"],
                   second["summary"]["achieved_duration_s"])
    grid=full_grid[full_grid<=domain_end+1e-8]
    if len(grid)<2:raise ValueError("NO_COMMON_TIMESTAMPS")
    gap=_voltage(first["sol"],grid)-_voltage(second["sol"],grid)
    c1=first["summary"]["coverage_fraction"]
    c2=second["summary"]["coverage_fraction"]
    return dict(visualized_common_prefix_only=True,
       compared_count=int(len(grid)),requested_count=500,
       common_duration_coverage=domain_end/expected,
       first_solver_coverage=c1,second_solver_coverage=c2,
       max_abs_difference_V=float(np.max(np.abs(gap))),
       rms_difference_V=float(np.sqrt(np.mean(gap**2))),
       tolerance_5mV_met_on_common_prefix=bool(np.max(np.abs(gap))<=.005),
       eligible_as_full_numerical_convergence_evidence=bool(
             c1>=.95 and c2>=.95 and
             first["summary"]["complete_full_horizon"] and
             second["summary"]["complete_full_horizon"]))

def verify_baseline_archived(result,archived):
    import numpy as np
    old=archived.get("trajectory")
    if not isinstance(old,list) or len(old)!=500:
        return dict(status="FAIL",reason="ORIGINAL_WORK_500_POINT_TRAJECTORY_MISSING")
    target=result["summary"]["target_duration_s"]
    end=result["summary"]["achieved_duration_s"]
    ts=np.linspace(0,min(target,end),500)
    vs=_voltage(result["sol"],ts)
    oldt=np.asarray([x["time_s"] for x in old],float)
    oldv=np.asarray([x["model_V"] for x in old],float)
    if not np.all(np.isfinite(oldv)) or not np.all(np.isfinite(oldt)):
        return dict(status="FAIL",reason="INVALID_ORIGINAL_WORK_TRAJECTORY")
    tdev=float(np.max(np.abs(ts-oldt)))
    vdev=float(np.max(np.abs(vs-oldv)))
    return dict(status="PASS" if tdev<=1e-6 and vdev<=1e-5 else "FAIL",
        archived_points=500,max_t_difference_s=tdev,max_V_difference_V=vdev,
        is_physics_comparable=tdev<=1e-6 and vdev<=1e-5)

def run(receipts,archive,out):
    import pybamm
    from scripts.fit_e66_generator_b import get_inputs
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
    report=dict(classification="RETROSPECTIVE_FROZEN_E66_1C_NUMERICAL_DIAG",
        state="BLOCKED_MISSING_ORIGINAL_WORK_RECEIPTS",
        original_evaluation_not_modified=True,
        no_refitting=True,stage4_protected_test_access=0,
        input_archive=Path(archive).name,models={},errors=[])
    try:
        spec,fit,freeze,ev,name,paths=verify_original_receipts(Path(receipts),Path(archive))
        if pybamm.__version__!="26.4.2":
            raise ValueError("PYBAMM_VERSION_DIFFERENT_FROM_PREREG: "+pybamm.__version__)
        recorded=freeze.get("environment",{})
        observed_version=platform.python_version()
        report["environment"]=dict(pybamm_version=pybamm.__version__,
            python_version=observed_version)
        for lib,actual in (("python",observed_version),
                           ("pybamm",pybamm.__version__)):
            registered=recorded.get(lib)
            if registered and registered!=actual:
                raise ValueError("FROZEN_ENVIRONMENT_DRIFT_"+lib+
                                 "_registered_"+str(registered)+"_actual_"+str(actual))
        report["freeze_sha256"]=hash_path(paths["GENERATOR_B_FREEZE.json"])
        report["original_evaluation_sha256"]=hash_path(paths["EVALUATION.json"])
        report["source_sha256"]=hash_path(ROOT/"scripts/fit_e66_generator_b.py")
        report["one_c_cell_source"]=name
        rows=get_inputs(Path(archive),[name])
        if len(rows)!=1:raise ValueError("INVALID_1C_DATA_SELECTION")
        d=rows[0]
        archival_source={
          x["model"]:x for x in ev["results"] if x.get("file")==name}
        for kind in ("SPMe","DFN"):
            models={}
            for label,config in CONFIGS.items():
                try:
                    x=simulate_fixed(d,fit,kind,config)
                    models[label]=x
                except Exception as e:
                    report["errors"].append(dict(model=kind,case=label,
                        message=type(e).__name__+": "+str(e)[:450]))
            if "A_FROZEN" in models:
                baseline=verify_baseline_archived(models["A_FROZEN"],archival_source[kind])
            else:
                baseline=dict(status="FAIL",reason="BASELINE_UNAVAILABLE")
            per_model=dict(baseline_reproduction=baseline,
                cases={},pairs={},original_work_metrics={
                     k:archival_source[kind].get(k) for k in (
                         "voltage_RMSE_V","voltage_max_error_V","coverage_fraction",
                         "numerical_refinement_max_V","gate","numerical_gate","termination")})
            for label,x in models.items():
                per_model["cases"][label]={
                    **x["summary"],"predictive":predictive_metrics(x,d)}
            for first,second in PAIRS:
                if first in models and second in models:
                    per_model["pairs"][first+"__"+second]=compare_records(
                        models[first],models[second])
            report["models"][kind]=per_model
            if baseline.get("status")!="PASS":
                report["errors"].append(dict(model=kind,case="A_FROZEN",
                    message="ORIGINAL_ARCHIVED_TRAJECTORY_NOT_REPRODUCED"))
            for pair_name,comparison in per_model["pairs"].items():
                if not comparison["eligible_as_full_numerical_convergence_evidence"]:
                    report["errors"].append(dict(model=kind,case=pair_name,
                        message="INCOMPLETE_SOLVER_HORIZON_CANNOT_PROVE_CONVERGENCE"))
            if len(per_model["cases"])!=len(CONFIGS) or len(per_model["pairs"])!=len(PAIRS):
                report["errors"].append(dict(model=kind,
                    message="REQUIRED_FACTORIAL_CASE_OR_PAIR_NOT_EXECUTED"))
            report["state"]="PARTIAL" if report["errors"] else "IN_PROGRESS"
            out.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
        report["state"]=("POST_HOC_NUMERICAL_DIAGNOSTICS_DONE"
                         if not report["errors"] and len(report["models"])==2
                         else "PARTIAL_UNVERIFIED_OR_INCOMPLETE")
    except Exception as exc:
        report["errors"].append(dict(level="PREREQUISITE_OR_CRASH",
            message=type(exc).__name__+": "+str(exc)[:600]))
        report["state"]="BLOCKED_OR_FAILED"
    out.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="models"},indent=2))
    for kind,entry in report["models"].items():
        print(json.dumps(dict(model=kind,baseline_reproduction=entry["baseline_reproduction"],
            cases=entry["cases"],pairs=entry["pairs"]),indent=2))
    if report["state"]!="POST_HOC_NUMERICAL_DIAGNOSTICS_DONE":
        raise SystemExit(3)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--receipts",required=True,type=Path)
    p.add_argument("--archive",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    run(a.receipts,a.archive,a.out)
