"""Prepare/finalize a labeled POST-HOC E66 fitting reconstruction.

Never substitutes the original missing Work freeze. The ONLY source changes
are to a throwaway CI copy of PROSPECTIVE.json's outer-container SHA.
No raw E66 cell data are published with the small summary artifact.
"""
from __future__ import annotations
import argparse,hashlib,json,os,platform,tempfile,urllib.request,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DOI="10.5683/SP3/7JP3NM"
URL="https://borealisdata.ca/api/access/datafile/837532"
EXPECTED_BYTES=152124241
EXPECTED_MD5="734d8c3c262d7dcbd4eaf1b6b366e079"
BASE=ROOT/"results/e66_calibration"
TARGET=ROOT/"results/tmp/stage4b/posthoc_reconstruction"
PROVENANCE=TARGET/"POSTHOC_PROVENANCE.json"
INNER=TARGET/"borealis_cell_original.zip"
WRAPPER=TARGET/"research_wrapper_NOT_original_Work_source.zip"

def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(4*1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def download():
    TARGET.mkdir(parents=True,exist_ok=True)
    h=hashlib.md5()
    count=0
    req=urllib.request.Request(URL,headers={
       "User-Agent":"ProjectTaycan-scientific-posthoc/1.0"})
    with urllib.request.urlopen(req,timeout=120) as response,INNER.open("wb") as dst:
        while True:
            chunk=response.read(4*1024*1024)
            if not chunk:break
            count+=len(chunk)
            if count>EXPECTED_BYTES:
                raise RuntimeError("PUBLISHER_BYTES_OVERFLOW")
            dst.write(chunk);h.update(chunk)
    if count!=EXPECTED_BYTES or h.hexdigest()!=EXPECTED_MD5:
        raise RuntimeError("SOURCE_MD5_OR_SIZE_MISMATCH")
    with zipfile.ZipFile(INNER) as src:
        files=set(src.namelist())
        spec=json.loads((BASE/"PROSPECTIVE.json").read_text())
        needed=spec["fit"]+spec["evaluation"]
        if len(needed)!=4 or not all(x in files for x in needed):
            raise RuntimeError("ORIGINAL_4_E66_CELL_FILES_NOT_FOUND")
        member_meta=[dict(name=x,compressed_bytes=src.getinfo(x).compress_size,
             size_bytes=src.getinfo(x).file_size,
             crc32=f"{src.getinfo(x).CRC:08x}") for x in needed]
        # Integrity of each of the four exposed physical measurements only.
        for x in needed:
            with src.open(x) as f:
                while f.read(2*1024*1024):pass
    original_spec_hash=sha(BASE/"PROSPECTIVE.json")
    original_outer_hash=spec["source_archive_SHA256"]
    # Construct a reproducible NEW outer container, never claim equivalence
    # to the original uploaded outer container.
    with zipfile.ZipFile(WRAPPER,"w") as out:
        info=zipfile.ZipInfo("1-Cell Data.zip",date_time=(2026,1,1,0,0,0))
        info.compress_type=zipfile.ZIP_STORED
        with out.open(info,"w") as f,INNER.open("rb") as source:
            for block in iter(lambda:source.read(4*1024*1024),b""):
                f.write(block)
    new_wrapper_hash=sha(WRAPPER)
    spec["source_archive_SHA256"]=new_wrapper_hash
    (BASE/"PROSPECTIVE.json").write_text(
       json.dumps(spec,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    receipt=dict(
       classification="POSTHOC_RECONSTRUCTED_AFTER_1C_OUTCOMES_KNOWN",
       source_doi=DOI,source_url=URL,inner_byte_count=count,
       official_inner_md5=h.hexdigest(),official_inner_sha256=sha(INNER),
       original_uploaded_outer_zip_sha256=original_outer_hash,
       original_uploaded_outer_zip_recovered=False,
       new_wrapper_sha256=new_wrapper_hash,
       old_repository_prereg_sha256=original_spec_hash,
       rewritten_ephemeral_prereg_sha256=sha(BASE/"PROSPECTIVE.json"),
       identical_original_source_python_sha256=sha(ROOT/"scripts/fit_e66_generator_b.py"),
       externally_prior_1c_failure_reported=True,
       chronological_original_pre_result_freeze_verified=False,
       retrofit_is_new_exploratory_reconstruction=True,
       only_four_prior_fit_eval_cell_mat_files_crc_tested=member_meta,
       other_dataset_files_numerically_read=False,
       target_stage4_sealed_test_rows_read=0,
       raw_files_never_archived=True,
       environment_python=platform.python_version(),
       state="SOURCE_VERIFIED_FIT_NOT_YET_RUN")
    PROVENANCE.write_text(json.dumps(receipt,indent=2)+"\n")
    print("OFFICIAL_INNER_MD5_PASS",h.hexdigest(),count,flush=True)
    print("PUBLISHER_INNER_SHA256",receipt["official_inner_sha256"],flush=True)
    print("NEW_WRAPPER_SHA256",new_wrapper_hash,flush=True)

def final():
    rec=json.loads(PROVENANCE.read_text())
    wanted=("FIT_RESULT.json","GENERATOR_B_FREEZE.json","EVALUATION.json")
    present={}
    for name in wanted:
        source=BASE/name
        if not source.is_file():
            rec["state"]="PARTIAL_WORK_RECONSTRUCTION_FAILED"
            rec["absent"]=name
            PROVENANCE.write_text(json.dumps(rec,indent=2)+"\n")
            raise RuntimeError("POSTHOC_NEW_RECEIPT_NOT_GENERATED:"+name)
        present[name]=sha(source)
    rec["reconstruction_receipt_sha256"]=present
    fit=json.loads((BASE/"FIT_RESULT.json").read_text())
    freeze=json.loads((BASE/"GENERATOR_B_FREEZE.json").read_text())
    eval_=json.loads((BASE/"EVALUATION.json").read_text())
    if freeze["fit_result_sha256"]!=present["FIT_RESULT.json"] or (
       eval_["freeze_sha256"]!=present["GENERATOR_B_FREEZE.json"]):
        raise RuntimeError("POSTHOC_FIT_FREEZE_EVAL_CHAIN_BROKEN")
    if freeze["source_sha256"]!=rec["identical_original_source_python_sha256"]:
        raise RuntimeError("POSTHOC_ORIGINAL_SOURCE_PYTHON_DRIFT")
    rec["fit_parameter_vector"]=fit["parameters"]
    rec["fit_RMSE_V"]=fit["fit_RMSE_V"]
    rec["optimization_success"]=fit["least_squares_success"]
    rec["evaluation_summary"]=[{k:v for k,v in row.items() if k not in
       ("trajectory",)} for row in eval_["results"]]
    rec["posthoc_generated_freeze_before_its_own_evaluation"]=bool(freeze.get("before_evaluation"))
    rec["original_Work_freeze_recovered"]=False
    rec["state"]="POSTHOC_RECONSTRUCTION_COMPLETED_NOT_ORIGINAL_FREEZE"
    PROVENANCE.write_text(json.dumps(rec,indent=2,allow_nan=False)+"\n")
    print("POSTHOC_RESULTS",json.dumps({k:v for k,v in rec.items() if k not in
       ("only_four_prior_fit_eval_cell_mat_files_crc_tested",)}),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("mode",choices=("prepare","final"))
    a=p.parse_args()
    download() if a.mode=="prepare" else final()
