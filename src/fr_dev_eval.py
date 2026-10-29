"""FR DEV evaluation of GATE (PROTOCOL_FR_DEV.md, registered in c4edc59a before any DEV gate result). EVALUATOR ONLY.
Model effect at identical paid data: the gate weights of src.fr_gate (job fr-dev, recorded paths) are combined with the RECORDED C1 and
HA_LEAN probabilities of the same prefixes (EA validation / cand-DEV exports):
  path A: C1 = C1_on_A (cand-DEV: C1), A = A_own (cand-DEV: A);  path C: C1 = C1_own, A = A_on_C1
  GATE = w p_C1 + (1 - w) p_A,  AVG = (p_C1 + p_A) / 2
Per learner-path: BA-AULC windows; per cluster (STD repeat; block startup, per region) the mean over learners and paths; t bounds.
    python -m src.fr_dev_eval
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import src.el_eval as EV
import src.rc18_common as RC
import src.rc19_pool as P

OUT = RC.ROOT / "outputs" / "research_campaign_20261029" / "opus_final_robustness"
EA = RC.ROOT / "outputs" / "research_campaign_20261026" / "opus_error_attribution" / "exports"
WINS = {"B8_B24": tuple(range(8, 25)), "B25_B60": tuple(range(25, 61)), "B8_B60": tuple(range(8, 61))}
SYSTEMS = ("C1", "A", "GATE", "AVG")
CONDS = {"STD": ("STD",), "K5": ("K5",), "K4": ("K4",), "GEOMETRIC": ("K5", "K4")}


def _npz(name):
    z = np.load(EA / name / "predictions_f32.npz"); keys = [str(k) for k in z["keys"]]; return z, {k: i for i, k in enumerate(keys)}


def recorded(cond, cl, l, tag, cache):
    if tag == "A":
        src = ("cand_dev_k5" if cond == "K5" and cl <= 40 else "cand_dev_k4" if cond == "K4" and cl <= 24 else f"validation_{cond.lower()}")
        s1, s2 = ("C1", "A") if src.startswith("cand") else ("C1_on_A", "A_own")
    else:
        src = f"validation_{cond.lower()}"; s1, s2 = "C1_own", "A_on_C1"
    if src not in cache:
        cache[src] = _npz(src)
    z, ix = cache[src]; i1, i2 = ix[f"{s1}|{cond}|{cl}|{l}"], ix[f"{s2}|{cond}|{cl}|{l}"]
    t1 = z[f"test_ids_{i1}"].astype(str)
    if not np.array_equal(t1, z[f"test_ids_{i2}"].astype(str)):
        raise RuntimeError("recorded systems do not share the test set")
    return np.asarray(z[f"pred_{i1}"], float), np.asarray(z[f"pred_{i2}"], float), t1


def load(M):
    E, GT, cache = {}, [], {}
    for f in sorted((OUT / "fr-dev" / "units").glob("*.json.gz")):
        u = RC.read_json_gz(f); c, cl, l, tag = u["condition"], int(u["cluster"]), int(u["learner"]), u["path"]
        p1, p2, ids = recorded(c, cl, l, tag, cache)
        if list(ids) != list(u["test_ids"]):
            raise RuntimeError(f"{f.name}: test set differs from the recorded export")
        if [e["budget"] for e in u["evals"]] != list(range(8, 61)):
            raise RuntimeError(f"{f.name}: budgets")
        W = np.array([e["w_test"] for e in u["evals"]], float); bs = np.arange(8, 61)
        lk = l * 10 + (1 if tag == "A" else 2)                      # learner-path key: learner x path
        E[("C1", c, cl, lk)] = (bs, p1, ids); E[("A", c, cl, lk)] = (bs, p2, ids)
        E[("GATE", c, cl, lk)] = (bs, W * p1 + (1 - W) * p2, ids); E[("AVG", c, cl, lk)] = (bs, 0.5 * p1 + 0.5 * p2, ids)
        for g in u["gates"]:
            GT.append({"condition": c, "cluster": cl, "learner": l, "path": tag, **{k: g.get(k) for k in ("b", "status", "a", "c", "oof_ll_C1", "oof_ll_A", "oof_ba_C1", "oof_ba_A", "n_disagree", "u_min", "u_max", "cpu_s")}})
        for j, b in enumerate(bs):
            GT.append({"condition": c, "cluster": cl, "learner": l, "path": tag, "b": int(b), "status": "w_test", "w_mean": float(W[j].mean()), "w_min": float(W[j].min())})
    return E, pd.DataFrame(GT)


def hard(E, M):
    sk = M.shortK_NEW_original.astype(bool); cn = (M.source_batch == "NEW") & (M.y == 0); rows = []
    for (sy, c, cl, lk), (bs, Pm, ids) in E.items():
        a = sk.reindex(ids).to_numpy(bool); z = cn.reindex(ids).to_numpy(bool); hat = np.asarray(Pm) >= 0.5
        for wn, ws in (("B8_B60", WINS["B8_B60"]), ("B25_B60", WINS["B25_B60"])):
            j = np.isin(bs, ws)
            rows.append({"system": sy, "condition": c, "cluster": cl, "learner": lk, "window": wn,
                         "shortK_NEW_recall": float(hat[j][:, a].mean()) if a.any() else np.nan, "NEW_cond_spec": float((~hat[j][:, z]).mean()) if z.any() else np.nan})
    return pd.DataFrame(rows)


def aulc(D):
    out = []
    for wn, ws in WINS.items():
        a = D[D.budget.isin(ws)].groupby(["system", "condition", "cluster", "learner"])[["BA", "sens", "spec", "ll", "brier"]].mean().reset_index(); a["window"] = wn; out.append(a)
    return pd.concat(out, ignore_index=True)


def contrast(Ai, conds, win, x, a, col="BA"):
    T = Ai[(Ai.window == win) & Ai.condition.isin(conds)]
    X_ = T[T.system == x].set_index(["condition", "cluster", "learner"])[col]; A_ = T[T.system == a].set_index(["condition", "cluster", "learner"])[col]
    d = (X_ - A_).dropna(); cm = d.groupby(level=[0, 1]).mean(); r = EV.tstats(cm.values); r.update(EV.boot(cm.values)); r["clusters"] = int(len(cm)); r["learner_paths"] = int(len(d)); return r


def run():
    RC.limit_threads(1); M = P.manifest(); E, GT = load(M); D = EV.learner_rows(E, M.y); Ai = aulc(D); H = hard(E, M)
    res = {"protocol": "PROTOCOL_FR_DEV.md (registered c4edc59a before any DEV gate result)", "evidence": "DEV (recorded paths; model effect at identical paid data)",
           "learner_paths": {c: int(Ai[(Ai.window == "B8_B60") & (Ai.system == "C1") & Ai.condition.isin(cs)].shape[0]) for c, cs in CONDS.items()}, "levels": {}, "contrasts": {}, "hard": {}}
    for c, cs in CONDS.items():
        for wn in WINS:
            T = Ai[(Ai.window == wn) & Ai.condition.isin(cs)]
            res["levels"][f"{c}|{wn}"] = {sy: float(T[T.system == sy].groupby(["condition", "cluster"]).BA.mean().mean()) for sy in SYSTEMS}
            res["contrasts"][f"{c}|{wn}"] = {f"{x}-{a}": contrast(Ai, cs, wn, x, a) for x, a in (("GATE", "C1"), ("AVG", "C1"), ("A", "C1"), ("GATE", "AVG"), ("GATE", "A"))}
        for wn in ("B8_B60",):
            res["contrasts"][f"{c}|{wn}|logloss"] = {f"{x}-{a}": contrast(Ai, cs, wn, x, a, "ll") for x, a in (("GATE", "C1"), ("AVG", "C1"))}
            res["contrasts"][f"{c}|{wn}|keyhole_recall"] = {f"{x}-{a}": contrast(Ai, cs, wn, x, a, "sens") for x, a in (("GATE", "C1"), ("AVG", "C1"))}
            res["contrasts"][f"{c}|{wn}|conduction_recall"] = {f"{x}-{a}": contrast(Ai, cs, wn, x, a, "spec") for x, a in (("GATE", "C1"), ("AVG", "C1"))}
        for wn in ("B8_B60", "B25_B60"):
            T = H[(H.window == wn) & H.condition.isin(cs)]
            res["hard"][f"{c}|{wn}"] = {sy: {k: float(T[T.system == sy].groupby(["condition", "cluster"])[k].mean().mean()) for k in ("shortK_NEW_recall", "NEW_cond_spec")} for sy in SYSTEMS}
    F = GT[GT.status == "fit"]; W_ = GT[GT.status == "w_test"]
    res["gate_fits"] = {c: {"fits": int(len(F[F.condition.isin(cs)])), "insufficient": int(len(GT[(GT.status == "insufficient") & GT.condition.isin(cs)])),
                            "a_mean": float(F[F.condition.isin(cs)].a.mean()), "c_mean": float(F[F.condition.isin(cs)].c.mean()),
                            "oof_ll_C1_minus_A": float((F[F.condition.isin(cs)].oof_ll_C1 - F[F.condition.isin(cs)].oof_ll_A).mean()),
                            "w_test_mean_B8_B24": float(W_[W_.condition.isin(cs) & (W_.b <= 24)].w_mean.mean()), "w_test_mean_B25_B60": float(W_[W_.condition.isin(cs) & (W_.b >= 25)].w_mean.mean()),
                            "gate_cpu_s_mean_per_fit": float(F[F.condition.isin(cs)].cpu_s.mean())} for c, cs in CONDS.items()}
    ct = res["contrasts"]; geo = ct["GEOMETRIC|B8_B60"]["GATE-C1"]; ea = ct["STD|B8_B24"]["GATE-C1"]; la = ct["STD|B25_B60"]["GATE-C1"]
    res["rule"] = {"C_GEO": geo, "C_GEO_pass": bool(geo["mean"] >= 0.010 and geo["lcb"] > 0), "C_EARLY": ea, "C_EARLY_pass": bool(ea["lcb"] >= -0.003),
                   "C_LATE": la, "C_LATE_pass": bool(la["lcb"] >= -0.003)}
    r = res["rule"]; r["decision"] = ("CARRY_TO_FRESH_TEST" if r["C_GEO_pass"] and r["C_EARLY_pass"] and r["C_LATE_pass"] else
                                     "CLOSE: paid-only gate does not capture the gain area (C-GEO)" if not r["C_GEO_pass"] else "CLOSE: harm (C-EARLY / C-LATE)")
    d = OUT / "dev"; d.mkdir(parents=True, exist_ok=True)
    Ai.to_csv(d / "dev_aulc.csv.gz", index=False, compression="gzip"); GT.to_csv(d / "dev_gates.csv.gz", index=False, compression="gzip"); H.to_csv(d / "dev_hard.csv.gz", index=False, compression="gzip")
    (d / "DEV_GATE.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8"); return res


if __name__ == "__main__":
    r = run(); print(json.dumps(r["rule"], indent=1, default=float)); print(json.dumps(r["levels"], indent=1)); print(json.dumps(r["gate_fits"], indent=1))
