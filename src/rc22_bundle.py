"""RC22 portable local review bundle (no upload): report, protocols, freezes, validation, decisions, every part's tables, exports
(per-budget probabilities, paid IDs), figures and the source of every module the stages ran, with a SHA-256 manifest.
Astra's files are NOT included (her package stays in her own directory).
    python -m src.rc22_bundle      -> opus_rc22/review_bundle/RC22_REVIEW_BUNDLE.zip (+ BUNDLE_MANIFEST.json)
"""
from __future__ import annotations

import hashlib
import json
import zipfile

import src.rc18_common as RC
import src.rc22_freeze as FR

OUT = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc22"
EXTRA_SRC = ["src/rc22_report.py", "src/rc22_figures.py", "src/rc22_validate.py", "src/rc22_freeze.py", "src/rc22_decisions.py", "src/rc22_bundle.py", "src/rc19_validate.py",
             "src/rc22_runner.ps1", "src/rc22_supervisor.ps1", "src/rc22_start_runner.ps1"]
DOCS = ["outputs/research_campaign_20261020/opus_rc21/MODEL_DEFINITIONS_RC21.md", "outputs/research_campaign_20261020/opus_rc21/ERRATUM_RC21_20261021.md",
        "outputs/research_campaign_20261020/opus_rc21/FINAL_REPORT_RC21.md", "outputs/research_campaign_20261020/opus_rc21/PROTOCOL_RC21B.md"]


def main():
    files = set(FR.FILES["F2"]) | set(EXTRA_SRC) | set(DOCS)
    for p in OUT.rglob("*"):
        rel = p.relative_to(RC.ROOT).as_posix()
        if p.is_file() and not any(s in rel for s in ("/units/", "/locks/", "/review_bundle/", "/runner/workers/", "runner.lock", "HEARTBEAT", "STATE.json", ".tmp")):
            files.add(rel)
    files = sorted(f for f in files if (RC.ROOT / f).exists()); d = OUT / "review_bundle"; d.mkdir(parents=True, exist_ok=True)
    man = {"utc": RC.utc(), "note": "RC22 local review bundle (DEV evidence; no physical validation). Paths are relative to the repository root.",
           "files": {f: hashlib.sha256((RC.ROOT / f).read_bytes()).hexdigest() for f in files}}
    (d / "BUNDLE_MANIFEST.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    with zipfile.ZipFile(d / "RC22_REVIEW_BUNDLE.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(RC.ROOT / f, f)
        z.write(d / "BUNDLE_MANIFEST.json", "BUNDLE_MANIFEST.json")
    print(len(files), "files ->", d / "RC22_REVIEW_BUNDLE.zip", round((d / "RC22_REVIEW_BUNDLE.zip").stat().st_size / 1e6, 1), "MB")


if __name__ == "__main__":
    main()
