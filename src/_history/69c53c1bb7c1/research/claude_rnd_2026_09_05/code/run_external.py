#!/usr/bin/env python
"""Frozen external replay runner (Phase 9/10).

  --prepare  inputs.csv out_dir            : build label-free partitions, initial designs, random orders (commit these)
  --run      inputs.csv labels.csv out_dir : run arms A, Bprime, C, D through the oracle; write metrics + access log
  --old-pool-regression out_dir            : regression test on the old 405 pool: arm A must reproduce the committed
                                             Phase 1.14 M3-margin path for run w85__r01_f01 (uses old labels; development only)

Inputs CSV columns: experiment_name, P, VX, LS, ST (plus optional configuration columns; ignored).
Labels CSV columns: experiment_name, has_keyhole (0/1).  Read ONLY by label_oracle.Oracle / Evaluator.
"""
from __future__ import annotations
import sys, json, math, hashlib, time
from pathlib import Path
import numpy as np, pandas as pd
from scipy.spatial import distance
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
for p in (HERE, HERE.parent.parent):
    if str(p) not in sys.path: sys.path.insert(0, str(p))
from challenger import FrozenThresholdPosterior, M3Incumbent, select, physics_coordinate, context, T_HYPER  # noqa
from label_oracle import Oracle, Evaluator  # noqa

SEED_ROOT = "rnd2026|v1|new"
REPEATS = 20; N_RANDOM = 10


def seed_u32(*parts) -> int:
    key = "|".join((SEED_ROOT, *(str(p) for p in parts)))
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "little") % (2 ** 32)


def fold_rule(N: int):
    Ks = [K for K in (5, 4, 3, 2) if N / K >= 85]; K = Ks[0] if Ks else 2
    n_test = N // K; n_train = N - n_test; H = min(80, int(math.floor(0.8 * n_train)))
    return K, n_test, n_train, H


def maximin_design(x_train_scaled: np.ndarray, train_rows: np.ndarray, rng: np.random.Generator, size: int = 16) -> list[int]:
    """Repository w85.initial_design logic (feature-only maximin, deterministic ties)."""
    chosen = [int(rng.integers(len(train_rows)))]
    while len(chosen) < size:
        remaining = np.setdiff1d(np.arange(len(train_rows)), np.asarray(chosen), assume_unique=True)
        nearest = distance.cdist(x_train_scaled[remaining], x_train_scaled[chosen]).min(axis=1)
        best = float(nearest.max()); ties = remaining[np.isclose(nearest, best, rtol=1e-12, atol=1e-14)]
        chosen.append(int(ties[np.argmin(train_rows[ties])]))
    return [int(train_rows[i]) for i in chosen]


def prepare(inputs_csv: str, out_dir: str):
    inp = pd.read_csv(inputs_csv); N = len(inp); ids = inp.experiment_name.astype(str).to_numpy()
    K, n_test, n_train, H = fold_rule(N)
    groups = pd.util.hash_pandas_object(inp[["P", "VX", "LS", "ST"]].round(9), index=False).to_numpy()
    ug = np.unique(groups); parts = {}
    x = inp[["P", "VX", "LS", "ST"]].to_numpy(float)
    for r in range(1, REPEATS + 1):
        rng = np.random.default_rng(seed_u32("outer_split", "repeat", f"{r:02d}")); perm = rng.permutation(len(ug)); fold_of_group = {ug[g]: (i % K) + 1 for i, g in enumerate(perm)}
        fold = np.array([fold_of_group[g] for g in groups])
        for f in range(1, K + 1):
            run_id = f"new__r{r:02d}_f{f:02d}"; test = np.flatnonzero(fold == f); train = np.flatnonzero(fold != f)
            scaled = StandardScaler().fit_transform(x[train])
            init = maximin_design(scaled, train, np.random.default_rng(seed_u32("run", run_id, "initial_design")))
            # predetermined feature-only continuation for one-class startup: extend maximin to 32 points
            startup = maximin_design(scaled, train, np.random.default_rng(seed_u32("run", run_id, "initial_design")), size=min(32, len(train)))
            rand_orders = []
            for c in range(N_RANDOM):
                rr = np.random.default_rng(seed_u32("run", run_id, "random", f"{c:02d}", "order")); rest = np.setdiff1d(train, np.asarray(init)); rand_orders.append([int(v) for v in rr.permutation(rest)])
            parts[run_id] = {"repeat": r, "fold": f, "train": [ids[i] for i in train], "test": [ids[i] for i in test], "train_rows": [int(i) for i in train], "test_rows": [int(i) for i in test],
                             "initial_design_rows": init, "startup_sequence_rows": startup, "random_orders_rows": rand_orders}
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    meta = {"N": N, "K": K, "n_test": n_test, "n_train": n_train, "H": H, "repeats": REPEATS, "inputs_sha256": hashlib.sha256(Path(inputs_csv).read_bytes()).hexdigest(), "seed_root": SEED_ROOT, "T_hyper": T_HYPER}
    json.dump(parts, open(out / "partitions.json", "w")); json.dump(meta, open(out / "prepare_meta.json", "w"), indent=2)
    print(json.dumps(meta, indent=2))


