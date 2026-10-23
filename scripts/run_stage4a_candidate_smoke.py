"""Research-only Stage 4A: independent, UNSEALED 12x6h candidate smoke.

Never uses the 2232 official episode IDs, their measured traces or held-out data.
Each six-hour run has new independent four-stream seeds. No official approval.
"""
from __future__ import annotations
import argparse,hashlib,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"src"),str(ROOT/"src/simulator")]
from candidate_sim import model_4a_activity_gated as phys
from observation.observation_layer_candidate import transform_observed_rows,auxiliary_trace_candidate,APPROVED_OBD_IDS
from scripts.duty_cycle_candidate import build_duty_inputs
from scripts.run_stage4_dev_separability import frozen_seed_set,dev_seeds,make_dev_row
from scripts.run_stage4_pilot2_dev import jobs as pilot_jobs,seeds as pilot_seeds
from scripts.run_stage4_experiments import HYPOTHESES,FEATURE_NAMES,MASK_NAMES,make_observation_config,feature_matrix,EXPECTED

NAMESPACE="STAGE4A-CANDIDATE-ONLY-20261023-v1"
PROFILES=("NOMINAL_6H","SHIFT_REGEN_COLD_6H")
OUT=ROOT/"results/tmp/stage4a_candidate_shards"
STREAMS=("physics","observer","aux","nuisance")
def file_hash(p):
 return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def seeds(label):
 return {k:int(hashlib.sha256((NAMESPACE+"|"+label+"|"+k).encode()).hexdigest()[:8],16) for k in STREAMS}
def plan():
 return [(h,PROFILES[i%2]) for i,h in enumerate(HYPOTHESES)]
def sources():
 paths={
  "stage3_model":"src/simulator/taycan_sim/model.py",
  "historical_freeze":"experiments/stage_04_data_validation/freeze.json",
  "historical_manifest":"experiments/stage_04_data_validation/STAGE4_EPISODE_MANIFEST.csv",
  "historical_prereg":"experiments/stage_04_data_validation/REVISION_PREREG_ADDENDUM.json",
  "candidate_physics":"src/simulator/candidate_sim/model_4a_activity_gated.py",
  "candidate_observer":"src/observation/observation_layer_candidate.py",
  "candidate_duty":"scripts/duty_cycle_candidate.py",
  "feature_contract":"scripts/run_stage4_experiments.py",
  "smoke_script":"scripts/run_stage4a_candidate_smoke.py"}
 d={k:file_hash(v) for k,v in paths.items()}
 for key,expected_key in (("stage3_model","model_py_sha256"),
                         ("historical_freeze","freeze_sha256"),
                         ("historical_manifest","manifest_sha256"),
                         ("historical_prereg","prereg_sha256")):
  if d[key]!=EXPECTED[expected_key]:raise AssertionError("HISTORICAL HASH DRIFT "+key)
 if len(FEATURE_NAMES)!=28 or len(MASK_NAMES)!=28:raise AssertionError("feature schema drift")
 return d
def seed_audit():
 used=frozen_seed_set()
 for h in HYPOTHESES:
  for i in range(16):used.update(dev_seeds(h,i).values())
 for j in pilot_jobs():used.update(pilot_seeds(j).values())
 fresh=set()
 for h,p in plan():
  for v in seeds(h+"|"+p).values():
   if v in used or v in fresh:raise AssertionError("SEED COLLISION")
   fresh.add(v)
 if len(fresh)!=48:raise AssertionError("four-stream plan mismatch")
 return len(fresh)
