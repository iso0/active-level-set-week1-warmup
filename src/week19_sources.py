"""Week 19 temporal regime audit: sources, provenance and pinned downloads.

Read-only with respect to every earlier output.  Raw simulator files live under the git-ignored cache
``data/raw/sph_v2/<revision>/<path in repo>`` (established in Weeks 7 and 18).  Cached bytes are reused only after
their content is verified against the pinned Hugging Face tree (size plus Git blob SHA-1, or the LFS SHA-256 when
the file is LFS-stored).  Missing files are downloaded at the pinned revision only.

Pins (verified, see outputs/week19_temporal_regime_audit/provenance/):
  OLD  ioandanielc/sph_v2 @ b6dc254a2b607a31cb9f97b40990339c3d5ca1e8  (final pin of data/population.csv)
  OLD  audit pin d69dac5bda8b622bc0de316b112815c6056c06ec            (Week 7; final pin = audit pin + 110 added files)
  NEW  ioandanielc/sph_v2 @ 2e1eec9c98fd57609d2815f174586336ab59da07  (October NEW, Week 11 intake revision)

Usage: python -m src.week19_sources [meta|download|all]
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPO_ID = "ioandanielc/sph_v2"
OLD_REV = "b6dc254a2b607a31cb9f97b40990339c3d5ca1e8"
OLD_AUDIT_REV = "d69dac5bda8b622bc0de316b112815c6056c06ec"
NEW_REV = "2e1eec9c98fd57609d2815f174586336ab59da07"
RAW = ROOT / "data" / "raw" / "sph_v2"
OUT = ROOT / "outputs" / "week19_temporal_regime_audit"
PROV = OUT / "provenance"
POPULATION = ROOT / "outputs/week7_06_real_data_boundary_active_level_set/primary_common_population.csv"
POPULATION_SHA256 = "c15658cac87a8616a1984185ec1afc8126a1db811f0d5819e62cfb621a7486c7"

NEW_LABEL_FILE = "labels_new_data_4_prep.csv"
NEW_LABEL_SIZE = 12_397_054
NEW_LABEL_SHA256 = "b45518a51ea59d97d1e28e3f2ce5ef563af1c049bce83d0d88b3d510b1adf16d"
OLD_LEDGERS = {"new-data": "labels_partition_1_new-data.csv",
               "old-data-local": "labels_partition_2_old-data-local.csv",
               "old-data-remote-clean": "labels_partition_3_old-data-remote-clean.csv"}
# Per-simulation files needed for the frame -> iteration -> time mapping and the depth series.
SIM_FILES = ("frames.csv", "monitor/iter.dat", "monitor/time.dat", "monitor/position-bounds_melt.dat")
KE_FILE = "monitor/kinetic-energy_melt.dat"   # downloaded only for a focused set of representative cases


def lp(p) -> Path:
    """Windows long-path form (sph_v2 folder names exceed MAX_PATH)."""
    p = str(Path(p).resolve())
    prefix = "\\\\?\\"
    return Path(prefix + p) if os.name == "nt" and not p.startswith(prefix) else Path(p)


def git_blob_sha1(path) -> str:
    path = lp(path)
    h = hashlib.sha1(usedforsecurity=False)
    h.update(f"blob {path.stat().st_size}\0".encode("ascii"))
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with lp(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def eligible_old() -> pd.DataFrame:
    """The frozen OLD common population (Week 7 primary_common_population.csv = data/alse/population.csv,
    sha256 c15658ca..., 405 rows, 73 has_keyhole)."""
    pop = pd.read_csv(POPULATION, usecols=["experiment_name", "partition", "P", "VX", "LS", "ST", "has_keyhole"])
    pop["has_keyhole"] = pop.has_keyhole.map({True: 1, False: 0, "True": 1, "False": 0}).astype(int)
    assert len(pop) == 405 and pop.has_keyhole.sum() == 73 and pop.experiment_name.is_unique
    return pop.rename(columns={"experiment_name": "sim_id"})


def eligible_new() -> pd.DataFrame:
    """The 136 usable October NEW runs (Week 11 included manifest; Week 12 audit copy with the sealed oracle label)."""
    new = pd.read_csv(ROOT / "outputs/week12_startup_and_transfer_development/audit/new136.csv",
                      usecols=["sim_id", "P", "VX", "LS", "ST", "has_keyhole"])
    assert len(new) == 136 and new.has_keyhole.sum() == 124 and new.sim_id.is_unique
    return new


def needed_paths():
    old, new = eligible_old(), eligible_new()
    paths = {OLD_REV: list(OLD_LEDGERS.values()) + [f"{s}/{f}" for s in old.sim_id for f in SIM_FILES],
             NEW_REV: [NEW_LABEL_FILE] + [f"{s}/{f}" for s in new.sim_id for f in SIM_FILES]}
    return paths


def remote_meta(revision: str, paths, batch=100) -> pd.DataFrame:
    """Size and content identity of each path in the pinned tree (HF paths-info API; metadata only)."""
    from huggingface_hub import HfApi
    api = HfApi()
    rows = []
    paths = list(dict.fromkeys(paths))
    for i in range(0, len(paths), batch):
        chunk = paths[i:i + batch]
        info = api.get_paths_info(REPO_ID, chunk, revision=revision, repo_type="dataset")
        got = {x.path: x for x in info}
        for p in chunk:
            x = got.get(p)
            lfs = getattr(x, "lfs", None) if x is not None else None
            lfs_sha = (lfs.get("sha256") if isinstance(lfs, dict) else getattr(lfs, "sha256", None)) if lfs else None
            rows.append({"revision": revision, "path": p, "remote_exists": x is not None,
                         "size": getattr(x, "size", None) if x is not None else None,
                         "blob_id": getattr(x, "blob_id", None) if x is not None else None, "lfs_sha256": lfs_sha})
        print(f"paths-info {revision[:8]}: {min(i + batch, len(paths))}/{len(paths)}", flush=True)
    return pd.DataFrame(rows)


def run_meta():
    PROV.mkdir(parents=True, exist_ok=True)
    frames = []
    for rev, paths in needed_paths().items():
        frames.append(remote_meta(rev, paths))
    # Kinetic energy metadata for every eligible run (metadata only; payloads only for focused cases).
    old, new = eligible_old(), eligible_new()
    frames.append(remote_meta(OLD_REV, [f"{s}/{KE_FILE}" for s in old.sim_id]))
    frames.append(remote_meta(NEW_REV, [f"{s}/{KE_FILE}" for s in new.sim_id]))
    meta = pd.concat(frames, ignore_index=True)
    meta.to_csv(PROV / "remote_metadata.csv.gz", index=False)
    print(meta.groupby(["revision", "remote_exists"]).size())
    return meta


def load_meta() -> pd.DataFrame:
    return pd.read_csv(PROV / "remote_metadata.csv.gz")


def _identity_ok(path, row) -> tuple[bool, str]:
    path = lp(path)
    if not path.exists():
        return False, "absent"
    if int(path.stat().st_size) != int(row["size"]):
        return False, "size_mismatch"
    if isinstance(row.get("lfs_sha256"), str) and row["lfs_sha256"]:
        return (sha256_file(path) == row["lfs_sha256"]), "lfs_sha256"
    return (git_blob_sha1(path) == row["blob_id"]), "git_blob_sha1"


def resolve(revision: str, path: str, row, download=True) -> dict:
    """Return a verified local copy: reuse the pinned-revision cache, else an identical cached copy at another
    revision (OLD audit pin), else download at the pinned revision."""
    candidates = [RAW / revision / path]
    if revision == OLD_REV:
        candidates.append(RAW / OLD_AUDIT_REV / path)
    for c in candidates:
        ok, how = _identity_ok(c, row)
        if ok:
            return {"revision": revision, "path": path, "local": str(c), "source": "verified_cache" if c.parts[-len(Path(path).parts) - 1] == revision else f"verified_cache_{OLD_AUDIT_REV[:8]}", "check": how, "verified": True}
    if not download:
        return {"revision": revision, "path": path, "local": "", "source": "missing", "check": "", "verified": False}
    from huggingface_hub import hf_hub_download
    local = Path(hf_hub_download(REPO_ID, filename=path, repo_type="dataset", revision=revision, local_dir=RAW / revision))
    ok, how = _identity_ok(local, row)
    return {"revision": revision, "path": path, "local": str(local), "source": "downloaded", "check": how, "verified": bool(ok)}


def run_download(include=None, workers=8):
    meta = load_meta()
    need = meta[meta.remote_exists & ~meta.path.str.endswith(KE_FILE)] if include is None else meta[meta.path.isin(include)]
    rows = need.to_dict("records")
    out = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(resolve, r["revision"], r["path"], r) for r in rows]
        for i, f in enumerate(concurrent.futures.as_completed(futs), 1):
            out.append(f.result())
            if i % 200 == 0 or i == len(futs):
                print(f"resolved {i}/{len(futs)}", flush=True)
    man = pd.DataFrame(out).sort_values(["revision", "path"])
    name = "download_manifest.csv" if include is None else "download_manifest_ke.csv"
    prev = PROV / name
    if prev.exists() and include is not None:
        man = pd.concat([pd.read_csv(prev), man]).drop_duplicates(["revision", "path"], keep="last")
    man.drop(columns=["local"]).to_csv(prev, index=False)
    bad = man[~man.verified]
    print(man.groupby(["revision", "source", "verified"]).size())
    if len(bad):
        print("UNVERIFIED:", bad.path.head().tolist())
    return man


def local_file(revision: str, path: str) -> Path:
    """Verified local path for a pinned file (reads the download manifest; never trusts an unverified copy)."""
    for name in ("download_manifest.csv", "download_manifest_ke.csv"):
        f = PROV / name
        if f.exists():
            m = pd.read_csv(f)
            hit = m[(m.revision == revision) & (m.path == path) & m.verified]
            if len(hit):
                src = hit.source.iloc[0]
                base = RAW / (OLD_AUDIT_REV if src.endswith(OLD_AUDIT_REV[:8]) else revision)
                return lp(base / path)
    raise FileNotFoundError(f"no verified local copy of {revision[:8]}:{path}")


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "all"
    if step in ("meta", "all"):
        run_meta()
    if step in ("download", "all"):
        run_download()
