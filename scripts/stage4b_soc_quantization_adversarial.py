"""Post-hoc TUM SOC quantization sensitivity using existing small JSON artifact."""
from __future__ import annotations
import argparse,hashlib,json,math,statistics
from pathlib import Path
DOC="docs/decisions/STAGE4B_TUM_SOC_QUANTIZATION_RETROSPECTIVE_2026-10-24.md"
def _hash(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def assess(src,dst):
 raw=json.loads(Path(src).read_text())
 if raw.get("dataset_doi")!="10.14459/2025mp1774217.001":
  raise ValueError("wrong TUM data version")
 sessions=raw["report"]
 if len(sessions)!=12 or any(r["status"]!="PASS" for r in sessions):
  raise ValueError("input incomplete")
 outputs=[];all_bounds=[]
 for r in sessions:
  w=[x for x in r["windows"] if x["eligible"]]
  rows=[]
  for q in w:
   d=abs(q["delta_soc_pp"])
   a=abs(q["current_ah_signed"])
   estimate=100*a/d
   lower=100*a/(d+1)
   upper=(100*a/(d-1)) if d>1 else None
   if upper is not None and not(lower<=estimate<=upper):
    raise AssertionError("quantization interval wrong")
   item=dict(window=q["index"],delta_soc_abs_pp=d,Ah_abs=a,
       capacity_naive_Ah=estimate,capacity_lower_Ah=lower,
       capacity_upper_Ah=upper,upper_unbounded=upper is None)
   rows.append(item);all_bounds.append(item)
  outputs.append(dict(source_csv=r["filename"],windows=len(w),
    naive_median_Ah=statistics.median(x["capacity_naive_Ah"] for x in rows) if rows else None,
    unbounded_upper=sum(x["upper_unbounded"] for x in rows),
    window_bounds=rows))
 n=len(all_bounds)
 result=dict(status="POST_HOC_SENSITIVITY_COMPLETED",
  source_doi=raw["dataset_doi"],input_sha256=_hash(src),
  quantization_assumption="SOC two endpoints each +/-0.5pp; their difference +/-1pp",
  this_is_a_confidence_interval=False,
  soc_resolution_verified_from_raw_data=False,
  BMS_SOC_independent_of_measured_current=False,
  original_sessions=12,eligible_windows=n,
  unbounded_upper=sum(x["upper_unbounded"] for x in all_bounds),
  finite_upper=sum(x["capacity_upper_Ah"] is not None for x in all_bounds),
  naive_between_session_median_Ah=statistics.median(
    x["naive_median_Ah"] for x in outputs if x["naive_median_Ah"] is not None),
  model_A_external_accuracy_claimed=False,
  output_by_session=outputs,limitations=[
   "Conditional worst-case range, not statistical CI",
   "BMS SOC may itself integrate the recorded current",
   "One physical RWD 93.4kWh vehicle, not 12 independent vehicles",
   "No chemistry/usable capacity calibration or pack identification"])
 Path(dst).parent.mkdir(parents=True,exist_ok=True)
 Path(dst).write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
 print(json.dumps({k:v for k,v in result.items() if k!="output_by_session"},indent=2))
if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--input",required=True,type=Path)
 p.add_argument("--out",required=True,type=Path)
 x=p.parse_args();assess(x.input,x.out)
