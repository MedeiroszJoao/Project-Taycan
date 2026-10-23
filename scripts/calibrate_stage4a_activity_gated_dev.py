"""Stage 4A: non-scoring prospective charge search and activity-gated I01 matching.

Uses NEW deterministic development seeds and no held-out observations.
The brackets are explicitly informed by earlier exploratory outcomes:
this is a NEW development protocol, not the historical [0,120] kW freeze.
"""
from __future__ import annotations
import argparse,hashlib,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"src"),str(ROOT/"src/simulator")]
from candidate_sim import model_4a_activity_gated as phys
from scripts.duty_cycle_candidate import build_duty_inputs
from scripts.run_stage4_dev_separability import frozen_seed_set,dev_seeds
from scripts.run_stage4_pilot2_dev import jobs as pilot_jobs,seeds as pilot_seeds
from scripts.run_stage4a_candidate_smoke import plan as smoke_plan,seeds as smoke_seeds
PROFILES={"NOMINAL_6H":(40.,55.),"SHIFT_REGEN_COLD_6H":(24.,40.)}
SEVERITIES=(.25,.5,1.)
DIFF=("uninformative","winding_proxy")
NS="STAGE4A-FOLLOWUP-CALIBRATION-DEVONLY-20261023-v1"
OUT=ROOT/"results/tmp/stage4a_prospective_calibration"
def seed_for(profile,kind):
 return int(hashlib.sha256((NS+"|"+profile+"|"+kind).encode()).hexdigest()[:8],16)
def check_seeds():
 protected=frozen_seed_set()
 for h in ("H00","B01","B02","B03","B04","B05","B06","B07","B08","B09","M01","I01"):
  for i in range(16):protected.update(dev_seeds(h,i).values())
 for j in pilot_jobs():protected.update(pilot_seeds(j).values())
 for h,p in smoke_plan():protected.update(smoke_seeds(h+"|"+p).values())
 used=set()
 for profile in PROFILES:
  for kind in ("physics","aux"):
   v=seed_for(profile,kind)
   if v in protected or v in used:raise AssertionError("seed collision")
   used.add(v)
 return sorted(used)
def run_phys(profile,power_kw,fault=None):
 dt=5.;steps=4320
 duty=build_duty_inputs(dt_s=dt,charge_power_kw=power_kw,profile_id=profile)
 kw=dict(seed=seed_for(profile,"physics"),steps=steps,dt_s=dt,initial_soc=.6,
         sensor_noise=False,auxiliary_amplitude_W=0,auxiliary_mean_W=700.)
 if profile=="SHIFT_REGEN_COLD_6H":kw.update(coolant_C=10.,init_module_C=16.)
 # No auxiliary RNG observed; reproducible deterministic time-series common across faults.
 aux=[700.+200.*math.sin(i*dt/190.) for i in range(steps)]
 sim=phys.simulate(fault or phys.Fault("H00",severity=0.),
        phys.ModelConfig(**kw),torque_trace_nm=duty.torque_nm,
        rpm_trace_rpm=duty.rpm,external_charge_trace_W=duty.charge_W,
        auxiliary_trace_W=aux)
 vmin=100*min(x["min_hidden_branch_soc"] for x in sim.truth)
 vmax=100*max(x["max_hidden_branch_soc"] for x in sim.truth)
 end=100*sim.truth[-1]["mean_hidden_soc"]
 return sim,duty,dict(power_kw=power_kw,final_mean_soc_percent=end,
    residual_soc_pp=end-60.,min_branch_soc_percent=vmin,max_branch_soc_percent=vmax,
    window_pass=vmin>=30 and vmax<=80)
