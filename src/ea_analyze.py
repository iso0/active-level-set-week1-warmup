"""EA study, stage 1 analysis of the rung ladder (PROTOCOL_EA_HYPOTHESES.md section 3). Test outcomes are read ONLY here.
Common rows: test rows with a recorded depth (one run in the pool has none). Windows: early = B8..B24 (every budget), late = B28..B60
(every 4). Individual learner = one (repeat / startup, fold / block); pooled = the learners of one cluster concatenated.
    python -m src.ea_analyze
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import src.el_eval as EV
import src.ea_diag as DG
import src.rc18_common as RC
import src.rc19_pool as P

OUT = DG.OUT / "diagnosis"
EARLY = tuple(b for b in DG.BUDS if b <= 24); LATE = tuple(b for b in DG.BUDS if b >= 28)
ORDER = ("R1b_L", "R2_L", "R3u", "R3", "R4", "R5")            # rung order for "first fix" transitions
CORNER = lambda M: ((M.VX > 0.85) & (M.P > 330))


def load(cond):
    rows = []; R6 = []
    for fp in sorted((DG.OUT / "ea-diag" / "units").glob(f"{cond}__*.json.gz")):
        u = RC.read_json_gz(fp); ids = np.asarray(u["test_ids"], str); ok = np.asarray(u["test_has_depth"], bool)
        for e in u["evals"]:
            for k, v in e["p"].items():
                rows.append((cond, u["repeat"], u["fold"], e["budget"], k, ids, ok, np.asarray(v, float), e.get("E_L"), e.get("E_T"), e["one_class"]))
        for k, v in u["R6"].items():
            R6.append((cond, u["repeat"], u["fold"], k, ids, ok, np.asarray(v, float)))
    return rows, R6


def confusion(p, y):
    hat = p >= 0.5; n1, n0 = int((y == 1).sum()), int((y == 0).sum()); tp = int((hat & (y == 1)).sum()); tn = int((~hat & (y == 0)).sum())
    return n1, n0, tp, tn


def tables(rows, M):
    y_of = M.y; recs = []; ex = []
    for (cond, r, f, b, k, ids, ok, p, EL, ET, one) in rows:
        idc = ids[ok]; y = y_of.reindex(idc).to_numpy(int); pc = p[ok]; n1, n0, tp, tn = confusion(pc, y)
        recs.append({"condition": cond, "cluster": r, "learner": f, "budget": b, "rung": k, "n1": n1, "n0": n0, "tp": tp, "tn": tn})
        ex.append((cond, r, f, b, k, idc, y, pc >= 0.5))
    D = pd.DataFrame(recs); D["sens"] = np.where(D.n1 > 0, D.tp / D.n1.clip(lower=1), np.nan); D["spec"] = np.where(D.n0 > 0, D.tn / D.n0.clip(lower=1), np.nan)
    D["BA"] = np.where((D.n1 > 0) & (D.n0 > 0), 0.5 * (D.sens + D.spec), np.nan)
    G = D.groupby(["condition", "cluster", "budget", "rung"])[["n1", "n0", "tp", "tn"]].sum().reset_index()
    G["sens"] = G.tp / G.n1; G["spec"] = G.tn / G.n0; G["BA"] = 0.5 * (G.sens + G.spec)
    return D, G, ex


def window_means(D, by):
    out = []
    for w, bs in (("early_B8_B24", EARLY), ("late_B28_B60", LATE)):
        a = D[D.budget.isin(bs)].groupby(list(by))[["BA", "sens", "spec"]].mean().reset_index(); a["window"] = w; out.append(a)
    return pd.concat(out, ignore_index=True)


def steps(Wi):
    """Paired rung steps on individual learners (cluster means; one-sided 95 % t bounds)."""
    S = {"test-time depth (R2_L - R0_L)": ("R2_L", "R0_L"), "training feature given true test depth (R3 - R2_L)": ("R3", "R2_L"),
         "attainable from inputs (R3u - R0_L)": ("R3u", "R0_L"), "not attainable from inputs with this emulator family (R3 - R3u)": ("R3", "R3u"),
         "true-depth total (R3 - R0_L)": ("R3", "R0_L"), "representation + transverse inputs (R4 - R3)": ("R4", "R3"),
         "flexible family over (h, a) (R5 - R3)": ("R5", "R3"), "trend emulator (R0_T - R0_L)": ("R0_T", "R0_L"),
         "trend emulator's test-time depth (R2_T - R0_T)": ("R2_T", "R0_T"), "in-sample training features (R1a_L - R0_L)": ("R1a_L", "R0_L"),
         "measured paid depth for training (R1b_L - R0_L)": ("R1b_L", "R0_L"), "true test depth after measured training (R3 - R1b_L)": ("R3", "R1b_L")}
    out = {}
    for w in Wi.window.unique():
        T = Wi[Wi.window == w].rename(columns={"rung": "system"})
        out[w] = {nm: {c: EV.cluster_diff(T, x, a, c) for c in ("BA", "sens", "spec")} for nm, (x, a) in S.items()}
    return out


def transitions(ex):
    """Per (learner, budget, test run): is R0_L wrong, and which rung (in ORDER) first gets it right; and R0_L-correct calls broken by R3."""
    idx = {}
    for (cond, r, f, b, k, ids, y, hat) in ex:
        idx[(cond, r, f, b, k)] = (ids, y, hat)
    recs = []
    for (cond, r, f, b, k), (ids, y, hat0) in idx.items():
        if k != "R0_L":
            continue
        corr = {kk: (idx[(cond, r, f, b, kk)][2] == y) for kk in ORDER}; c0 = hat0 == y
        first = np.full(len(y), "none", dtype=object)
        for kk in ORDER[::-1]:                                   # later assignment = earlier rung in ORDER -> the first rung that fixes it
            first = np.where(~c0 & corr[kk], kk, first)
        win = "early" if b <= 24 else "late"
        for i in range(len(y)):
            if not c0[i]:
                recs.append({"condition": cond, "cluster": r, "learner": f, "budget": b, "window": win, "sim_id": ids[i], "y": int(y[i]),
                             "error": "false_keyhole" if y[i] == 0 else "missed_keyhole", "first_fix": first[i], "fixed_by_R3": bool(corr["R3"][i]),
                             "fixed_by_R3u": bool(corr["R3u"][i]), "fixed_by_R2_L": bool(corr["R2_L"][i]), "fixed_by_R5": bool(corr["R5"][i]), "fixed_by_R4": bool(corr["R4"][i])})
            elif not corr["R3"][i]:
                recs.append({"condition": cond, "cluster": r, "learner": f, "budget": b, "window": win, "sim_id": ids[i], "y": int(y[i]),
                             "error": "R0_correct_R3_wrong", "first_fix": "-", "fixed_by_R3": False, "fixed_by_R3u": bool(corr["R3u"][i]),
                             "fixed_by_R2_L": bool(corr["R2_L"][i]), "fixed_by_R5": bool(corr["R5"][i]), "fixed_by_R4": bool(corr["R4"][i])})
    return pd.DataFrame(recs)


def emulator_error(rows, M, U):
    a_of = M.log_A_um; c_of = CORNER(M); recs = []
    for (cond, r, f, b, k, ids, ok, p, EL, ET, one) in rows:
        if k != "R0_L" or EL is None:
            continue
        idc = ids[ok]; a = a_of.reindex(idc).to_numpy(float); cr = c_of.reindex(idc).to_numpy(bool)
        for nm, E in (("HA_LEAN", np.asarray(EL, float)[ok]), ("HA_TREND", np.asarray(ET, float)[ok])):
            d = E - a
            for reg, m in (("corner", cr), ("rest", ~cr)):
                if m.any():
                    recs.append({"condition": cond, "cluster": r, "learner": f, "budget": b, "emulator": nm, "region": reg, "bias": float(d[m].mean()),
                                 "rmse": float(np.sqrt(np.mean(d[m] ** 2))), "n": int(m.sum())})
    Eg = pd.DataFrame(recs)
    a = M.log_A_um.to_numpy(float); u = U.reindex(M.index).to_numpy(float); ok = np.isfinite(a); cr = CORNER(M).to_numpy(bool)
    unl = {reg: {"bias": float((u - a)[ok & m].mean()), "rmse": float(np.sqrt(np.mean((u - a)[ok & m] ** 2))), "n": int((ok & m).sum())} for reg, m in (("corner", cr), ("rest", ~cr))}
    return Eg, unl


def interleaved_pairs(M):
    """Full pool (evaluator-only): runs whose nearest opposite-label neighbour in standardised (z_h, log A) is closer than their nearest
    same-label neighbour, with descriptors. Not read as unlearnable / random / label error."""
    lx = np.log(M[list(P.INPUTS)].to_numpy(float)); h = lx[:, 0] - 0.5 * lx[:, 1] - 1.5 * lx[:, 2]; a = M.log_A_um.to_numpy(float); y = M.y.to_numpy(int)
    ok = np.isfinite(a); H = np.c_[(h - h[ok].mean()) / h[ok].std(), (a - a[ok].mean()) / a[ok].std()]; idx = np.flatnonzero(ok); recs = []
    for i in idx:
        d = np.sqrt(np.sum((H[idx] - H[i]) ** 2, 1)); d[idx == i] = np.inf; same = d[(y[idx] == y[i])]; opp = d[(y[idx] != y[i])]
        j = idx[(y[idx] != y[i])][int(np.argmin(opp))]
        recs.append({"sim_id": M.index[i], "y": int(y[i]), "d_same": float(same.min()), "d_opp": float(opp.min()), "interleaved": bool(opp.min() < same.min()),
                     "partner": M.index[j], "z_h": float(H[i, 0]), "z_a": float(H[i, 1]), "corner": bool(CORNER(M).iloc[i]), "batch_provenance": str(M.source_batch.iloc[i]),
                     "short_record": bool(M.short_record.iloc[i]), "early_end": bool(M.early_end.iloc[i]), "shortK_pooled": bool(M.shortK_pooled.iloc[i]),
                     "frac_K_FCK": float(M.frac_K_FCK.iloc[i]) if np.isfinite(M.frac_K_FCK.iloc[i]) else np.nan, "P": float(M.P.iloc[i]), "VX": float(M.VX.iloc[i]),
                     "LS_um": float(M.LS.iloc[i] * 1e6), "ST": float(M.ST.iloc[i]),
                     "partner_dP": float(M.P.iloc[j] - M.P.iloc[i]), "partner_dVX": float(M.VX.iloc[j] - M.VX.iloc[i]), "partner_dST": float(M.ST.iloc[j] - M.ST.iloc[i])})
    return pd.DataFrame(recs)


def hard_group(rows, M):
    m = M; sk = set(m.index[m.shortK_NEW_original.astype(bool)]); cn = set(m.index[(m.source_batch == "NEW") & (m.y == 0)]); recs = []
    for (cond, r, f, b, k, ids, ok, p, EL, ET, one) in rows:
        if cond != "STD":
            continue
        hat = p >= 0.5
        for i, s in enumerate(ids):
            if s in sk or s in cn:
                recs.append({"cluster": r, "budget": b, "rung": k, "group": "shortK_NEW" if s in sk else "NEW_conduction", "has_depth": bool(ok[i]), "pred_K": bool(hat[i])})
    H = pd.DataFrame(recs); H["window"] = np.where(H.budget <= 24, "early", "late")
    return H.groupby(["window", "rung", "group"]).agg(n=("pred_K", "size"), pred_K_rate=("pred_K", "mean")).reset_index()


def run():
    OUT.mkdir(parents=True, exist_ok=True); M = P.manifest(); U = DG.load_unlimited(); res = {}
    for cond in ("STD", "K5", "K4"):
        rows, R6 = load(cond); D, G, ex = tables(rows, M)
        Wi = window_means(D, ("condition", "cluster", "learner", "rung")); Wp = window_means(G, ("condition", "cluster", "rung"))
        summ = Wi.groupby(["window", "rung"])[["BA", "sens", "spec"]].mean().round(4).reset_index(); summ_p = Wp.groupby(["window", "rung"])[["BA", "sens", "spec"]].mean().round(4).reset_index()
        atb = D[D.budget.isin((8, 12, 16, 24, 40, 60))].groupby(["budget", "rung"]).BA.mean().round(4).unstack().to_dict()
        r6 = []
        for (c, r, f, k, ids, ok, p) in R6:
            idc = ids[ok]; y = M.y.reindex(idc).to_numpy(int); n1, n0, tp, tn = confusion(p[ok], y)
            r6.append({"rung": k, "BA": 0.5 * (tp / n1 + tn / n0) if n1 and n0 else np.nan, "sens": tp / n1 if n1 else np.nan, "spec": tn / n0 if n0 else np.nan})
        r6 = pd.DataFrame(r6).groupby("rung")[["BA", "sens", "spec"]].mean().round(4).to_dict()
        res[cond] = {"individual": summ.to_dict(orient="records"), "pooled": summ_p.to_dict(orient="records"), "BA_at_budget_individual": atb, "R6_large_n_individual": r6}
        if cond == "STD":
            res[cond]["steps"] = steps(Wi)
            T = transitions(ex); T.to_csv(OUT / "std_error_transitions.csv.gz", index=False, compression="gzip")
            tsum = T[T.error != "R0_correct_R3_wrong"].groupby(["window", "error", "first_fix"]).size().unstack(fill_value=0)
            res[cond]["transitions_first_fix"] = tsum.to_dict(orient="index"); res[cond]["broken_by_R3"] = T[T.error == "R0_correct_R3_wrong"].groupby("window").size().to_dict()
            pers = T[(T.window == "late") & (~T.fixed_by_R3) & (T.error != "R0_correct_R3_wrong")].groupby(["sim_id", "error"]).size().reset_index(name="late_learner_budget_errors")
            pers.to_csv(OUT / "std_persistent_errors_not_fixed_by_true_depth.csv", index=False)
            Eg, unl = emulator_error(rows, M, U); Eg.to_csv(OUT / "std_emulator_error.csv.gz", index=False, compression="gzip")
            Eg["window"] = np.where(Eg.budget <= 24, "early", "late")
            res[cond]["emulator_error"] = Eg.groupby(["window", "emulator", "region"])[["bias", "rmse"]].mean().round(4).reset_index().to_dict(orient="records")
            res[cond]["unlimited_emulator_error"] = unl
            HG = hard_group(rows, M); HG.to_csv(OUT / "std_hard_group.csv", index=False)
            res[cond]["hard_group_pred_K_rate"] = HG.round(4).to_dict(orient="records")
        for nm, T in (("learner_rungs", D), ("pooled_rungs", G), ("window_individual", Wi), ("window_pooled", Wp)):
            T.to_csv(OUT / f"{cond.lower()}_{nm}.csv.gz", index=False, compression="gzip")
    IP = interleaved_pairs(M); IP.to_csv(OUT / "pool_interleaved_h_depth.csv", index=False)
    res["interleaved_h_depth"] = {"n_with_depth": int(len(IP)), "interleaved": int(IP.interleaved.sum()),
                                  "by_class": IP[IP.interleaved].y.value_counts().to_dict(), "corner_share": float(IP[IP.interleaved].corner.mean()),
                                  "pool_corner_share": float(IP.corner.mean()), "descriptor_rates_interleaved_vs_rest": {
                                      c: [float(IP[IP.interleaved][c].mean()), float(IP[~IP.interleaved][c].mean())] for c in ("short_record", "early_end", "shortK_pooled", "corner")}}
    (OUT / "DIAGNOSIS.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8"); return res


if __name__ == "__main__":
    r = run(); print(json.dumps({k: v for k, v in r["STD"].items() if k in ("individual",)}, indent=0, default=float)[:3000])
