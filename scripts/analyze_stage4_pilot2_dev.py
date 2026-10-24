"""Pilot 2 feature audit: all 66 pairs x 5 quotas x 3 levels x 28 features.

200 whole-session bootstrap resamples. No classifier, AUC, posterior,
held-out test evaluation or claims of identifiability. All results synthetic.
"""
from __future__ import annotations
import argparse,collections,itertools,json,math,random,statistics,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"src/simulator")]
from scripts.run_stage4_experiments import FEATURE_NAMES,HYPOTHESES
from scripts.run_stage4_pilot2_dev import LEVELS,SEVS
BOOTSTRAPS=200
def metric(a,b):
 if len(a)<8 or len(b)<8:return dict(fisher=None,jeffreys_normal=None,why="n_valid_below_8")
 ma,mb=statistics.fmean(a),statistics.fmean(b)
 va,vb=statistics.variance(a),statistics.variance(b)
 if va<=0 or vb<=0:return dict(fisher=None,jeffreys_normal=None,why="zero_variance")
 d=(ma-mb)**2
 return dict(fisher=d/(va+vb),
   jeffreys_normal=.5*(va/vb+vb/va-2+d*(1/va+1/vb)),
   mean_a=ma,mean_b=mb,why=None)
def analyze(directory:Path):
 rows=[]
 for shard in range(6):
  path=directory/f"pilot2-shard-{shard}.jsonl"
  if not path.is_file():raise FileNotFoundError(path)
  rows.extend(json.loads(s) for s in path.read_text().splitlines())
 ids=[x["id"] for x in rows]
 if len(ids)!=len(set(ids)) or len(rows)!=2916:
  raise AssertionError("missing or duplicate planned development runs")
 grouped=collections.defaultdict(list)
 status=collections.Counter((r["level"],r["kind"],r["status"]) for r in rows)
 failed=[r for r in rows if r["status"]!="PASS"]
 availability=collections.defaultdict(dict)
 for r in rows:
  if r["kind"]=="short" and r["status"]=="PASS":
   grouped[(r["h"],r["quota"],r["level"])].append(r)
 for (h,q,level),rs in grouped.items():
  availability[f"{h}|{q}|{level}"]={
    "n_attempted":16,
    "n_successful":len(rs),
    "fraction_any_feature_available":sum(x["valid"]>0 for x in rs)/16,
    "mean_available_features":sum(x["valid"] for x in rs)/16,
    "per_feature_available":{f:sum(x["f"].get("mask_"+f.split("_")[0])==0 for x in rs)/16
                             for f in FEATURE_NAMES}}
 reports=[]
 for a,b in itertools.combinations(HYPOTHESES,2):
  for severity in SEVS:
   for level in LEVELS:
    ra=grouped[(a,severity,level)]
    rb=grouped[(b,severity,level)]
    for feature in FEATURE_NAMES:
     mask="mask_"+feature.split("_")[0]
     aa=[x["f"][feature] for x in ra
         if x["f"].get(mask)==0 and x["f"].get(feature) is not None]
     bb=[x["f"][feature] for x in rb
         if x["f"].get(mask)==0 and x["f"].get(feature) is not None]
     out=metric(aa,bb)
     ci=None
     if out["fisher"] is not None:
      # Fixed digest-derived seed; bootstrap at the EPISODE level.
      import hashlib
      label=f"{a}|{b}|{severity}|{level}|{feature}"
      sr=int(hashlib.sha256(label.encode()).hexdigest()[:16],16)
      rng=random.Random(sr);boots=[]
      for _ in range(BOOTSTRAPS):
       am=[aa[rng.randrange(len(aa))] for _ in aa]
       bm=[bb[rng.randrange(len(bb))] for _ in bb]
       v=metric(am,bm)["fisher"]
       if v is not None and math.isfinite(v):boots.append(v)
      if len(boots)>=160:
       boots.sort();ci=[boots[int(.025*(len(boots)-1))],
                        boots[int(.975*(len(boots)-1))]]
     reports.append(dict(a=a,b=b,severity=severity,level=level,
         feature=feature,n_a=len(aa),n_b=len(bb),fisher=out["fisher"],
         jeffreys_normal=out["jeffreys_normal"],boot95_fisher=ci,
         reason=out["why"]))
 out=directory/"pilot2_pairwise_all.jsonl"
 with out.open("w") as handle:
  for r in reports:handle.write(json.dumps(r,allow_nan=False)+"\n")
 interest={p:[] for p in ("H00|B02","H00|B07","B02|B07","M01|I01")}
 for r in reports:
  p=r["a"]+"|"+r["b"]
  if p in interest and r["severity"]==.5 and r["fisher"] is not None:
   interest[p].append(r)
 top={p:{level:sorted(
   (r for r in interest[p] if r["level"]==level),
   key=lambda r:r["fisher"],reverse=True)[:3] for level in LEVELS}
   for p in interest}
 report=dict(classification="UNSEALED_DEVELOPMENT_ONLY_NOT_MODEL_B",
   total_runs=len(rows),short_runs=sum(r["kind"]=="short" for r in rows),
   long_runs=sum(r["kind"]=="long" for r in rows),
   passes=len(rows)-len(failed),failures=len(failed),
   error_examples=[{k:r.get(k) for k in ("id","error")} for r in failed[:12]],
   pairwise_rows=len(reports),expected_pairwise_rows=66*5*3*28,
   unestimable=sum(r["fisher"] is None for r in reports),
   missing_boot_ci=sum(r["fisher"] is not None and r["boot95_fisher"] is None
                       for r in reports),
   status_counts={"|".join(map(str,k)):v for k,v in status.items()},
   feature_availability=availability,highlights_severity_point5=top,
   detection_at_5pct_FPR_80pct_power="NOT_DEMONSTRATED",
   limitations=[
    "Tiny 16-session cells and optimizer bias; not out-of-generator validation",
    "Unavailable features not silently imputed or excluded from QC denominators",
    "Univariate Fisher and normal KL proxy do not measure joint class identifiability",
    "The I01/M01 raw-severity comparisons are not energy matched",
    "No classifier or heldout test data read",
    "No longitudinal vehicle instance, no empirical Taycan instrument validation"] )
 (directory/"pilot2_analysis_summary.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
 print(json.dumps({k:v for k,v in report.items() if k in
  ("total_runs","short_runs","long_runs","passes","failures","pairwise_rows",
   "unestimable","missing_boot_ci","highlights_severity_point5")},indent=2)[:10000],flush=True)
 return report
if __name__=="__main__":
 ap=argparse.ArgumentParser()
 ap.add_argument("--outdir",default="results/tmp/stage4_pilot2")
 a=ap.parse_args()
 analyze(ROOT/a.outdir)
