"""Stage4B POST-HOC control of numerical effects with UNFITTED Chen2020.

This does NOT reconstruct or validate Work's missing E66 generator freeze. It
uses no E66 cell experiment, no Taycan simulator A and no protected holdout.
The fixed generic 1C current checks *software-level* mesh/tolerance behavior.
"""
from __future__ import annotations
import argparse,hashlib,json,math,platform,statistics,time
from pathlib import Path

GRID={"A_original_numerics":(20,1e-6,1e-7),
      "B_mesh_only":(40,1e-6,1e-7),
      "C_tolerance_only":(20,1e-8,1e-9),
      "D_both":(40,1e-8,1e-9)}
PAIRS=(("A_original_numerics","B_mesh_only"),
       ("A_original_numerics","C_tolerance_only"),
       ("A_original_numerics","D_both"),
       ("B_mesh_only","D_both"),
       ("C_tolerance_only","D_both"))
TIME_END=1200.
SAMPLES=241
INITIAL_SOC=.8
I_A=5.
TEMP_K=298.15
GAP_THRESHOLD_V=.005

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def run_model(model_name,n,rtol,atol,grid,pybamm):
    import numpy as np
    p=pybamm.ParameterValues("Chen2020")
    p.set_initial_stoichiometries(INITIAL_SOC,inplace=True)
    p.update({"Current function [A]":I_A,
              "Initial temperature [K]":TEMP_K,
              "Ambient temperature [K]":TEMP_K,
              "Contact resistance [Ohm]":.001})
    model_cls=getattr(pybamm.lithium_ion,model_name)
    model=model_cls(options={"thermal":"isothermal","contact resistance":"true"})
    sim=pybamm.Simulation(model,parameter_values=p,
        var_pts={k:n for k in ("x_n","x_s","x_p","r_n","r_p")},
        solver=pybamm.IDAKLUSolver(rtol=rtol,atol=atol))
    start=time.monotonic()
    sol=sim.solve(t_eval=np.linspace(0,TIME_END,SAMPLES))
    elapsed=time.monotonic()-start
    last=float(sol.t[-1])
    if len(sol.t)<2 or last>TIME_END+1e-8:
        raise ValueError("INVALID_SOLVER_TIME")
    mask=grid<=last+1e-7
    times=grid[mask]
    if not len(times):raise ValueError("NO_TIME_GRID")
    voltage=np.asarray(sol["Voltage [V]"](times),float).reshape(-1)
    if voltage.size!=times.size or not np.all(np.isfinite(voltage)):
        raise ValueError("INVALID_CELL_VOLTAGE")
    if any((voltage<2.5)|(voltage>4.3)):
        raise ValueError("OUTSIDE_GENERIC_CELL_VOLTAGE_RANGE")
    return dict(model=model_name,mesh=n,rtol=rtol,atol=atol,
        t_final_s=last,coverage_fraction=last/TIME_END,
        full_horizon=bool(last>=TIME_END-1e-5),
        n_points=int(len(times)),voltage_min_V=float(voltage.min()),
        voltage_max_V=float(voltage.max()),voltage_end_V=float(voltage[-1]),
        termination=str(sol.termination),elapsed_wall_seconds=elapsed,
        trace_sha256=hashlib.sha256(voltage.tobytes()).hexdigest()),voltage,mask

def comparison(a,b):
    import numpy as np
    x,v,m=a;y,w,n=b
    mask=m&n
    if not np.any(mask):raise ValueError("NO_COMMON_TIME")
    err=v[:int(np.sum(mask))]-w[:int(np.sum(mask))]
    mx=float(np.max(np.abs(err)))
    return dict(model=x["model"],comparison=x["label"]+"_vs_"+y["label"],
       n_common=int(mask.sum()),max_abs_voltage_gap_V=mx,
       rms_voltage_gap_V=float(np.sqrt(np.mean(err*err))),
       max_gap_threshold_met=bool(mx<=GAP_THRESHOLD_V),
       both_full_horizon=bool(x["full_horizon"] and y["full_horizon"]),
       allowed_to_claim_full_horizon_convergence=bool(
           x["full_horizon"] and y["full_horizon"] and mx<=GAP_THRESHOLD_V))

def run(out):
    import numpy as np,pybamm
    if pybamm.__version__!="26.4.2":raise ValueError("PYBAMM_VERSION_DRIFT")
    t=np.linspace(0,TIME_END,SAMPLES)
    path=Path(out);path.parent.mkdir(parents=True,exist_ok=True)
    report=dict(status="IN_PROGRESS",
      classification="POSTHOC_UNFITTED_CHEN2020_NUMERICS_ONLY_NOT_E66_FREEZE",
      no_e66_empirical_files_read=True,no_original_stage4_test_read=True,
      no_porsche_4s_calibration=True,original_work_1c_failure_preserved=True,
      original_work_frozen_params_recovered=False,
      python=platform.python_version(),pybamm=pybamm.__version__,
      model_parameters="Chen2020 LG M50 UNFITTED",
      current_A=I_A,temperature_K=TEMP_K,initial_soc=INITIAL_SOC,
      requested_seconds=TIME_END,output_points=SAMPLES,
      file_sha256=sha(__file__),models={},comparisons=[],failures=[])
    for kind in ("SPMe","DFN"):
        cases={}
        for label,(mesh,rtol,atol) in GRID.items():
            try:
                d,v,mask=run_model(kind,mesh,rtol,atol,t,pybamm)
                d["label"]=label
                cases[label]=(d,v,mask)
                report["models"].setdefault(kind,[]).append(d)
                print("SOLVED",kind,label,"max",d["voltage_max_V"],
                      "end",d["t_final_s"],flush=True)
            except Exception as e:
                report["failures"].append(dict(model=kind,label=label,
                    error=type(e).__name__+": "+str(e)[:450]))
        for first,second in PAIRS:
            if first in cases and second in cases:
                try:
                    report["comparisons"].append(comparison(cases[first],cases[second]))
                except Exception as e:
                    report["failures"].append(dict(model=kind,
                        pair=first+"__"+second,error=type(e).__name__+": "+str(e)[:450]))
        path.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    report["status"]=("NUMERICAL_CONTROL_EXECUTED"
       if all(len(z)==4 for z in report["models"].values())
          and len(report["models"])==2 and len(report["comparisons"])==10
          and not report["failures"]
       else "INCOMPLETE")
    report["scientific_gate"]="PASS" if (
       report["status"]=="NUMERICAL_CONTROL_EXECUTED" and
       all(x["allowed_to_claim_full_horizon_convergence"] for x in report["comparisons"])
       ) else "FAIL_OR_INCONCLUSIVE"
    path.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print("SUMMARY",json.dumps({k:v for k,v in report.items() if k!="models"},
                                 allow_nan=False))
    if report["status"]!="NUMERICAL_CONTROL_EXECUTED":
        raise SystemExit("CONTROL_INCOMPLETE")
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True,type=Path)
    run(p.parse_args().out)
