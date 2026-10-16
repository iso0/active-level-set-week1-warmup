"""Pinned physical monitor data for the NEW runs (owner approval of 2026-10-16: velocity + KE + laser power + temperature,
136 NEW runs, ~797 MB, Hugging Face ioandanielc/sph_v2 @ 2e1eec9c, into the git-ignored cache data/raw/sph_v2/<revision>/).

Reuses src.week19_sources unchanged (paths-info metadata, verified-cache reuse, pinned download, git-blob-SHA-1 / LFS
SHA-256 identity check).  The cache lives in the main checkout (where Weeks 7/18/19 stored it).  Never downloads another
revision, never trusts an unverified copy.  Manifest: outputs/joint_depth_label_development/physical/provenance/.
    python -m src.jdl_physical_data download --threads 1
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

import concurrent.futures
import datetime as dt
import json
import sys
from pathlib import Path

import pandas as pd

import src.jdl_stage_m as SMM
import src.week19_sources as W19

MAIN_RAW = Path(r"C:\Users\ozgur\Documents\thesis\data\raw\sph_v2")
W19.RAW = MAIN_RAW                                         # the established cache (main checkout), not the worktree
CHANNELS = ("maximum-velocity_melt.dat", "kinetic-energy_melt.dat", "transferred-laser-power_melt.dat", "maximum-temperature_melt.dat")
LOCAL_CHANNELS = ("time.dat", "iter.dat", "position-bounds_melt.dat")
PROV = SMM.OUT / "physical" / "provenance"


def new_ids():
    import src.jdl_trained_al_eval as TE
    _, F = TE.frame()
    return [str(s) for s in F["ids"]]


def download(workers=4):
    PROV.mkdir(parents=True, exist_ok=True)
    ids = new_ids()
    paths = [f"{s}/monitor/{c}" for s in ids for c in CHANNELS + LOCAL_CHANNELS]
    meta = W19.remote_meta(W19.NEW_REV, paths)
    meta.to_csv(PROV / "remote_metadata_physical.csv.gz", index=False)
    if not meta.remote_exists.all():
        raise SystemExit(f"{int((~meta.remote_exists).sum())} pinned paths do not exist")
    rows, out = meta.to_dict("records"), []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(W19.resolve, r["revision"], r["path"], r) for r in rows]
        for i, f in enumerate(concurrent.futures.as_completed(futs), 1):
            out.append(f.result())
            if i % 100 == 0 or i == len(futs):
                print(json.dumps({"resolved": i, "of": len(futs), "utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}), flush=True)
    man = pd.DataFrame(out).sort_values("path")
    man.drop(columns=["local"]).to_csv(PROV / "download_manifest_physical.csv", index=False)
    summary = {"files": len(man), "verified": int(man.verified.sum()), "by_source": man.groupby("source").size().to_dict(),
               "bytes": int(meta["size"].sum()), "revision": W19.NEW_REV, "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    (PROV / "DOWNLOAD_SUMMARY.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    if summary["verified"] != summary["files"]:
        raise SystemExit("unverified files present")


def local(sim_id: str, channel: str) -> Path:
    """Verified local path (reads the physical download manifest)."""
    m = pd.read_csv(PROV / "download_manifest_physical.csv")
    path = f"{sim_id}/monitor/{channel}"
    hit = m[(m.path == path) & m.verified]
    if not len(hit):
        raise FileNotFoundError(path)
    return W19.lp(MAIN_RAW / W19.NEW_REV / path)


if __name__ == "__main__":
    {"download": download}[sys.argv[1] if len(sys.argv) > 1 else "download"]()
