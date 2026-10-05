"""Week 18 D1 — NEW continuous outputs: download the NEW monitors (owner permission 2026-10-05) and compute max depth.

Source: Hugging Face dataset ioandanielc/sph_v2 at the NEW revision 2e1eec9c98fd57609d2815f174586336ab59da07 (the
Week 11 intake revision), files <sim>/monitor/position-bounds_melt.dat and <sim>/monitor/time.dat for the 136
included NEW runs (Bug-withheld runs are not downloaded).  Bytes are verified against the pinned tree metadata saved
in Week 11 (size and Git blob id).  Raw files live in data/raw/ (git-ignored).

max depth = Week 7 Phase 2 definition (src/week7_phase2_sph_v2_physical_target_extraction.py): parse with the same
`load_numeric` (supervisor-confirmed sentinel rule), valid rows = finite, |value| < 1e30, ordered bounds; depth per
row = max(0, −z_min); max over valid rows, in µm.  The definition is re-validated on OLD runs at the Week 7 revision
before it is applied to NEW.
Usage: python -m src.week18_new_depth [download|validate_old|compute|all]
"""
from __future__ import annotations

import concurrent.futures
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPO_ID = "ioandanielc/sph_v2"
NEW_REVISION = "2e1eec9c98fd57609d2815f174586336ab59da07"
W7_REVISION = "d69dac5bda8b622bc0de316b112815c6056c06ec"
RAW = ROOT / "data/raw/sph_v2"
OUT = ROOT / "outputs/week18_independent_research/phase1"
FILES = ("position-bounds_melt.dat", "time.dat")


def new_sims():
    return pd.read_csv(ROOT / "outputs/week12_startup_and_transfer_development/audit/new136.csv").sim_id.tolist()


def _blob_sha1(path):
    import hashlib
    data = Path(path).read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def download(revision, paths, meta=None, workers=6):
    from huggingface_hub import hf_hub_download
    dest = RAW / revision

    def one(p):
        local = Path(hf_hub_download(REPO_ID, filename=p, repo_type="dataset", revision=revision, local_dir=dest))
        rec = {"path": p, "local": str(local), "size": local.stat().st_size, "blob_sha1": _blob_sha1(local)}
        if meta is not None and p in meta:
            rec["expected_size"] = meta[p]["size"]; rec["expected_oid"] = meta[p]["oid"]
            rec["verified"] = bool(rec["size"] == meta[p]["size"] and rec["blob_sha1"] == meta[p]["oid"])
        return rec
    out = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for i, r in enumerate(pool.map(one, paths), 1):
            out.append(r)
            if i % 25 == 0 or i == len(paths):
                print(f"downloaded {i}/{len(paths)}", flush=True)
    return out


def _lp(p):
    """Windows long-path form (the sph_v2 folder names exceed MAX_PATH)."""
    import os
    p = str(Path(p).resolve())
    prefix = "\\\\?\\"
    return Path(prefix + p) if os.name == "nt" and not p.startswith(prefix) else Path(p)


def max_depth_um(bounds_path, time_path=None):
    from src.week7_phase2_sph_v2_physical_target_extraction import load_numeric
    from src.week6_phase1_melt_pool_data_audit import SENTINEL_THRESHOLD
    bounds_path = _lp(bounds_path); time_path = _lp(time_path) if time_path is not None else None
    b, audit = load_numeric(bounds_path, "position-bounds_melt.dat")
    finite = np.isfinite(b).all(1); non_sent = (np.abs(b) < SENTINEL_THRESHOLD).all(1)
    ordered = (b[:, 1] >= b[:, 0]) & (b[:, 3] >= b[:, 2]) & (b[:, 5] >= b[:, 4])
    valid = finite & non_sent & ordered
    malformed = int((finite & non_sent & ~ordered).sum())
    rec = {"rows": int(len(b)), "valid_rows": int(valid.sum()), "malformed_rows": malformed,
           "sentinel_rule_applied": bool(audit.get("known_malformed_no_melt_sentinel_rule_applied", False))}
    depth = np.where(valid, np.maximum(0.0, -b[:, 4]), np.nan) * 1e6
    rec["max_depth_um"] = float(np.nanmax(depth)) if valid.any() else np.nan
    rec["max_depth_row_index"] = int(np.nanargmax(depth)) if valid.any() else -1
    if time_path is not None:
        t = np.loadtxt(time_path, ndmin=1)
        rec["time_rows"] = int(len(t)); rec["time_increasing"] = bool(np.all(np.diff(t) > 0))
        rec["time_rows_match"] = bool(len(t) == len(b))
    return rec


