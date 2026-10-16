"""Additional pinned monitor data (owner approval of 2026-10-17: "hepsine onay veriyorum"): NEW total-energy and
particle-number of the melt (136 runs), and the six physical melt channels for the 405 OLD runs (velocity, KE, laser power,
max temperature, total energy, particle number), from Hugging Face ioandanielc/sph_v2 at the pinned revisions (NEW 2e1eec9c;
OLD b6dc254a with verified reuse of the d69dac5b audit-pin cache), into the git-ignored cache data/raw/sph_v2/<revision>/.
Reuses src.week19_sources unchanged (paths-info, verified cache, pinned download, git-blob SHA-1 / LFS SHA-256 identity).
src/jdl_physical_data.py (frozen with PHYSICAL_PILOT) is not modified.
    python -m src.jdl_physical_data2 download --threads 1
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

import src.jdl_physical_data as PD
import src.jdl_stage_m as SMM
import src.week19_sources as W19

W19.RAW = PD.MAIN_RAW
NEW_EXTRA = ("total-energy_melt.dat", "particle-number_melt.dat")
OLD_CHANNELS = ("maximum-velocity_melt.dat", "kinetic-energy_melt.dat", "transferred-laser-power_melt.dat", "maximum-temperature_melt.dat",
                "total-energy_melt.dat", "particle-number_melt.dat")
OLD_LOCAL = ("time.dat", "iter.dat", "position-bounds_melt.dat")
PROV = SMM.OUT / "physical" / "provenance"
MAN = PROV / "download_manifest_physical2.csv"


def old_ids():
    return [str(s) for s in W19.eligible_old().sim_id]


def download(workers=4):
    PROV.mkdir(parents=True, exist_ok=True)
    rows = [(W19.NEW_REV, f"{s}/monitor/{c}") for s in PD.new_ids() for c in NEW_EXTRA]
    rows += [(W19.OLD_REV, f"{s}/monitor/{c}") for s in old_ids() for c in OLD_CHANNELS + OLD_LOCAL]
    metas = []
    for rev in (W19.NEW_REV, W19.OLD_REV):
        metas.append(W19.remote_meta(rev, [p for r, p in rows if r == rev]))
    meta = pd.concat(metas, ignore_index=True)
    meta.to_csv(PROV / "remote_metadata_physical2.csv.gz", index=False)
    missing = meta[~meta.remote_exists]
    print(json.dumps({"paths": len(meta), "missing_remote": len(missing), "bytes": int(meta["size"].fillna(0).sum())}), flush=True)
    todo = meta[meta.remote_exists].to_dict("records"); out = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(W19.resolve, r["revision"], r["path"], r) for r in todo]
        for i, f in enumerate(concurrent.futures.as_completed(futs), 1):
            out.append(f.result())
            if i % 250 == 0 or i == len(futs):
                print(json.dumps({"resolved": i, "of": len(futs), "utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}), flush=True)
    man = pd.DataFrame(out).sort_values(["revision", "path"])
    man.drop(columns=["local"]).to_csv(MAN, index=False)
    summary = {"files": len(man), "verified": int(man.verified.sum()), "by_source": man.groupby("source").size().to_dict(),
               "missing_remote": missing.path.tolist()[:20], "n_missing_remote": len(missing), "bytes_remote": int(meta["size"].fillna(0).sum()),
               "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    (PROV / "DOWNLOAD_SUMMARY_physical2.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    if summary["verified"] != summary["files"]:
        raise SystemExit("unverified files present")


def local(sim_id: str, channel: str, population: str) -> Path:
    """Verified local path for NEW (both manifests) or OLD (this manifest; final pin or verified audit-pin cache)."""
    if population == "NEW":
        try:
            return PD.local(sim_id, channel)
        except FileNotFoundError:
            pass
    m = pd.read_csv(MAN); path = f"{sim_id}/monitor/{channel}"
    hit = m[(m.path == path) & m.verified]
    if not len(hit):
        raise FileNotFoundError(path)
    src = str(hit.source.iloc[0]); rev = hit.revision.iloc[0]
    base = W19.OLD_AUDIT_REV if src.endswith(W19.OLD_AUDIT_REV[:8]) else rev
    return W19.lp(PD.MAIN_RAW / base / path)


if __name__ == "__main__":
    {"download": download}[sys.argv[1] if len(sys.argv) > 1 else "download"]()
