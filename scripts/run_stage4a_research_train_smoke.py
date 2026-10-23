"""Stage4A research-only successor smoke: first TRAIN row per hypothesis.

Never simulates reserved validation/test outcomes; never modifies historical runner,
freeze or manifest. This is a NEW model specification, not an officially scored run.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"src"),str(ROOT/"src/simulator")]
from candidate_sim import model_4a_activity_gated as phys
from observation.observation_layer_4a_candidate import transform_observed_rows,auxiliary_trace_candidate,APPROVED_OBD_IDS
from scripts.duty_cycle_candidate import build_duty_inputs
from scripts.run_stage4a_candidate_smoke import sources as candidate_sources
from scripts.run_stage4_experiments import HYPOTHESES,FEATURE_NAMES,MASK_NAMES,make_observation_config,feature_matrix,EXPECTED
OUTPUT=ROOT/"results/tmp/stage4a_successor_train_smoke"
POWER_KW={"NOMINAL_6H":47.79296875,"SHIFT_REGEN_COLD_6H":31.5625}
def sha(path):
 return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
def sources():
 d=candidate_sources()
 d["successor_train_runner"]=sha("scripts/run_stage4a_research_train_smoke.py")
 d["internal_research_approval"]=sha("docs/decisions/STAGE4A_INTERNAL_NONCOMMERCIAL_ACCEPTANCE_2026-10-23.md")
 d["successor_spec"]=sha("docs/decisions/STAGE4A_SUCCESSOR_TRAIN_SMOKE_SPEC_2026-10-23.md")
 d["historical_amendment"]=sha("experiments/stage_04_data_validation/STAGE4_APPEND_ONLY_AMENDMENT.json")
 if d["historical_amendment"]!=EXPECTED["amendment_sha256"]:
  raise AssertionError("original amendment hash drift")
 return d
def selected_train():
 path=ROOT/"experiments/stage_04_data_validation/STAGE4_EPISODE_MANIFEST.csv"
 seen=set();chosen=[]
 with path.open(newline="",encoding="utf-8") as f:
  rows=list(csv.DictReader(f))
 if len(rows)!=2232:raise AssertionError("original episode count drift")
 for row in rows:
  if row["split"]=="train" and row["hypothesis"] not in seen:
   seen.add(row["hypothesis"]);chosen.append(row)
 if [x["hypothesis"] for x in chosen]!=HYPOTHESES:raise AssertionError("train class ordering drift")
 if len({x["episode_id"] for x in chosen})!=12:raise AssertionError("train IDs not unique")
 for row in chosen:
  if (int(row["duration_s"]),int(row["dt_s"]))!=(21600,5):
   raise AssertionError("not frozen six-hour timebase")
  if row["profile"] not in POWER_KW:raise AssertionError("unrecognized profile")
  if not all(0<=int(row["seed_"+k])<2**32 for k in ("physics","observer","aux","nuisance")):
   raise AssertionError("invalid manifest seed")
 return chosen
def apply_fault_severity(row,duty):
 target=float(row["severity"])
 if row["hypothesis"]!="I01":return target
 p=phys.ModelConfig()
 active_sec=5*sum(abs(t)>1e-9 and abs(r)>1e-9 for t,r in zip(duty.torque_nm,duty.rpm))
 tau_squared_s=sum(t*t*5 for t in duty.torque_nm)
 energy=p.motor_copper_coeff_w_per_nm2*(p.motor_loss_fault_multiplier-1)*target*tau_squared_s
 applied=energy/(p.inverter_fault_extra_W*active_sec)
 if not 0<=applied<=1:raise AssertionError("I01 energy match infeasible")
 return applied
def run_one(row,prereg):
 h=row["hypothesis"];profile=row["profile"];episode=row["episode_id"]
 conf=make_observation_config(row,prereg,verify_draws=True)
 duty=build_duty_inputs(dt_s=5.,charge_power_kw=POWER_KW[profile],profile_id=profile)
 if len(duty.mode)!=4320:raise AssertionError("invalid driver length")
 severity=apply_fault_severity(row,duty)
 aux=auxiliary_trace_candidate(conf,5.,4320)
 kw=dict(seed=int(row["seed_physics"]),steps=4320,dt_s=5.,initial_soc=.6,
  sensor_noise=False,auxiliary_amplitude_W=0,acquisition_mode=row["acquisition_mode"],
  counter_source=row["counter_source"],diff_motor_t_mapping=row["diff_motor_t_mapping"])
 if profile=="SHIFT_REGEN_COLD_6H":kw.update(coolant_C=10.,init_module_C=16.)
 sim=phys.simulate(phys.Fault(h,severity=severity),phys.ModelConfig(**kw),
  torque_trace_nm=duty.torque_nm,rpm_trace_rpm=duty.rpm,
  external_charge_trace_W=duty.charge_W,auxiliary_trace_W=aux)
 if len(sim.truth)!=4320 or len(sim.observations)!=4320:raise AssertionError("incomplete simulation")
 if any(set(r)-APPROVED_OBD_IDS-{"dt_s","time_s"} for r in sim.observations):
  raise AssertionError("unapproved physics observed channels")
 observed,info=transform_observed_rows(sim.observations,conf,5.)
 if len(observed)!=4320 or any(set(r)-APPROVED_OBD_IDS-{"dt_s","time_s"} for r in observed):
  raise AssertionError("unapproved observed channels")
 features,diag=feature_matrix(episode,observed,5.,counter_timing_verified=True)
 if set(FEATURE_NAMES+MASK_NAMES)-set(features):raise AssertionError("feature schema missing")
 for name in FEATURE_NAMES:
  code=name.split("_")[0];mask=features["mask_"+code];v=features[name]
  if mask not in (0,1):raise AssertionError("nonbinary missingness")
  if v is not None and not math.isfinite(float(v)):raise AssertionError("NaN feature")
  if mask==0 and v is None:raise AssertionError("nonmasked missing feature")
  if mask==1 and v is not None:raise AssertionError("masked feature numeric leakage")
 soclo=100*min(r["min_hidden_branch_soc"] for r in sim.truth)
 sochi=100*max(r["max_hidden_branch_soc"] for r in sim.truth)
 dc=max(abs(r["power_dc_W"]-r["power_requested_dc_W"]) for r in sim.truth)
 rc=max(abs(r["rc_input_work_J_step"]-r["rc_dissipation_J_step"]
  -r["rc_capacitor_storage_delta_J_step"]) for r in sim.truth)
 if not all(map(math.isfinite,(soclo,sochi,dc,rc))):raise AssertionError("nonfinite QC")
 if soclo<30 or sochi>80:raise AssertionError("branch SOC outside prereg window")
 if dc>1e-5 or rc>1e-4:raise AssertionError("local energy tolerance")
 for r in sim.truth:
  for k in ("power_motor_loss_W","power_inverter_loss_W","power_gearbox_loss_W",
             "r0_dissipation_J_step","rc_dissipation_J_step","leakage_dissipation_J_step"):
   if r[k]<-1e-8 or not math.isfinite(r[k]):raise AssertionError("invalid dissipation")
 if h=="I01" and any(abs(x["power_inverter_loss_W"])>1e-8 for m,x in zip(duty.mode,sim.truth)
                    if m in ("charge","rest")):raise AssertionError("I01 parked loss")
 # Keep all hidden truth only in QC metadata. The 28-feature vector is separately attested.
 vals={name:features[name] for name in FEATURE_NAMES+MASK_NAMES}
 return dict(kind="TRAIN_ONLY_UNSCORED_SMOKE",episode_id=episode,hypothesis=h,
  profile=profile,manifest_target_severity=float(row["severity"]),
  injected_severity=severity,available_features=sum(features[m]==0 for m in MASK_NAMES),
  feature_sha256=hashlib.sha256(json.dumps(vals,sort_keys=True,allow_nan=False).encode()).hexdigest(),
  observed_features_only=vals,truth_soc_min_pct=soclo,truth_soc_max_pct=sochi,
  final_mean_soc_pct=100*sim.truth[-1]["mean_hidden_soc"],
  dc_residual_max_W=dc,rc_residual_max_J=rc,
  observer_soc_clip_count=info["soc_clipped_group_samples"],
  seeds_sha256=hashlib.sha256(json.dumps({k:row["seed_"+k] for k in ("physics","observer","aux","nuisance")},sort_keys=True).encode()).hexdigest(),
  acquisition_mode=row["acquisition_mode"],counter_source=row["counter_source"],
  diff_motor_t_mapping=row["diff_motor_t_mapping"])
def shard_run(shard):
 if not 0<=shard<6:raise ValueError("shard out of bounds")
 hashes=sources();chosen=selected_train()
 prereg=json.loads((ROOT/"experiments/stage_04_data_validation/REVISION_PREREG_ADDENDUM.json").read_text())
 selected=chosen[2*shard:2*shard+2]
 out=[]
 try:
  out=[run_one(row,prereg) for row in selected]
 except Exception as e:
  OUTPUT.mkdir(parents=True,exist_ok=True)
  err=dict(shard=shard,status="FAILED",error=type(e).__name__+":"+str(e),sources=hashes,
           attempted_ids=[row["episode_id"] for row in selected])
  (OUTPUT/f"train-shard-{shard}.json").write_text(json.dumps(err,indent=2)+"\n")
  raise
 OUTPUT.mkdir(parents=True,exist_ok=True)
 report=dict(shard=shard,status="PASS",sources=hashes,episodes=out)
 (OUTPUT/f"train-shard-{shard}.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
 print(json.dumps({k:v for k,v in report.items() if k!="episodes"} | {
  "summaries":[{k:v for k,v in item.items() if k!="observed_features_only"} for item in out]}))
def aggregate():
 hashes=sources();rows=[]
 for shard in range(6):
  path=OUTPUT/f"train-shard-{shard}.json"
  if not path.is_file():raise AssertionError("missing shard")
  obj=json.loads(path.read_text())
  if obj["status"]!="PASS" or obj["shard"]!=shard or obj["sources"]!=hashes:
   raise AssertionError("mismatched source, shard or failure")
  if len(obj["episodes"])!=2:raise AssertionError("incomplete shard")
  rows.extend(obj["episodes"])
 expected=[x["episode_id"] for x in selected_train()]
 if [r["episode_id"] for r in rows]!=expected:raise AssertionError("train-only selection mismatch")
 if any(x["available_features"]!=28 for x in rows):
  raise AssertionError("not all nominal features available")
 report=dict(classification="RESEARCH_ONLY_TRAIN_SMOKE_NOT_OFFICIAL_HISTORICAL",
  implementation="STAGE4A_CORRECTED_CANDIDATE_SUCCESSOR",passed=12,failed=0,
  train_only=True,validation_runs=0,reserved_test_runs=0,
  min_soc_pct=min(x["truth_soc_min_pct"] for x in rows),
  max_soc_pct=max(x["truth_soc_max_pct"] for x in rows),
  max_dc_W=max(x["dc_residual_max_W"] for x in rows),
  max_rc_J=max(x["rc_residual_max_J"] for x in rows),
  sources=hashes,results=rows)
 (OUTPUT/"research_train_smoke12_attestation.json").write_text(
  json.dumps(report,indent=2,allow_nan=False)+"\n")
 print(json.dumps({k:v for k,v in report.items() if k!="results"},indent=2))
if __name__=="__main__":
 ap=argparse.ArgumentParser()
 mode=ap.add_mutually_exclusive_group(required=True)
 mode.add_argument("--shard",type=int);mode.add_argument("--aggregate",action="store_true")
 x=ap.parse_args()
 aggregate() if x.aggregate else shard_run(x.shard)
