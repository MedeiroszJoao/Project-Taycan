"""Pilot 2: unsealed exploratory generation. Python stdlib; no official scoring."""
from __future__ import annotations
import argparse,csv,hashlib,json,math,random,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"src"),str(ROOT/"src/simulator")]
from candidate_sim import model_energy_consistent as phys
from observation.observation_layer_candidate import transform_observed_rows,auxiliary_trace_candidate,APPROVED_OBD_IDS,MODULE_T_CHANNELS
from scripts.duty_cycle_candidate import build_duty_inputs
from scripts.run_stage4_dev_separability import frozen_seed_set,dev_seeds,make_dev_row
from scripts.run_stage4_experiments import FEATURE_NAMES,MASK_NAMES,HYPOTHESES,make_observation_config,feature_matrix,OBSERVED_CHANNEL_WHITELIST
NAMESPACE="TAYCAN-PILOT2-DEVONLY-2026-10-23-C"
LEVELS=("nominal","realistic_assumed","severe_assumed")
SEVS=(.1,.25,.5,.75,1.)
LONG=("H00","B02","B04","B07","M01","I01")
PROFILES=("NOMINAL_6H","SHIFT_REGEN_COLD_6H")
Q={
 "nominal":(0,0,0,0,0,0,0,0,0,0,0,0,0),
 "realistic_assumed":(.1,.005,.2,.5,2,.1,.01,.001,2,3,1,2,2),
 "severe_assumed":(.5,.02,1,2,10,.5,.1,.01,20,15,4,12,6)}
def jobs():
 for h in HYPOTHESES:
  for sev in SEVS:
   for level in LEVELS:
    for rep in range(16):yield(h,0 if h=="H00" else sev,sev,level,rep,"short","NOMINAL_6H")
 for h in LONG:
  for level in LEVELS:
   for profile in PROFILES:
    severity=0 if h=="H00" else (.5*(.059297892 if profile=="NOMINAL_6H" else .063862109) if h=="I01" else .5)
    yield(h,severity,.5,level,0,"long",profile)
def key(j):return "|".join(map(str,j))
def seeds(j):
 return {s:int(hashlib.sha256((NAMESPACE+"|"+key(j)+"|"+s).encode()).hexdigest()[:8],16) for s in ("physics","observer","aux","nuisance","degrade")}
def seed_audit():
 old=frozen_seed_set()
 prior={s for h in HYPOTHESES for i in range(16) for s in dev_seeds(h,i).values()}
 new=set();n=0
 for j in jobs():
  n+=1
  for v in seeds(j).values():
   if v in old or v in prior or v in new:raise AssertionError("seed overlap")
   new.add(v)
 assert n==2916 and len(new)==14580 and len(old)==8928
 return len(new)
def quantization(k,q):
 if k.endswith(("_T1","_T2","_T3")) or k=="TAYCAN_DIFF_MOTOR_T":return q[0]
 if k.endswith("_SOC") or k=="TAYCAN_BMS_SOC":return q[5]
 if "RPM" in k:return q[4]
 if "TORQ" in k:return q[3]
 if k.endswith(("_AH_CHRG","_AH_DCHRG")):return q[6]
 if k.endswith(("_KWH_CHRG","_KWH_DCHRG")):return q[7]
 if k in ("TAYCAN_BMS_I","TAYCAN_HVBAT_CURRENT"):return q[2]
 if k.endswith(("_V","_VOLT")):return q[1]
 return 0
def degrade(rows,level,seed):
 q=Q[level];rng=random.Random(seed)
 inactive=set(rng.sample([k for k in MODULE_T_CHANNELS if k in rows[0]],q[8]))
 available=[k for k in OBSERVED_CHANNEL_WHITELIST if k in rows[0] and k not in inactive]
 rng.shuffle(available)
 lag=set(available[:q[9]])
 missing=available[q[9]:q[9]+q[11]]
 starts={k:rng.randrange(max(1,len(rows)-q[12]+1)) for k in missing}
 out=[];count=0
 for i,row in enumerate(rows):
  r={}
  for k,v in row.items():
   if k in ("time_s","dt_s"):r[k]=v;continue
   if k not in APPROVED_OBD_IDS:raise ValueError("unapproved channel")
   if k in inactive or (k in starts and starts[k]<=i<starts[k]+q[12]):
    count+=1;continue
   x=rows[max(0,i-q[10])][k] if k in lag else v
   width=quantization(k,q)
   r[k]=round(x/width)*width if width else x
  out.append(r)
 return out,count