def run_download():
    meta = {r["path"]: r for r in json.loads((ROOT / "outputs/week11_new_data_arrival_audit/new_monitor_metadata.json").read_text())}
    paths = [f"{s}/monitor/{f}" for s in new_sims() for f in FILES]
    missing = [p for p in paths if p not in meta]
    if missing:
        raise SystemExit(f"{len(missing)} files absent from the pinned Week 11 tree metadata, e.g. {missing[:2]}")
    recs = download(NEW_REVISION, paths, meta)
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(recs).drop(columns=["local"]).to_csv(OUT / "new_monitor_download_manifest.csv", index=False)
    bad = [r for r in recs if not r.get("verified")]
    print("verified", len(recs) - len(bad), "of", len(recs))
    return recs


def run_validate_old(n=12, seed=0):
    """Re-derive max depth for a random sample of OLD runs at the Week 7 revision and compare with Week 7's table."""
    pop = pd.read_csv(ROOT / "outputs/week7_06_real_data_boundary_active_level_set/primary_common_population.csv", usecols=["experiment_name", "max_depth_um"])
    pick = pop.sample(n, random_state=seed)
    paths = [f"{e}/monitor/position-bounds_melt.dat" for e in pick.experiment_name]
    recs = download(W7_REVISION, paths)
    rows = []
    for (e, ref), r in zip(pick.itertuples(index=False), recs):
        d = max_depth_um(r["local"])
        rows.append({"experiment_name": e, "week7_max_depth_um": ref, "week18_max_depth_um": d["max_depth_um"], "abs_diff": abs(d["max_depth_um"] - ref)})
    df = pd.DataFrame(rows); df.to_csv(OUT / "new_depth_definition_check_old.csv", index=False)
    print(df.round(6).to_string()); print("max abs diff", df.abs_diff.max())
    return df


def run_compute():
    new = pd.read_csv(ROOT / "outputs/week12_startup_and_transfer_development/audit/new136.csv")
    rows = []
    for s in new.sim_id:
        base = RAW / NEW_REVISION / s / "monitor"
        r = max_depth_um(base / "position-bounds_melt.dat", base / "time.dat"); r["sim_id"] = s
        rows.append(r)
    d = new[["sim_id", "has_keyhole", "P", "VX", "LS", "ST"]].merge(pd.DataFrame(rows), on="sim_id")
    d.to_csv(OUT / "new_depth.csv", index=False)
    from sklearn.metrics import roc_auc_score
    kh, nk = d[d.has_keyhole == 1].max_depth_um, d[d.has_keyhole == 0].max_depth_um
    summ = {"n": int(len(d)), "keyhole": int(d.has_keyhole.sum()), "AUC_max_depth": float(roc_auc_score(d.has_keyhole, d.max_depth_um)),
            "min_keyhole_depth_um": float(kh.min()), "max_nonkeyhole_depth_um": float(nk.max()),
            "nonkeyhole_above_111": int((nk >= 111.2).sum()), "keyhole_below_111": int((kh < 111.2).sum()),
            "malformed_rows_total": int(d.malformed_rows.sum()), "time_checks_ok": bool(d.time_increasing.all() and d.time_rows_match.all())}
    (OUT / "new_depth_summary.json").write_text(json.dumps(summ, indent=1))
    print(json.dumps(summ, indent=1))
    return d, summ


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "all"
    if step in ("download", "all"):
        run_download()
    if step in ("validate_old", "all"):
        run_validate_old()
    if step in ("compute", "all"):
        run_compute()
