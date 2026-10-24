"""Non-scoring Stage 4 DEVELOPMENT-only pairwise feature separability.

Generates 16 unique independently seeded 10-minute candidate simulations for
each of 12 hypotheses using seeds derived from a *new* namespace. Refuses
collisions with ALL frozen manifest seeds. Uses no heldout episodes, and never
fits a classifier, a posterior or calibration parameters. The resulting
univariate Fisher ratios and symmetric Gaussian KL divergences are descriptive
under an unapproved candidate simulator, not predictive validation.
"""
from __future__ import annotations
import csv
import hashlib
import itertools
import json
import math
import statistics
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'src/simulator')]
from candidate_sim import model as phys
from observation.observation_layer_candidate import transform_observed_rows, auxiliary_trace_candidate
from scripts.run_stage4_experiments import (
    DRAW_SPEC, FEATURE_NAMES, HYPOTHESES, MASK_NAMES, XorShift32,
    make_observation_config, feature_matrix
)

N_PER_HYPOTHESIS=16
DT_S=5.0
STEPS=120
SEVERITY=0.5
NAMESPACE="TAYCAN-STAGE4-UNSEALED-DEVONLY-20261023-PAIRWISE-v1"

def dev_seeds(hypothesis:str,rep:int)->dict[str,int]:
    return {kind:int(hashlib.sha256(
        f"{NAMESPACE}|{hypothesis}|{rep}|{kind}".encode("utf-8")
    ).hexdigest()[:8],16) for kind in ("physics","observer","aux","nuisance")}

def frozen_seed_set()->set[int]:
    path=ROOT/'experiments/stage_04_data_validation/STAGE4_EPISODE_MANIFEST.csv'
    with path.open(newline="",encoding="utf-8") as h:
        return {int(r[f"seed_{stream}"]) for r in csv.DictReader(h)
                for stream in ("physics","observer","aux","nuisance")}

def make_dev_row(hypothesis:str,rep:int,prereg:dict,seeds:dict)->dict[str,str]:
    ranges=prereg["split_policy"]["parameters_assumed"]
    ng=XorShift32(seeds["nuisance"])
    row={"episode_id":f"DEV_ONLY_{hypothesis}_{rep:02}",
         "hypothesis":hypothesis, "split":"UNSEALED_DEVELOPMENT_ONLY",
         "severity":str(0.0 if hypothesis=="H00" else SEVERITY),
         "soc_phi_per_s":str((0.9,0.97,0.99,0.995)[rep%4])}
    combos=list(itertools.product(("independent","shared"),
                                  ("BMS_I","HVBAT_CURRENT"),
                                  ("uninformative","winding_proxy")))
    row["acquisition_mode"],row["counter_source"],row["diff_motor_t_mapping"]=combos[rep%8]
    for col,range_key in DRAW_SPEC:
        lo,hi=ranges[range_key]
        row[col]=repr(lo+(hi-lo)*ng.uniform())
    for kind,value in seeds.items():
        row[f"seed_{kind}"]=str(value)
    return row

def metric(xs:list[float],ys:list[float])->dict:
    """Descriptive 1-dimensional, not fitted Bayesian likelihood."""
    n1,n2=len(xs),len(ys)
    if n1<8 or n2<8:
        return {"n1":n1,"n2":n2,"Fisher_ratio":None,
                "symmetric_gaussian_KL":None,"reason":"small_sample"}
    m1,m2=statistics.fmean(xs),statistics.fmean(ys)
    v1,v2=statistics.variance(xs),statistics.variance(ys)
    if v1<=0 or v2<=0:
        return {"n1":n1,"n2":n2,"mean_difference":m1-m2,
                "Fisher_ratio":None,"symmetric_gaussian_KL":None,
                "reason":"zero_empirical_variance"}
    delta=(m1-m2)**2
    # Mean-difference effect scaled by within-class variances.
    fisher=delta/(v1+v2)
    # Jeffreys / symmetric KL for *separate marginal Gaussian proxies*.
    # KL(N1||N2)+KL(N2||N1) = 0.5*(v1/v2+v2/v1-2
    #                                     + delta*(1/v1+1/v2)).
    symmetric_kl=0.5*(v1/v2+v2/v1-2+delta*(1/v1+1/v2))
    return {"n1":n1,"n2":n2,"mean_difference":m1-m2,
            "Fisher_ratio":fisher,"symmetric_gaussian_KL":symmetric_kl,
            "reason":None}

