"""SURPRISE_DISCOVERY (pilot A; owner request of 2026-10-16, primary method question; Ioan's post-meeting task).

Question.  After a purchased observation that the pre-observation posterior did not expect, does a short local
exploration around it (while global exploration continues) find the other members of that behaviour family with
fewer queries than margin, straddle or random selection, at the same budget and without global harm?
Rule SD (identical for both base selectors; fixed before any run):
  surprise   the observed label had probability <= SURPRISE_P = 0.2 under the posterior fitted BEFORE that observation
             (for a one-class paid set the posterior is the constant (n1 + 0.5) / (n + 1)).  A missing or non-finite
             response is a QC event (logged, never a surprise); the label still counts.
  seeds      a surprising observation becomes a seed (FIFO).  While a seed is active, queries alternate LOCAL, GLOBAL,
             LOCAL, ... (1:1); a seed gets at most M_LOCAL = 3 local probes.  LOCAL = the nearest unpaid pool point to
             the seed in the fold-standardised log inputs (ties by simulation ID).  GLOBAL = the base selector.  A local
             probe that is itself surprising becomes a new seed.  Every probe is a paid query in the same budget.
Arms.  Synthetic: MARGIN (GPC), STRADDLE (GPR on the response, threshold 0), RANDOM, SD_MARGIN, SD_STRADDLE.
  Real replay (NEW, DEV repeats 3-4, frozen feature-only B16 starts, B16-B40): G3_MARGIN and E1_STRADDLE are the frozen
  Week 18 learners (week18_engine G3 / GPR_depth, ML-II every step) with margin / straddle as in TRAINED_AL; RANDOM
  uses G3; SD_MARGIN = G3 + SD(margin); SD_STRADDLE = E1 + SD(straddle).
One-class rule (all arms, fixed in advance): while the usable paid labels are one-class the learner cannot be fitted;
  the next query is the next unpaid point of the frozen feature-only path (label-free), predictions are the constant.
Observation contract: paid features, labels and A only.  No test label, short-K or q20 membership, corner (VX > 0.85)
  or global class count enters a selector.  Synthetic truth is evaluator-only.
Steps: python -m src.jdl_surprise validate | manifest | work [--part synthetic|real] | evaluate
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

import datetime as dt
import gzip
import json
import sys
import time
import traceback
import warnings

import numpy as np
import pandas as pd

import src.jdl_stage_m as SMM
import src.jdl_trained_al as TA

STUDY = "SURPRISE_DISCOVERY"
OUT = SMM.OUT / "surprise_discovery"
CACHE = SMM.OUT / "_cache" / "surprise_discovery"
MANIFEST = OUT / "SURPRISE_MANIFEST.json"
VALIDATION = OUT / "SURPRISE_VALIDATION.json"
SURPRISE_P, M_LOCAL = 0.2, 3
SYN_ARMS = ("MARGIN", "STRADDLE", "RANDOM", "SD_MARGIN", "SD_STRADDLE")
REAL_ARMS = ("G3_MARGIN", "E1_STRADDLE", "RANDOM", "SD_MARGIN", "SD_STRADDLE")
SYN_SEEDS, SYN_POOL, SYN_TEST, SYN_START, SYN_END = tuple(range(1, 11)), 300, 1000, 10, 40
REPEATS, FOLDS, B_START, B_END = (3, 4), (1, 2, 3, 4, 5), 16, 40
UNIT_TIME_LIMIT_S = 1800                      # a unit exceeding this is stopped and recorded (TIME_LIMIT), never silently dropped
CODE = ("src/jdl_surprise.py", "src/jdl_trained_al.py", "src/jdl_stage_m.py", "src/week18_engine.py", "src/jdl_evaluate.py", "src/jdl_trained_al_eval.py")


# ======================================================================================== the SD rule (shared)
class SDState:
    def __init__(self):
        self.seeds = []            # [index, remaining probes]
        self.last_local = False
        self.log = []

    def observe(self, idx, p_obs, budget, qc_ok=True):
        """p_obs = pre-observation probability of the observed label."""
        surprising = bool(qc_ok and p_obs is not None and p_obs <= SURPRISE_P)
        self.log.append({"budget": budget, "index": int(idx), "p_observed_label_before": None if p_obs is None else float(p_obs), "qc_ok": bool(qc_ok),
                         "surprise": surprising})
        if surprising:
            self.seeds.append([int(idx), M_LOCAL])
        return surprising

    def next_local(self, Z, unpaid, ids):
        """Nearest unpaid point to the active seed (or None)."""
        while self.seeds and self.seeds[0][1] <= 0:
            self.seeds.pop(0)
        if not self.seeds or self.last_local:
            return None
        s = self.seeds[0][0]
        d = np.linalg.norm(Z[unpaid] - Z[s], axis=1)
        order = np.lexsort((np.asarray(ids)[unpaid].astype(str), d))
        self.seeds[0][1] -= 1
        return int(unpaid[order[0]])


# ======================================================================================== synthetic island world
def syn_world(seed):
    """2-D world: smooth background boundary plus one small island of the opposite class inside the class-1 side.
    Response r(x) (observed, noisy) defines the label y = 1{r > 0}.  The island is evaluator truth only."""
    g = np.random.default_rng(1000 + seed)
    def r(X):
        base = 2.5 * (X[:, 0] + 0.25 * np.sin(6 * X[:, 1]) - 0.45)
        c = np.array([0.80, 0.25]) + g_shift
        isl = -6.0 * np.exp(-np.sum((X - c) ** 2, 1) / (2 * 0.07 ** 2))
        return base + isl
    g_shift = g.uniform(-0.05, 0.05, 2)
    Xp, Xt = g.uniform(0, 1, (SYN_POOL, 2)), g.uniform(0, 1, (SYN_TEST, 2))
    rp, rt = r(Xp) + g.normal(0, 0.05, SYN_POOL), r(Xt)
    c = np.array([0.80, 0.25]) + g_shift
    island = lambda X: np.sum((X - c) ** 2, 1) <= (0.12) ** 2
    yp, yt = (rp > 0).astype(int), (rt > 0).astype(int)
    from src.week13_synthetic_al import maximin_order
    path = maximin_order(Xp, np.random.default_rng([1000 + seed, 2]))
    return {"Xp": Xp, "Xt": Xt, "rp": rp, "yp": yp, "yt": yt, "isl_p": island(Xp) & (yp == 0), "isl_t": island(Xt) & (yt == 0), "path": np.asarray(path)}


def _syn_models(Xp, L, yp, rp):
    from sklearn.gaussian_process import GaussianProcessClassifier, GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import RBF, ConstantKernel, WhiteKernel
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        gpc = GaussianProcessClassifier(ConstantKernel(1.0, (0.05, 50)) * RBF([0.3, 0.3], (0.02, 5)), random_state=0).fit(Xp[L], yp[L])
        gpr = GaussianProcessRegressor(ConstantKernel(1.0, (0.05, 50)) * RBF([0.3, 0.3], (0.02, 5)) + WhiteKernel(0.01, (1e-4, 1)), normalize_y=True,
                                       random_state=0).fit(Xp[L], rp[L])
    return gpc, gpr


def run_syn(seed, arm, planted=False):
    """planted=True: the first post-start query of EVERY arm is the island pool point nearest the island centre (the
    experimental condition 'a surprising observation has been purchased'); otherwise the arms choose freely."""
    w = syn_world(seed); Xp, yp, rp = w["Xp"], w["yp"], w["rp"]; ids = np.array([f"s{i:04d}" for i in range(len(Xp))])
    rng = np.random.default_rng(7000 + seed * 13 + SYN_ARMS.index(arm))
    L = [int(i) for i in w["path"][:SYN_START]]; sd = SDState(); evals = []; t0 = time.time()
    isl_idx = np.flatnonzero(w["isl_p"] & ~np.isin(np.arange(len(Xp)), L))
    plant = int(isl_idx[np.argmin(np.linalg.norm(Xp[isl_idx] - Xp[isl_idx].mean(0), axis=1))]) if (planted and len(isl_idx)) else None
    use_gpr = arm in ("STRADDLE", "SD_STRADDLE")
    for b in range(SYN_START, SYN_END + 1):
        one_class = len(set(yp[L].tolist())) < 2
        if one_class:
            n1, n = int(yp[L].sum()), len(L); pc = (n1 + 0.5) / (n + 1)
            p_t = np.full(len(w["Xt"]), pc); pfun = lambda X: np.full(len(X), pc)
        else:
            gpc, gpr = _syn_models(Xp, L, yp, rp)
            if use_gpr:
                from scipy.stats import norm
                def pfun(X):
                    m, s = gpr.predict(X, return_std=True); return norm.cdf(m / np.maximum(s, 1e-9))
            else:
                pfun = lambda X: gpc.predict_proba(X)[:, 1]
            p_t = pfun(w["Xt"])
        evals.append({"budget": b, "p": p_t.astype(np.float32).tolist(), "paid_island": int(w["isl_p"][L].sum())})
        if b == SYN_END:
            break
        unpaid = np.setdiff1d(np.arange(len(Xp)), L)
        nxt = sd.next_local(Xp, unpaid, ids) if arm.startswith("SD_") else None
        if plant is not None and b == SYN_START:
            nxt = plant; sd.last_local = False
        elif nxt is not None:
            sd.last_local = True
        elif one_class:
            nxt = int([i for i in w["path"] if i not in set(L)][0]); sd.last_local = False
        elif arm == "RANDOM":
            nxt = int(rng.choice(unpaid)); sd.last_local = False
        elif use_gpr:
            m, s = gpr.predict(Xp[unpaid], return_std=True); nxt = int(unpaid[np.argmax(1.96 * s - np.abs(m))]); sd.last_local = False
        else:
            p = gpc.predict_proba(Xp[unpaid])[:, 1]; nxt = int(unpaid[np.argmin(np.abs(p - 0.5))]); sd.last_local = False
        p_before = float(pfun(Xp[[nxt]])[0]); p_obs = p_before if yp[nxt] == 1 else 1 - p_before
        L.append(nxt)
        if arm.startswith("SD_"):
            sd.observe(nxt, p_obs, b + 1)
    return {"part": "synthetic_planted" if planted else "synthetic", "seed": seed, "arm": arm, "paid": L, "evals": evals, "sd_log": sd.log,
            "seconds": time.time() - t0, "n_island_pool": int(w["isl_p"].sum()), "planted_index": plant, "status": "ok"}


# ======================================================================================== real replay (frozen Week 18 learners)
def run_real(task, arm, deadline=None):
    import src.week18_engine as E
    X, y, ids, pool, A = task["X"], task["y"], task["ids"], task["pool"], task["A"]
    std = SMM.standardizer(task)[0]; Z = np.zeros((len(X), 4)); Z[pool] = std(X[pool]); Z[task["test"]] = std(X[task["test"]])
    e1 = arm in ("E1_STRADDLE", "SD_STRADDLE"); learner = ("GPR_depth", "mlii") if e1 else ("G3", "mlii")
    rng = np.random.default_rng(9100 + 100 * task["repeat"] + task["fold"] + REAL_ARMS.index(arm))
    L = [int(i) for i in task["path"][:B_START]]; sd = SDState(); evals, steps = [], []; t0 = time.time(); status = "ok"
    for b in range(B_START, B_END + 1):
        if deadline is not None and time.time() > deadline:
            status = f"TIME_LIMIT at B{b}"; break
        Lr = np.asarray(L); usable = np.isfinite(A[Lr]) & (A[Lr] > 0) if e1 else np.ones(len(Lr), bool)
        one_class = len(set(y[Lr][usable].tolist())) < 2
        ts = time.time()
        if one_class:
            n1, n = int(y[Lr][usable].sum()), int(usable.sum()); pc = (n1 + 0.5) / (n + 1)
            pfun = lambda Xq: np.full(len(Xq), pc); f = None
        else:
            y_m = np.full(len(y), -1, int); y_m[Lr] = y[Lr]
            d_m = np.full(len(y), np.nan)
            if e1:
                d_m[Lr] = A[Lr]
            mt = {"X": X, "y": y_m, "pool": pool, "prior": np.array([], int), "depth": d_m}
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                try:
                    f = E.fit_learner(learner, mt, L, None, {"kernel": None, "b0": len(L)})
                except Exception as ex:
                    status = f"fit_failed at B{b}: {type(ex).__name__}"; break
            pfun = lambda Xq: np.asarray(E.proba(f, Xq), float)
        evals.append({"budget": b, "p": pfun(X[task["test"]]).tolist(), "constant_predictor": bool(one_class)})
        steps.append({"budget": b, "fit_seconds": time.time() - ts, "one_class": bool(one_class)})
        if b == B_END:
            break
        unpaid = np.setdiff1d(pool, Lr)
        nxt = sd.next_local(Z, unpaid, ids) if arm.startswith("SD_") else None
        how = "local"
        if nxt is not None:
            sd.last_local = True
        else:
            sd.last_local = False
            if one_class:
                nxt = int([i for i in task["path"] if i not in set(L)][0]); how = "path_continuation"
            elif arm == "RANDOM":
                nxt = int(rng.choice(unpaid)); how = "random"
            elif e1:
                m, v = E.latent(f, X[unpaid]); nxt = int(unpaid[np.argmax(1.96 * np.sqrt(v) - np.abs(m))]); how = "straddle"
            else:
                nxt = int(unpaid[np.argmin(np.abs(pfun(X[unpaid]) - 0.5))]); how = "margin"
        p_before = float(pfun(X[[nxt]])[0]); p_obs = p_before if y[nxt] == 1 else 1 - p_before
        qc_ok = (not e1) or bool(np.isfinite(A[nxt]) and A[nxt] > 0)
        L.append(int(nxt)); steps[-1].update({"selected": str(ids[nxt]), "how": how})
        if arm.startswith("SD_"):
            sd.observe(nxt, p_obs, b + 1, qc_ok)
    return {"part": "real", "repeat": task["repeat"], "fold": task["fold"], "arm": arm, "paid": L, "paid_ids": [str(ids[i]) for i in L],
            "test_ids": [str(ids[i]) for i in task["test"]], "evals": evals, "steps": steps, "sd_log": sd.log, "status": status, "seconds": time.time() - t0}


# ======================================================================================== units and workers
def units(part):
    if part == "synthetic":
        return [(pt, s, a) for pt in ("synthetic", "synthetic_planted") for a in SYN_ARMS for s in SYN_SEEDS]
    return [("real", (r, f), a) for a in REAL_ARMS for r in REPEATS for f in FOLDS]


def unit_name(part, key, arm):
    if part == "synthetic":
        return f"SYN__s{key:02d}__{arm}"
    if part == "synthetic_planted":
        return f"SYNP__s{key:02d}__{arm}"
    return f"NEW__r{key[0]}_f{key[1]}__{arm}"


def work(argv=()):
    argv = list(argv); part = argv[argv.index("--part") + 1] if "--part" in argv else "synthetic"
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if not SMM._git("log", "--format=%H", "--", str(MANIFEST.relative_to(SMM.ROOT)).replace("\\", "/")):
        raise SystemExit("commit the SURPRISE manifest before any run")
    for c, h in man["code_sha256"].items():
        if SMM.sha256(SMM.ROOT / c) != h:
            raise SystemExit(f"{c} changed after the SURPRISE freeze")
    tasks = {(t["repeat"], t["fold"]): t for t in TA.build_tasks()} if part == "real" else None
    CACHE.mkdir(parents=True, exist_ok=True); locks = CACHE / "locks"; locks.mkdir(exist_ok=True)
    for pt, key, arm in units(part):
        name = unit_name(pt, key, arm); out = CACHE / f"{name}.json.gz"
        if out.exists():
            continue
        lock = locks / f"{name}.lock"
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            continue
        os.write(fd, str(os.getpid()).encode()); os.close(fd)
        try:
            t0 = time.time()
            res = run_syn(key, arm, planted=(pt == "synthetic_planted")) if pt.startswith("synthetic") else run_real(tasks[key], arm, deadline=t0 + UNIT_TIME_LIMIT_S)
            res.update({"study": STUDY, "unit": name, "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
            TA._atomic_write(out, res)
            print(json.dumps({"unit": name, "status": res["status"], "s": round(res["seconds"], 1)}), flush=True)
        finally:
            lock.unlink(missing_ok=True)


# ======================================================================================== evaluation (frozen with the manifest)
def _aud(curve):
    x = np.arange(len(curve), dtype=float); return float(np.trapezoid(curve, x) / max(1, len(curve) - 1))


def evaluate():
    import src.jdl_evaluate as EV
    import src.jdl_trained_al_eval as TE
    R = {}
    for p in sorted(CACHE.glob("*.json.gz")):
        r = json.loads(gzip.decompress(p.read_bytes())); R[r["unit"]] = r
    res = {"units_done": len(R), "synthetic": {}, "real": {}}
    rng = np.random.default_rng(20261016)
    # ---- synthetic: island recall curve and final test BA / island-region recall
    rows = []
    for (pt, s, a) in units("synthetic"):
        r = R.get(unit_name(pt, s, a))
        if r is None:
            continue
        w = syn_world(s); n_is = max(1, r["n_island_pool"])
        curve = np.array([e["paid_island"] for e in r["evals"]]) / n_is
        pt_ = np.asarray(r["evals"][-1]["p"]); d = pt_ >= 0.5
        ba = 0.5 * (np.mean(d[w["yt"] == 1]) + np.mean(~d[w["yt"] == 0]))
        isl_rec = float(np.mean(~d[w["isl_t"]])) if w["isl_t"].any() else np.nan
        first = next((e["budget"] for e in r["evals"] if e["paid_island"] > 0), None)
        rows.append({"condition": pt, "seed": s, "arm": a, "island_AUDC": _aud(curve), "island_found_end": float(curve[-1]), "first_island_hit_budget": first,
                     "test_BA_end": float(ba), "island_test_recall_end": isl_rec, "seconds": r["seconds"],
                     "surprises": int(sum(x["surprise"] for x in r["sd_log"]))})
    S = pd.DataFrame(rows)
    if len(S):
        for cond in ("synthetic", "synthetic_planted"):
            Sc = S[S.condition == cond]; res["synthetic"][cond] = {}
            for a in SYN_ARMS:
                res["synthetic"][cond][a] = Sc[Sc.arm == a].drop(columns=["condition", "seed", "arm"]).mean(numeric_only=True).round(4).to_dict()
            for cand, ref in (("SD_MARGIN", "MARGIN"), ("SD_STRADDLE", "STRADDLE"), ("SD_MARGIN", "RANDOM")):
                m = Sc[Sc.arm == cand].set_index("seed").join(Sc[Sc.arm == ref].set_index("seed"), rsuffix="_ref", how="inner")
                if len(m):
                    for k in ("island_AUDC", "test_BA_end", "island_test_recall_end"):
                        d = (m[k] - m[k + "_ref"]).to_numpy(float); d = d[np.isfinite(d)]
                        if not len(d):
                            continue
                        bs = [np.mean(rng.choice(d, len(d))) for _ in range(2000)]
                        res["synthetic"][cond][f"{cand}-{ref}:{k}"] = {"estimate": float(d.mean()), "lo": float(np.percentile(bs, 2.5)), "hi": float(np.percentile(bs, 97.5)), "n": len(d)}
    # ---- real replay: discovery of no-Keyhole, corner and short-K runs among paid queries; same-budget metrics
    _, F = TE.frame(); y, sk = F["y"], F["shortk"]; W = EV.boot_weights(y)
    VX = dict(zip(F["ids"], F["VX"])); Y = dict(zip(F["ids"], y)); SK = dict(zip(F["ids"], sk))
    tasks = {(t["repeat"], t["fold"]): t for t in TA.build_tasks()}
    drows, M = [], {}
    for (pt, key, a) in units("real"):
        r = R.get(unit_name(pt, key, a))
        if r is None:
            continue
        t = tasks[key]; pool_ids = [str(t["ids"][i]) for i in t["pool"]]
        n_neg = sum(Y[s] == 0 for s in pool_ids); n_cor = sum(VX[s] > SMM.FAST_VX for s in pool_ids); n_sk = sum(bool(SK[s]) for s in pool_ids)
        paid = r["paid_ids"]
        cn = [sum(Y[s] == 0 for s in paid[:b]) / max(1, n_neg) for b in range(B_START, len(paid) + 1)]
        cc = [sum(VX[s] > SMM.FAST_VX for s in paid[:b]) / max(1, n_cor) for b in range(B_START, len(paid) + 1)]
        cs = [sum(bool(SK[s]) for s in paid[:b]) / max(1, n_sk) for b in range(B_START, len(paid) + 1)]
        half = next((B_START + i for i, v in enumerate(cn) if v >= 0.5), None)
        drows.append({"repeat": key[0], "fold": key[1], "arm": a, "status": r["status"], "complete": len(paid) >= B_END,
                      "negatives_AUDC": _aud(cn), "corner_AUDC_EVALUATOR_ONLY": _aud(cc), "shortK_AUDC_EVALUATOR_ONLY": _aud(cs),
                      "negatives_found_B24": cn[min(8, len(cn) - 1)], "negatives_found_B40": cn[-1], "queries_to_half_negatives": half,
                      "surprises": int(sum(x["surprise"] for x in r["sd_log"])), "local_probes": int(sum(s.get("how") == "local" for s in r["steps"])),
                      "seconds": r["seconds"]})
    D = pd.DataFrame(drows)
    for a in REAL_ARMS:
        for rep in REPEATS:
            for b in (16, 24, 32, 40):
                per = []
                for f in FOLDS:
                    r = R.get(unit_name("real", (rep, f), a))
                    e = None if r is None else {x["budget"]: x for x in r["evals"]}.get(b)
                    if e is not None:
                        per.append((r["test_ids"], e["p"]))
                if len(per) == len(FOLDS):
                    pos = {s: i for i, s in enumerate(F["ids"])}; p = np.full(len(F["ids"]), np.nan)
                    for tid, q in per:
                        p[[pos[s] for s in tid]] = q
                    m = EV.wmetrics(p, np.ones(len(p), bool), y, sk, F["q20"][rep], F["fold"][rep], W)
                    M[(a, rep, b)] = {k: float(m[k][0]) for k in ("BA", "sensitivity", "specificity", "q20", "shortK_sensitivity", "AUC", "brier")}
                    M[(a, rep, b)]["shortK_caught"] = int(((p >= .5) & sk).sum()); M[(a, rep, b)]["shortK_total"] = int(sk.sum())
    res["real"]["metrics"] = {f"{a}|r{rep}|B{b}": v for (a, rep, b), v in M.items()}
    if len(D):
        res["real"]["discovery_mean"] = D.groupby("arm")[["negatives_AUDC", "corner_AUDC_EVALUATOR_ONLY", "shortK_AUDC_EVALUATOR_ONLY", "negatives_found_B24",
                                                          "negatives_found_B40", "surprises", "local_probes", "seconds"]].mean().round(4).to_dict(orient="index")
        for cand, ref in (("SD_MARGIN", "G3_MARGIN"), ("SD_STRADDLE", "E1_STRADDLE"), ("SD_MARGIN", "RANDOM")):
            m = D[D.arm == cand].set_index(["repeat", "fold"]).join(D[D.arm == ref].set_index(["repeat", "fold"]), rsuffix="_ref", how="inner")
            if len(m):
                d = (m["negatives_AUDC"] - m["negatives_AUDC_ref"]).to_numpy(); bs = [np.mean(rng.choice(d, len(d))) for _ in range(2000)]
                ba = [M.get((cand, rep, 40), {}).get("BA", np.nan) - M.get((ref, rep, 40), {}).get("BA", np.nan) for rep in REPEATS]
                skd = [M.get((cand, rep, 40), {}).get("shortK_caught", np.nan) - M.get((ref, rep, 40), {}).get("shortK_caught", np.nan) for rep in REPEATS]
                gain = float(d.mean()) > 0 and np.percentile(bs, 2.5) > 0
                harm = (np.nanmean(ba) < -0.02) or (np.nansum(skd) < -2)
                res["real"][f"{cand}-{ref}"] = {"negatives_AUDC_diff": float(d.mean()), "lo": float(np.percentile(bs, 2.5)), "hi": float(np.percentile(bs, 97.5)), "pairs": len(d),
                                                "BA_B40_diff_per_repeat": ba, "shortK_caught_B40_diff_per_repeat": skd,
                                                "verdict": "DISCOVERY GAIN (DEV)" if gain and not harm else "GAIN WITH GLOBAL HARM" if gain else "NO DISCOVERY GAIN ESTABLISHED"}
    OUT.mkdir(parents=True, exist_ok=True); (OUT / "results").mkdir(exist_ok=True)
    S.to_csv(OUT / "results" / "synthetic_per_seed.csv", index=False, lineterminator="\n"); D.to_csv(OUT / "results" / "real_discovery_per_trajectory.csv", index=False, lineterminator="\n")
    (OUT / "results" / "SURPRISE_RESULTS.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "real"} | {"real_keys": [k for k in res["real"] if k != "metrics"]}, indent=1, default=str)[:4000])
    return res


# ======================================================================================== validation
def validate():
    t0 = time.time(); checks, info = {}, {}
    try:
        s = SDState(); s.observe(5, 0.1, 17); s.observe(6, 0.5, 18); s.observe(7, 0.05, 19, qc_ok=False)
        checks["sd_trigger_threshold_and_qc"] = [x["surprise"] for x in s.log] == [True, False, False] and len(s.seeds) == 1
        Z = np.array([[0, 0], [1, 0], [0.1, 0], [5, 5.]]); ids = np.array(["a", "b", "c", "d"])
        s2 = SDState(); s2.seeds = [[0, 3]]
        checks["sd_local_is_nearest_unpaid"] = s2.next_local(Z, np.array([1, 2, 3]), ids) == 2 and s2.seeds[0][1] == 2
        s2.last_local = True; checks["sd_alternates_local_global"] = s2.next_local(Z, np.array([1, 3]), ids) is None
        a = run_syn(1, "SD_MARGIN"); b = run_syn(1, "SD_MARGIN")
        checks["synthetic_deterministic"] = a["paid"] == b["paid"] and len(a["paid"]) == SYN_END
        info["synthetic_seed1_SD_MARGIN"] = {"surprises": sum(x["surprise"] for x in a["sd_log"]), "island_paid_end": a["evals"][-1]["paid_island"], "n_island": a["n_island_pool"], "s": a["seconds"]}
        pm, pr = run_syn(1, "SD_MARGIN", planted=True), run_syn(1, "MARGIN", planted=True)
        checks["planted_point_identical_for_all_arms"] = pm["planted_index"] is not None and pm["paid"][SYN_START] == pr["paid"][SYN_START] == pm["planted_index"]
        checks["planted_surprise_triggers_local_probes"] = bool(pm["sd_log"] and pm["sd_log"][0]["surprise"])
        info["planted_seed1"] = {"SD_MARGIN_island_paid_end": pm["evals"][-1]["paid_island"], "MARGIN_island_paid_end": pr["evals"][-1]["paid_island"]}
        tasks = {(t["repeat"], t["fold"]): t for t in TA.build_tasks()}
        t = tasks[(3, 1)]; tt = time.time(); r1 = run_real(t, "SD_MARGIN"); info["real_unit_seconds_SD_MARGIN_r3f1"] = time.time() - tt
        checks["real_unit_runs"] = r1["status"] == "ok" and len(r1["paid"]) == B_END
        y2, A2 = t["y"].copy(), t["A"].copy(); hidden = np.setdiff1d(np.arange(len(y2)), r1["paid"]); y2[hidden] = 1 - y2[hidden]; A2[hidden] = 4000.0
        r2 = run_real({**t, "y": y2, "A": A2}, "SD_MARGIN")
        checks["hidden_outcomes_do_not_change_path_or_predictions"] = r1["paid"] == r2["paid"] and r1["evals"][-1]["p"] == r2["evals"][-1]["p"]
        old = SMM.FAST_VX; SMM.FAST_VX = 0.1
        try:
            r3 = run_real(t, "SD_MARGIN")
        finally:
            SMM.FAST_VX = old
        checks["selector_ignores_evaluator_corner"] = r3["paid"] == r1["paid"]
        t4 = tasks[(3, 4)]; tt = time.time(); r4 = run_real(t4, "G3_MARGIN"); info["real_unit_seconds_G3_r3f4"] = time.time() - tt
        checks["one_class_start_continues_on_frozen_path"] = r4["status"] == "ok" and r4["steps"][0]["one_class"] and r4["paid"][16] == int([i for i in t4["path"] if i not in set(t4["path"][:16])][0])
        ref = TA._read(TA.CACHE / "NEW__r4_f1__G3_MARGIN.json.gz")
        g = run_real(tasks[(4, 1)], "G3_MARGIN")
        checks["G3_MARGIN_reproduces_TRAINED_AL_r4f1"] = g["paid_ids"][:40] == ref["paid_ids"][:40]
        e = run_real(tasks[(4, 1)], "E1_STRADDLE"); refe = TA._read(TA.CACHE / "NEW__r4_f1__ACTIVE_E1_STRADDLE.json.gz")
        checks["E1_STRADDLE_reproduces_TRAINED_AL_r4f1"] = e["paid_ids"][:40] == refe["paid_ids"][:40]
    except Exception as ex:
        checks["selftest_completed"] = False; info["error"] = f"{type(ex).__name__}: {ex}"[:400]; info["traceback"] = traceback.format_exc()[-2500:]
    res = {"study": STUDY, "status": "PASS" if checks and all(checks.values()) else "FAIL", "checks": {k: bool(v) for k, v in checks.items()}, "info": info,
           "seconds": time.time() - t0, "module_sha256": SMM.sha256(SMM.ROOT / "src" / "jdl_surprise.py")}
    OUT.mkdir(parents=True, exist_ok=True)
    VALIDATION.write_text(json.dumps(res, indent=1, default=TA._default), encoding="utf-8")
    print(json.dumps({"status": res["status"], "checks": res["checks"], "info": {k: v for k, v in info.items() if k != "traceback"}}, indent=1, default=TA._default))
    if res["status"] != "PASS":
        raise SystemExit(1)


def write_manifest():
    val = json.loads(VALIDATION.read_text(encoding="utf-8"))
    if val["status"] != "PASS" or val["module_sha256"] != SMM.sha256(SMM.ROOT / "src" / "jdl_surprise.py"):
        raise SystemExit("SURPRISE validation must PASS with this module before the freeze")
    man = {"study": STUDY, "status": "FROZEN BEFORE ANY SURPRISE_DISCOVERY OUTCOME", "written_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "parent_commit": SMM._git("rev-parse", "HEAD"), "authorization": "owner request of 2026-10-16 (primary method question; Ioan's post-meeting task)",
           "rule": {"surprise_p": SURPRISE_P, "m_local": M_LOCAL, "alternation": "local:global 1:1 while a seed is active", "local": "nearest unpaid pool point to the seed (standardised log inputs)"},
           "synthetic": {"seeds": list(SYN_SEEDS), "pool": SYN_POOL, "test": SYN_TEST, "budgets": [SYN_START, SYN_END], "arms": list(SYN_ARMS),
                         "conditions": {"synthetic": "arms choose freely from the feature-only start",
                                        "synthetic_planted": "first post-start query of every arm = the island pool point nearest the island centre"}},
           "real": {"population": "NEW, DEV repeats 3-4, folds 1-5, frozen feature-only B16 starts", "budgets": [B_START, B_END], "arms": list(REAL_ARMS)},
           "unit_time_limit_s": UNIT_TIME_LIMIT_S, "validation": {"status": val["status"], "sha256": SMM.sha256(VALIDATION)},
           "code_sha256": {c: SMM.sha256(SMM.ROOT / c) for c in CODE}}
    MANIFEST.write_text(json.dumps(man, indent=1), encoding="utf-8")
    print(json.dumps({k: man[k] for k in ("status", "written_utc")}, indent=1))


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "evaluate"
    {"validate": validate, "manifest": write_manifest, "work": lambda: work(sys.argv[2:]), "evaluate": evaluate}[step]()
