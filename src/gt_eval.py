"""GT evaluation (PROTOCOL_GT.md sections 5-6). Test outcomes are read ONLY here (and in src.gt_recompute).

Reused unchanged: src.el_eval (learner_rows, aulc, cluster_diff, contrast_table, tstats, boot), src.ea_fwd_eval.verdicts / status_saving
(the registered EA rules), src.ea_cand_eval.sustained. Added (registered): targets 0.80 / 0.90 / 0.93 / 0.95 (endpoints4 = el_eval.endpoints
with a target argument; V8 checks it reproduces el_eval.endpoints at 0.90 / 0.93 / 0.95), subgroups (short-Keyhole, NEW conduction,
corner, ceiling), the G2 selection / promising / carry rules, the G3 decomposition and transition rule, the G4 verdict mapping.
    python -m src.gt_eval g2 | g3 | g4
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

import src.ea_cand_eval as CE
import src.ea_fwd_eval as FE
import src.el_eval as EV
import src.gt_data as GD
import src.gt_dev as DV
import src.gt_geo as GG
import src.rc18_common as RC
import src.rc19_pool as P

OUT = DV.OUT
TAUS4 = (0.80, 0.90, 0.93, 0.95)
LATE = tuple(range(28, 61))
GEOS = tuple(GG.GEO)


# ======================================================================================== loading
def _E_add(E, key, evals, sysname, ids, field="p"):
    E[key] = (np.array([e["budget"] for e in evals], int), np.array([e[field][sysname] for e in evals], float), np.asarray(ids, str))


def load_g2():
    E, CPU, CHK = {}, [], []
    for c in DV.DEV:
        for r in DV.DEV[c]:
            for f in range(1, DV.NL[c] + 1):
                n = f"{c}__{'r' if c == 'STD' else 's'}{r}_{'f' if c == 'STD' else 'b'}{f}"
                u = RC.read_json_gz(OUT / "gt-dev" / "units" / f"{n}.json.gz"); uX = DV.recorded(c, r, f); ids = u["test_ids"]
                if list(uX["test_ids"]) != list(ids):
                    raise RuntimeError(n)
                _E_add(E, ("C1", c, r, f), uX["evals"], "C1", ids)
                for s in u["evals"][0]["p"]:
                    if s == "C1":
                        _E_add(E, ("C1_recomputed", c, r, f), u["evals"], "C1", ids)
                    else:
                        _E_add(E, (s, c, r, f), u["evals"], s, ids)
                CPU.append({"condition": c, "cluster": r, "learner": f, **{s: float(np.mean([e["cpu_s"].get(s, np.nan) for e in u["evals"]])) for s in u["evals"][0]["cpu_s"]}})
                CHK.append({"condition": c, "cluster": r, "learner": f, "c1_max_abs": max(e["c1_vs_recorded_maxabs"] for e in u["evals"]),
                            "startup_ok": bool(u["startup_is_task_path"]), "gp_fail": int(sum(e["gp_fail"] for e in u["evals"])),
                            "gp_fits": int(sum(e["gp_fits"] for e in u["evals"])), "fallbacks": int(sum(len(e["fallback"]) for e in u["evals"])),
                            "one_class_budgets": int(sum(e["one_class"] for e in u["evals"]))})
    for k, v in E.items():
        if not np.array_equal(v[0], np.arange(8, 61)):
            raise RuntimeError(f"{k}: budgets are not 8..60")
    return E, pd.DataFrame(CPU), pd.DataFrame(CHK)


# ======================================================================================== tables
def endpoints4(T, by, taus=TAUS4):
    """= src.el_eval.endpoints with the target list as an argument (V8 checks equality at 0.90 / 0.93 / 0.95)."""
    out = []
    for key, g in T.groupby(list(by)):
        cur = dict(zip(g.budget.astype(int), g.BA.astype(float))); bs = sorted(cur); defined = all(np.isfinite(cur[b]) for b in bs)
        for tau in taus:
            row = dict(zip(by, key)); row["target"] = tau; row["defined"] = defined
            if not defined:
                out.append(row); continue
            first = next((b for b in bs if cur[b] >= tau), None)
            conf = next((b for b in bs if b + 4 in cur and cur[b] >= tau and cur[b + 4] >= tau), None)
            att = conf is not None; spend = conf + 4 if att else None
            row.update({"first": first, "confirmed_b": conf, "spend": spend, "attained": att, "rms": float(spend) if att else float(EV.CENS),
                        "maintenance": float(np.mean([cur[b] >= tau for b in bs if b >= conf])) if att else np.nan,
                        "kept": bool(att and cur[max(bs)] >= tau), "lost": bool(att and cur[max(bs)] < tau)})
            out.append(row)
    return pd.DataFrame(out)


def v8(D):
    by = ("system", "condition", "cluster", "learner"); A_ = EV.endpoints(D, by); B_ = endpoints4(D, by, EV.TAUS)
    cols = ["first", "confirmed_b", "spend", "attained", "rms", "kept", "lost"]
    a = A_.sort_values(list(by) + ["target"]).reset_index(drop=True)[cols].astype(float); b = B_.sort_values(list(by) + ["target"]).reset_index(drop=True)[cols].astype(float)
    return bool(a.equals(b) or np.allclose(a.fillna(-9).to_numpy(), b.fillna(-9).to_numpy()))


def tables(E, M):
    D = EV.learner_rows(E, M.y); by = ("system", "cluster", "learner")
    out = {}
    for cond in sorted(D.condition.unique()):
        Dc = D[D.condition == cond]; Ai = EV.aulc(Dc, by)
        late = Dc[Dc.budget.isin(LATE)].groupby(list(by))[["BA", "sens", "spec", "ll", "brier"]].mean().reset_index(); late["window"] = "B28_B60"
        Ai = pd.concat([Ai, late], ignore_index=True); Ei = endpoints4(Dc, by); Su = CE.sustained(Dc, by, TAUS4)
        b60 = Dc[Dc.budget == 60][list(by) + ["BA"]].dropna()
        B60 = pd.concat([b60.assign(target=t, above=(b60.BA >= t)) for t in TAUS4], ignore_index=True)
        out[cond] = {"D": Dc, "Ai": Ai, "Ei": Ei, "Su": Su, "B60": B60}
    return out


def contrast(t, x, a):
    Ai, Ei, Su = t["Ai"], t["Ei"], t["Su"]
    c = EV.contrast_table(Ai[Ai.window != "B28_B60"], Ei, x, a)
    L_ = Ai[Ai.window == "B28_B60"]
    for col in ("BA", "sens", "spec", "ll", "brier"):
        c[f"d{col}_B28_B60" if col != "BA" else "dBA_B28_B60"] = EV.cluster_diff(L_, x, a, col)
    for tau in TAUS4:
        T = Su[Su.target == tau].copy(); T["s"] = T.sustained.astype(float); c[f"d_sustained_{tau}"] = EV.cluster_diff(T, x, a, "s")
    T = Ei[(Ei.target == 0.80) & (Ei.defined == True)].copy()  # noqa: E712
    T["att"] = T.attained.astype(float); T["kp"] = T.kept.astype(float)
    c["rms_saving_0.8"] = EV.cluster_diff(T, x, a, "rms", sign=-1.0); c["d_attain_0.8"] = EV.cluster_diff(T, x, a, "att"); c["d_kept_0.8"] = EV.cluster_diff(T, x, a, "kp")
    return c


def summary(t, systems):
    rows = []; D, Ai, Ei, Su, B60 = t["D"], t["Ai"], t["Ei"], t["Su"], t["B60"]
    for sy in systems:
        r = {"system": sy}
        for w in ("B8_B24", "B8_B60", "B28_B60"):
            T = Ai[(Ai.window == w) & (Ai.system == sy)]
            for col in ("BA", "sens", "spec", "ll", "brier"):
                r[f"{col}_{w}"] = float(T[col].mean())
        for b in EV.AT_B:
            T = D[(D.system == sy) & (D.budget == b)]; r[f"BA_b{b}"] = float(T.BA.mean()); r[f"sens_b{b}"] = float(T.sens.mean()); r[f"spec_b{b}"] = float(T.spec.mean())
        for tau in TAUS4:
            T = Ei[(Ei.system == sy) & (Ei.target == tau) & (Ei.defined == True)]  # noqa: E712
            att = T.attained.astype(bool); n = len(T); sp = T.spend[att].astype(float); spall = np.where(att, T.spend.astype(float).fillna(np.inf), np.inf)
            su = Su[(Su.system == sy) & (Su.target == tau)]; b6 = B60[(B60.system == sy) & (B60.target == tau)]
            med_all = float(np.median(spall)) if n else np.nan
            r.update({f"attained_{tau}": f"{int(att.sum())}/{n}", f"attain_rate_{tau}": float(att.mean()) if n else np.nan,
                      f"first_mean_reached_{tau}": float(T["first"].dropna().astype(float).mean()) if T["first"].notna().any() else np.nan,
                      f"confirmed_b_mean_att_{tau}": float(T.confirmed_b[att].astype(float).mean()) if att.any() else np.nan,
                      f"spend_mean_att_{tau}": float(sp.mean()) if att.any() else np.nan, f"spend_median_att_{tau}": float(sp.median()) if att.any() else np.nan,
                      f"spend_median_all_{tau}": med_all if np.isfinite(med_all) else "inf (not reached by half)",
                      f"rms61_{tau}": float(T.rms.mean()) if n else np.nan, f"kept_{tau}": f"{int(T.kept.astype(bool).sum())}/{n}",
                      f"above_B60_{tau}": f"{int(b6.above.sum())}/{len(b6)}", f"sustained_{tau}": f"{int(su.sustained.sum())}/{len(su)}",
                      f"never_reached_{tau}": int(n - att.sum())})
        rows.append(r)
    return pd.DataFrame(rows)


def subgroups(E, M, systems, windows=((8, 24), (24, 60))):
    """Evaluator-only subgroup recalls per learner and window: short-Keyhole (pooled; NEW original), NEW conduction (EA hard group),
    corner (VX > 0.85, P > 330), ceiling Keyhole (A >= 295 um), Keyhole below the ceiling, all conduction."""
    R = GD.runs(); A_ = R.A_um.reindex(M.index).to_numpy(float)
    grp = {"shortK_pooled": (M.shortK_pooled.to_numpy(bool), 1), "shortK_NEW": (M.shortK_NEW_original.to_numpy(bool), 1),
           "NEW_conduction": (((M.source_batch == "NEW") & (M.y == 0)).to_numpy(), 0), "corner_keyhole": (((M.VX > 0.85) & (M.P > 330) & (M.y == 1)).to_numpy(), 1),
           "corner_conduction": (((M.VX > 0.85) & (M.P > 330) & (M.y == 0)).to_numpy(), 0), "ceiling_keyhole": (((M.y == 1).to_numpy() & (A_ >= 295)), 1),
           "keyhole_below_ceiling": (((M.y == 1).to_numpy() & (A_ < 295)), 1), "conduction": ((M.y == 0).to_numpy(), 0)}
    idx = {s: i for i, s in enumerate(M.index.astype(str))}; rows = []
    for (sy, cond, c, l), (bs, Pm, ids) in E.items():
        if sy not in systems:
            continue
        ii = np.array([idx[s] for s in ids]); hat = np.asarray(Pm, float) >= 0.5
        for g, (mask, cls) in grp.items():
            m = mask[ii]
            if not m.any():
                continue
            ok = (hat[:, m] == bool(cls)).mean(1)
            for (lo, hi) in windows:
                sel = (bs >= lo) & (bs <= hi)
                rows.append({"system": sy, "condition": cond, "cluster": c, "learner": l, "group": g, "window": f"B{lo}_B{hi}", "recall": float(ok[sel].mean()), "n": int(m.sum())})
    return pd.DataFrame(rows)


def sub_contrast(S, x, a):
    out = {}
    for (cond, g, w), T in S.groupby(["condition", "group", "window"]):
        out[f"{cond}|{g}|{w}"] = {**EV.cluster_diff(T, x, a, "recall"), "x_mean": float(T[T.system == x].recall.mean()), "a_mean": float(T[T.system == a].recall.mean()),
                                  "runs_per_learner_median": float(T[T.system == x].n.median())}
    return out


def q20_rows(E, M, systems, windows=((8, 24), (8, 60), (24, 60))):
    """Evaluator-only near-boundary decision success: BA on the q20 test runs of each task (the 20 % of the fold / block closest to the
    pooled boundary, src.rc19_pool semantics), per learner and window. Descriptive addition (owner: judge decisions near the boundary)."""
    import src.el_cross as X
    keys = sorted({(c, r, f) for (s, c, r, f) in E if s in systems})
    T = X.tasks_for({f"k{i}": (None,) + k for i, k in enumerate(keys)}, M); rows = []
    for (s, c, r, f), (bs, Pm, ids) in E.items():
        if s not in systems:
            continue
        task = T[(c, r, f)]; q = np.asarray(task["q20"], bool)
        if [task["ids"][i] for i in task["test"]] != list(ids):
            raise RuntimeError("q20 alignment")
        y = M.y.reindex(ids).to_numpy(int)[q]; P_ = np.asarray(Pm, float)[:, q] >= 0.5
        n1, n0 = (y == 1).sum(), (y == 0).sum()
        if n1 == 0 or n0 == 0:
            continue
        ba = 0.5 * ((P_ & (y == 1)).sum(1) / n1 + (~P_ & (y == 0)).sum(1) / n0)
        for lo, hi in windows:
            m = (bs >= lo) & (bs <= hi); rows.append({"system": s, "condition": c, "cluster": r, "learner": f, "window": f"B{lo}_B{hi}", "q20_BA": float(ba[m].mean())})
    return pd.DataFrame(rows)


def q20_contrast(Q, x, a):
    out = {}
    for (cond, w), T in Q.groupby(["condition", "window"]):
        out[f"{cond}|{w}"] = {**EV.cluster_diff(T, x, a, "q20_BA"), "x_mean": float(T[T.system == x].q20_BA.mean()), "a_mean": float(T[T.system == a].q20_BA.mean())}
    return out


def per_region(t, x, a):
    Td = t["Ai"][t["Ai"].window == "B8_B60"].dropna(subset=["BA"]); Rr = Td.groupby(["system", "cluster"]).BA.mean()
    r = EV.tstats((Rr.loc[x] - Rr.loc[a]).dropna().values); r["warning"] = bool(np.isfinite(r["lcb"]) and r["lcb"] < -0.02); return r


def ceiling_share(E, M, x, a):
    """Descriptive: per-learner B8-B60 BA difference against the share of paid ceiling runs (A >= 295 um) on the recorded C1 path."""
    R = GD.runs(); cap = set(R.index[(R.A_um >= 295).to_numpy()]); rows = []
    for (sy, cond, c, l), (bs, Pm, ids) in E.items():
        if sy != x or cond != "STD":
            continue
        uX = DV.recorded(cond, c, l); share = float(np.mean([s in cap for s in uX["paid_ids"][:60]]))
        y = M.y.reindex(ids).to_numpy(int); ba = lambda P_: np.nanmean([0.5 * (((p >= 0.5) & (y == 1)).sum() / max(1, (y == 1).sum()) + ((p < 0.5) & (y == 0)).sum() / max(1, (y == 0).sum())) for p in P_])  # noqa: E731
        rows.append({"cluster": c, "learner": l, "paid_ceiling_share": share, "dBA_B8_B60": ba(Pm) - ba(E[(a, cond, c, l)][1])})
    T = pd.DataFrame(rows)
    if len(T) < 3:
        return {}
    rho = float(T[["paid_ceiling_share", "dBA_B8_B60"]].corr(method="spearman").iloc[0, 1])
    return {"learners": int(len(T)), "spearman_rho": rho, "share_median": float(T.paid_ceiling_share.median())}


def jdump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(obj, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)), encoding="utf-8")


# ======================================================================================== G2
def g2():
    (OUT / "dev").mkdir(parents=True, exist_ok=True)
    M = P.manifest(); E, CPU, CHK = load_g2(); t = tables(E, M); D = EV.learner_rows(E, M.y)
    systems = ["C1"] + list(GEOS) + ["CAL_B1", "C1_G", "C1_T", "ORACLE_T"]
    res = {"utc": RC.utc(), "acceptance": {"V4_c1_recomputed_max_abs": float(CHK.c1_max_abs.max()), "V5_startups_ok": bool(CHK.startup_ok.all()),
                                           "V8_endpoints_equal": v8(D[D.system == "C1"]), "gp_fail": int(CHK.gp_fail.sum()), "gp_fits": int(CHK.gp_fits.sum()),
                                           "fallbacks": int(CHK.fallbacks.sum()), "learners": int(len(CHK))}}
    res["contrasts"] = {cond: {s: contrast(t[cond], s, "C1") for s in systems[1:]} for cond in t}
    res["per_region"] = {cond: {s: per_region(t[cond], s, "C1") for s in systems[1:]} for cond in ("K5", "K4")}
    S = subgroups(E, M, systems); res["subgroups"] = {s: sub_contrast(S[S.system.isin([s, "C1"])], s, "C1") for s in systems[1:]}
    Q = q20_rows(E, M, systems); res["q20"] = {s: q20_contrast(Q[Q.system.isin([s, "C1"])], s, "C1") for s in systems[1:]}
    Q.to_csv(OUT / "dev" / "G2_q20.csv.gz", index=False, lineterminator="\n")
    res["ceiling_share"] = {s: ceiling_share(E, M, s, "C1") for s in GEOS}
    st = res["contrasts"]["STD"]; early = {s: st[s]["dBA_B8_B24"]["mean"] for s in GEOS}
    best = max(early, key=early.get); close = [s for s in GEOS if abs(early[s] - early[best]) < 0.0005]
    if len(close) > 1:
        best = max(close, key=lambda s: st[s]["dBA_B8_B60"]["mean"])
    prom = bool(early[best] >= -0.003)
    carry_g = bool(st["C1_G"]["dBA_B8_B24"]["mean"] >= 0.005 and st["C1_G"]["dBA_B8_B24"]["lcb"] > 0)
    carry_t = bool(st["C1_T"]["dBA_B8_B24"]["mean"] >= 0.005 and st["C1_T"]["dBA_B8_B24"]["lcb"] > 0)
    res["selection"] = {"early_by_geo": early, "GEO_star": best, "tie_break_used": len(close) > 1, "promising": prom,
                        "rule": "promising iff STD mean dBA-AULC B8-B24 (GEO* - C1) >= -0.003", "C1_G_carried": carry_g, "C1_T_carried": carry_t,
                        "decision": ("G3 own path for GEO*" if prom else "GEOMETRY STOP (no G3, no G4)"),
                        "temperature_A": "carried to an own-path test" if carry_t else "TEMPERATURE-A STOP (no time-model campaign)"}
    jdump(OUT / "dev" / "G2_RESULT.json", res)
    for cond in t:
        summary(t[cond], systems).to_csv(OUT / "dev" / f"G2_summary_{cond}.csv", index=False, lineterminator="\n")
    S.to_csv(OUT / "dev" / "G2_subgroups.csv.gz", index=False, lineterminator="\n"); CPU.to_csv(OUT / "dev" / "G2_cpu.csv", index=False, lineterminator="\n")
    CHK.to_csv(OUT / "dev" / "G2_checks.csv", index=False, lineterminator="\n")
    jdump(OUT / "dev" / "G2_SELECTION.json", {"system": best, "promising": prom, "selector_controls": prom, "C1_G_carried": carry_g, "C1_T_carried": carry_t,
                                               "utc": RC.utc(), "rule": "PROTOCOL_GT section 5 G2"})
    print(json.dumps({"acceptance": res["acceptance"], "selection": res["selection"]}, indent=1, default=str))
    return res


# ======================================================================================== G3 (DEV own path)
def _sel():
    return json.loads((OUT / "dev" / "G2_SELECTION.json").read_text(encoding="utf-8"))


def load_g3():
    sel = _sel(); gs = sel["system"]; E, CPU, paths = {}, [], []
    for c in DV.DEV:
        for r in DV.DEV[c]:
            for f in range(1, DV.NL[c] + 1):
                n = f"{c}__{'r' if c == 'STD' else 's'}{r}_{'f' if c == 'STD' else 'b'}{f}"
                uX = DV.recorded(c, r, f); ids = uX["test_ids"]; _E_add(E, ("C1_own", c, r, f), uX["evals"], "C1", ids)
                u2 = RC.read_json_gz(OUT / "gt-dev" / "units" / f"{n}.json.gz"); _E_add(E, ("GEO_on_C1", c, r, f), u2["evals"], gs, ids)
                cpu = {"condition": c, "cluster": r, "learner": f, "C1_own": float(np.mean([e["cpu_s"] for e in uX["evals"][:52]]))}
                for q, s in enumerate(uX["paid_ids"][:60], 1):
                    paths.append(("C1_own (recorded EA)", c, r, f, q, s))
                for s in ("margin", "straddle", "space"):
                    fp = OUT / "gt-own" / "units" / f"{n}__{s}.json.gz"
                    if not fp.exists():
                        continue
                    u = RC.read_json_gz(fp)
                    if list(u["test_ids"]) != list(ids) or u["paid_ids"][:8] != uX["paid_ids"][:8]:
                        raise RuntimeError(f"{n} {s}: test set or startup differs")
                    _E_add(E, (f"GEO_{s}_own", c, r, f), u["evals"], gs, ids); cpu[f"GEO_{s}_own"] = float(np.mean([e["cpu_s"] for e in u["evals"][:52]]))
                    for q, sid in enumerate(u["paid_ids"][:60], 1):
                        paths.append((f"GEO_{s}_own", c, r, f, q, sid))
                    if s == "margin" and "cross" in u:
                        _E_add(E, ("C1_on_GEO", c, r, f), u["cross"], "C1", ids)
                CPU.append(cpu)
    return E, pd.DataFrame(CPU), paths


def g3():
    M = P.manifest(); sel = _sel(); E, CPU, paths = load_g3(); t = tables(E, M)
    own = [s for s in ("GEO_margin_own", "GEO_straddle_own", "GEO_space_own") if any(k[0] == s for k in E)]
    pairs = [(s, "C1_own") for s in own] + [("GEO_on_C1", "C1_own"), ("GEO_margin_own", "C1_on_GEO"), ("GEO_margin_own", "GEO_on_C1"), ("C1_on_GEO", "C1_own")]
    pairs = [p for p in pairs if all(any(k[0] == s for k in E) for s in p)]
    res = {"utc": RC.utc(), "GEO_star": sel["system"], "contrasts": {cond: {f"{x}-{a}": contrast(t[cond], x, a) for x, a in pairs} for cond in t}}
    res["per_region"] = {cond: {f"{x}-C1_own": per_region(t[cond], x, "C1_own") for x in own} for cond in ("K5", "K4")}
    S = subgroups(E, M, ["C1_own"] + own); res["subgroups"] = {s: sub_contrast(S[S.system.isin([s, "C1_own"])], s, "C1_own") for s in own}
    Q = q20_rows(E, M, ["C1_own"] + own); res["q20"] = {s: q20_contrast(Q[Q.system.isin([s, "C1_own"])], s, "C1_own") for s in own}
    st = res["contrasts"]["STD"]
    # interaction (B - C) - (D - A) with A = C1_own, B = GEO_margin_own, C = C1_on_GEO, D = GEO_on_C1
    if {"GEO_margin_own", "C1_on_GEO"} <= {k[0] for k in E}:
        Ai = t["STD"]["Ai"]; T = Ai[Ai.window == "B8_B24"].pivot_table(index=["cluster", "learner"], columns="system", values="BA")
        d = (T["GEO_margin_own"] - T["C1_on_GEO"]) - (T["GEO_on_C1"] - T["C1_own"]); cm = d.dropna().groupby(level=0).mean()
        res["interaction_B8_B24"] = {**EV.tstats(cm.values), **EV.boot(cm.values)}
    early = {s: st[f"{s}-C1_own"]["dBA_B8_B24"]["mean"] for s in own}; best = max(early, key=early.get); c = st[f"{best}-C1_own"]
    route_a = bool(c["dBA_B8_B24"]["mean"] >= 0.005 and c["dBA_B8_B24"]["lcb"] > 0)
    route_b = bool(c["rms_saving_0.95"]["mean"] >= 1.0 and c["rms_saving_0.95"]["lcb"] > 0 and c["dBA_B8_B24"]["lcb"] > -0.003)
    harm = {"late_lcb_ge_-0.005": bool(c["dBA_B28_B60"]["lcb"] >= -0.005),
            "blocks_lcb_ge_-0.02": bool(all(res["per_region"][cd][f"{best}-C1_own"]["lcb"] >= -0.02 for cd in ("K5", "K4") if f"{best}-C1_own" in res["per_region"][cd])),
            "dLL_B8_B60_le_0.030": bool(c["dll_B8_B60"]["mean"] <= 0.030)}
    go = bool((route_a or route_b) and all(harm.values()))
    cpu_ratio = {s: float(CPU[s].mean() / CPU["C1_own"].mean()) for s in own if s in CPU}
    res["transition"] = {"early_by_selector": early, "selected": best, "selector": best.split("_")[1], "route_a_early": route_a, "route_b_saving_095": route_b,
                         "harm": harm, "go_to_G4": go, "cpu_ratio_vs_C1_own": cpu_ratio,
                         "decision": f"G4 fresh validation of {sel['system']} + {best.split('_')[1]}" if go else "GEOMETRY STOP after G3 (no G4)"}
    res["recompute_pairs"] = [f"{x}|{a}|{cd}" for x, a in pairs for cd in ("STD", "K5", "K4")]
    jdump(OUT / "dev" / "G3_RESULT.json", res)
    for cond in t:
        summary(t[cond], ["C1_own"] + own + [s for s in ("GEO_on_C1", "C1_on_GEO") if any(k[0] == s for k in E)]).to_csv(OUT / "dev" / f"G3_summary_{cond}.csv", index=False, lineterminator="\n")
    CPU.to_csv(OUT / "dev" / "G3_cpu.csv", index=False, lineterminator="\n"); S.to_csv(OUT / "dev" / "G3_subgroups.csv.gz", index=False, lineterminator="\n")
    print(json.dumps(res["transition"], indent=1, default=str))
    return res


# ======================================================================================== G4 (fresh validation)
def load_g4():
    import src.gt_own as OW
    fz = json.loads((OUT / "freeze" / "G4_FREEZE.json").read_text(encoding="utf-8")); gs = fz["system"]; E, CPU, paths = {}, [], []
    for c in OW.FRESH:
        for r in OW.FRESH[c]:
            for f in range(1, OW.NL[c] + 1):
                n = f"{c}__{'r' if c == 'STD' else 's'}{r}_{'f' if c == 'STD' else 'b'}{f}"
                uC = RC.read_json_gz(OUT / "gt-val" / "units" / f"{n}__C.json.gz"); uG = RC.read_json_gz(OUT / "gt-val" / "units" / f"{n}__G.json.gz")
                ids = uC["test_ids"]
                if list(uG["test_ids"]) != list(ids) or uC["paid_ids"][:8] != uG["paid_ids"][:8]:
                    raise RuntimeError(f"{n}: test set or startup differs")
                _E_add(E, ("C1_own", c, r, f), uC["evals"], "C1", ids); _E_add(E, ("GEO_own", c, r, f), uG["evals"], gs, ids)
                _E_add(E, ("GEO_on_C1", c, r, f), uC["geo_on_c1"], gs, ids)
                CPU.append({"condition": c, "cluster": r, "learner": f, "C1_own": float(np.mean([e["cpu_s"] for e in uC["evals"][:52]])),
                            "GEO_own": float(np.mean([e["cpu_s"] for e in uG["evals"][:52]]))})
                for q, s in enumerate(uC["paid_ids"][:60], 1):
                    paths.append(("C1_own", c, r, f, q, s))
                for q, s in enumerate(uG["paid_ids"][:60], 1):
                    paths.append(("GEO_own", c, r, f, q, s))
    return E, pd.DataFrame(CPU), paths


def g4():
    M = P.manifest(); E, CPU, paths = load_g4(); t = tables(E, M); fz = json.loads((OUT / "freeze" / "G4_FREEZE.json").read_text(encoding="utf-8"))
    pairs = [("GEO_own", "C1_own"), ("GEO_on_C1", "C1_own")]
    res = {"utc": RC.utc(), "frozen": fz, "contrasts": {cond: {f"{x}-{a}": contrast(t[cond], x, a) for x, a in pairs} for cond in t}}
    res["per_region"] = {cond: {"GEO_own-C1_own": per_region(t[cond], "GEO_own", "C1_own")} for cond in ("K5", "K4")}
    S = subgroups(E, M, ["C1_own", "GEO_own"]); res["subgroups"] = sub_contrast(S, "GEO_own", "C1_own")
    Q = q20_rows(E, M, ["C1_own", "GEO_own"]); res["q20"] = q20_contrast(Q, "GEO_own", "C1_own")
    con = res["contrasts"]["STD"]["GEO_own-C1_own"]; cpu = CPU[CPU.condition == "STD"]
    v = FE.verdicts(con, cpu, "GEO_own", "C1_own"); v["LATE_PRESERVED"] = "PRESERVED_WITHIN_0.003" if con["dBA_B28_B60"]["lcb"] > -0.003 else "PRESERVATION_NOT_SHOWN"
    blocks_ok = not any(res["per_region"][cd]["GEO_own-C1_own"]["warning"] for cd in ("K5", "K4"))
    early_ok = v["V_EARLY"] == "EARLY_GAIN_SHOWN+PRACTICAL"
    save_ok = v["saving_095_status"] == "SAVING_SHOWN+PRACTICAL" and con["dBA_B8_B24"]["lcb"] > -0.003
    harm_ok = v["LATE_PRESERVED"] == "PRESERVED_WITHIN_0.003" and v["V_095"] == "RELIABLE" and all(v["harm"][k] for k in ("LL_ok", "Brier_ok", "CPU_ok")) and blocks_ok
    res["verdicts"] = v; res["blocks_ok"] = blocks_ok
    res["decision"] = (f"ADAY GELİŞTİRİLDİ VE DOĞRULANDI ({fz['system']} + {fz['selector']})" if (early_ok or save_ok) and harm_ok else "C1 KORUNUYOR")
    res["recompute_pairs"] = [f"{x}|{a}|{cd}" for x, a in pairs for cd in ("STD", "K5", "K4")]
    (OUT / "validation").mkdir(parents=True, exist_ok=True); jdump(OUT / "validation" / "G4_RESULT.json", res)
    for cond in t:
        summary(t[cond], ["C1_own", "GEO_own", "GEO_on_C1"]).to_csv(OUT / "validation" / f"G4_summary_{cond}.csv", index=False, lineterminator="\n")
    CPU.to_csv(OUT / "validation" / "G4_cpu.csv", index=False, lineterminator="\n")
    print(json.dumps({"decision": res["decision"], "V_EARLY": v["V_EARLY"], "early": v["early"], "LATE_PRESERVED": v["LATE_PRESERVED"]}, indent=1, default=str))
    return res


if __name__ == "__main__":
    {"g2": g2, "g3": g3, "g4": g4}[sys.argv[1]]()
