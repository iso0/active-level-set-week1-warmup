"""EL stage 2 (PROTOCOL_EL2_MECHANISM.md, registered before any evaluation): system E = HA_LEAN selects (margin, A's path) /
evidence-weighted HA_LEAN + HA_TREND mixture predicts.
The emulator choice e in {L: HA_LEAN constant-mean depth GP, T: HA_TREND trend depth GP} is one more discrete hyperparameter of the
SAME evidence rule HA_LEAN uses for its grid g = (tau_F, tau_h): w_{e,g} ~ exp(log Z_{e,g}) (uniform prior; log Z = Laplace log marginal
likelihood of the paid labels for the learned-regularisation classifier on [z_h, F_e]); p_E = sum_{e,g} w_{e,g} sigmoid(m_{e,g}) =
W_L p_L + W_T p_T, with p_L / p_T exactly HA_LEAN / HA_TREND. Paid observations only; no budget rule, no OLD/NEW, no test labels.
    python -m src.el_mix work el-mix-dev | el-mix-fwd | el-mix-smoke ;  python -m src.el_mix dev | final
"""
from __future__ import annotations

import json
import sys
import time
import warnings

import numpy as np
from scipy.special import expit

import src.el_cross as X
import src.rc18_common as RC
import src.rc19_learn as LN
import src.rc19_pool as P
import src.rc19b_keyhole as K
import src.rc20_attr as A
import src.rc21_phr as PH
import src.rc22_common as C22
import src.rc23_common as C23
import src.rc24_pac as PC

OUT = X.OUT; BUD = tuple(range(8, 61))
DEV_STD = tuple(range(51, 59)) + tuple(range(67, 123)); DEV_K5 = tuple(range(1, 33)); DEV_K4 = tuple(range(1, 17))
FWD_STD = tuple(range(123, 163)); FWD_K5 = tuple(range(33, 41)); FWD_K4 = tuple(range(17, 25))


def fam_ev(Ftr, htr, y, Fev, hev):
    """src.rc22_common.phr_family(Ftr, htr, y, Fev, hev, feats=(0,)) verbatim, also returning the 16 Laplace log evidences."""
    Xtr = np.c_[htr, Ftr[:, [0]]]; Xev = np.c_[hev, Fev[:, [0]]]
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-12; Htr, Hev = (Xtr - mu) / sd, (Xev - mu) / sd; y = np.asarray(y, float)
    Utr, Uev = np.zeros((len(Htr), 1)), np.zeros((len(Hev), 1)); Gtt = PH.Gram(Htr, Htr, Utr, Utr); Get = PH.Gram(Hev, Htr, Uev, Utr)
    kss_h = Hev[:, 0] ** 2; kss_F = np.sum(Hev[:, 1:] ** 2, 1); cfg = [(tf, th) for tf in PH.TAU_F for th in PH.TAU_H]
    logw = np.empty(len(cfg)); Mm = np.empty((len(cfg), len(Hev)))
    for g, (tf, th) in enumerate(cfg):
        mode = PH.laplace(Gtt.K(tf, th, 0.0, None), y); kss = PH.V0 + th ** 2 * kss_h + tf ** 2 * kss_F
        Mm[g], _, _ = PH.predictive(mode, Get.K(tf, th, 0.0, None), kss, plugin=True); logw[g] = mode["logZ"]
    w = np.exp(logw - logw.max()); w /= w.sum()
    return w @ expit(Mm), logw


def mix_state(task, rev, Z, rows):
    y_p = rev.paid_y(); A_p = rev.paid_A(); L = rev.paid; y = y_p[L]; usable = np.isfinite(A_p[L])
    if len(set(y_p[L][usable].tolist())) < 2:                     # HA_LEAN / HA_TREND one-class rule (shared)
        c = np.full(len(rows), float(np.mean(y))); return {"p_L": c, "p_T": c, "p_E": c, "W_T": None, "logZ_L": None, "logZ_T": None, "one_class": True, "cpu_L": 0.0, "cpu_T": 0.0}
    h = A.hcol(task)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        t0 = time.process_time(); R1 = A.cf(Z, rev, C23.DEPTH, "SHQ", rows, A.KF); pL, lwL = fam_ev(R1["F"], h[L], y, R1["E"], h[rows]); cL = time.process_time() - t0
        t1 = time.process_time(); R2 = PC.cf_phys(task, rev, Z, rows); pT, lwT = fam_ev(R2["F"], h[L], y, R2["E"], h[rows]); cT = time.process_time() - t1
    lw = np.r_[lwL, lwT]; W = np.exp(lw - lw.max()); W /= W.sum(); WL, WT = float(W[:16].sum()), float(W[16:].sum())
    return {"p_L": pL, "p_T": pT, "p_E": WL * pL + WT * pT, "W_T": WT, "logZ_L": lwL.tolist(), "logZ_T": lwT.tolist(), "one_class": False, "cpu_L": cL, "cpu_T": cT}


