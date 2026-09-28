"""Shared contracts. This module has no oracle or historical-data loader."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FEATURES = ("P", "VX", "LS", "ST")
ARMS = ("M3_margin_incumbent", "early8__coverage_then_margin_B40", "coverage_then_margin_B40")
BUDGETS = list(range(16, 81))
PRIMARY = "Fold-B1-q20 accuracy normalized trapezoidal AULC B16-B80"
PAIRED_INTERVAL_METHOD = "paired_repeat_bootstrap_percentile_10000"
GROUPING = "group_token"
SPLIT_CONSTRUCTION = "PreassignedGroupFiveFold"
CORE = ROOT / "docs/trackA_freeze/TRACK_A_FREEZE.json"


class ReadinessError(RuntimeError):
    """A failed information barrier, integrity check, or unresolved pre-label decision."""


def require(condition, message):
    if not condition:
        raise ReadinessError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(encoded(value))


def write_new_bytes(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)


def read_digest_sidecar(path):
    """Read a one-token lowercase SHA-256 sidecar and reject extra content."""
    tokens = Path(path).read_text(encoding="ascii").split()
    require(len(tokens) == 1 and len(tokens[0]) == 64 and
            all(c in "0123456789abcdef" for c in tokens[0]), "Malformed SHA-256 sidecar")
    return tokens[0]


def environment():
    return {"python": sys.version, "platform": platform.platform(),
            "packages": {name: importlib.metadata.version(name) for name in
                         ("numpy", "scipy", "pandas", "scikit-learn", "threadpoolctl")}}


def core_hashes():
    core = json.loads(CORE.read_text())
    for name, expected in core["pinned_sha256"].items():
        require(sha((ROOT / name).read_bytes()) == expected, f"Frozen source drift: {name}")
    require(core["primary_endpoint"] == PRIMARY, "Frozen endpoint mismatch")
    paths = list((ROOT / "src").glob("*.py")) + list((ROOT / "src/external_validation").glob("*.py"))
    paths += list((ROOT / "docs/trackA_freeze").glob("*"))
    paths += [ROOT / name for name in core["pinned_sha256"]]
    return {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p.read_bytes())
            for p in sorted(set(paths)) if p.is_file()}


def check_hashes(hashes):
    for name, expected in hashes.items():
        require(sha((ROOT / name).read_bytes()) == expected, f"Source/protocol changed: {name}")


def check_environment(expected):
    require(environment() == expected, "Execution environment differs from the pre-label freeze")


def committed(path, commit):
    """Require a concrete ancestral Git commit containing exactly this working-tree file."""
    path = Path(path).resolve()
    require(path.is_relative_to(ROOT), "Freeze and pinned source files must be in this repository")
    rel = str(path.relative_to(ROOT)).replace("\\", "/")
    require(len(commit) == 40 and all(c in "0123456789abcdef" for c in commit), "Concrete commit SHA required")
    require(subprocess.run(["git", "merge-base", "--is-ancestor", commit, "HEAD"], cwd=ROOT,
                           capture_output=True).returncode == 0, "Freeze commit is not an ancestor of HEAD")
    stored = subprocess.check_output(["git", "rev-parse", f"{commit}:{rel}"], cwd=ROOT, text=True).strip()
    local = subprocess.check_output(["git", "hash-object", f"--path={rel}", str(path)], cwd=ROOT, text=True).strip()
    require(stored == local, f"Uncommitted/different freeze dependency: {rel}")