def simulate(j,prereg):
 h,sev,quota,level,rep,kind,profile=j
 sd=seeds(j)
 row=make_dev_row(h,rep,prereg,sd)
 row["episode_id"]="PILOT2_"+hashlib.sha256(key(j).encode()).hexdigest()[:20]
 row["severity"]=str(sev)
 config=make_observation_config(row,prereg,verify_draws=True)
 steps=4320 if kind=="long" else 120
 if kind=="long":
  power=47.8046875 if profile=="NOMINAL_6H" else 31.5625
  d=build_duty_inputs(dt_s=5.,charge_power_kw=power,profile_id=profile)
  torque,rpm,charge=d.torque_nm,d.rpm,d.charge_W
 else:
  torque=[25+100*math.sin(i*5/40)+14*math.cos(i*5/15) for i in range(steps)]
  rpm=charge=None
 aux=auxiliary_trace_candidate(config,5.,steps)
 kw=dict(seed=sd["physics"],dt_s=5.,steps=steps,initial_soc=.6,sensor_noise=False,
         auxiliary_amplitude_W=0,acquisition_mode=row["acquisition_mode"],
         counter_source=row["counter_source"],diff_motor_t_mapping=row["diff_motor_t_mapping"])
 if kind=="long" and profile=="SHIFT_REGEN_COLD_6H":kw.update(coolant_C=10.,init_module_C=16.)
 sim=phys.simulate(phys.Fault(h,severity=sev),phys.ModelConfig(**kw),torque_trace_nm=torque,
                   rpm_trace_rpm=rpm,external_charge_trace_W=charge,auxiliary_trace_W=aux)
 measured,_=transform_observed_rows(sim.observations,config,5.)
 damaged,missing_cells=degrade(measured,level,sd["degrade"])
 features,diag=feature_matrix(row["episode_id"],damaged,5.,counter_timing_verified=True)
 if set(FEATURE_NAMES+MASK_NAMES).difference(features):raise AssertionError("wrong feature schema")
 return dict(id=row["episode_id"],h=h,s=sev,quota=quota,level=level,kind=kind,
   profile=profile,rep=rep,status="PASS",f={k:features[k] for k in FEATURE_NAMES+MASK_NAMES},
   valid=sum(features[k]==0 for k in MASK_NAMES),deleted_observations=missing_cells,
   soc_min=(min(100*r["mean_hidden_soc"] for r in sim.truth) if kind=="long" else None),
   soc_max=(max(100*r["mean_hidden_soc"] for r in sim.truth) if kind=="long" else None))
def run(shard,outdir):
 if shard not in range(6):raise ValueError("shard range [0,5]")
 count=seed_audit()
 pre=json.loads((ROOT/"experiments/stage_04_data_validation/REVISION_PREREG_ADDENDUM.json").read_text())
 selected=[j for j in jobs() if HYPOTHESES.index(j[0])//2==shard]
 outdir.mkdir(parents=True,exist_ok=True)
 path=outdir/f"pilot2-shard-{shard}.jsonl"
 done={}
 if path.exists():
  for line in path.read_text().splitlines():
   x=json.loads(line);done[x["id"]]=x
 expected={"PILOT2_"+hashlib.sha256(key(j).encode()).hexdigest()[:20] for j in selected}
 if set(done)-expected:raise AssertionError("wrong checkpoint IDs")
 with path.open("a") as f:
  for j in selected:
   eid="PILOT2_"+hashlib.sha256(key(j).encode()).hexdigest()[:20]
   if eid in done:continue
   try:x=simulate(j,pre)
   except Exception as e:
    x=dict(id=eid,h=j[0],s=j[1],quota=j[2],level=j[3],kind=j[5],
           profile=j[6],rep=j[4],status="FAIL",error=type(e).__name__+":"+str(e)[:180])
   done[eid]=x
   f.write(json.dumps(x,allow_nan=False,separators=(",",":"))+"\n");f.flush()
 summary=dict(shard=shard,planned=len(selected),attempted=len(done),
       passed=sum(x["status"]=="PASS" for x in done.values()),
       failed=sum(x["status"]!="PASS" for x in done.values()),new_seeds_global=count,
       errors=[dict(id=x["id"],error=x["error"]) for x in done.values()
               if x["status"]!="PASS"][:10],category="DEVELOPMENT_ONLY")
 (outdir/f"pilot2-shard-{shard}.summary.json").write_text(json.dumps(summary,indent=2)+"\n")
 print(json.dumps(summary,indent=2),flush=True)
if __name__=="__main__":
 a=argparse.ArgumentParser();a.add_argument("--shard",type=int,required=True)
 a.add_argument("--outdir",default="results/tmp/stage4_pilot2")
 z=a.parse_args();run(z.shard,ROOT/z.outdir)
