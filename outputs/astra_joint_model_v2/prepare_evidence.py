"""Copy small pinned evidence files only; never import or alter the repository."""
from pathlib import Path
import subprocess,json,hashlib,csv,io

HERE=Path(__file__).resolve().parent
REPO=Path(r"C:\Users\ozgur\Documents\thesis")
PIN="e2bcf97a55736cdd2933b6761678d8b695358205"
BASE="outputs/week20_active_temporal_development/"
FILES=["DEVELOPMENT_REPORT.md","c3/FREEZE_C3.md","c3/freeze_c3.json",
       "c3/decision_c3.json","c3/contrasts.csv",
       "track1_ext/decision.json","track1_ext/contrasts_r1_8.csv",
       "track1_ext/contrasts_r5_8.csv","track1_ext/manifest_track1_ext.json"]
evidence=HERE/"evidence";evidence.mkdir(exist_ok=True)
manifest={"commit":PIN,"files":{}}
for relative in FILES:
    path=BASE+relative
    data=subprocess.run(["git","show",PIN+":"+path],cwd=REPO,check=True,capture_output=True).stdout
    target=evidence/relative
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    manifest["files"][path]=hashlib.sha256(data).hexdigest()
old=HERE.parent/"week20_method_development"
manifest["immutable_V1_sha256"]={str(p.relative_to(old)):hashlib.sha256(p.read_bytes()).hexdigest()
    for p in old.rglob("*") if p.is_file() and "__pycache__" not in str(p)}
manifest["V1_reference_copy_identical"]=(HERE/"v1_reference.py").read_bytes()==(old/"joint_depth_label_gp.py").read_bytes()
assert manifest["V1_reference_copy_identical"]
(evidence/"PROVENANCE.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
rows=list(csv.DictReader((evidence/"c3/contrasts.csv").read_text().splitlines()))
print("Pinned evidence files:",len(FILES))
print("CSV columns:",list(rows[0]))
for r in rows:
    values=list(r.values())
    if "R3_NEW" in values and "ACTIVE_E1_STRADDLE" in values and "G3_MARGIN" in values:
        print(r)
    if "R3_OLD" in values and "ACTIVE_E1_STRADDLE" in values and any("q20" in v for v in values):
        print(r)
