"""C1C evaluation and verdicts (PROTOCOL_C1C.md sections 3-5; frozen before any new result). Test outcomes are read only through src.el_eval.

Reused UNCHANGED: src.ea_fwd_eval.load (unit reading and checks; its UNITS is pointed at the C1C job), .verdicts and .status_saving (the EA
section 4 rules: V-EARLY, V-0.93, V-0.95 RELIABLE, saving statuses, LATE, harm limits); src.ea_cand_eval.sustained and .load (DEV paths);
src.el_eval (metrics, endpoints, cluster t bounds, bootstrap check).
Added BEFORE any new result (protocol section 3.2):
  V_090            status_saving on the 0.90 restricted-mean saving (the V-0.93 rule)
  LATE_PRESERVED   PRESERVED_WITHIN_0.003 if LCB(dBA-AULC B28-B60) > -0.003, else PRESERVATION_NOT_SHOWN (non-inferiority margin = the
                   PRACTICAL early threshold); reported beside LATE (LOSS_SHOWN / NO_LOSS_SHOWN), which is unchanged
  replication      early_replicated = V-EARLY shown; saving_095_replicated = 0.95 saving status SAVING_SHOWN (80 main repeats only)
  descriptive      per-target tables (attained / kept / above target at B60 / sustained / lost, first, confirmed, spend with attainer-only
                   means and medians and their denominators, median with non-attainers = infinity, cumulative attainment), recalls at
                   budgets, pooled contrasts, the second-class cost of one-class starts, subgroup S1 / S2 contrasts, startup rule, prior rule
    python -m src.c1c_eval main | start | prior | sidebyside | all
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

import src.c1c_fwd as FW
import src.ea_cand_eval as CE
import src.ea_fwd_eval as FE
import src.el_eval as EV
import src.rc18_common as RC
import src.rc19_pool as P

OUT = FW.OUT / "evaluation"
LATE = tuple(range(28, 61)); MARGIN_LATE = 0.003; TAUS = EV.TAUS
PAIRS = [("C1_own", "A_own"), ("C1_on_A", "A_own"), ("D_on_A", "A_own"), ("E_on_A", "A_own"), ("C1_on_A", "D_on_A"), ("C1_own", "D_on_A"),
         ("C1_own", "E_on_A"), ("C1_own", "A_on_C1"), ("A_on_C1", "A_own"), ("C1_own", "C1_on_A")]
VPAIRS = [("C1_own", "A_own"), ("C1_on_A", "A_own"), ("D_on_A", "A_own"), ("E_on_A", "A_own"), ("C1_on_A", "D_on_A")]
SYSTEMS = ("C1_own", "A_own", "C1_on_A", "D_on_A", "E_on_A", "A_on_C1")


# ======================================================================================== loading
def load(units_dir, cond, clusters=None):
    FE.UNITS = units_dir
    E, CPU, CHK = FE.load(cond)
    if clusters is not None:
        cs = set(int(c) for c in clusters); E = {k: v for k, v in E.items() if int(k[2]) in cs}
        CPU = CPU[CPU.cluster.isin(cs)].reset_index(drop=True); CHK = CHK[CHK.cluster.isin(cs)].reset_index(drop=True)
    return E, CPU, CHK


def tables(E, M):
    D = EV.learner_rows(E, M.y); G = EV.pooled_rows(E, M.y)
    Ai = EV.aulc(D, ("system", "cluster", "learner")); Ap = EV.aulc(G, ("system", "cluster"))
    cols = ["BA", "sens", "spec", "ll", "brier"]
    late = D[D.budget.isin(LATE)].groupby(["system", "cluster", "learner"])[cols].mean().reset_index(); late["window"] = "B28_B60"
    latep = G[G.budget.isin(LATE)].groupby(["system", "cluster"])[cols].mean().reset_index(); latep["window"] = "B28_B60"
    Ai2 = pd.concat([Ai, late], ignore_index=True); Ap2 = pd.concat([Ap, latep], ignore_index=True)
    Ei = EV.endpoints(D, ("system", "cluster", "learner")); Ep = EV.endpoints(G, ("system", "cluster"))
    Su = CE.sustained(D, ("system", "cluster", "learner")); Sup = CE.sustained(G, ("system", "cluster"))
    b60 = D[D.budget == 60][["system", "cluster", "learner", "BA"]].dropna()
    B60 = pd.concat([b60.assign(target=t, above=(b60.BA >= t)) for t in TAUS], ignore_index=True)
    return {"D": D, "G": G, "Ai": Ai2, "Ap": Ap2, "Ei": Ei, "Ep": Ep, "Su": Su, "Sup": Sup, "B60": B60}


# ======================================================================================== contrasts and verdicts
def contrast(t, x, a, pooled=False):
    if pooled:
        Ai = t["Ap"].assign(learner=0); Ei = t["Ep"].assign(learner=0); Su = t["Sup"].assign(learner=0)
    else:
        Ai, Ei, Su = t["Ai"], t["Ei"], t["Su"]
    c = EV.contrast_table(Ai[Ai.window != "B28_B60"], Ei, x, a); L_ = Ai[Ai.window == "B28_B60"]
    for col in ("BA", "sens", "spec", "ll", "brier"):
        c[f"d{col}_B28_B60" if col != "BA" else "dBA_B28_B60"] = EV.cluster_diff(L_, x, a, col)
    for tau in TAUS:
        T = Su[Su.target == tau].copy(); T["s"] = T.sustained.astype(float); c[f"d_sustained_{tau}"] = EV.cluster_diff(T, x, a, "s")
        if not pooled:
            B = t["B60"][t["B60"].target == tau].copy(); B["ab"] = B.above.astype(float); c[f"d_above_B60_{tau}"] = EV.cluster_diff(B, x, a, "ab")
    return c


def verdict(con, cpu, x, a):
    v = FE.verdicts(con, cpu, x, a)
    v["V_090"] = FE.status_saving(con["rms_saving_0.9"])
    v["LATE_PRESERVED"] = "PRESERVED_WITHIN_0.003" if con["dBA_B28_B60"]["lcb"] > -MARGIN_LATE else "PRESERVATION_NOT_SHOWN"
    v["early_replicated"] = bool(v["V_EARLY"].startswith("EARLY_GAIN_SHOWN"))
    v["saving_095_replicated"] = bool(v["saving_095_status"].startswith("SAVING_SHOWN"))
    v["d_sustained_093"] = con["d_sustained_0.93"]; v["d_attain_093"] = con["d_attain_0.93"]; v["d_kept_093"] = con["d_kept_0.93"]
    v["B8_B60"] = con["dBA_B8_B60"]
    return v


def target_table(t, systems):
    """Per system and target (individual learners): counts with their denominators, attainer-only means and medians, medians with
    non-attainers = infinity, cumulative attainment, above target at B60, sustained (from the confirmed budget to 60)."""
    rows = []; Ei, Su, B6 = t["Ei"], t["Su"], t["B60"]
    for sy in systems:
        for tau in TAUS:
            T = Ei[(Ei.system == sy) & (Ei.target == tau) & (Ei.defined == True)]  # noqa: E712
            n = len(T); att = T.attained.astype(bool); na = int(att.sum())
            sp = T.spend[att].astype(float); fi = T["first"].dropna().astype(float); cf = T.confirmed_b[att].astype(float)
            spall = np.where(att, T.spend.astype(float).fillna(np.inf), np.inf)
            su = Su[(Su.system == sy) & (Su.target == tau)]; b6 = B6[(B6.system == sy) & (B6.target == tau)]
            med_all = float(np.median(spall)) if n else np.nan
            rows.append({"system": sy, "target": tau, "learners": n, "attained": na, "attain_rate": na / n if n else np.nan,
                         "kept": int(T.kept.astype(bool).sum()), "lost": int(T.lost.astype(bool).sum()),
                         "above_target_B60": int(b6.above.sum()), "above_B60_denominator": int(len(b6)),
                         "sustained": int(su.sustained.sum()), "sustained_denominator": int(len(su)),
                         "reached_once": int(len(fi)), "first_mean_reached": float(fi.mean()) if len(fi) else np.nan,
                         "first_mean_attainers": float(T["first"][att].astype(float).mean()) if na else np.nan,
                         "confirmed_b_mean_attainers": float(cf.mean()) if na else np.nan,
                         "spend_mean_attainers": float(sp.mean()) if na else np.nan, "spend_median_attainers": float(sp.median()) if na else np.nan,
                         "spend_median_all_noninf": (med_all if np.isfinite(med_all) else "not reached by half"),
                         "rms_61_capped": float(T.rms.mean()) if n else np.nan,
                         **{f"cum_attain_b{b}": float(np.mean(spall <= b)) if n else np.nan for b in EV.CUM_B}})
    return pd.DataFrame(rows)


def recalls_at(D, systems):
    rows = []
    for sy in systems:
        for b in EV.AT_B:
            T = D[(D.system == sy) & (D.budget == b)]
            rows.append({"system": sy, "budget": b, "BA": float(T.BA.mean()), "keyhole_recall": float(T.sens.mean()), "conduction_recall": float(T.spec.mean()), "learners": int(T.BA.notna().sum())})
    return pd.DataFrame(rows)


def second_class(units_dir, cond, clusters=None):
    """Learners whose 8-point startup holds one usable class: extra label-free path queries before both classes are present (counted
    as spend in every arm). Both arms follow the same label-free path until then (checked)."""
    rows = []; cs = None if clusters is None else set(clusters)
    for fL in sorted(units_dir.glob(f"{cond}__*__L.json.gz")):
        uL = RC.read_json_gz(fL); uX = RC.read_json_gz(fL.with_name(fL.name.replace("__L.json.gz", "__X.json.gz")))
        if cs is not None and int(uL["repeat"]) not in cs:
            continue
        kL = sum(1 for e in uL["evals"] if e.get("how") == "path"); kX = sum(1 for e in uX["evals"] if e.get("how") == "path")
        rows.append({"cluster": int(uL["repeat"]), "learner": int(uL["fold"]), "extra_L": kL, "extra_X": kX,
                     "same_path_until_both_classes": bool(kL == kX and uL["paid_ids"][:8 + kL] == uX["paid_ids"][:8 + kX])})
    R = pd.DataFrame(rows)
    one = R[R.extra_L > 0]
    return R, {"learners": int(len(R)), "one_class_starts": int(len(one)), "share": float(len(one) / len(R)) if len(R) else np.nan,
               "extra_queries_mean_all": float(R.extra_L.mean()) if len(R) else np.nan, "extra_queries_mean_one_class": float(one.extra_L.mean()) if len(one) else 0.0,
               "extra_queries_median_one_class": float(one.extra_L.median()) if len(one) else 0.0, "extra_queries_max": int(R.extra_L.max()) if len(R) else 0,
               "budget_both_classes_mean": float(8 + R.extra_L.mean()) if len(R) else np.nan, "arms_identical_until_both_classes": bool(R.same_path_until_both_classes.all())}


def evaluate_set(units_dir, cond, M, clusters=None, pooled=True):
    E, CPU, CHK = load(units_dir, cond, clusters); t = tables(E, M)
    con = {f"{x}-{a}": contrast(t, x, a) for x, a in PAIRS}
    ver = {f"{x}-{a}": verdict(con[f"{x}-{a}"], CPU, x, a) for x, a in VPAIRS}
    res = {"condition": cond, "clusters": int(t["D"].cluster.nunique()), "learners": int(t["D"][["cluster", "learner"]].drop_duplicates().shape[0]),
           "contrasts": con, "verdicts": ver, "ba_at": {x: EV.ba_at(t["D"], x, "A_own") for x in ("C1_own", "C1_on_A", "D_on_A", "E_on_A")},
           "cpu_mean_per_step": CPU.drop(columns=["cluster", "learner"]).mean().round(4).to_dict(), "check_pL_vs_own_A_maxabs": float(CHK.pL_vs_own_A.max()),
           "late_window_means": t["Ai"][t["Ai"].window == "B28_B60"].groupby("system")[["BA", "ll", "brier"]].mean().round(4).to_dict()}
    if pooled:
        res["pooled_primary"] = contrast(t, "C1_own", "A_own", pooled=True)
    S = EV.summary_by_system(t["D"], t["Ai"][t["Ai"].window != "B28_B60"], t["Ei"], t["G"], t["Ap"][t["Ap"].window != "B28_B60"], t["Ep"])
    return res, t, S, CPU


# ======================================================================================== the three parts
def _save(prefix, t, S, CPU, extra=None):
    OUT.mkdir(parents=True, exist_ok=True)
    for nm in ("D", "Ai", "Ap", "Ei", "Ep", "Su"):
        t[nm].to_csv(OUT / f"{prefix}_{nm.lower()}.csv.gz", index=False, compression="gzip")
    S.to_csv(OUT / f"{prefix}_summary.csv", index=False); CPU.to_csv(OUT / f"{prefix}_cpu.csv.gz", index=False, compression="gzip")
    for k, v in (extra or {}).items():
        v.to_csv(OUT / f"{prefix}_{k}.csv", index=False)


def main_part(M):
    d = FW.OUT / "c1c-main" / "units"; res, t, S, CPU = evaluate_set(d, "STD", M)
    TT = target_table(t, SYSTEMS); RA = recalls_at(t["D"], SYSTEMS); R2, sc = second_class(d, "STD")
    res["target_table"] = TT.to_dict(orient="records"); res["recalls_at"] = RA.to_dict(orient="records"); res["second_class"] = sc
    res["subgroups"] = {}
    for g, reps in FW.SUB.items():
        rg, tg, Sg, Cg = evaluate_set(d, "STD", M, clusters=reps, pooled=False)
        res["subgroups"][g] = {"repeats": f"{reps[0]}-{reps[-1]}", "clusters": rg["clusters"], "learners": rg["learners"], "verdicts": rg["verdicts"],
                               "primary": rg["contrasts"]["C1_own-A_own"], "target_table": target_table(tg, ("C1_own", "A_own")).to_dict(orient="records")}
    _save("main", t, S, CPU, {"target_table": TT, "recalls_at": RA, "second_class": R2})
    return res


def startup_rule(vs):
    """vs[cond] = verdict of C1_own - A_own under RAND8 / LOCAL8 (20 clusters each; descriptive verdict labels)."""
    early_ok = all(v["early"]["mean"] > 0 and not (v["early"]["ucb"] < 0) for v in vs.values())
    s95_ok = all(v["saving_095"]["mean"] >= 0 for v in vs.values())
    late_loss = [c for c, v in vs.items() if v["LATE"] == "LOSS_SHOWN"]
    harm = [c for c, v in vs.items() if not (v["harm"]["LL_ok"] and v["harm"]["Brier_ok"] and v["harm"]["CPU_ok"])]
    return {"early": "STARTUP_CONSISTENT" if early_ok else "STARTUP_DEPENDENT", "early_shown": {c: v["V_EARLY"] for c, v in vs.items()},
            "saving_095": "NO_CONTRADICTION" if s95_ok else "STARTUP_DEPENDENT", "late_loss_shown_in": late_loss, "harm_limit_exceeded_in": harm}


def start_part(M):
    d = FW.OUT / "c1c-start" / "units"; out = {}; vs = {}
    for cond in FW.START:
        res, t, S, CPU = evaluate_set(d, cond, M)
        TT = target_table(t, SYSTEMS); RA = recalls_at(t["D"], SYSTEMS); R2, sc = second_class(d, cond)
        res["target_table"] = TT.to_dict(orient="records"); res["recalls_at"] = RA.to_dict(orient="records"); res["second_class"] = sc
        out[cond] = res; vs[cond] = res["verdicts"]["C1_own-A_own"]
        _save(f"start_{cond.lower()}", t, S, CPU, {"target_table": TT, "recalls_at": RA, "second_class": R2})
    out["startup_rule"] = startup_rule(vs); return out


def prior_load(M):
    E, CPU0 = CE.load("STD")
    E = {k: v for k, v in E.items() if k[0] in ("A", "D", "C1")}; cpu = []
    for fp in sorted((FW.OUT / "c1c-prior" / "units").glob("STD__*.json.gz")):
        u = RC.read_json_gz(fp); r, f = int(u["repeat"]), int(u["fold"]); ids = np.asarray(u["test_ids"], str); bs = np.array([e["budget"] for e in u["evals"]], int)
        if not np.array_equal(bs, np.arange(8, 61)):
            raise RuntimeError(f"{fp.name}: budgets are not 8..60")
        if list(ids) != list(E[("A", "STD", r, f)][2]):
            raise RuntimeError(f"{fp.name}: test ids differ from the DEV record")
        for nm in ("C1_S05", "C1_S2"):
            E[(nm, "STD", r, f)] = (bs, np.array([e["p"][nm] for e in u["evals"]], float), ids)
        cpu.append({"cluster": r, "learner": f, **{nm: float(np.mean([e["cpu_s"][nm] for e in u["evals"][:52]])) for nm in ("C1_S05", "C1_S2")}})
    C = CPU0[["cluster", "learner", "C1"]].merge(pd.DataFrame(cpu), on=["cluster", "learner"])
    return E, C


def prior_part(M):
    E, C = prior_load(M); t = tables(E, M)
    pairs = [("C1_S05", "A"), ("C1_S2", "A"), ("C1", "A"), ("C1_S05", "C1"), ("C1_S2", "C1"), ("C1_S05", "D"), ("C1_S2", "D"), ("C1", "D")]
    con = {f"{x}-{a}": contrast(t, x, a) for x, a in pairs}
    rob = all(con[f"{k}-A"]["dBA_B8_B24"]["lcb"] > 0 for k in ("C1_S05", "C1_S2"))
    eq = {k: bool(abs(con[f"{k}-C1"]["dBA_B8_B24"]["mean"]) < 0.003) for k in ("C1_S05", "C1_S2")}
    TT = target_table(t, ("C1_S05", "C1_S2", "C1", "A", "D"))
    S = EV.summary_by_system(t["D"], t["Ai"][t["Ai"].window != "B28_B60"], t["Ei"], t["G"], t["Ap"][t["Ap"].window != "B28_B60"], t["Ep"])
    _save("prior", t, S, C, {"target_table": TT})
    return {"paths": "recorded HA_LEAN DEV paths, STD repeats 123-162 (reviewed in EA; not new independent validation)", "learners": int(t["D"][["cluster", "learner"]].drop_duplicates().shape[0]),
            "contrasts": con, "PRIOR_RULE_EARLY": "PRIOR_ROBUST_EARLY" if rob else "PRIOR_SENSITIVE_EARLY", "practically_equal_to_C1_early": eq,
            "cpu_mean_per_step": C.drop(columns=["cluster", "learner"]).mean().round(4).to_dict(), "target_table": TT.to_dict(orient="records"),
            "note": "a control only: neither control can become the candidate, whatever it shows"}


def sidebyside(M, main=None):
    """The same primary contrasts, computed with this module's code, for the EA DEV paths (C1 on A's path, 123-162), the EA fresh validation
    (163-202) and the new main validation (203-282) with its subgroups. Nothing is pooled across sets."""
    rows = []

    def row(name, ids, con, kind):
        r = {"set": name, "repeats": ids, "kind": kind}
        for k, key in (("early_B8_B24", "dBA_B8_B24"), ("late_B28_B60", "dBA_B28_B60"), ("B8_B60", "dBA_B8_B60"), ("rms_saving_090", "rms_saving_0.9"),
                       ("rms_saving_093", "rms_saving_0.93"), ("rms_saving_095", "rms_saving_0.95"), ("d_attain_095", "d_attain_0.95"), ("d_kept_095", "d_kept_0.95"),
                       ("d_sustained_095", "d_sustained_0.95"), ("dLL_B8_B60", "dll_B8_B60")):
            v = con[key]; r[k] = v["mean"]; r[k + "_lcb"] = v["lcb"]; r[k + "_ucb"] = v["ucb"]
        r["clusters"] = con["dBA_B8_B24"]["n"]; rows.append(r)
    Edev, _ = CE.load("STD"); tdev = tables({k: v for k, v in Edev.items() if k[0] in ("A", "C1", "D")}, M)
    row("EA DEV (C1 on A's recorded path)", "123-162", contrast(tdev, "C1", "A"), "DEV, cross-path")
    rea, _, _, _ = evaluate_set(FW.EA / "ea-fwd" / "units", "STD", M, pooled=False)
    row("EA fresh validation", "163-202", rea["contrasts"]["C1_own-A_own"], "own paths")
    if main is not None:
        row("C1C main validation", "203-282", main["contrasts"]["C1_own-A_own"], "own paths (VERDICT SET)")
        for g, v in main["subgroups"].items():
            row(f"C1C subgroup {g}", v["repeats"], v["primary"], "own paths (descriptive)")
    return pd.DataFrame(rows), rea


def run(parts=("main", "start", "prior", "sidebyside")):
    OUT.mkdir(parents=True, exist_ok=True); M = P.manifest(); fp = OUT / "C1C_DECISION.json"
    res = json.loads(fp.read_text(encoding="utf-8")) if fp.exists() else {}
    if "main" in parts:
        res["main"] = main_part(M)
    if "start" in parts:
        res["start"] = start_part(M)
    if "prior" in parts:
        res["prior"] = prior_part(M)
    if "sidebyside" in parts:
        SB, rea = sidebyside(M, res.get("main"))
        SB.to_csv(OUT / "sidebyside_primary.csv", index=False); res["sidebyside"] = SB.to_dict(orient="records")
        ea = json.loads((FW.EA / "validation" / "EA_VALIDATION_DECISION.json").read_text(encoding="utf-8"))["verdicts"]["primary"]
        res["ea_consistency_check"] = {"early_mean_recomputed": rea["contrasts"]["C1_own-A_own"]["dBA_B8_B24"]["mean"], "early_mean_EA_record": ea["early"]["mean"],
                                       "saving_095_recomputed": rea["contrasts"]["C1_own-A_own"]["rms_saving_0.95"]["mean"], "saving_095_EA_record": ea["saving_095"]["mean"],
                                       "PASS": bool(abs(rea["contrasts"]["C1_own-A_own"]["dBA_B8_B24"]["mean"] - ea["early"]["mean"]) < 1e-12 and
                                                    abs(rea["contrasts"]["C1_own-A_own"]["rms_saving_0.95"]["mean"] - ea["saving_095"]["mean"]) < 1e-12)}
    res["utc"] = RC.utc(); fp.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8"); return res


if __name__ == "__main__":
    parts = ("main", "start", "prior", "sidebyside") if sys.argv[1] == "all" else tuple(sys.argv[1:])
    r = run(parts)
    if "main" in r:
        v = r["main"]["verdicts"]["C1_own-A_own"]
        print(json.dumps({k: v[k] for k in ("V_EARLY", "V_090", "V_093", "V_095", "saving_095_status", "LATE", "LATE_PRESERVED", "harm")}, indent=1, default=float))