def run_one(h,profile,prereg):
 sd=seeds(h+"|"+profile)
 row=make_dev_row(h,0,prereg,sd)
 row["episode_id"]="STAGE4A_DEVONLY_"+h+"_"+profile
 row["severity"]=str(0 if h=="H00" else .25)
 config=make_observation_config(row,prereg,verify_draws=True)
 power=47.8046875 if profile=="NOMINAL_6H" else 31.5625
 duty=build_duty_inputs(dt_s=5.,charge_power_kw=power,profile_id=profile)
 steps=len(duty.mode)
 if steps!=4320:raise AssertionError("6h timebase")
 aux=auxiliary_trace_candidate(config,5.,steps)
 kw=dict(seed=sd["physics"],dt_s=5.,steps=steps,initial_soc=.6,
         sensor_noise=False,auxiliary_amplitude_W=0,
         acquisition_mode=row["acquisition_mode"],
         counter_source=row["counter_source"],
         diff_motor_t_mapping=row["diff_motor_t_mapping"])
 if profile=="SHIFT_REGEN_COLD_6H":kw.update(coolant_C=10.,init_module_C=16.)
 sim=phys.simulate(phys.Fault(h,severity=0 if h=="H00" else .25),
     phys.ModelConfig(**kw),torque_trace_nm=duty.torque_nm,
     rpm_trace_rpm=duty.rpm,external_charge_trace_W=duty.charge_W,
     auxiliary_trace_W=aux)
 if len(sim.truth)!=steps or len(sim.observations)!=steps:raise AssertionError("timebase mismatch")
 if any(set(x)-APPROVED_OBD_IDS-{"time_s","dt_s"} for x in sim.observations):
  raise AssertionError("latent or unapproved observed channel")
 observed,obs_meta=transform_observed_rows(sim.observations,config,5.)
 if any(set(x)-APPROVED_OBD_IDS-{"time_s","dt_s"} for x in observed):
  raise AssertionError("observer channel leakage")
 f,diag=feature_matrix(row["episode_id"],observed,5.,counter_timing_verified=True)
 if set(FEATURE_NAMES+MASK_NAMES)-set(f):raise AssertionError("feature schema missing")
 for name in FEATURE_NAMES:
  mask=f["mask_"+name.split("_")[0]]
  value=f[name]
  if mask not in (0,1):raise AssertionError("invalid feature mask")
  if mask==0 and (value is None or not math.isfinite(float(value))):
   raise AssertionError("invalid unmasked feature")
  if value is not None and not math.isfinite(float(value)):
   raise AssertionError("nonfinite feature")
 soc_min=min(100*x["min_hidden_branch_soc"] for x in sim.truth)
 soc_max=max(100*x["max_hidden_branch_soc"] for x in sim.truth)
 if soc_min<30 or soc_max>80:raise AssertionError("SOC window violation")
 dc_error=max(abs(x["power_requested_dc_W"]-x["power_dc_W"]) for x in sim.truth)
 rc_error=max(abs(x["rc_input_work_J_step"]-x["rc_dissipation_J_step"]
                 -x["rc_capacitor_storage_delta_J_step"]) for x in sim.truth)
 if dc_error>1e-5:raise AssertionError("local DC balance failure")
 if rc_error>1e-4:raise AssertionError("fixed-step RC identity failure")
 for x in sim.truth:
  for k in ("power_motor_loss_W","power_inverter_loss_W",
            "power_gearbox_loss_W","power_auxiliary_W",
            "rc_dissipation_J_step","r0_dissipation_J_step",
            "leakage_dissipation_J_step"):
   if not math.isfinite(x[k]) or x[k]<-1e-8:raise AssertionError("negative/nonfinite loss "+k)
 if h=="I01":
  for mode,x in zip(duty.mode,sim.truth):
   if mode in ("rest","charge") and abs(x["power_inverter_loss_W"])>1e-8:
    raise AssertionError("I01 extra inverter loss while parked")
 data={k:f[k] for k in FEATURE_NAMES+MASK_NAMES}
 fingerprint=hashlib.sha256(json.dumps(data,sort_keys=True,allow_nan=False).encode()).hexdigest()
 return dict(hypothesis=h,profile=profile,status="PASS",severity=0 if h=="H00" else .25,
   steps=steps,dt_s=5.,valid_features=sum(f[k]==0 for k in MASK_NAMES),
   min_branch_SOC_pct=soc_min,max_branch_SOC_pct=soc_max,
   final_mean_SOC_pct=100*sim.truth[-1]["mean_hidden_soc"],
   dc_algebra_max_error_W=dc_error,rc_fixed_step_max_error_J=rc_error,
   charge_energy_kWh=sum(x["power_charge_to_dc_bus_W"]*5/3600000 for x in sim.truth),
   feature_sha256=fingerprint,features=data,
   observer_clipping=obs_meta.get("clipping",None))
def run_shard(shard):
 if shard not in range(6):raise ValueError("shard outside 0..5")
 hashes=sources();seed_audit()
 prereg=json.loads((ROOT/"experiments/stage_04_data_validation/REVISION_PREREG_ADDENDUM.json").read_text())
 rows=[run_one(*pair,prereg) for i,pair in enumerate(plan()) if i//2==shard]
 if len(rows)!=2:raise AssertionError("expected two six-hour runs per shard")
 OUT.mkdir(parents=True,exist_ok=True)
 out=dict(classification="STAGE4A_UNSEALED_CANDIDATE_ONLY",
   note="local DC and fixed-coefficient 1RC identities are NOT whole-cell first-law closure",
   seed_namespace=NAMESPACE,source_sha256=hashes,shard=shard,results=rows)
 (OUT/f"shard-{shard}.json").write_text(json.dumps(out,indent=2,allow_nan=False)+"\n")
 print(json.dumps(dict(shard=shard,status="PASS",summaries=[
  {k:v for k,v in x.items() if k!="features"} for x in rows]),allow_nan=False))
def aggregate():
 hashes=sources();seed_audit()
 files=sorted(OUT.glob("shard-*.json"))
 if len(files)!=6:raise AssertionError("expected exactly six shard artifacts")
 rows=[]
 for i,p in enumerate(files):
  obj=json.loads(p.read_text())
  if obj["shard"]!=i or obj["source_sha256"]!=hashes:
   raise AssertionError("mismatched source or shard")
  rows.extend(obj["results"])
 if len(rows)!=12 or len({x["hypothesis"] for x in rows})!=12:
  raise AssertionError("incomplete class coverage")
 if sorted((x["hypothesis"],x["profile"]) for x in rows)!=sorted(plan()):
  raise AssertionError("profile mismatch")
 if any(x["status"]!="PASS" or x["steps"]!=4320 for x in rows):
  raise AssertionError("incomplete six-hour run")
 summary=dict(classification="STAGE4A_CANDIDATE_ONLY_NOT_APPROVED",
  total=12,passed=12,source_sha256=hashes,seed_namespace=NAMESPACE,
  local_dc_error_max_W=max(x["dc_algebra_max_error_W"] for x in rows),
  local_rc_error_max_J=max(x["rc_fixed_step_max_error_J"] for x in rows),
  physical_energy_closure="UNRESOLVED",historical_manifest_untouched=True,
  official_test_episodes_run=0,results=rows)
 (OUT/"stage4a_candidate_smoke12.json").write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n")
 print(json.dumps({k:v for k,v in summary.items() if k!="results"},indent=2))
if __name__=="__main__":
 parser=argparse.ArgumentParser()
 g=parser.add_mutually_exclusive_group(required=True)
 g.add_argument("--shard",type=int);g.add_argument("--aggregate",action="store_true")
 args=parser.parse_args()
 aggregate() if args.aggregate else run_shard(args.shard)