def calibrate(profile):
 low,high=PROFILES[profile]
 init_low=run_phys(profile,low)[2]
 init_high=run_phys(profile,high)[2]
 if init_low["residual_soc_pp"]*init_high["residual_soc_pp"]>=0:
  raise RuntimeError("No bisection bracket; do not move endpoints post hoc")
 if not init_low["window_pass"] or not init_high["window_pass"]:
  raise RuntimeError("Unacceptable endpoint: preregistered bracket blocked")
 trace=[{"trial":"LOW",**init_low},{"trial":"HIGH",**init_high}]
 selected=None
 for iteration in range(1,13):
  mid=(low+high)/2
  _,_,v=run_phys(profile,mid)
  trace.append(dict(iteration=iteration,**v))
  if not v["window_pass"]:
   raise RuntimeError("SOC excursion during calibration; fail closed")
  if abs(v["residual_soc_pp"])<=.5 and iteration>=8:
   selected=mid
   break
  if v["residual_soc_pp"]>0:high=mid
  else:low=mid
 if selected is None:raise RuntimeError("No acceptable SOC convergence within 12 iterations")
 return selected,trace
def match(profile,power):
 baseline,duty,_=run_phys(profile,power)
 p=phys.ModelConfig()
 active_sec=5*sum(abs(t)>1e-9 and abs(r)>1e-9 for t,r in zip(duty.torque_nm,duty.rpm))
 if active_sec!=12960.:raise AssertionError("Operation-state duration drift")
 torque_energy=sum(t*t*5 for t in duty.torque_nm)
 maps=[]
 for dmode in DIFF:
  for msev in SEVERITIES:
   em=p.motor_copper_coeff_w_per_nm2*(p.motor_loss_fault_multiplier-1)*msev*torque_energy
   isev=em/(p.inverter_fault_extra_W*active_sec)
   if not 0<=isev<=1:raise RuntimeError("matching physically infeasible")
   ei=isev*p.inverter_fault_extra_W*active_sec
   maps.append(dict(profile=profile,diff_motor_t_mapping=dmode,
        M01_severity=msev,I01_matched_severity=isev,delta_M01_J=em,
        delta_I01_J=ei,delta_relative_pct=100*abs(em-ei)/em,
        status="ALGEBRAIC_MATCH_BY_ASSUMPTION_NOT_EXTERNAL_VALIDATION"))
 # Verify two actual 6h runs under equal driver/auxiliary input.
 m,_d,_=run_phys(profile,power,phys.Fault("M01",severity=1.))
 i,_d,_=run_phys(profile,power,phys.Fault("I01",severity=maps[2]["I01_matched_severity"]))
 em_actual=sum((x["power_motor_loss_W"]-b["power_motor_loss_W"])*5
               for x,b in zip(m.truth,baseline.truth))
 ei_actual=sum((x["power_inverter_loss_W"]-b["power_inverter_loss_W"])*5
               for x,b in zip(i.truth,baseline.truth))
 err=100*abs(em_actual-ei_actual)/max(1.,em_actual)
 if err>1.e-5:raise AssertionError("six-hour loss injection check mismatch")
 return maps,dict(profile=profile,active_seconds=active_sec,
       delta_M01_actual_J=em_actual,delta_I01_actual_J=ei_actual,
       relative_difference_percent=err)
def main(profile):
 check_seeds()
 power,trace=calibrate(profile)
 mappings,validation=match(profile,power)
 OUT.mkdir(parents=True,exist_ok=True)
 record=dict(classification="RESEARCH_ONLY_PROSPECTIVE_DEVELOPMENT_NOT_HISTORICAL",
   profile=profile,selected_charge_power_kw=power,charge_bisection=trace,
   exact_activity_gated_M01_I01_matches=mappings,
   six_hour_matched_injections=validation,
   source="candidate_sim.model_4a_activity_gated",seed_namespace=NS,
   original_stage4_data_used=False,owner_approval=False)
 (OUT/(profile+".json")).write_text(json.dumps(record,indent=2,allow_nan=False)+"\n")
 print(json.dumps(dict(profile=profile,charge_kw=power,
   iterations=len(trace)-2,last_residual_pp=trace[-1]["residual_soc_pp"],
   matched_mappings=len(mappings),verification=validation),indent=2))
if __name__=="__main__":
 ap=argparse.ArgumentParser()
 ap.add_argument("--profile",choices=list(PROFILES),required=True)
 a=ap.parse_args();main(a.profile)
