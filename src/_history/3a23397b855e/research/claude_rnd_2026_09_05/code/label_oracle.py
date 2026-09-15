"""Blinded label oracle and isolated evaluator for the external confirmation (Phase 9).

Design rules (frozen):
  * The label file is read ONLY by this module.  Its SHA-256 is recorded at first open.
  * `Oracle.reveal(run_id, row_ids)` returns labels for explicitly requested row ids and
    appends every access to an append-only JSONL log (timestamp, run_id, ids, counter).
    A run may only reveal rows in its own training pool (enforced by the partition manifest).
  * `Evaluator` holds the held-out labels of each fold and computes the frozen metrics
    (Fold-B1-q20/q30 accuracy, KH recall, full-fold accuracy) for a probability vector.
    Method code never receives the evaluator's labels; it receives only metric values.
  * B1 distances and q20/q30 flags are computed inside the evaluator from the full new-pool
    labels (evaluation-only, as in the historical protocol) and are never exposed to methods.
"""
from __future__ import annotations
import hashlib, json, time, math, threading
from pathlib import Path
import numpy as np, pandas as pd
from scipy.spatial import distance
from sklearn.preprocessing import StandardScaler

FEATURES = ("P", "VX", "LS", "ST")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


class Oracle:
    def __init__(self, label_csv: str, partition_json: str, log_path: str, id_col="experiment_name", label_col="has_keyhole"):
        self.path = Path(label_csv); self.sha256 = sha256_file(self.path)
        df = pd.read_csv(self.path)
        if id_col not in df.columns or label_col not in df.columns:
            raise ValueError("label file must contain id and label columns")
        self._labels = {str(k): int(v) for k, v in zip(df[id_col], df[label_col])}
        self.partitions = json.load(open(partition_json))   # run_id -> {"train": [...ids], "test": [...ids]}
        self.log = Path(log_path); self.log.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock(); self._counter = 0
        self._append({"event": "open", "label_file": str(self.path), "label_sha256": self.sha256, "n_rows": len(df)})

    def _append(self, rec: dict):
        rec = {"t": time.time(), "seq": self._counter, **rec}; self._counter += 1
        with self._lock, open(self.log, "a") as f:
            f.write(json.dumps(rec) + "\n")

    def reveal(self, run_id: str, ids) -> dict:
        ids = [str(i) for i in ids]
        allowed = set(self.partitions[run_id]["train"])
        bad = [i for i in ids if i not in allowed]
        if bad:
            self._append({"event": "refused", "run_id": run_id, "ids": bad})
            raise PermissionError(f"run {run_id} requested ids outside its training pool: {bad[:5]}")
        out = {i: self._labels[i] for i in ids}
        self._append({"event": "reveal", "run_id": run_id, "ids": ids})
        return out

    def access_log(self) -> list[dict]:
        return [json.loads(l) for l in open(self.log)]


class Evaluator:
    """Isolated evaluator: computes frozen metrics on a fold's held-out rows."""

    def __init__(self, label_csv: str, inputs_csv: str, partition_json: str, id_col="experiment_name", label_col="has_keyhole"):
        lab = pd.read_csv(label_csv); inp = pd.read_csv(inputs_csv)
        df = inp.merge(lab[[id_col, label_col]], on=id_col, validate="one_to_one")
        self.ids = df[id_col].astype(str).to_numpy(); self.y = df[label_col].astype(int).to_numpy()
        self.index = {i: k for k, i in enumerate(self.ids)}
        z = StandardScaler().fit_transform(df.loc[:, FEATURES].to_numpy(float))
        dmat = distance.cdist(z, z); opposite = self.y[:, None] != self.y[None, :]
        self.b1 = np.where(opposite, dmat, np.inf).min(axis=1)          # evaluation-only
        self.partitions = json.load(open(partition_json))

    def flags(self, run_id: str):
        test = [self.index[i] for i in self.partitions[run_id]["test"]]
        names = self.ids[test]; order = np.lexsort((names, self.b1[test]))
        out = {"full": np.ones(len(test), bool)}
        for q in (20, 30):
            f = np.zeros(len(test), bool); f[order[: int(math.ceil(q / 100 * len(test)))]] = True; out[f"q{q}"] = f
        return np.asarray(test), out

    def evaluate(self, run_id: str, prob_by_id: dict) -> dict:
        test, flags = self.flags(run_id)
        p = np.array([prob_by_id[self.ids[k]] for k in test], float); yt = self.y[test]; pred = (p >= .5).astype(int)
        res = {}
        for name, f in flags.items():
            res[f"{name}_accuracy"] = float((pred[f] == yt[f]).mean()) if f.any() else float("nan")
            kh = f & (yt == 1); res[f"{name}_kh_recall"] = float((pred[kh] == 1).mean()) if kh.any() else float("nan")
            res[f"{name}_n"] = int(f.sum()); res[f"{name}_n_kh"] = int(kh.sum())
        return res