def run_arm(arm: str, rid: str, part: dict, inp: pd.DataFrame, oracle: Oracle, evaluator: Evaluator, H: int, budgets, rand_order=None):
    ids = inp.experiment_name.astype(str).to_numpy(); x4 = inp[["P", "VX", "LS", "ST"]].to_numpy(float)
    logh = physics_coordinate(x4[:, 0], x4[:, 1], x4[:, 2]); Zraw = context(x4[:, 1], x4[:, 2], x4[:, 3])
    train = np.asarray(part["train_rows"]); test = np.asarray(part["test_rows"])
    m3 = M3Incumbent(x4, logh, train, lambda b: seed_u32("run", rid, "m3_physics", b)); T = FrozenThresholdPosterior(logh, Zraw, train)
    revealed = list(part["initial_design_rows"]); labels = {}
    labels.update({r: v for r, v in zip(revealed, oracle.reveal(rid, [ids[r] for r in revealed]).values())})
    # one-class startup
    startup = [r for r in part["startup_sequence_rows"] if r not in revealed]
    while len(set(labels[r] for r in revealed)) < 2 and len(revealed) < H and startup:
        nxt = startup.pop(0); labels[nxt] = oracle.reveal(rid, [ids[nxt]])[ids[nxt]]; revealed.append(nxt)
    rows = []
    for b in budgets:
        if len(revealed) < b:  # startup consumed fewer than b? (cannot happen: startup only extends) -> pad by policy below
            pass
        rev = np.asarray(revealed[:b]); lab = np.array([labels[r] for r in rev])
        diverging = len(np.unique(lab)) == 2
        if diverging:
            m3.fit(rev, lab, b); prob = m3.proba(test)
        else:
            prob = np.full(len(test), (lab.sum() + 1) / (len(lab) + 2))
        res = evaluator.evaluate(rid, {ids[t]: float(p) for t, p in zip(test, prob)})
        rows.append({"run_id": rid, "arm": arm, "budget": b, "diverging": diverging, **res})
        if b < H and len(revealed) == b:
            cand = np.setdiff1d(train, rev)
            if not diverging:
                nxt = [r for r in part["startup_sequence_rows"] if r in set(cand)]; nxt = nxt[0] if nxt else int(cand[0])
            elif arm == "A":
                nxt = select(cand, 1 - 2 * np.abs(m3.proba(cand) - .5))
            elif arm in ("Bprime", "C"):
                T.fit(rev, lab); nxt = select(cand, T.margin_scores(cand) if arm == "Bprime" else T.tv_scores(cand))
            elif arm == "D":
                nxt = next(r for r in rand_order if r in set(cand))
            labels[nxt] = oracle.reveal(rid, [ids[nxt]])[ids[nxt]]; revealed.append(int(nxt))
    return rows, revealed