def summarize(samples:list[dict])->dict:
    grouped={h:[] for h in HYPOTHESES}
    for s in samples:
        if s["hypothesis"] not in grouped or s["split"]!="UNSEALED_DEVELOPMENT_ONLY":
            raise ValueError("nondevelopment / unknown hypothesis rejected")
        grouped[s["hypothesis"]].append(s)
    reports=[]
    for a,b in itertools.combinations(HYPOTHESES,2):
        scores={}
        for f in FEATURE_NAMES:
            code=f.split("_")[0]
            mask="mask_"+code
            aa=[r["features"][f] for r in grouped[a]
                if r["features"].get(mask)==0 and r["features"].get(f) is not None]
            bb=[r["features"][f] for r in grouped[b]
                if r["features"].get(mask)==0 and r["features"].get(f) is not None]
            scores[f]=metric(aa,bb)
        ordered=sorted(
            [(n,m["Fisher_ratio"]) for n,m in scores.items()
             if m["Fisher_ratio"] is not None],
            key=lambda x:x[1],reverse=True
        )
        reports.append({"a":a,"b":b,"top_univariate_Fisher":ordered[:5],
                        "feature_metrics":scores,"n_a":len(grouped[a]),"n_b":len(grouped[b])})
    return {"classification":"DEVELOPMENT_ONLY_DESCRIPTIVE_NOT_OFFICIAL_DIAGNOSTIC_ACCURACY",
            "source_model":"UNAPPROVED candidate_sim.model (not approved frozen Stage 3)",
            "namespace":NAMESPACE, "severity":SEVERITY,"steps":STEPS,"dt_s":DT_S,
            "hypotheses":len(HYPOTHESES),"replicates_per_hypothesis":N_PER_HYPOTHESIS,
            "pairs":reports,"limitations":[
            "No classifier or posterior trained; no heldout data or split used.",
            "16 ten-minute sessions per class are not 6-hour registered episodes.",
            "Only severity 0.5 is investigated; H00 has severity zero.",
            "Marginal Gaussian KL is a distributional approximation; no joint KL.",
            "Shared generator biases and noise may make all estimates optimistic.",
            "Large Fisher in a frozen or uninformative channel may be leakage; audit each.",
            "Correlated feature multiplicity and small n prohibit significance claims.",
            "No vehicle-level repeated-measure baseline, unknown classes or compound faults."
            ]}

def run()->dict:
    seen=frozen_seed_set()
    generated=set()
    prereg=json.loads((ROOT/'experiments/stage_04_data_validation/REVISION_PREREG_ADDENDUM.json').read_text())
    samples=[]
    torque=[25+100*math.sin(i*DT_S/40)+14*math.cos(i*DT_S/15) for i in range(STEPS)]
    for hypothesis in HYPOTHESES:
        for rep in range(N_PER_HYPOTHESIS):
            seeds=dev_seeds(hypothesis,rep)
            for s in seeds.values():
                if s in seen or s in generated:
                    raise ValueError("DEV/FROZEN/OTHER DEV RNG SEED COLLISION; ABORT")
                generated.add(s)
            row=make_dev_row(hypothesis,rep,prereg,seeds)
            config=make_observation_config(row,prereg,verify_draws=True)
            aux=auxiliary_trace_candidate(config,DT_S,STEPS)
            pcfg=phys.ModelConfig(seed=seeds["physics"],dt_s=DT_S,steps=STEPS,
                initial_soc=.60,sensor_noise=False,
                acquisition_mode=row["acquisition_mode"],
                counter_source=row["counter_source"],
                diff_motor_t_mapping=row["diff_motor_t_mapping"],
                auxiliary_amplitude_W=0)
            sim=phys.simulate(phys.Fault(hypothesis,
                severity=0.0 if hypothesis=="H00" else SEVERITY),
                pcfg,torque_trace_nm=torque,auxiliary_trace_W=aux)
            observed,metadata=transform_observed_rows(sim.observations,config,DT_S)
            features,_=feature_matrix(row["episode_id"],observed,DT_S,
                                      counter_timing_verified=True)
            if not all(k in features for k in FEATURE_NAMES+MASK_NAMES):
                raise AssertionError("feature schema not available")
            samples.append({"hypothesis":hypothesis,"split":"UNSEALED_DEVELOPMENT_ONLY",
                            "replicate":rep,"features":features})
    report=summarize(samples)
    report["unique_unsealed_seeds"]=len(generated)
    report["frozen_seed_overlap"]=len(generated & seen)
    report["frozen_manifest_episodes_touched"]=0
    report["development_episodes_generated"]=len(samples)
    report["physical_candidate_SHA256"]=hashlib.sha256(
        (ROOT/'src/simulator/candidate_sim/model.py').read_bytes()).hexdigest()
    out=ROOT/'results/tmp/stage4_devonly/pairwise_feature_separability.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps({"classification":report["classification"],
         "development_episodes":len(samples),"unique_dev_seeds":len(generated),
         "frozen_collision":len(generated & seen),"pair_count":len(report["pairs"]),
         "top_pairs_Fisher":[{"pair":f"{v['a']}/{v['b']}",
              "top":v["top_univariate_Fisher"][:2]} for v in report["pairs"]
              if (v["a"],v["b"]) in
              [("H00","B02"),("H00","B07"),("B02","B07"),("M01","I01")]],
         "path":str(out)},indent=2))
    return report

if __name__=="__main__":
    run()
