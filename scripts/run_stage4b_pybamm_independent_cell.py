"""Stage4B solver-only generator B: genuine third-party PyBaMM, no A model imports.

This is not A-versus-B scoring, empirical Porsche validation or GENERATOR_B_FREEZE.
"""
from __future__ import annotations
import argparse, hashlib, json, math, sys, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RESEARCH_SPEC=ROOT/"docs/decisions/STAGE4B_PYBAMM_SOLVER_QUALIFICATION_2026-10-24.md"
EXPECTED_VERSION="26.4.2"
PARAMETERS="Chen2020"
COMMANDS=[
    "Discharge at 0.5C for 20 minutes",
    "Rest for 10 minutes",
    "Charge at 0.2C for 20 minutes",
]
TEMPERATURE_KEYS=("Volume-averaged cell temperature [K]","Cell temperature [K]")
VOLTAGE_KEYS=("Terminal voltage [V]","Voltage [V]")
CURRENT_KEYS=("Current [A]",)

def _file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _choose_entries(sol,names):
    for key in names:
        try:
            entries=sol[key].entries
            data=entries.flatten().tolist() if hasattr(entries,"flatten") else list(entries)
            if not data:continue
            result=[float(x) for x in data]
            if all(math.isfinite(x) for x in result):
                return key,result
        except (KeyError, ValueError,TypeError, AttributeError):
            continue
    raise RuntimeError("missing/nonfinite solver field: "+", ".join(names))

def _solve(kind, parameters):
    import pybamm
    opts={"thermal":"lumped"}
    if kind=="SPMe":model=pybamm.lithium_ion.SPMe(options=opts)
    elif kind=="DFN":model=pybamm.lithium_ion.DFN(options=opts)
    else:raise ValueError("supported B model SPMe or DFN")
    sim=pybamm.Simulation(model,parameter_values=parameters,
       experiment=pybamm.Experiment(COMMANDS,period="30 seconds"),
       solver=pybamm.IDAKLUSolver())
    t0=time.monotonic()
    result=sim.solve(initial_soc=0.60)
    elapsed=time.monotonic()-t0
    times=[float(x) for x in result.t]
    if len(times)<3 or any(not math.isfinite(x) for x in times):
        raise RuntimeError("empty/nonfinite time grid")
    if any(y<=x for x,y in zip(times,times[1:])):
        raise RuntimeError("non-increasing time grid")
    vkey,volts=_choose_entries(result,VOLTAGE_KEYS)
    ikey,amps=_choose_entries(result,CURRENT_KEYS)
    temp_key,temps=_choose_entries(result,TEMPERATURE_KEYS)
    if not len(volts)==len(amps)==len(temps)==len(times):
        raise RuntimeError("output data shape disagreement")
    if not all(2.5<=v<=4.3 for v in volts):
        raise RuntimeError("voltage left fixed generic cell envelope")
    if not all(200.<v<380. for v in temps):
        raise RuntimeError("temperature outside broad finite solver safety range")
    # The sign of current must switch between initial discharge and last charge.
    discharge=[a for t,a in zip(times,amps) if 0<t<1199]
    charge=[a for t,a in zip(times,amps) if 1810<t<2990]
    if not discharge or not charge or sum(discharge)*sum(charge)>=0:
        raise RuntimeError("discharge/charge current sign did not reverse")
    if abs(times[-1]-3000)>60:
        raise RuntimeError("unexpected premature termination/timebase")
    return dict(model=kind,solver_name="IDAKLU",wall_seconds=elapsed,
       n_points=len(times),time_max_s=times[-1],time_min_s=times[0],
       voltage_variable=vkey,voltage_min_V=min(volts),voltage_max_V=max(volts),
       voltage_final_V=volts[-1],
       temperature_variable=temp_key,temperature_min_K=min(temps),
       temperature_max_K=max(temps),current_variable=ikey,
       discharge_current_mean_A=sum(discharge)/len(discharge),
       charge_current_mean_A=sum(charge)/len(charge),
       source_trajectory_sha256=hashlib.sha256(json.dumps(
          [[round(t,8),round(v,10),round(a,10),round(temp,8)]
           for t,v,a,temp in zip(times,volts,amps,temps)],
          separators=(",",":")).encode()).hexdigest(),
       trajectory=[dict(t_s=t,V=v,I_A=a,T_K=temp)
                   for t,v,a,temp in zip(times,volts,amps,temps)])

def main(dest):
    import pybamm
    if pybamm.__version__!=EXPECTED_VERSION:
        raise RuntimeError("unfrozen pybamm version "+pybamm.__version__)
    params=pybamm.ParameterValues(PARAMETERS)
    base=dict(status="IN_PROGRESS",scope="INDEPENDENT_PYBAMM_CELL_ONLY",
       is_approved_generator_B_freeze=False,real_taycan_validation=False,
       cross_generator_assessment=False,stage4_sealed_test_rows_used=0,
       pybamm_version=pybamm.__version__,python_version=sys.version.split()[0],
       parameter_set=PARAMETERS,parameterization_cell="LG M50, not Taycan E66",
       models=["SPMe","DFN"],thermal="lumped",initial_soc=.6,
       protocol=COMMANDS,sampling_period_s=30,
       spec_sha256=_file_hash(RESEARCH_SPEC),
       script_sha256=_file_hash(Path(__file__)),results=[])
    dest.parent.mkdir(parents=True,exist_ok=True)
    try:
        for kind in ("SPMe","DFN"):
            v=_solve(kind,params)
            base["results"].append(v)
            dest.write_text(json.dumps(base,indent=2,allow_nan=False)+"\n")
        # A second exact run of SPMe tests deterministic fixed-input repeatability.
        other=_solve("SPMe",params)
        main=base["results"][0]
        base["repeatability"]={
            "repeat_same_pybamm_SPMe_sha256":other["source_trajectory_sha256"]
                ==main["source_trajectory_sha256"],
            "voltage_final_difference_V":other["voltage_final_V"]-main["voltage_final_V"]}
        if abs(other["voltage_final_V"]-main["voltage_final_V"])>1e-6:
            raise RuntimeError("solver repeatability exceeds 1 microvolt")
        base["status"]="SOLVER_QUALIFIED_ONLY"
    except Exception as err:
        base["status"]="FAILED"
        base["error"]=type(err).__name__+": "+str(err)
        dest.write_text(json.dumps(base,indent=2,allow_nan=False)+"\n")
        raise
    dest.write_text(json.dumps(base,indent=2,allow_nan=False)+"\n")
    print(json.dumps({k:v for k,v in base.items() if k!="results"}))
    for r in base["results"]:
        print(json.dumps({k:v for k,v in r.items() if k!="trajectory"}))

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",required=True,type=Path)
    main(p.parse_args().out)
