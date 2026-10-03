"""Read-only historical adapters and shared Week 12 developmental evaluation.

No frozen runner is resumed. The old prediction file is read only for its
already-open included truth mapping, never for partial performance estimates.
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (average_precision_score, brier_score_loss,
                             log_loss, roc_auc_score)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/week12_startup_and_transfer_development"
FEATURES = ["P", "VX", "LS", "ST"]
FREEZE = ROOT / "outputs/week11_external_prelabel_freeze_final/EXTERNAL_BATCH_FREEZE.json"
HIST = ROOT / "outputs/week11_track_a_external_validation/external_validation"
MANIFEST = ROOT / "outputs/week11_new_data_arrival_audit/WEEK11_NEW_BATCH_MANIFEST.csv"
OLD = ROOT / "outputs/week7_06_real_data_boundary_active_level_set/primary_common_population.csv"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe(value):
    if isinstance(value, dict):
        return {str(k): safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [safe(v) for v in value]
    if isinstance(value, (np.integer, np.floating, np.bool_)):
        value = value.item()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if isinstance(value, Path):
        return str(value)
    return value


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(safe(payload), indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def write_csv(path, frame):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    kwargs = {"compression": {"method": "gzip", "mtime": 0}} if path.suffix == ".gz" else {}
    frame.to_csv(path, index=False, lineterminator="\n", **kwargs)


def seed(*parts):
    return int.from_bytes(hashlib.sha256(("week12|" + "|".join(map(str, parts))).encode()).digest()[:4], "little")


def logh(x):
    x = np.asarray(x, float)
    return np.log(x[:, 0]) - .5 * np.log(x[:, 1]) - 1.5 * np.log(x[:, 2])


def load_new():
    frozen = json.loads(FREEZE.read_text())
    manifest = pd.read_csv(MANIFEST).set_index("sim_id").loc[frozen["included_ids"]].reset_index()
    truth = pd.read_csv(HIST / "per_budget_predictions.csv", usecols=["sim_id", "truth"])
    require(truth.groupby("sim_id").truth.nunique().eq(1).all(), "Historical truth disagreement")
    mapping = truth.drop_duplicates("sim_id").set_index("sim_id").truth
    require(set(mapping.index) == set(manifest.sim_id), "Included truth coverage mismatch")
    manifest["has_keyhole"] = manifest.sim_id.map(mapping).astype(int)
    manifest["row_index"] = np.arange(len(manifest))
    manifest["log_h"] = logh(manifest[FEATURES])
    require(len(manifest) == 136 and manifest.has_keyhole.sum() == 124, "NEW-136 class counts drift")
    return manifest


def load_old():
    frame = pd.read_csv(OLD, usecols=["experiment_name", "has_keyhole", *FEATURES])
    require(len(frame) == 405 and frame.has_keyhole.sum() == 73, "OLD-405 class counts drift")
    frame = frame.rename(columns={"experiment_name": "sim_id"})
    frame["log_h"] = logh(frame[FEATURES])
    return frame


def load_splits():
    return json.loads((HIST / "split_manifest.json").read_text())


def original_order(x, split):
    from src.external_validation.runner import feature_only_maximin
    from src import week8_5_frozen_sample_efficiency_confirmation as w85
    key = w85.seed_u32(w85.seed_key("run", split["split_id"], "initial_design"))
    return feature_only_maximin(x, split["train_indices"], key, len(split["train_indices"]))


def q20_flags(x, y, ids, test):
    from src.external_validation.analysis import boundary_flags
    return boundary_flags(x, y, test, ids, "entire_evaluation_batch")[20]


def metrics(y, p):
    y, p = np.asarray(y, int), np.asarray(p, float)
    require(len(y) == len(p) and len(y) > 0, "Invalid metric input")
    require(np.isfinite(p).all() and ((p >= 0) & (p <= 1)).all(), "Invalid probability")
    pred = p >= .5
    pos, neg = y == 1, y == 0
    r1 = float(np.mean(pred[pos])) if pos.any() else np.nan
    r0 = float(np.mean(~pred[neg])) if neg.any() else np.nan
    both = pos.any() and neg.any()
    return {"n": len(y), "n_keyhole": int(pos.sum()), "n_non_keyhole": int(neg.sum()),
            "accuracy": float(np.mean(pred == y)),
            "balanced_accuracy": (r1 + r0) / 2 if both else np.nan,
            "keyhole_recall": r1, "non_keyhole_recall": r0,
            "roc_auc": float(roc_auc_score(y, p)) if both else np.nan,
            "pr_auc_keyhole": float(average_precision_score(y, p)) if both else np.nan,
            "pr_auc_non_keyhole": float(average_precision_score(1-y, 1-p)) if both else np.nan,
            "brier": float(brier_score_loss(y, p)),
            "log_loss": float(log_loss(y, np.clip(p, 1e-12, 1-1e-12), labels=[0, 1]))}


def initialize_audit():
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / "audit/protected_hashes.json"
    require(not dest.exists(), "Do not overwrite initial evidence snapshot")
    frozen = json.loads(FREEZE.read_text())
    protected = set(ROOT / p for p in frozen["source_code_hashes"])
    for parent in (ROOT / "outputs", ROOT / "docs"):
        for d in parent.glob("week11*"):
            protected.update(p for p in d.rglob("*") if p.is_file())
    protected.update(p for p in (ROOT / "docs/trackA_freeze").rglob("*") if p.is_file())
    protected.update([OLD, MANIFEST])
    write_json(dest, {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p) for p in sorted(protected)})
    import scipy, sklearn, threadpoolctl
    write_json(OUT / "audit/repository_state.json", {
        "start_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "branch": "main", "remote_main_verified_equal": True,
        "python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
        "scipy": scipy.__version__, "scikit_learn": sklearn.__version__, "threadpoolctl": threadpoolctl.__version__,
        "runtime": ".venv/Scripts/python.exe", "protected_file_count": len(protected),
        "new_status": "POST-HOC DEVELOPMENT DATA", "frozen_external_status": "INCOMPLETE_FROZEN_STOP",
        "data_mixing": False, "withheld_outcomes_accessed": False,
        "label_recovery": "Unique included sim_id/truth mapping only; no historical probabilities loaded",
        "freeze_sha256": sha(FREEZE)})
    new, old = load_new(), load_old()
    require(not set(new.sim_id) & set(old.sim_id), "OLD/NEW ID overlap")
    write_csv(OUT / "audit/new136.csv", new)
    write_csv(OUT / "audit/old405_inputs_labels.csv", old)
    write_json(OUT / "audit/original_splits.json", load_splits())
    write_json(OUT / "audit/input_provenance.json", {str(p.relative_to(ROOT)): sha(p) for p in [FREEZE, MANIFEST, OLD, HIST / "per_budget_predictions.csv", HIST / "split_manifest.json"]})


def verify_protected():
    expected = json.loads((OUT / "audit/protected_hashes.json").read_text())
    bad = [p for p, digest in expected.items() if not (ROOT/p).exists() or sha(ROOT/p) != digest]
    return {"status": "PASS" if not bad else "FAIL", "file_count": len(expected), "changed_files": bad}


if __name__ == "__main__":
    initialize_audit()
