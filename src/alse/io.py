"""Small I/O and seeding helpers shared by every module.

The seed derivations are frozen: every stored trajectory, split and bootstrap
interval in the thesis depends on them. Do not change the join characters,
byte counts or endianness.
"""

from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


# --- seeds -----------------------------------------------------------------


def seed_key(root: str, *parts: object) -> str:
    """'|'-joined seed key with a namespace root.

    frozen: week8_5_frozen_sample_efficiency_confirmation.py::seed_key and the
    Week 9 ``seed_u32(*parts)`` variants (root = per-module SEED_ROOT).
    """
    return "|".join((root, *(str(part) for part in parts)))


def seed_u32(key: str) -> int:
    """sha256(key)[:8] little-endian modulo 2**32.

    frozen: week8_5_frozen_sample_efficiency_confirmation.py::seed_u32
    """
    return int.from_bytes(hashlib.sha256(key.encode("utf-8")).digest()[:8], "little") % (2**32)


def stable_seed(*parts: object) -> int:
    """':'-joined variant used by the Phase 6/7 real-data benchmark.

    frozen: week7_phase6_real_data_boundary_active_level_set.py::stable_seed
    """
    digest = hashlib.sha256(":".join(map(str, parts)).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "little") % (2**32)


def stable_rng(*parts: object) -> np.random.Generator:
    return np.random.default_rng(stable_seed(*parts))


# --- serialisation ---------------------------------------------------------


def json_safe(value: Any) -> Any:
    """Convert numpy/pandas scalars and containers to plain JSON values."""
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, (pd.Timestamp, dt.datetime, dt.date)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def write_json(path: Path, payload: Any) -> None:
    """Atomic, sorted-key, LF-terminated JSON (the archive's canonical form)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(json_safe(payload), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    frame.to_csv(temporary, index=False, lineterminator="\n")
    temporary.replace(path)


def write_checkpoint(path: Path, payload: Any) -> None:
    """gzip-compressed JSON checkpoint (restartable long runs)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    with gzip.open(temporary, "wt", encoding="utf-8") as handle:
        json.dump(json_safe(payload), handle, sort_keys=True)
    temporary.replace(path)


def read_checkpoint(path: Path) -> Any:
    with gzip.open(Path(path), "rt", encoding="utf-8") as handle:
        return json.load(handle)


# --- hashing ---------------------------------------------------------------


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path, chunk_size: int = 2**20) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text_lf(path: Path) -> str:
    """sha256 after CRLF->LF normalisation (how the archive hashed text artifacts)."""
    return sha256_bytes(Path(path).read_bytes().replace(b"\r\n", b"\n"))


def canonical_json_bytes(payload: Any) -> bytes:
    """Canonical protocol bytes (indent 2, sorted keys, trailing LF).

    frozen: week8_5_frozen_sample_efficiency_confirmation.py::canonical_protocol_bytes
    """
    return (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def strict_bool(series: pd.Series) -> pd.Series:
    """Parse a column that must contain only true/false values."""
    if pd.api.types.is_bool_dtype(series):
        return series.astype(bool)
    mapping = {"true": True, "false": False, "1": True, "0": False}
    lowered = series.astype(str).str.strip().str.lower()
    require(lowered.isin(mapping).all(), f"Unexpected boolean values: {sorted(lowered.unique())}")
    return lowered.map(mapping).astype(bool)