def mix_on_path(task, paid_ids, M, budgets=BUD):
    Z = P.zstd(task); pos = {s: i for i, s in enumerate(task["ids"])}; paid = [pos[s] for s in paid_ids]; rows = np.asarray(task["test"]); ev = []
    for b in budgets:
        rev = K._rev_with(task, M, paid[:b]); s = mix_state(task, rev, Z, rows)
        ev.append({"budget": b, "p_L": LN._f32(s["p_L"]), "p_T": LN._f32(s["p_T"]), "p_E": LN._f32(s["p_E"]), "W_T": s["W_T"], "logZ_L": s["logZ_L"], "logZ_T": s["logZ_T"],
                   "one_class": s["one_class"], "cpu_L": s["cpu_L"], "cpu_T": s["cpu_T"]})
    return ev


def _mx(a, b):
    return float(np.max(np.abs(np.asarray(a, float) - np.asarray(b, float))))


def dev_path(cond, r, f):
    """Recorded HA_LEAN path unit and the recorded A and D predictions {budget: p} available for the checks."""
    fwd = (cond == "STD" and r >= 83) or (cond == "K5" and r >= 25) or (cond == "K4" and r >= 9)
    if fwd:
        u = RC.read_json_gz(OUT / "el-fwd" / "units" / (f"STD__r{r}_f{f}__L.json.gz" if cond == "STD" else f"{cond}__s{r}_b{f}__L.json.gz"))
        return u, {e["budget"]: e["p"]["HA_LEAN"] for e in u["evals"]}, {e["budget"]: e["p"]["HA_TREND"] for e in u["cross"]["evals"]}
    fa, ka = X.own_path(cond, r, f, "L"); u = RC.read_json_gz(fa); a = {e["budget"]: e["p"][ka] for e in u["evals"]}
    fd, kd, every = X.existing_D(cond, r, f); d = {e["budget"]: e["p"][kd] for e in RC.read_json_gz(fd)["evals"]}
    if not every:
        for e in RC.read_json_gz(OUT / "el-cross" / "units" / f"D__{cond}__r{r}_f{f}.json.gz")["evals"]:
            d.setdefault(e["budget"], e["p"]["HA_TREND"])
    return u, a, d


def units(job):
    if job == "el-mix-dev":
        return ([(f"STD__r{r}_f{f}", ("dev", "STD", r, f)) for r in DEV_STD for f in range(1, 6)]
                + [(f"K5__s{s}_b{b}", ("dev", "K5", s, b)) for s in DEV_K5 for b in range(1, 6)]
                + [(f"K4__s{s}_b{b}", ("dev", "K4", s, b)) for s in DEV_K4 for b in range(1, 5)])
    if job == "el-mix-fwd":
        return ([(f"STD__r{r}_f{f}", ("fwd", "STD", r, f)) for r in FWD_STD for f in range(1, 6)]
                + [(f"K5__s{s}_b{b}", ("fwd", "K5", s, b)) for s in FWD_K5 for b in range(1, 6)]
                + [(f"K4__s{s}_b{b}", ("fwd", "K4", s, b)) for s in FWD_K4 for b in range(1, 5)])
    if job == "el-mix-smoke":
        return [("STD__r1_f1", ("fwd", "STD", 1, 1))]
    raise ValueError(job)


def work(job):
    RC.limit_threads(1); U = units(job); M = P.manifest(); S = dict(U); C22.set_manifest(M)
    if job == "el-mix-fwd":
        import src.el2_freeze as FR
        FR.check(job)
    T = X.tasks_for({n: (None, c, r, f) for n, (k, c, r, f) in S.items()}, M)

    def fn(name):
        kind, c, r, f = S[name]; task = T[(c, r, f)]
        if kind == "dev":
            u, a, d = dev_path(c, r, f)
            if list(u["test_ids"]) != [task["ids"][i] for i in task["test"]]:
                raise RuntimeError("recorded test set differs from the task")
            ev = mix_on_path(task, u["paid_ids"][:60], M)
            cA = max(_mx(e["p_L"], a[e["budget"]]) for e in ev); cD = max(_mx(e["p_T"], d[e["budget"]]) for e in ev if e["budget"] in d)
            return {"kind": "dev", "condition": c, "repeat": r, "fold": f, "selects": "HA_LEAN", "paid_ids": u["paid_ids"][:60], "test_ids": u["test_ids"], "evals": ev,
                    "check_pL_vs_recorded_A_maxabs": cA, "check_pT_vs_recorded_D_maxabs": cD, "check_D_budgets": len([e for e in ev if e["budget"] in d])}
        bmax = 14 if job == "el-mix-smoke" else 60
        u = C23.run_arm(task, "HA_LEAN", M, bmax=bmax); ev = mix_on_path(task, u["paid_ids"][:bmax], M, budgets=tuple(range(8, bmax + 1)))
        cA = max(_mx(e["p_L"], o["p"]["HA_LEAN"]) for e, o in zip(ev, u["evals"]))
        return {"kind": "fwd", "condition": c, "repeat": r, "fold": f, "selects": "HA_LEAN", "paid_ids": u["paid_ids"], "test_ids": u["test_ids"], "own_evals": u["evals"],
                "evals": ev, "check_pL_vs_own_A_maxabs": cA, "own_cpu_s": u["cpu_s"]}
    d = OUT / job
    RC.run_units([n for n, _ in U], fn, d / "units", d / "locks", d / "failed", log=lambda s: print(s, flush=True))


