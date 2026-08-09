"""Shared, revision-pinned utilities for the Week 7 ``sph_v2`` audit.

This module intentionally contains data access, provenance, and parsing helpers
only.  It does not contain predictive modelling code.  All Hugging Face access
is pinned to :data:`SPH_V2_REVISION`; ``main`` is queried only to record whether
the floating branch still points at the analysed revision.
"""

from __future__ import annotations

import concurrent.futures
import datetime as dt
import hashlib
import json
import math
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Iterable, Sequence

import nbformat
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from huggingface_hub import HfApi, hf_hub_download


ROOT = Path(__file__).resolve().parents[1]
SPH_V2_REPO_ID = "ioandanielc/sph_v2"
SPH_V2_REVISION = "d69dac5bda8b622bc0de316b112815c6056c06ec"
WEEK6_REPO_ID = "ioandanielc/sph_dataset"
WEEK6_REVISION = "0e859b748fdbc8454f66e58e101e333ac0479d42"
WEEK6_BASE_COMMIT = "cba151880fc670d1b8a20ff2f7f25295f9bcb892"

RAW_ROOT = ROOT / "data" / "raw" / "sph_v2" / SPH_V2_REVISION
WEEK6_RAW_ROOT = (
    Path(r"C:\Users\ozgur\Documents\thesis-week6-melt-pool-audit")
    / "data"
    / "raw"
    / "huggingface"
    / "sph_dataset"
    / "final_data_processed"
)

PARTITIONS: dict[str, str] = {
    "new-data": "labels_partition_1_new-data.csv",
    "old-data-local": "labels_partition_2_old-data-local.csv",
    "old-data-remote-clean": "labels_partition_3_old-data-remote-clean.csv",
}
PARTITION_ORDER = list(PARTITIONS)

FEATURE_UNITS = {"P": "W", "VX": "m/s", "LS": "m", "ST": "K"}
PHYSICAL_LABELS = {"Forming Phase", "Conduction", "Keyhole"}
TECHNICAL_LABELS = {
    "Initial Emptiness",
    "Scanning Stopped",
    "Solidifying Stopped",
    "Screenshot Bug",
    "Unsure",
}

FOLDER_KEYS = ["P", "VX", "LS", "ST", "M", "XI", "XF", "XL", "TE", "DT", "H"]
FOLDER_PATTERN = re.compile(
    r"^P-(?P<P>[^_]+)_VX-(?P<VX>[^_]+)_LS-(?P<LS>[^_]+)_"
    r"ST-(?P<ST>[^_]+)_M-(?P<M>[^_]+)_XI-(?P<XI>[^_]+)_"
    r"XF-(?P<XF>[^_]+)_XL-(?P<XL>[^_]+)_TE-(?P<TE>[^_]+)_"
    r"DT-(?P<DT>[^_]+)_H-(?P<H>[^_]+)$"
)


def utc_now() -> str:
    """Return a timezone-aware UTC timestamp with second precision."""

    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def decode_number(value: Any) -> float:
    """Decode the repository's filename/CSV number representation.

    Examples are ``101p25`` -> ``101.25`` and ``-0p0002`` -> ``-0.0002``.
    Numeric inputs are returned as floats unchanged.
    """

    if value is None or (isinstance(value, float) and math.isnan(value)):
        return math.nan
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)
    text = str(value).strip()
    if not text:
        return math.nan
    return float(text.replace("p", "."))


def parse_experiment_name(name: str) -> dict[str, Any]:
    """Parse one semantic ``sph_v2`` experiment-folder name."""

    match = FOLDER_PATTERN.fullmatch(str(name))
    if not match:
        return {
            "experiment_name": str(name),
            "folder_name_valid": False,
            **{key: math.nan for key in ["P", "VX", "LS", "ST", "XI", "XF", "XL", "TE", "DT"]},
            "material": "",
            "folder_hash": "",
        }
    values = match.groupdict()
    return {
        "experiment_name": str(name),
        "folder_name_valid": True,
        "P": decode_number(values["P"]),
        "VX": decode_number(values["VX"]),
        "LS": decode_number(values["LS"]),
        "ST": decode_number(values["ST"]),
        "XI": decode_number(values["XI"]),
        "XF": decode_number(values["XF"]),
        "XL": decode_number(values["XL"]),
        "TE": decode_number(values["TE"]),
        "DT": decode_number(values["DT"]),
        "material": values["M"],
        "folder_hash": values["H"],
    }


