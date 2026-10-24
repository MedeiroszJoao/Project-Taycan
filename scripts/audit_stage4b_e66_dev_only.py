"""Stage4B real E66 module: examine only prospectively assigned development data.

Four BLIND and two VALIDATION files never extracted, decompressed or read.
"""
from __future__ import annotations
import argparse,io,json,tempfile,zipfile
from pathlib import Path
from scripts.audit_stage4b_real_e66_module import download,inspect
DEV={
"20240209_0.7C_CP_Loss.mat","20240209_1C_CP_Loss.mat",
"20240323_1.2C_CP_Loss.mat","20240314_1C_Test (MCCC).mat",
"20240315_0.5C_Test (MCCC) Part1.mat",
"20240315_0.5C_Test (MCCC) Part2.mat"}
VALIDATION={
"20240207_1.5C_CP_Loss.mat","20240313_1.5C_Test (MCCC).mat"}
BLIND={
"20240318_2C_Test (MCCC) Part 1.mat",
"20240318_2C_Test (MCCC) Part 2.mat",
"20240322_TopUp&DC_for_FC.mat","20240323_Fast_Charge.mat"}
METRICS=("RecordingTime","AVL_Current","AVL_Voltage",
         "BMS_Current","BMS_Voltage","CellVoltage","CellID",
         "Battery_Temp_DegC","CoolantIN","CoolantOUT")
def _simple(obj):
    import numpy as np
    if obj is None:return None
    try:
        data=np.asarray(obj).astype(float).ravel()
        if data.size==0:return dict(n=0)
        good=data[np.isfinite(data)]
        return dict(total=int(data.size),finite=int(good.size),
           missing=int(data.size-good.size),
           minimum=float(good.min()) if good.size else None,
           maximum=float(good.max()) if good.size else None,
           mean=float(good.mean()) if good.size else None)
    except (TypeError,ValueError):return dict(non_numeric=True)

def dev_summary(z,member):
    import scipy.io as sio
    raw=z.read(member)
    vals=sio.loadmat(io.BytesIO(raw),variable_names=["meas"],
        squeeze_me=True,struct_as_record=False)
    meas=vals.get("meas")
    if meas is None:raise ValueError("no meas structure")
    fields=getattr(meas,"_fieldnames",None)
    if fields is None:raise ValueError("unexpected MATLAB meas layout")
    qc={k:_simple(getattr(meas,k,None)) for k in METRICS}
    v=qc.get("AVL_Voltage")
    guess="INCONCLUSIVE"
    if isinstance(v,dict) and v.get("finite",0)>100:
        lo=v["minimum"];hi=v["maximum"]
        if lo is not None and hi is not None:
            if lo>14 and hi<30:guess="VOLTAGE_SUGGESTS_SIX_SERIES_GROUPS"
            elif lo>5 and hi<10:guess="VOLTAGE_SUGGESTS_TWO_SERIES_GROUPS"
    return dict(file=Path(member).name,role="FIT_DEVELOPMENT",
        matlab_meas_fields=list(fields),observables=qc,
        architecture_voltage_heuristic=guess,
        actual_measurement_source="Original E66 module lab data; not model A")

def run(out):
    import scipy
    with tempfile.TemporaryDirectory() as directory:
        src=Path(directory)/"module.zip"
        digests=download(src)
        directory_info=inspect(src,digests)
        results=[];errors=[]
        with zipfile.ZipFile(src) as z:
            members={Path(m.filename).name:m.filename for m in z.infolist() if not m.is_dir()}
            if set(members)!=(DEV|VALIDATION|BLIND):
                raise AssertionError("prospective file split names disagree with archive")
            for n in sorted(DEV):
                try:results.append(dev_summary(z,members[n]))
                except Exception as e:
                    errors.append(dict(file=n,error=type(e).__name__+": "+str(e)[:280]))
            # VALIDATION and BLIND numeric file contents not accessed.
        response=dict(status="DEVELOPMENT_DATA_INSPECTED" if not errors else "PARTIAL",
            source="doi:10.5683/SP3/7JP3NM",archive_sha256=directory_info["sha256"],
            scipy_version=scipy.__version__,
            roles=dict(fit=sorted(DEV),validation=sorted(VALIDATION),blind=sorted(BLIND)),
            dev_measured_results=results,errors=errors,
            validation_numeric_files_read=0,blind_numeric_files_read=0,
            fitted_parameters_count=0,model_B_frozen=False,
            stage4_sealed_examples_read=0,all_real_lg_e66_module=True,
            important="Do not convert 6p2s label into pack physics without wiring verification")
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(response,indent=2,allow_nan=False)+"\n")
        print(json.dumps({k:v for k,v in response.items() if k not in
          ("dev_measured_results",)},indent=2))
        for r in results:
            print(json.dumps({k:v for k,v in r.items() if k in
                ("file","architecture_voltage_heuristic","observables")},allow_nan=False))
        if errors or len(results)!=len(DEV):raise SystemExit(2)
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args();run(args.out)
