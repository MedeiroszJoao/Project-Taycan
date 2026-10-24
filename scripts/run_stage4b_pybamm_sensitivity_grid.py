"""Fixed 18-solve PyBaMM cell-level sensitivity. NEVER imports simulator A."""
from __future__ import annotations
import argparse,hashlib,json,math,statistics,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.run_stage4b_pybamm_independent_cell import _choose_entries,_file_hash
RATES=(.25,.5,1.)
TEMPS=(288.15,298.15,308.15)
KEYS_TEMP=("Volume-averaged cell temperature [K]","Cell temperature [K]")
KEYS_V=("Terminal voltage [V]","Voltage [V]")
KEYS_I=("Current [A]",)
PREREG=ROOT/"docs/decisions/STAGE4B_PYBAMM_SENSITIVITY_PREREG_2026-10-24.md"

def _interp(times,values,target):
    import bisect
    if target<times[0]-1e-6 or target>times[-1]+1e-6:
        raise ValueError("extrapolation prohibited")
    if target<=times[0]:return values[0]
    if target>=times[-1]:return values[-1]
    ix=bisect.bisect_right(times,target)-1
    t0,t1=times[ix],times[ix+1]
    return values[ix]+(values[ix+1]-values[ix])*(target-t0)/(t1-t0)

def solve_case(kind,rate,temp,pybamm):
    p=pybamm.ParameterValues("Chen2020")
    p.update({"Initial temperature [K]":temp,"Ambient temperature [K]":temp})
    opts={"thermal":"lumped"}
    mod=pybamm.lithium_ion.SPMe(options=opts) if kind=="SPMe" else pybamm.lithium_ion.DFN(options=opts)
    exp=pybamm.Experiment(
       [f"Discharge at {rate}C for 20 minutes","Rest for 10 minutes",
        "Charge at 0.2C for 20 minutes"],period="30 seconds")
    sim=pybamm.Simulation(mod,parameter_values=p,experiment=exp,solver=pybamm.IDAKLUSolver())
    now=time.monotonic()
    sol=sim.solve(initial_soc=.6)
    elapsed=time.monotonic()-now
    t=[float(v) for v in sol.t]
    vk,v=_choose_entries(sol,KEYS_V);tk,T=_choose_entries(sol,KEYS_TEMP)
    ik,I=_choose_entries(sol,KEYS_I)
    if len(t)!=len(v) or len(t)!=len(T) or len(t)!=len(I):
        raise ValueError("ragged solver outputs")
    if len(t)<30 or abs(t[-1]-3000)>60:
        raise ValueError("early termination or insufficient results")
    if any(y<=x for x,y in zip(t,t[1:])):
        raise ValueError("timebase is not increasing")
    if not all(2.5<=x<=4.3 for x in v):
        raise ValueError("cell voltage outside prospective screening range")
    if not all(200<x<380 for x in T):
        raise ValueError("cell temperature outside broad prospective screening range")
    if not abs(T[0]-temp)<1.e-3:
        raise ValueError("initial thermal condition not applied")
    charge=[x for tt,x in zip(t,I) if 1810<tt<2990]
    discharge=[x for tt,x in zip(t,I) if 5<tt<1195]
    if not charge or not discharge or statistics.fmean(discharge)*statistics.fmean(charge)>=0:
        raise ValueError("current sign does not switch")
    return dict(model=kind,rate_C=rate,ambient_initial_K=temp,
       n_samples=len(t),duration_s=t[-1],solver_wall_s=elapsed,
       voltage_min_V=min(v),voltage_max_V=max(v),voltage_end_V=v[-1],
       temperature_min_K=min(T),temperature_max_K=max(T),temperature_end_K=T[-1],
       current_discharge_mean_A=statistics.fmean(discharge),
       current_charge_mean_A=statistics.fmean(charge),variable_names=dict(V=vk,T=tk,I=ik),
       trajectory_sha256=hashlib.sha256(json.dumps(
           list(zip(t,v,T,I)),separators=(",",":")).encode()).hexdigest(),
       trajectory=dict(t=t,volts=v,temp=T,current=I))
def pair_compare(a,b):
    ticks=list(range(0,3001,30))
    dv=[_interp(a["trajectory"]["t"],a["trajectory"]["volts"],t)-
        _interp(b["trajectory"]["t"],b["trajectory"]["volts"],t) for t in ticks]
    dt=[_interp(a["trajectory"]["t"],a["trajectory"]["temp"],t)-
        _interp(b["trajectory"]["t"],b["trajectory"]["temp"],t) for t in ticks]
    return dict(rate_C=a["rate_C"],ambient_initial_K=a["ambient_initial_K"],
      common_times=101,
      rms_voltage_difference_V=math.sqrt(statistics.fmean(x*x for x in dv)),
      max_absolute_voltage_difference_V=max(map(abs,dv)),
      rms_temperature_difference_K=math.sqrt(statistics.fmean(x*x for x in dt)),
      max_absolute_temperature_difference_K=max(map(abs,dt)))

def main(out):
    import pybamm
    if pybamm.__version__!="26.4.2":raise ValueError("version contract")
    result=dict(status="IN_PROGRESS",classification="INDEPENDENT_CELL_MODEL_FORM_SENSITIVITY",
       independent_from_project_A=True,external_cell_validation=False,
       formal_generator_B_freeze=False,stage4_sealed_cases_read=0,
       PyBaMM_version=pybamm.__version__,python_version=sys.version.split()[0],
       model_parameter_set="Chen2020 (LG M50, not Porsche E66)",
       models=["SPMe","DFN"],rates=list(RATES),temps_K=list(TEMPS),
       spec_sha256=_file_hash(PREREG),script_sha256=_file_hash(Path(__file__)),
       runs=[],comparisons=[],errors=[])
    out.parent.mkdir(parents=True,exist_ok=True)
    for temp in TEMPS:
        for rate in RATES:
            cases=[]
            for kind in ("SPMe","DFN"):
                try:
                    x=solve_case(kind,rate,temp,pybamm)
                    cases.append(x)
                    result["runs"].append({k:v for k,v in x.items() if k!="trajectory"})
                    print("SOLVED",kind,"T",temp,"C",rate,flush=True)
                except Exception as exc:
                    result["errors"].append(dict(model=kind,rate_C=rate,
                        temp_K=temp,error=type(exc).__name__+": "+str(exc)[:330]))
            if len(cases)==2:
                try:result["comparisons"].append(pair_compare(*cases))
                except Exception as exc:
                    result["errors"].append(dict(rate_C=rate,temp_K=temp,
                        comparison_error=type(exc).__name__+": "+str(exc)[:330]))
            out.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    if len(result["runs"])==18 and len(result["comparisons"])==9 and not result["errors"]:
        result["status"]="GRID_PASS_MODEL_FORM_ONLY"
    else:result["status"]="GRID_INCOMPLETE"
    out.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k not in ("runs","comparisons")},indent=2))
    print("COMPARISONS",json.dumps(result["comparisons"],indent=2))
    if result["status"]!="GRID_PASS_MODEL_FORM_ONLY":raise SystemExit(3)
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    main(args.out)