def json_safe(value: Any) -> Any:
    """Convert numpy/pandas objects to strict JSON-compatible values."""

    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, (pd.Timestamp, dt.datetime, dt.date)):
        return value.isoformat()
    if pd.isna(value):
        return None
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(json_safe(payload), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, lineterminator="\n")


def sha256_file(path: Path, chunk_size: int = 2**20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_blob_sha1(path: Path, chunk_size: int = 2**20) -> str:
    """Return the Git blob SHA-1 for a local file without invoking Git."""

    size = path.stat().st_size
    digest = hashlib.sha1(usedforsecurity=False)
    digest.update(f"blob {size}\0".encode("ascii"))
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_output(*arguments: str, cwd: Path = ROOT) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def current_main_revision(api: HfApi | None = None) -> str:
    """Resolve floating ``main`` for provenance only."""

    client = api or HfApi()
    return str(client.dataset_info(SPH_V2_REPO_ID, revision="main").sha)


def download_pinned_file(filename: str, *, force: bool = False) -> Path:
    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    return Path(
        hf_hub_download(
            repo_id=SPH_V2_REPO_ID,
            repo_type="dataset",
            revision=SPH_V2_REVISION,
            filename=filename,
            local_dir=RAW_ROOT,
            force_download=force,
        )
    )


def download_pinned_files(
    filenames: Sequence[str],
    *,
    workers: int = 6,
    force: bool = False,
    progress_every: int = 25,
) -> dict[str, Path]:
    """Download an explicit file list at the exact revision."""

    unique = list(dict.fromkeys(str(item) for item in filenames))
    downloaded: dict[str, Path] = {}

    def one(filename: str) -> tuple[str, Path]:
        return filename, download_pinned_file(filename, force=force)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = [pool.submit(one, filename) for filename in unique]
        for position, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            filename, path = future.result()
            downloaded[filename] = path
            if position % progress_every == 0 or position == len(unique):
                print(f"Pinned downloads: {position}/{len(unique)}", flush=True)
    return downloaded


def load_partition_labels(*, workers: int = 3) -> pd.DataFrame:
    """Download and combine the three partition label ledgers."""

    paths = download_pinned_files(list(PARTITIONS.values()), workers=workers)
    frames: list[pd.DataFrame] = []
    expected = [
        "name",
        "hash",
        "P",
        "VX",
        "LS",
        "ST",
        "bug_free",
        "correctly_finished",
        "timestep",
        "label_1",
        "label_2",
        "label_final",
    ]
    for number, (partition, filename) in enumerate(PARTITIONS.items(), start=1):
        frame = pd.read_csv(paths[filename])
        if frame.columns.tolist() != expected:
            raise RuntimeError(f"{filename}: unexpected label schema {frame.columns.tolist()}")
        frame.insert(0, "partition_number", number)
        frame.insert(1, "partition", partition)
        frame.insert(2, "partition_label_file", filename)
        frame.insert(3, "frame_row_in_partition", np.arange(len(frame), dtype=int))
        for feature in ["P", "VX", "LS", "ST"]:
            frame[f"{feature}_numeric"] = frame[feature].map(decode_number)
        frames.append(frame)
    combined = pd.concat(frames, ignore_index=True)
    combined["experiment_name"] = combined["name"].astype(str)
    return combined


def top_level_inventory(api: HfApi | None = None) -> pd.DataFrame:
    client = api or HfApi()
    rows: list[dict[str, Any]] = []
    for item in client.list_repo_tree(
        repo_id=SPH_V2_REPO_ID,
        repo_type="dataset",
        revision=SPH_V2_REVISION,
        recursive=False,
        expand=True,
    ):
        rows.append(_repo_item_row(item))
    return pd.DataFrame(rows).sort_values(["item_type", "path"]).reset_index(drop=True)


def _repo_item_row(item: Any) -> dict[str, Any]:
    lfs = getattr(item, "lfs", None)
    last_commit = getattr(item, "last_commit", None)
    return {
        "path": str(item.path),
        "item_type": "folder" if item.__class__.__name__ == "RepoFolder" else "file",
        "size_bytes": getattr(item, "size", None),
        "blob_id": getattr(item, "blob_id", None),
        "lfs_sha256": getattr(lfs, "sha256", None) if lfs else None,
        "xet_hash": getattr(item, "xet_hash", None),
        "last_commit_oid": getattr(last_commit, "oid", None) if last_commit else None,
        "last_commit_date": (
            getattr(last_commit, "date", None).isoformat()
            if last_commit and getattr(last_commit, "date", None)
            else None
        ),
    }


def _write_inventory_batches(
    iterator: Iterable[Any], cache_path: Path, *, progress_label: str
) -> int:
    schema = pa.schema(
        [
            ("path", pa.string()),
            ("item_type", pa.string()),
            ("size_bytes", pa.int64()),
            ("blob_id", pa.string()),
            ("lfs_sha256", pa.string()),
            ("xet_hash", pa.string()),
            ("last_commit_oid", pa.string()),
            ("last_commit_date", pa.string()),
        ]
    )
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    writer = pq.ParquetWriter(cache_path, schema=schema, compression="zstd")
    buffer: list[dict[str, Any]] = []
    count = 0
    try:
        for item in iterator:
            buffer.append(_repo_item_row(item))
            count += 1
            if len(buffer) >= 10_000:
                writer.write_table(pa.Table.from_pylist(buffer, schema=schema))
                buffer.clear()
                print(f"{progress_label}: {count:,} tree items", flush=True)
        if buffer:
            writer.write_table(pa.Table.from_pylist(buffer, schema=schema))
    finally:
        writer.close()
    print(f"{progress_label}: complete with {count:,} tree items", flush=True)
    return count


def complete_tree_inventory(*, refresh: bool = False) -> pd.DataFrame:
    """Return the complete pinned repository tree, cached outside Git."""

    cache = RAW_ROOT / f".complete_tree_{SPH_V2_REVISION}.parquet"
    if refresh and cache.exists():
        cache.unlink()
    if not cache.exists():
        api = HfApi()
        iterator = api.list_repo_tree(
            repo_id=SPH_V2_REPO_ID,
            repo_type="dataset",
            revision=SPH_V2_REVISION,
            recursive=True,
            # ``expand`` asks the Hub API for per-item commit metadata.  That is
            # useful for a handful of files, but prohibitively slow for the
            # hundreds of thousands of frame/GIF objects in sph_v2.  Path,
            # size, blob id, and LFS/Xet identifiers are still returned here
            # and are the fields this audit actually uses.
            expand=False,
        )
        _write_inventory_batches(iterator, cache, progress_label="Pinned repository inventory")
    return pd.read_parquet(cache)


def subset_tree_inventory(
    experiment_names: Sequence[str], *, refresh: bool = False
) -> pd.DataFrame:
    """Inventory selected experiment folders for a cheap smoke test."""

    token = hashlib.sha256("\n".join(sorted(experiment_names)).encode()).hexdigest()[:12]
    cache = RAW_ROOT / f".subset_tree_{SPH_V2_REVISION}_{token}.parquet"
    if refresh and cache.exists():
        cache.unlink()
    if not cache.exists():
        api = HfApi()

        def items() -> Iterable[Any]:
            for experiment_name in experiment_names:
                yield from api.list_repo_tree(
                    repo_id=SPH_V2_REPO_ID,
                    repo_type="dataset",
                    revision=SPH_V2_REVISION,
                    path_in_repo=experiment_name,
                    recursive=True,
                    expand=False,
                )

        _write_inventory_batches(items(), cache, progress_label="Smoke repository inventory")
    return pd.read_parquet(cache)


def add_tree_path_fields(tree: pd.DataFrame, experiment_names: set[str]) -> pd.DataFrame:
    frame = tree.copy()
    first = frame["path"].astype(str).str.split("/", n=1, expand=True)
    frame["top_level"] = first[0]
    frame["relative_inside_experiment"] = np.where(
        frame["top_level"].isin(experiment_names),
        first[1] if first.shape[1] > 1 else "",
        "",
    )
    frame["experiment_name"] = np.where(
        frame["top_level"].isin(experiment_names), frame["top_level"], ""
    )
    frame["extension"] = (
        frame["path"].astype(str).map(lambda value: Path(value).suffix.lower() or "[none]")
    )
    return frame


def notebook_has_errors(path: Path) -> bool:
    if not path.is_file():
        return True
    notebook = nbformat.read(path, as_version=4)
    return any(
        output.get("output_type") == "error"
        for cell in notebook.cells
        if cell.cell_type == "code"
        for output in cell.get("outputs", [])
    )


def strict_bool(series: pd.Series) -> np.ndarray:
    if pd.api.types.is_bool_dtype(series):
        return series.to_numpy(bool)
    lowered = series.astype(str).str.strip().str.lower()
    mapping = {"true": True, "false": False, "1": True, "0": False}
    if not lowered.isin(mapping).all():
        raise ValueError(f"Unexpected boolean values: {sorted(lowered.unique())}")
    return lowered.map(mapping).to_numpy(bool)


def dataframe_sha256(frame: pd.DataFrame, columns: Sequence[str]) -> str:
    canonical = frame.loc[:, list(columns)].sort_values(list(columns)).to_csv(index=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def directory_size(paths: Iterable[Path]) -> int:
    return sum(path.stat().st_size for path in paths if path.is_file())


def ensure_no_modelling_imports(source_path: Path) -> tuple[bool, str]:
    """Guard the hard Phase 1/2 boundary with a source-level scan."""

    text = source_path.read_text(encoding="utf-8").lower()
    forbidden = [
        "gaussianprocessregressor",
        "ridge(",
        "polynomialfeatures",
        "active learning",
        "level-set estimation",
    ]
    hits = [term for term in forbidden if term in text]
    # Explanatory statements saying that modelling did not occur are allowed.
    executable_hits = [term for term in hits if term in {"gaussianprocessregressor", "ridge(", "polynomialfeatures"}]
    return not executable_hits, ", ".join(executable_hits) if executable_hits else "none"


def output_manifest(output_dir: Path) -> pd.DataFrame:
    rows = []
    for path in sorted(output_dir.rglob("*")):
        # Avoid a self-referential hash and orchestration logs that can receive
        # one final line after the scientific artifacts have been written.
        if path.is_file() and path.name != "output_manifest.csv" and path.suffix.lower() != ".log":
            rows.append(
                {
                    "relative_path": path.relative_to(ROOT).as_posix(),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    return pd.DataFrame(rows)


__all__ = [
    "FEATURE_UNITS",
    "FOLDER_KEYS",
    "PARTITIONS",
    "PARTITION_ORDER",
    "PHYSICAL_LABELS",
    "RAW_ROOT",
    "ROOT",
    "SPH_V2_REPO_ID",
    "SPH_V2_REVISION",
    "TECHNICAL_LABELS",
    "WEEK6_BASE_COMMIT",
    "WEEK6_RAW_ROOT",
    "WEEK6_REPO_ID",
    "WEEK6_REVISION",
    "add_tree_path_fields",
    "complete_tree_inventory",
    "current_main_revision",
    "dataframe_sha256",
    "decode_number",
    "directory_size",
    "download_pinned_file",
    "download_pinned_files",
    "ensure_no_modelling_imports",
    "git_blob_sha1",
    "git_output",
    "json_safe",
    "load_partition_labels",
    "notebook_has_errors",
    "output_manifest",
    "parse_experiment_name",
    "sha256_file",
    "strict_bool",
    "subset_tree_inventory",
    "top_level_inventory",
    "utc_now",
    "write_csv",
    "write_json",
]
