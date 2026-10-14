"""Read-only scientific checks plus a delivery manifest; no model fitting."""
import os
for name in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS"):
    os.environ[name]="1"
from pathlib import Path
import hashlib,json,pickle,re,subprocess
import numpy as np

root=Path(__file__).resolve().parent
result=json.loads((root/"CONTROLLED_RESULTS.json").read_text())
selection=json.loads((root/"SELECTION_RECORD_V2.json").read_text())
refs=json.loads((root/"NUMERICAL_REFERENCES.json").read_text())
supp=result["supplemental_diagnostics"]
assert result["status"]=="COMPLETE_WITH_REPORTED_LIMITATIONS"
assert result["total_accounting"]["controlled_model_requests"]==307
assert result["total_accounting"]["component_solves_including_correctness_and_induced_fallback"]==580
assert len(refs["checks"])==17 and all(x["passed"] for x in refs["checks"].values())
assert supp["status"]=="PASS"
fits=[r for r in result["records"] if "arm" in r]
queries=[r for r in result["records"] if "arm" not in r]
assert len(fits)==290 and len(queries)==72
assert all(r["status"]=="ok" for r in fits+queries)
assert len(result["worlds"])==29
for name,digest in result["run_state"]["source_sha256"].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
for name,digest in refs["source_sha256"].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
for name,digest in supp["source_sha256"].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
provenance=json.loads((root/"evidence/PROVENANCE.json").read_text())
for name,digest in provenance["immutable_V1_sha256"].items():
    assert hashlib.sha256((root.parent/"week20_method_development"/name).read_bytes()).hexdigest()==digest
for record in fits:
    assert (root/"checkpoints"/(record["key"]+".pkl")).is_file()
    assert len(record["paid_ids"])==record["budget"]
    assert len(set(record["paid_ids"]))==record["budget"]
    assert len(record["predictions"])==96
    assert record["metrics"]["TP"]+record["metrics"]["FN"]+record["metrics"]["TN"]+record["metrics"]["FP"]==96
# Existing fitted object only: prove batching does not recenter discrepancy.
model=pickle.loads((root/"checkpoints/static_informative_depth_1301_B16_V2_EP_mixture.pkl").read_bytes())
world=result["worlds"]["informative_depth_1301_40"]
X=np.array(world["X"])
whole=model.predict_proba(X)
pieces=np.concatenate([model.predict_proba(X[:17]),model.predict_proba(X[17:53]),model.predict_proba(X[53:])])
batch_error=float(np.max(abs(whole-pieces)))
assert batch_error<1e-12
local=set();pinned=set()
for p in root.glob("*.md"):
    text=p.read_text(encoding="utf-8")
    for target in re.findall(r"<(C:/[^>]+)>",text):
        assert Path(target).is_file(),target
        local.add(target)
    for target in re.findall(r"https://github.com/iso0/active-level-set-week1-warmup/blob/([a-f0-9]{40})/([^\s)#]+)",text):
        pinned.add(target)
    assert text.count("$$")%2==0,p.name
for pin,path in pinned:
    subprocess.run(["git","cat-file","-e",pin+":"+path],cwd=r"C:\Users\ozgur\Documents\thesis",
                   check=True,capture_output=True)
manifest={"status":"PASS","no_model_fits_in_delivery_validation":True,
          "static_fit_records":200,"sequential_fit_records":90,"query_records":72,
          "controlled_requests":307,"component_solves":580,"ceiling":600,
          "core_correctness_checks":17,"supplemental_checks":"leakage and induced whole-mixture fallback",
          "maximum_prediction_batch_difference":batch_error,
          "all_V1_artifacts_unchanged":True,"local_references_verified":len(local),
          "pinned_repository_paths_verified":len(pinned),
          "files_sha256":{p.name:hashlib.sha256(p.read_bytes()).hexdigest()
           for p in sorted(root.iterdir()) if p.is_file() and p.name not in ("DELIVERY_VALIDATION.json","ASTRA_JOINT_MODEL_V2_PACKAGE.zip")}}
(root/"DELIVERY_VALIDATION.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
print(json.dumps({k:v for k,v in manifest.items() if k!="files_sha256"},indent=2))