# ======================================================================================== evaluation (A, D, E on the HA_LEAN path)
def load(job, cond):
    E, CPU, W, CHK = {}, [], [], []
    for fp in sorted((OUT / job / "units").glob(f"{cond}__*.json.gz")):
        u = RC.read_json_gz(fp); c, l = int(u["repeat"]), int(u["fold"]); ids = np.asarray(u["test_ids"], str); ev = u["evals"]
        bs = np.array([e["budget"] for e in ev], int)
        if not np.array_equal(bs, np.arange(8, 61)):
            raise RuntimeError(f"{fp.name}: budgets are not 8..60")
        for sy, k in (("A", "p_L"), ("D", "p_T"), ("E", "p_E")):
            E[(sy, cond, c, l)] = (bs, np.array([e[k] for e in ev], float), ids)
        sel = range(52)
        stepA = [u["own_evals"][i]["cpu_s"] for i in sel] if "own_evals" in u else [ev[i]["cpu_L"] for i in sel]
        CPU.append({"cluster": c, "learner": l, "A": float(np.mean(stepA)), "D": float(np.mean(stepA) + np.mean([ev[i]["cpu_T"] for i in sel])),
                    "E": float(np.mean(stepA) + np.mean([ev[i]["cpu_T"] for i in sel]))})
        for e in ev:
            W.append({"cluster": c, "learner": l, "budget": e["budget"], "W_T": e["W_T"]})
        CHK.append({"cluster": c, "learner": l, "pL_vs_A": u.get("check_pL_vs_recorded_A_maxabs", u.get("check_pL_vs_own_A_maxabs")), "pT_vs_D": u.get("check_pT_vs_recorded_D_maxabs", np.nan)})
    import pandas as pd
    return E, pd.DataFrame(CPU), pd.DataFrame(W), pd.DataFrame(CHK)


def evaluate(job, cond, M):
    import src.el_eval as EV
    E, CPU, W, CHK = load(job, cond)
    D = EV.learner_rows(E, M.y); G = EV.pooled_rows(E, M.y); Ai = EV.aulc(D, ("system", "cluster", "learner")); Ap = EV.aulc(G, ("system", "cluster"))
    Ei = EV.endpoints(D, ("system", "cluster", "learner")); Ep = EV.endpoints(G, ("system", "cluster")); S = EV.summary_by_system(D, Ai, Ei, G, Ap, Ep)
    con = {x: EV.contrast_table(Ai, Ei, x, "A") for x in ("D", "E")}; conED = EV.contrast_table(Ai, Ei, "E", "D")
    bat = {x: EV.ba_at(D, x, "A") for x in ("D", "E")}
    wt = W.dropna(subset=["W_T"]).groupby("budget").W_T.agg(mean="mean", median="median", share_T_majority=lambda s: float((s > 0.5).mean()))
    reg = None
    if cond != "STD":
        Td = Ai[Ai.window == "B8_B60"].dropna(subset=["BA"]); R = Td.groupby(["system", "cluster"]).BA.mean()
        reg = {x: EV.tstats((R.loc[x] - R.loc["A"]).dropna().values) for x in ("D", "E")}
    return {"E": E, "D": D, "G": G, "Ai": Ai, "Ap": Ap, "Ei": Ei, "Ep": Ep, "S": S, "con": con, "conED": conED, "bat": bat, "W": wt, "CPU": CPU, "CHK": CHK, "reg": reg}