def run(inputs_csv: str, labels_csv: str, out_dir: str, arms=("A", "Bprime", "C", "D")):
    out = Path(out_dir); parts = json.load(open(out / "partitions.json")); meta = json.load(open(out / "prepare_meta.json")); H = meta["H"]
    inp = pd.read_csv(inputs_csv)
    assert hashlib.sha256(Path(inputs_csv).read_bytes()).hexdigest() == meta["inputs_sha256"], "inputs changed since --prepare"
    oracle = Oracle(labels_csv, str(out / "partitions.json"), str(out / "oracle_access_log.jsonl")); evaluator = Evaluator(labels_csv, inputs_csv, str(out / "partitions.json"))
    budgets = list(range(16, H + 1)); all_rows = []; paths = {}
    for rid, part in parts.items():
        for arm in arms:
            if arm == "D":
                for c, order in enumerate(part["random_orders_rows"]):
                    rows, path = run_arm("D", rid, part, inp, oracle, evaluator, H, budgets, rand_order=order); [r.update({"continuation": c}) for r in rows]; all_rows += rows; paths[f"{rid}|D|{c}"] = path
            else:
                rows, path = run_arm(arm, rid, part, inp, oracle, evaluator, H, budgets); all_rows += rows; paths[f"{rid}|{arm}"] = path
        pd.DataFrame(all_rows).to_csv(out / "metrics.csv", index=False); json.dump(paths, open(out / "paths.json", "w"))
    print("done; oracle label sha256:", oracle.sha256)


def old_pool_regression(out_dir: str):
    """Arm A on the old pool must reproduce the committed Phase 1.14 path (development-only test)."""
    from core import Data, REPO, w85
    d = Data(); spec = d.specs[0]; out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    inp = d.population[["experiment_name", "P", "VX", "LS", "ST"]].copy(); inp.to_csv(out / "old_inputs.csv", index=False)
    lab = d.population[["experiment_name", "has_keyhole"]].copy(); lab["has_keyhole"] = lab.has_keyhole.astype(int); lab.to_csv(out / "old_labels.csv", index=False)
    ids = inp.experiment_name.astype(str).to_numpy(); train = np.asarray(spec.train_indices); test = np.asarray(spec.test_indices)
    init = list(map(int, w85.initial_design(spec, d.population)))
    parts = {spec.run_id: {"repeat": spec.repeat, "fold": spec.fold, "train": [ids[i] for i in train], "test": [ids[i] for i in test], "train_rows": [int(i) for i in train], "test_rows": [int(i) for i in test], "initial_design_rows": init, "startup_sequence_rows": init, "random_orders_rows": []}}
    json.dump(parts, open(out / "partitions.json", "w"))
    oracle = Oracle(str(out / "old_labels.csv"), str(out / "partitions.json"), str(out / "oracle_access_log.jsonl")); ev = Evaluator(str(out / "old_labels.csv"), str(out / "old_inputs.csv"), str(out / "partitions.json"))
    # M3 seeds must match Phase 1.14 for exact path reproduction: patch seed function to the repository's
    from core import p13
    x4 = inp[["P", "VX", "LS", "ST"]].to_numpy(float); logh = physics_coordinate(x4[:, 0], x4[:, 1], x4[:, 2]); Zraw = context(x4[:, 1], x4[:, 2], x4[:, 3])
    m3 = M3Incumbent(x4, logh, train, lambda b: p13.seed_u32("shared_physics", spec.run_id, b))
    revealed = list(init); labels = oracle.reveal(spec.run_id, [ids[r] for r in revealed]); lab = {r: labels[ids[r]] for r in revealed}
    for b in range(16, 80):
        rev = np.asarray(revealed); m3.fit(rev, np.array([lab[r] for r in rev]), b); cand = np.setdiff1d(train, rev)
        nxt = select(cand, 1 - 2 * np.abs(m3.proba(cand) - .5)); lab[nxt] = oracle.reveal(spec.run_id, [ids[nxt]])[ids[nxt]]; revealed.append(int(nxt))
    committed = pd.read_csv(REPO / "outputs/week9_phase1_14_m3_margin_acquisition/m3_margin_paths.csv.gz"); ref = committed[(committed.path == "P1") & (committed.run_id == spec.run_id)].sort_values("query_order").population_row_index.astype(int).tolist()
    ok = revealed == ref; log = oracle.access_log()
    print("arm A reproduces committed Phase 1.14 path:", ok, "| oracle reveals:", sum(len(r.get("ids", [])) for r in log if r["event"] == "reveal"))
    return ok


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "--prepare": prepare(a[1], a[2])
    elif a[0] == "--run": run(a[1], a[2], a[3])
    elif a[0] == "--old-pool-regression": sys.exit(0 if old_pool_regression(a[1]) else 1)
    else: raise SystemExit(__doc__)
