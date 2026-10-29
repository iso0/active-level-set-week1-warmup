"""C1S DEV screen of decision-level stabilisers on the RECORDED C1C C1 + margin paths (no new GP fit, no new query).

DEV only (STD repeats 203-282 and the C1C RAND8 / LOCAL8 startups 283-322, all evaluated before). Every variant below is computed
from C1's OWN per-budget probabilities on C1's OWN path, so paid data, spend in simulations and the selector are identical to C1;
only the reported classifier at budget b changes. Nothing reads a test label except the evaluator (src.el_eval).
  C1        unchanged C1 + margin
  AVGk      b <= 24: p_b; b >= 25: mean of p over the last k budgets (k = 4 candidate; k = 2, 8 DEV sensitivity only)
  HYSTd     b >= 25: decision hysteresis, the 0.5 decision changes only when |p - 0.5| >= d/100 (d = 05 candidate; 02, 10 sensitivity)
  EVERY4    simple control "update less often": b >= 24: p at the last multiple-of-4 budget >= 24 (24, 28, ..., 60)
  FREEZE24  simple control "freeze at a fixed budget": b >= 24: p_24
  A         HA_LEAN + margin (reference, own path)
Excursion analysis: run lengths of wrong-side stays of test points after B24 (how long a harmful flip lasts before it reverts).
    python -m src.c1s_dev screen
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

import src.ea_cand_eval as CE
import src.el_eval as EV
import src.el_export as EX
import src.rc18_common as RC
import src.rc19_pool as P

OUT = RC.ROOT / "outputs" / "research_campaign_20261029" / "opus_c1_stability"
C1C = RC.ROOT / "outputs" / "research_campaign_20261026" / "opus_c1_confirmation"
B0 = 24


def variant(bs, Pm, kind):
    bs = np.asarray(bs, int); Pm = np.asarray(Pm, float); Q = Pm.copy(); ix = {int(b): i for i, b in enumerate(bs)}
    for i, b in enumerate(bs):
        if kind.startswith("AVG") and b > B0:
            k = int(kind[3:]); lo = max(0, i - k + 1); Q[i] = Pm[lo:i + 1].mean(0)
        elif kind == "EVERY4" and b >= B0:
            Q[i] = Pm[ix[B0 + 4 * ((b - B0) // 4)]]
        elif kind == "FREEZE24" and b >= B0:
            Q[i] = Pm[ix[B0]]
    if kind.startswith("HYST"):                    # decision hysteresis: keep the previous decision while |p - 0.5| < delta (b >= 25)
        dl = int(kind[4:]) / 100.0; dec = Pm[0] >= 0.5
        for i, b in enumerate(bs):
            cur = Pm[i] >= 0.5
            dec = cur if b <= B0 else np.where(np.abs(Pm[i] - 0.5) < dl, dec, cur)
            # the overridden points get a probability just on the decided side (|p - 0.5| < delta there, so LL / Brier change negligibly)
            Q[i] = np.where(dec == cur, Pm[i], np.where(dec, 0.5 + 1e-9, 0.5 - 1e-9))
    return Q


def s95(D, tau=0.95):
    T = D[(D.budget >= 24) & (D.budget <= 60)].copy(); T["short"] = np.maximum(0.0, tau - T.BA)
    return T.groupby(["system", "cluster", "learner"]).short.mean().reset_index().rename(columns={"short": f"S{int(round(tau * 100))}"})


def excursions(bs, Pm, y):
    """Lengths (in budgets) of wrong-side stays that start after B24 and end (revert) before 60; censored stays reported apart."""
    hat = Pm >= 0.5; corr = hat == (y == 1)[None, :]; m = np.asarray(bs) >= B0; C = corr[m]; out, cens = [], 0
    for i in range(C.shape[1]):
        run = 0; started = False
        for t in range(1, C.shape[0]):
            if C[t - 1, i] and not C[t, i]:
                run = 1; started = True
            elif started and not C[t, i]:
                run += 1
            elif started and C[t, i]:
                out.append(run); started = False; run = 0
        if started:
            cens += 1
    return out, cens


def load(sets, systems=("C1_own", "A_own")):
    E = {}
    for s in sets:
        E.update({k: v for k, v in EX.load(C1C / "exports" / s).items() if k[0] in systems})
    return E


def screen_set(E, M, label):
    V = {}
    for (sy, cond, c, l), (bs, Pm, ids) in E.items():
        if sy == "A_own":
            V[("A", cond, c, l)] = (bs, Pm, ids); continue
        V[("C1", cond, c, l)] = (bs, Pm, ids)
        for kind in ("AVG2", "AVG4", "AVG8", "HYST02", "HYST05", "HYST10", "EVERY4", "FREEZE24"):
            V[(kind, cond, c, l)] = (bs, variant(bs, Pm, kind), ids)
    D = EV.learner_rows(V, M.y); Ai = EV.aulc(D, ("system", "cluster", "learner"))
    late = D[D.budget.isin(range(24, 61))].groupby(["system", "cluster", "learner"])[["BA", "sens", "spec", "ll", "brier"]].mean().reset_index(); late["window"] = "B24_B60"
    Ai = pd.concat([Ai, late], ignore_index=True); Ei = EV.endpoints(D, ("system", "cluster", "learner")); Su = CE.sustained(D, ("system", "cluster", "learner"))
    S = s95(D).merge(s95(D, 0.93), on=["system", "cluster", "learner"])
    out = {"set": label, "learners": int(D[["cluster", "learner"]].drop_duplicates().shape[0]), "clusters": int(D.cluster.nunique()), "contrasts": {}}
    systems = ("AVG2", "AVG4", "AVG8", "HYST02", "HYST05", "HYST10", "EVERY4", "FREEZE24", "A")
    for x in systems:
        r = {}
        for col in ("S95", "S93"):
            r[f"d{col}"] = EV.cluster_diff(S, x, "C1", col)
        for w in ("B8_B24", "B8_B60", "B24_B60"):
            T = Ai[Ai.window == w]
            for col in ("BA", "sens", "spec"):
                r[f"d{col}_{w}"] = EV.cluster_diff(T, x, "C1", col)
        for tau in EV.TAUS:
            T = Ei[(Ei.target == tau) & (Ei.defined == True)].copy(); T["att"] = T.attained.astype(float); T["kp"] = T.kept.astype(float)  # noqa: E712
            r[f"rms_saving_{tau}"] = EV.cluster_diff(T, x, "C1", "rms", sign=-1.0); r[f"d_attain_{tau}"] = EV.cluster_diff(T, x, "C1", "att"); r[f"d_kept_{tau}"] = EV.cluster_diff(T, x, "C1", "kp")
            U = Su[Su.target == tau].copy(); U["s"] = U.sustained.astype(float); r[f"d_sustained_{tau}"] = EV.cluster_diff(U, x, "C1", "s")
        b60 = D[D.budget == 60]; X = b60[b60.system == x].set_index(["cluster", "learner"]); C = b60[b60.system == "C1"].set_index(["cluster", "learner"])
        r["FN_B60_mean"] = {"x": float((X.n1 - X.tp).mean()), "C1": float((C.n1 - C.tp).mean())}; r["FP_B60_mean"] = {"x": float((X.n0 - X.tn).mean()), "C1": float((C.n0 - C.tn).mean())}
        out["contrasts"][x] = r
    out["means"] = {sy: {"S95": float(S[S.system == sy].S95.mean()), "S93": float(S[S.system == sy].S93.mean()),
                         "BA_B8_B24": float(Ai[(Ai.window == "B8_B24") & (Ai.system == sy)].BA.mean()), "BA_B24_B60": float(Ai[(Ai.window == "B24_B60") & (Ai.system == sy)].BA.mean()),
                         "BA60": float(D[(D.budget == 60) & (D.system == sy)].BA.mean())} for sy in ("C1",) + systems}
    return out, D, S


def screen():
    M = P.manifest(); res = {}
    E = load(("main_s1", "main_s2")); r, D, S = screen_set(E, M, "STD 203-282"); res["STD"] = r
    # excursion lengths of C1 (wrong-side stays after B24)
    y_all = M.y.astype(int); runs, cens = [], 0
    for (sy, cond, c, l), (bs, Pm, ids) in E.items():
        if sy == "C1_own":
            o, ce = excursions(bs, Pm, y_all.reindex(ids).to_numpy(int)); runs += o; cens += ce
    runs = np.asarray(runs)
    res["excursions_C1"] = {"completed": int(len(runs)), "censored_at_60": int(cens), "length_share": {str(k): float(np.mean(runs == k)) for k in range(1, 9)},
                            "length_share_ge9": float(np.mean(runs >= 9)), "median": float(np.median(runs)), "share_le3": float(np.mean(runs <= 3))}
    for cond, sset in (("RAND8", "start_rand8"), ("LOCAL8", "start_local8")):
        r2, _, _ = screen_set(load((sset,)), M, cond); res[cond] = r2
    (OUT / "dev").mkdir(parents=True, exist_ok=True); (OUT / "dev" / "DEV_SCREEN.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    S.to_csv(OUT / "dev" / "dev_std_S.csv.gz", index=False, compression="gzip")
    return res


if __name__ == "__main__":
    if sys.argv[1] == "screen":
        r = screen()
        for k in ("STD", "RAND8", "LOCAL8"):
            print(k, json.dumps(r[k]["means"], indent=0, default=float)[:1500])
        print(json.dumps(r["excursions_C1"], indent=1))