def entry_rule(r):
    """PROTOCOL_EL2_MECHANISM.md section 3 (point estimates on DEV STD)."""
    cE, cD = r["con"]["E"], r["con"]["D"]; S = r["S"].set_index("system")
    kept = lambda s: int(S.loc[s, "kept_0.95"].split("/")[0]) / int(S.loc[s, "kept_0.95"].split("/")[1])
    c = {"early_gain_positive": cE["dBA_B8_B24"]["mean"] > 0, "rms_saving_0.93_positive": cE["rms_saving_0.93"]["mean"] > 0, "rms_saving_0.95_positive": cE["rms_saving_0.95"]["mean"] > 0,
         "attain_0.95_not_lower_by_0.025": bool(S.loc["E", "attain_rate_0.95"] >= S.loc["A", "attain_rate_0.95"] - 0.025), "kept_0.95_not_lower_by_0.025": bool(kept("E") >= kept("A") - 0.025),
         "better_than_D_at_0.95": cE["rms_saving_0.95"]["mean"] > cD["rms_saving_0.95"]["mean"]}
    c = {k: bool(v) for k, v in c.items()}; c["enters_confirmation"] = all(c.values()); return c


def dev():
    import pandas as pd
    M = P.manifest(); d = OUT / "el2_dev"; d.mkdir(parents=True, exist_ok=True); res = {}
    for cond in ("STD", "K5", "K4"):
        r = evaluate("el-mix-dev", cond, M)
        for nm in ("D", "Ai", "Ei", "S", "CPU", "CHK"):
            r[nm].to_csv(d / f"{cond.lower()}_{nm.lower()}.csv", index=False)
        r["W"].to_csv(d / f"{cond.lower()}_weights_by_budget.csv")
        res[cond] = {"learners": int(r["D"][["cluster", "learner"]].drop_duplicates().shape[0]), "clusters": int(r["D"].cluster.nunique()), "summary": r["S"].round(4).to_dict(orient="records"),
                     "contrasts_vs_A": r["con"], "E_vs_D": r["conED"], "BA_at_budgets_vs_A": r["bat"], "W_T_by_budget": r["W"].round(4).reset_index().to_dict(orient="records"),
                     "per_region_vs_A": r["reg"], "cpu_mean_per_step": r["CPU"][["A", "D", "E"]].mean().round(4).to_dict(),
                     "checks": {"pL_vs_recorded_A_maxabs": float(r["CHK"].pL_vs_A.max()), "pT_vs_recorded_D_maxabs": float(r["CHK"].pT_vs_D.max())}}
        if cond == "STD":
            res["entry_rule"] = entry_rule(r)
    (d / "EL2_DEV.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8"); return res


def final():
    import src.el_decide as DC
    M = P.manifest(); d = OUT / "el2_final"; d.mkdir(parents=True, exist_ok=True); res = {}; R = {}
    for cond in ("STD", "K5", "K4"):
        R[cond] = r = evaluate("el-mix-fwd", cond, M)
        for nm in ("D", "G", "Ai", "Ap", "Ei", "Ep", "S", "CPU", "CHK"):
            r[nm].to_csv(d / f"{cond.lower()}_{nm.lower()}.csv", index=False)
        r["W"].to_csv(d / f"{cond.lower()}_weights_by_budget.csv")
        res[cond] = {"learners": int(r["D"][["cluster", "learner"]].drop_duplicates().shape[0]), "clusters": int(r["D"].cluster.nunique()), "summary": r["S"].round(4).to_dict(orient="records"),
                     "contrasts_vs_A": r["con"], "E_vs_D": r["conED"], "BA_at_budgets_vs_A": r["bat"], "W_T_by_budget": r["W"].round(4).reset_index().to_dict(orient="records"),
                     "per_region_vs_A": r["reg"], "cpu_mean_per_step": r["CPU"][["A", "D", "E"]].mean().round(4).to_dict(),
                     "checks": {"pL_vs_own_A_maxabs": float(r["CHK"].pL_vs_A.max())}}
    std = R["STD"]
    res["decision"] = {"primary": DC.verdict(std["con"]["E"], std["CPU"], "E"), "secondary": {"D": DC.verdict(std["con"]["D"], std["CPU"], "D")},
                       "robustness_warning": {c: {x: {**R[c]["reg"][x], "warning": bool(np.isfinite(R[c]["reg"][x]["lcb"]) and R[c]["reg"][x]["lcb"] < DC.W_REG)} for x in ("D", "E")} for c in ("K5", "K4")}}
    (d / "EL2_FINAL_DECISION.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8"); return res


if __name__ == "__main__":
    if sys.argv[1] == "work":
        work(sys.argv[2])
    elif sys.argv[1] == "dev":
        r = dev(); print(json.dumps(r["entry_rule"], indent=1))
    elif sys.argv[1] == "final":
        r = final(); print(json.dumps(r["decision"]["primary"], indent=1, default=float)[:3000])
    elif sys.argv[1] == "list":
        print({j: len(units(j)) for j in ("el-mix-dev", "el-mix-fwd", "el-mix-smoke")})
