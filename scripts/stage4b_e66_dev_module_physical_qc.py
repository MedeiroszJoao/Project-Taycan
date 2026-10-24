"""Six precommitted real LG E66 FIT module tables only; never read blind payloads."""
from __future__ import annotations
import argparse,hashlib,json,math,statistics,tempfile,zipfile
from pathlib import Path
from scripts.audit_stage4b_real_e66_module import download,inspect
from scripts.audit_stage4b_e66_dev_only import DEV,VALIDATION,BLIND

COLUMNS={"time":("RecordingTime","RecordingTime"),
  "AVL_V":("AVL_Voltage","ACT_U"),
  "BMS_V":("BMS_Voltage","Pack_Summed_Voltage"),
  "AVL_I":("AVL_Current","ACT_I"),
  "BMS_I":("BMS_Current","Pack_Current"),
  "cell_V":("CellVoltage","CellVoltage"),
  "cell_id":("CellID","CellId"),
  "coolant_in":("CoolantIN","CoolantIN"),
  "coolant_out":("CoolantOUT","CoolantOUT")}
def get_measured_table(meas,key,col):
    import pandas as pd
    if getattr(meas,"dtype",None) is None or key not in (meas.dtype.names or ()):
        return None
    v=meas[key].flat[0]
    if not isinstance(v,pd.DataFrame) or col not in v.columns:return None
    return pd.to_numeric(v[col],errors="coerce").to_numpy(dtype=float)

def finite_report(arr):
    import numpy as np
    if arr is None:return dict(status="ABSENT")
    good=arr[np.isfinite(arr)]
    return dict(status="MEASURED",total=int(arr.size),finite=int(good.size),
      missing=int(arr.size-good.size),
      minimum=float(good.min()) if good.size else None,
      maximum=float(good.max()) if good.size else None)

def pairs(a,b):
    import numpy as np
    if a is None or b is None:return (None,None)
    n=min(len(a),len(b))
    if n==0:return (None,None)
    mask=np.isfinite(a[:n])&np.isfinite(b[:n])
    return a[:n][mask],b[:n][mask]
def analyze(meas,member,bytes):
    import numpy as np
    signals={label:get_measured_table(meas,*cols) for label,cols in COLUMNS.items()}
    v,cell=pairs(signals["AVL_V"],signals["cell_V"])
    topology=dict(status="UNESTIMABLE",samples=0)
    if v is not None and len(v)>=100:
        good=(v>0)&(cell>0)
        ratio=v[good]/cell[good]
        if len(ratio)>=100:
            topology=dict(status="ESTIMABLE",samples=int(len(ratio)),
              module_to_cell_ratio_median=float(np.median(ratio)),
              ratio_fraction_4p5_to_7p5=float(np.mean((ratio>4.5)&(ratio<7.5))))
    x,y=pairs(signals["AVL_I"],signals["BMS_I"])
    current=dict(status="UNESTIMABLE",samples=0)
    if x is not None and len(x)>=100:
        if np.std(x)>1e-9 and np.std(y)>1e-9:
            current=dict(status="ESTIMABLE",samples=int(len(x)),
              correlation=float(np.corrcoef(x,y)[0,1]),
              median_sum_A=float(np.median(x+y)),
              mean_signed_AVL_A=float(np.mean(x)),
              mean_signed_BMS_A=float(np.mean(y)))
    ids=signals["cell_id"]
    unique=[]
    if ids is not None:
        valid=ids[np.isfinite(ids)]
        if len(valid):unique=[int(z) for z in np.unique(valid)[:25]]
    return dict(filename=Path(member).name,sha256=hashlib.sha256(bytes).hexdigest(),
        schema="MATLAB MCOS table decoded by mat-io==1.0.1",
        signal_stats={name:finite_report(a) for name,a in signals.items()},
        voltage_ratio=topology,current_sensor_comparison=current,
        cell_IDs_observed=unique,
        summary_only=True,never_observed_validation_or_blind=True)
def run(out):
    import matio, scipy, numpy, pandas
    with tempfile.TemporaryDirectory() as tmp:
        zip_path=Path(tmp)/"real_e66_module.zip"
        dig=download(zip_path);receipt=inspect(zip_path,dig)
        results=[];errors=[]
        with zipfile.ZipFile(zip_path) as archive:
            mem={Path(z.filename).name:z.filename for z in archive.infolist() if not z.is_dir()}
            if set(mem)!=(DEV|VALIDATION|BLIND):
                raise ValueError("source file roles drifted")
            for name in sorted(DEV):
                try:
                    import io
                    content=archive.read(mem[name])
                    data=matio.load_from_mat(io.BytesIO(content),raw_data=False)
                    result=analyze(data["meas"],mem[name],content)
                    results.append(result)
                    print("DECODED FIT",name,"V_RATIO",result["voltage_ratio"],
                        "I_CORR",result["current_sensor_comparison"],flush=True)
                except Exception as exc:
                    errors.append(dict(file=name,error=type(exc).__name__+":"+str(exc)[:380]))
                    print("FAILED FIT",name,str(exc)[:200],flush=True)
        fitted_voltages=[r["voltage_ratio"] for r in results if r["voltage_ratio"]["status"]=="ESTIMABLE"]
        fitted_current=[r["current_sensor_comparison"] for r in results if r["current_sensor_comparison"]["status"]=="ESTIMABLE"]
        receipt_out=dict(status="FIT_DATA_QC_PASS" if len(results)==6 and not errors else "INCOMPLETE",
           dataset_doi="10.5683/SP3/7JP3NM",archive_sha256=receipt["sha256"],
           reader="mat-io==1.0.1",scipy_version=scipy.__version__,
           numpy_version=numpy.__version__,pandas_version=pandas.__version__,
           source_fit_roles=sorted(DEV),source_validation_roles=sorted(VALIDATION),
           source_blind_roles=sorted(BLIND),
           actual_fit_files_read=len(results),validation_payload_files_read=0,
           blind_payload_files_read=0,stage4_reserved_test_rows_read=0,
           model_B_parameter_fit_performed=False,results=results,errors=errors,
           topology_support=dict(n_files_with_ratio=len(fitted_voltages),
              medians=[x["module_to_cell_ratio_median"] for x in fitted_voltages]),
           instrument_polarity=dict(n_files_with_correlations=len(fitted_current),
              pearson_r=[x["correlation"] for x in fitted_current]),
           physical_scope="Taycan recovered experimental E66 MODULE, not full vehicle")
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(receipt_out,indent=2,allow_nan=False)+"\n")
        print("SUMMARY",json.dumps({k:v for k,v in receipt_out.items() if k!="results"},indent=2))
        if receipt_out["status"]!="FIT_DATA_QC_PASS":raise SystemExit(3)
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True,type=Path)
    run(p.parse_args().out)
