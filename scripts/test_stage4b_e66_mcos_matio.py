"""Open-source MATLAB MCOS table decoder capability test. ONLY predeclared 1C FIT."""
from __future__ import annotations
import argparse,hashlib,json,tempfile,zipfile
from pathlib import Path
from scripts.audit_stage4b_real_e66_module import download,inspect
TEST_NAME="20240314_1C_Test (MCCC).mat"
FIELDS=("RecordingTime","AVL_Current","AVL_Voltage","BMS_Current",
        "BMS_Voltage","CellVoltage","CellID","CoolantIN","CoolantOUT")
def child(obj,key):
    if isinstance(obj,dict):return obj.get(key)
    if hasattr(obj,"_fieldnames"):return getattr(obj,key,None)
    if getattr(obj,"dtype",None) is not None:
        if obj.dtype.names and key in obj.dtype.names:
            v=obj[key]
            if getattr(v,"size",0)==1:return v.flat[0]
            return v
    return getattr(obj,key,None)
def schema(obj):
    import numpy as np
    import pandas as pd
    if obj is None:return {"kind":"MISSING"}
    desc={"type":type(obj).__name__}
    if isinstance(obj,pd.DataFrame):
        desc.update(rows=len(obj),columns=[str(x) for x in obj.columns],
            numeric={})
        for col in obj.select_dtypes(include="number").columns:
            v=pd.to_numeric(obj[col],errors="coerce").dropna()
            desc["numeric"][str(col)]=dict(n=int(v.size),
                min=float(v.min()) if v.size else None,
                max=float(v.max()) if v.size else None)
    elif isinstance(obj,np.ndarray):
        desc.update(shape=list(obj.shape),dtype=str(obj.dtype),
            fieldnames=list(obj.dtype.names or []))
        if np.issubdtype(obj.dtype,np.number):
            data=obj.astype(float).ravel()
            vals=data[np.isfinite(data)]
            desc["numeric"]=dict(n=int(vals.size),minimum=float(vals.min()) if vals.size else None,
                maximum=float(vals.max()) if vals.size else None)
    elif isinstance(obj,dict):
        desc["keys"]=list(obj)[:50]
    else:
        desc["attributes"]=[k for k in ("columns","index","properties","classname","_fieldnames")
                            if hasattr(obj,k)]
    return desc
def run(out):
    import scipy,matio,pandas,numpy
    with tempfile.TemporaryDirectory() as temp:
        path=Path(temp)/"module.zip"
        hashes=download(path)
        verify=inspect(path,hashes)
        with zipfile.ZipFile(path) as z:
            names={Path(x.filename).name:x.filename for x in z.infolist() if not x.is_dir()}
            # Do not ever read validation or blind members.
            data=z.read(names[TEST_NAME])
        local=Path(temp)/"fit_only.mat";local.write_bytes(data)
        del data
        try:
            loaded=matio.load_from_mat(str(local),raw_data=False)
            meas=loaded.get("meas")
            result=dict(status="MCOS_READ_ATTEMPTED",source_archive_sha256=verify["sha256"],
              tested_file=TEST_NAME,file_role="FIT_DEVELOPMENT_ONLY",
              dependent_versions=dict(mat_io="0.4.0",scipy=scipy.__version__,
                 pandas=pandas.__version__,numpy=numpy.__version__),
              loaded_root=schema(loaded),meas=schema(meas),
              measurements={k:schema(child(meas,k)) for k in FIELDS},
              validation_file_contents_read=0,blind_file_contents_read=0,
              stage4_reserved_test_rows_read=0)
            numeric_keys=[k for k,x in result["measurements"].items()
                          if x.get("numeric")]
            result["decode_success_at_least_one_numeric_field"]=bool(numeric_keys)
            result["status"]="MCOS_NUMERIC_SUPPORTED" if numeric_keys else "MCOS_NUMERIC_UNSUPPORTED"
        except Exception as err:
            result=dict(status="MCOS_DECODER_ERROR",
                source_archive_sha256=verify["sha256"],
                tested_file=TEST_NAME,decoder="mat-io==0.4.0",
                error=type(err).__name__+": "+str(err)[:500],
                validation_file_contents_read=0,blind_file_contents_read=0,
                stage4_reserved_test_rows_read=0)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+"\n")
    print(json.dumps(result,ensure_ascii=False,allow_nan=False)[:14000])
    if result["status"]!="MCOS_NUMERIC_SUPPORTED":raise SystemExit(3)
if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",required=True,type=Path)
    run(ap.parse_args().out)
