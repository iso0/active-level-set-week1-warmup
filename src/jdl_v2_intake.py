"""Verbatim intake check of Astra's V2 package (file hashes only; no model code is imported or run).

Compares the copy in outputs/astra_joint_model_v2/ with (a) the delivered DELIVERY_VALIDATION.json hashes, (b) the
original directory outside the repository and (c) the members of ASTRA_JOINT_MODEL_V2_PACKAGE.zip. Pickled checkpoints
are hashed, never unpickled.

Step: python -m src.jdl_v2_intake
"""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COPY = ROOT / "outputs" / "astra_joint_model_v2"
ORIGINAL = Path(r"C:\Users\ozgur\Documents\Codex\2026-10-10\files-pasted-by-the-user-you\outputs\astra_joint_model_v2")
OUT = ROOT / "outputs" / "joint_depth_label_development" / "v2_model_comparison" / "intake"


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in COPY.rglob("*") if p.is_file())
    copy_hash = {p.relative_to(COPY).as_posix(): sha(p.read_bytes()) for p in files}
    delivered = json.loads((COPY / "DELIVERY_VALIDATION.json").read_text(encoding="utf-8"))["files_sha256"]
    delivered_ok = {k: copy_hash.get(k) == v for k, v in delivered.items()}
    original_ok = {}
    if ORIGINAL.exists():
        for rel, h in copy_hash.items():
            o = ORIGINAL / rel
            original_ok[rel] = o.is_file() and sha(o.read_bytes()) == h
    zip_rows, zip_ok = {}, {}
    with zipfile.ZipFile(COPY / "ASTRA_JOINT_MODEL_V2_PACKAGE.zip") as zf:
        for info in zf.infolist():
            if info.is_dir() or "__pycache__" in info.filename:
                continue
            rel = info.filename.split("/", 1)[1] if "/" in info.filename else info.filename
            zip_rows[rel] = sha(zf.read(info))
    for rel, h in zip_rows.items():
        zip_ok[rel] = copy_hash.get(rel) == h
    design = (COPY / "ASTRA_JOINT_MODEL_V2_DESIGN.md").read_text(encoding="utf-8")
    erratum = [l for l in design.splitlines() if "erratum" in l.lower()]
    rec = {"design_document": {"delivered_and_zipped_sha256": delivered.get("ASTRA_JOINT_MODEL_V2_DESIGN.md"),
                               "live_copy_sha256": copy_hash.get("ASTRA_JOINT_MODEL_V2_DESIGN.md"), "erratum_lines_in_live_copy": erratum,
                               "note": "The live directory carries a later documentation erratum (BA formula plus sign); the zip preserves the delivered pre-erratum text. Both are kept."},
           "copy_files": len(copy_hash), "delivered_hashes_checked": len(delivered_ok), "delivered_hashes_match": all(delivered_ok.values()),
           "delivered_mismatches": [k for k, v in delivered_ok.items() if not v],
           "original_files_compared": len(original_ok), "original_identical": all(original_ok.values()) if original_ok else None,
           "zip_members": len(zip_rows), "zip_members_identical_to_copy": all(zip_ok.values()),
           "zip_members_not_in_copy_or_different": [k for k, v in zip_ok.items() if not v],
           "copy_files_not_in_zip": sorted(set(copy_hash) - set(zip_rows) - {"ASTRA_JOINT_MODEL_V2_PACKAGE.zip"}),
           "zip_sha256": copy_hash["ASTRA_JOINT_MODEL_V2_PACKAGE.zip"],
           "not_copied": ["__pycache__/ (compiled bytecode)", "ASTRA_JOINT_MODEL_V2_PACKAGE/ (unzipped duplicate of the zip)"],
           "pickles": "checkpoints/*.pkl are hashed only and never unpickled in this repository",
           "files_sha256": copy_hash}
    (OUT / "PACKAGE_INTAKE.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in rec.items() if k != "files_sha256"}, indent=1))


if __name__ == "__main__":
    main()
