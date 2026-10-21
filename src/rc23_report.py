"""RC23 reports (presentation layer; metrics, verdicts, endpoints, non-inferiority and the decision come from the frozen
src/rc23_eval.py and src/rc22_eval.py).
    python -m src.rc23_report match | all | smoke
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
from scipy.special import logit
from scipy.stats import spearmanr

import src.rc18_common as RC
import src.rc19_eval as EV
import src.rc19_pool as P
import src.rc22_common as C22
import src.rc22_eval as E22
import src.rc23_eval as E
from src.rc19_report import md

OUT = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc23"
R21 = RC.ROOT / "outputs" / "research_campaign_20261020" / "opus_rc21" / "e-final" / "units"
R22 = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc22"
CONS = ("PHR_NRMAP", "HA_LR", "HA_LEAN", "HONLY_LR")
PLAIN = {"PHR_NRMAP": "RC22 reference (PHR_NRMAP)", "HA_LR": "RC22 candidate, shared upstream (HA_LR)", "HA_LEAN": "fully lean h + depth (HA_LEAN)",
         "HONLY_LR": "h only (HONLY_LR)"}
FIXED_B = (8, 12, 16, 20, 24, 32, 40, 60)


def _load(job):
    return EV.load_units(OUT / job)


def _write(part, name, L):
    d = OUT / part; d.mkdir(parents=True, exist_ok=True); (d / name).write_text("\n".join(L) + "\n", encoding="utf-8")


def _own(u):
    return [(list(u["evals"][0]["p"].keys())[0], u.get("arm"))]


def _reuse_ref(cond, reps):
    """Completed PHR_NRMAP + margin trajectories reused for the robustness conditions (no rerun)."""
    U = []
    if cond == "STD":
        for r in reps:
            for f in range(1, 6):
                u = RC.read_json_gz(R21 / f"r{r}_f{f}__NEW_MARGIN.json.gz"); U.append({**u, "arm": "PHR_NRMAP", "evals": [{**e, "p": {"PHR_NRMAP": e["p"]["PHR_NRMAP"]}} for e in u["evals"]]})
    elif cond in ("RAND8", "LOCAL8"):
        for r in reps:
            for f in range(1, 6):
                u = RC.read_json_gz(R22 / "g-start" / "units" / f"{cond}__r{r}_f{f}__REF.json.gz"); U.append({**u, "arm": "PHR_NRMAP", "evals": [{**e, "p": {"PHR_NRMAP": e["p"]["PHR_NRMAP"]}} for e in u["evals"]]})
    else:
        for s in reps:
            for b in range(1, 6):
                u = RC.read_json_gz(R22 / "g-block" / "units" / f"s{s}_b{b}__REF.json.gz"); U.append({**u, "arm": "PHR_NRMAP", "evals": [{**e, "p": {"PHR_NRMAP": e["p"]["PHR_NRMAP"]}} for e in u["evals"]]})
    return U


def _tables(U, M, T):
    rows = E22.learner_rows(U, M, T, cons_map=_own); B = E22.pooled_metrics(rows); LB = E22.learner_metrics(rows)
    A = {w: E22.aulc(B, w) for w in ("small", "all")}; return rows, B, LB, A


def _summ(T):
    cols = [c for c in ("BA", "log_loss", "brier", "sensitivity", "specificity") if c in T]
    S = T.groupby("arm")[cols].agg(["mean", lambda x: x.std(ddof=1) / np.sqrt(len(x))]); S.columns = [f"{a}_{'se' if b == '<lambda_0>' else b}" for a, b in S.columns]
    return S.reset_index()


def _contrasts(A, E_, pairs):
    V, SP, NI = [], [], []
    for a, b in pairs:
        for w, met, mg, dirn in (("small", "BA", 0.020, "higher"), ("all", "BA", 0.020, "higher"), ("small", "log_loss", 0.010, "lower"), ("all", "log_loss", 0.005, "lower"),
                                 ("small", "sensitivity", 0.020, "higher"), ("small", "specificity", 0.020, "higher")):
            V.append({"window": w, **E22.contrast(A[w], a, b, met, mg, dirn)})
        for w in ("small", "all"):
            NI.append({"window": w, **E.noninferiority(A[w], a, b, "BA")})
        for tg in ("BA >= 0.80", "BA >= 0.90", "BA >= 0.93", "BA >= 0.95"):
            SP.append(E.spend_pair(E_, a, b, tg))
    return pd.DataFrame(V), pd.DataFrame(SP), pd.DataFrame(NI)


def export(part, U, rows, B):
    d = OUT / part / "export"; d.mkdir(parents=True, exist_ok=True); acc = {}; keys, arrs, tids, buds, paths = [], [], [], [], []
    for r in rows:
        acc.setdefault((r["arm"], r["repeat"], r["fold"]), {})[r["budget"]] = r
    for (arm, rep, f), bd in acc.items():
        bs = sorted(bd); keys.append(f"{arm}|r{rep}|f{f}"); arrs.append(np.asarray([bd[b]["p"] for b in bs], np.float32)); tids.append(np.asarray(bd[bs[0]]["ids"])); buds.append(np.asarray(bs, np.int16))
    for u in U:
        hows = [e.get("how") for e in u["evals"]]
        for q, s in enumerate(u["paid_ids"], 1):
            paths.append({"arm": u["arm"], "startup": u.get("startup", "STD"), "block": u.get("block"), "repeat": u["repeat"], "fold": u["fold"], "query": q, "sim_id": s,
                          "rule": "startup" if q <= P.B0 else (hows[q - P.B0 - 1] if q - P.B0 - 1 < len(hows) and hows[q - P.B0 - 1] else "margin")})
    np.savez_compressed(d / "predictions_f32.npz", keys=np.asarray(keys), **{f"pred_{i}": v for i, v in enumerate(arrs)}, **{f"test_ids_{i}": t for i, t in enumerate(tids)},
                        **{f"budgets_{i}": t for i, t in enumerate(buds)}, schema=np.asarray([json.dumps({"pred": "pred[budget, test] = P(Keyhole), float32; key arm|repeat|fold"})]))
    pd.DataFrame(paths).to_csv(d / "paths.csv.gz", index=False, compression="gzip")
    Z = np.load(d / "predictions_f32.npz", allow_pickle=False); byk = {(r["arm"], r["repeat"], r["fold"], r["budget"]): r for r in rows}; R2 = []
    for i, k in enumerate(Z["keys"]):
        arm, rep, f = k.rsplit("|", 2)
        for j, b in enumerate(Z[f"budgets_{i}"]):
            rr = dict(byk[(arm, int(rep[1:]), int(f[1:]), int(b))]); rr["p"] = Z[f"pred_{i}"][j].astype(float); R2.append(rr)
    B2 = E22.pooled_metrics(R2); j = B2.merge(B, on=["arm", "repeat", "budget"], suffixes=("_x", "_t")); res = {"cells": int(len(j)), "cells_table": int(len(B))}
    for c in ("BA", "log_loss", "sensitivity", "specificity", "brier"):
        dd = np.abs(j[f"{c}_x"].to_numpy(float) - j[f"{c}_t"].to_numpy(float)); dd = dd[np.isfinite(dd)]; res[c] = float(dd.max()) if len(dd) else 0.0
    res["PASS"] = bool(res["cells"] == res["cells_table"] and all(res[c] <= 1e-12 for c in ("BA", "log_loss", "sensitivity", "specificity", "brier")))
    (d / "EXPORT_ACCEPTANCE.json").write_text(json.dumps(res, indent=1), encoding="utf-8"); return res


def condition(part, title, U, M, T, by_label):
    rows, B, LB, A = _tables(U, M, T); E_ = E.endpoints(B); EL = E.endpoints(LB, by=("arm", "repeat", "fold"))
    pairs = [("HA_LEAN", "PHR_NRMAP"), ("HA_LR", "PHR_NRMAP"), ("HA_LEAN", "HA_LR"), ("HA_LEAN", "HONLY_LR"), ("HONLY_LR", "PHR_NRMAP")]
    pairs = [p for p in pairs if p[0] in set(B.arm) and p[1] in set(B.arm)]
    V, SP, NI = _contrasts(A, E_, pairs); R = OUT / part; R.mkdir(parents=True, exist_ok=True)
    for nm, df in (("pooled_metrics", B), ("learner_metrics", LB), ("verdicts", V), ("spend", SP), ("noninferiority", NI), ("endpoints_pooled", E_), ("endpoints_learners", EL)):
        df.to_csv(R / f"{part}_{nm}.csv", index=False, lineterminator="\n")
    FB = B[B.budget.isin(FIXED_B)].groupby(["arm", "budget"])[["BA", "sensitivity", "specificity", "log_loss", "brier", "spec_NEW", "q20_BA"]].mean().reset_index()
    cpu = pd.DataFrame([{"arm": u["arm"], "cpu_s_per_step": float(np.mean([e["cpu_s"] for e in u["evals"] if e.get("cpu_s") is not None])) if any(e.get("cpu_s") is not None for e in u["evals"]) else np.nan,
                         "cpu_s_trajectory": float(u.get("cpu_s") or np.nan)} for u in U]).groupby("arm").mean().reset_index()
    acc = export(part, U, rows, B)
    L = [f"# {title}", "", "Arms (plain name, code alias): " + "; ".join(f"{PLAIN[c]}" for c in CONS if c in set(B.arm)) + ". Selector: margin in every arm.", "",
         "## AULC (fold-pooled repeat curves; mean and SE over the paired units)", "", "B8–B24:", "", md(_summ(A["small"]), 4), "", "B8–B60:", "", md(_summ(A["all"]), 4), "",
         "## Paired contrasts (practical-superiority verdicts, margins as RC20–RC22)", "", md(V, 4), "",
         "## Performance preservation (one-sided 95 % lower bound of the paired BA-AULC difference vs −0.010)", "", md(NI, 4), "",
         "## BA at fixed budgets (fold-pooled, mean over units)", "", md(FB, 3), "",
         "## BA targets — fold-pooled repeat curves (first budget; 8 = already at the startup; spend = b + 4 at confirmation; censored = not confirmed by B60)", "", md(E.attainment_table(E_), 2), "",
         "## BA targets — individual learners (one test fold / block each; undefined when its test set has one class)", "", md(E.attainment_table(EL), 2), "",
         "## Paired spend (observed difference on both-attained units kept apart from the restricted score with censored = 61)", "", md(SP, 2), "",
         "## Decision / training CPU of each arm's own construction (single thread)", "", md(cpu, 3), "", f"Export acceptance: {json.dumps(acc)}", ""]
    _write(part, f"{part.upper()}.md", L); return A, E_


def match():
    M = P.manifest(); U = _load("h-match"); T = {(t["repeat"], t["fold"]): t for t in P.tasks(sorted({u["repeat"] for u in U}))}
    rows = E22.learner_rows(U, M, T, cons_map=lambda u: [(c, f"{c}@{u['path_of']}") for c in CONS]); B = E22.pooled_metrics(rows)
    B["cons"] = B.arm.str.split("@").str[0]
    A = {w: B[B.budget.isin(bs)].groupby(["cons", "repeat"])[["BA", "log_loss", "sensitivity", "specificity", "brier"]].mean().reset_index().rename(columns={"cons": "arm"})
         for w, bs in (("small", (8, 12, 16, 20, 24)), ("all", tuple(range(8, 61, 4))))}
    pairs = [("HA_LEAN", "HA_LR"), ("HA_LEAN", "HONLY_LR"), ("HA_LEAN", "PHR_NRMAP"), ("HA_LR", "PHR_NRMAP"), ("HONLY_LR", "PHR_NRMAP")]
    Cn = pd.DataFrame([{"window": w, **E22.material(A[w], a, b, met, met == "log_loss")} for w in ("small", "all") for a, b in pairs for met in ("BA", "log_loss", "sensitivity", "specificity")])
    S = pd.DataFrame([{"construction": PLAIN[c], **{f"{m} {w}": float(A[w][A[w].arm == c][m].mean()) for w in ("small", "all") for m in ("BA", "log_loss", "sensitivity", "specificity")}} for c in CONS])
    ag = []
    for u in U:
        for e in u["evals"]:
            if "cand" not in e:
                continue
            c = e["cand"]; ta = np.asarray(e["p"]["HA_LR"], float); tl = np.asarray(e["p"]["HA_LEAN"], float)
            pa, pl = np.asarray(c["p:HA_LR"], float), np.asarray(c["p:HA_LEAN"], float); ma, ml = -np.abs(pa - 0.5), -np.abs(pl - 0.5)
            ag.append({"budget": e["budget"], "test_decision_disagree": float(np.mean((ta >= 0.5) != (tl >= 0.5))), "cand_decision_disagree": float(np.mean((pa >= 0.5) != (pl >= 0.5))),
                       "spearman_margin": float(spearmanr(ma, ml).correlation), "top1_same": bool(np.argmax(ma) == np.argmax(ml)),
                       "logit_slope": float(np.polyfit(logit(np.clip(pa, 1e-6, 1 - 1e-6)), logit(np.clip(pl, 1e-6, 1 - 1e-6)), 1)[0])})
    AG = pd.DataFrame(ag).groupby("budget").agg(test_decision_disagree=("test_decision_disagree", "mean"), cand_decision_disagree=("cand_decision_disagree", "mean"),
                                                spearman_margin=("spearman_margin", "median"), top1_same=("top1_same", "mean"), logit_slope=("logit_slope", "median")).reset_index()
    chk = [v for u in U for e in u["evals"] for v in (e.get("check_vs_rc22") or {}).values()]
    R = OUT / "match"; R.mkdir(parents=True, exist_ok=True); B.to_csv(R / "match_pooled_metrics.csv", index=False, lineterminator="\n"); Cn.to_csv(R / "match_contrasts.csv", index=False, lineterminator="\n")
    AG.to_csv(R / "match_agreement.csv", index=False, lineterminator="\n")
    L = ["# RC23 stage 1 — mechanism on identical saved paid prefixes (RC22 acquisition paths A1 / A5, repeats 43–50; fixed paths, NOT active learning)", "",
         f"Reproduction of recorded RC22 probabilities: max |Δ| = {max(chk):.2e} ({len(chk)} checks).", "", "## Fold-pooled AULC (mean over the 2 path types and 8 repeats)", "", md(S, 4), "",
         "## Matched contrasts (MATERIAL iff |Δ| ≥ 0.010 in the good direction and ≥ 7/8)", "", md(Cn, 4), "",
         "## Same-path agreement of the lean system with the shared-upstream candidate (HA_LEAN vs HA_LR)", "", md(AG, 3), ""]
    _write("match", "MATCH.md", L); print("\n".join(L)[:6000])


def all_():
    M = P.manifest(); out = {}
    U = _load("h-std"); T = {(t["repeat"], t["fold"]): t for t in P.tasks(sorted({u["repeat"] for u in U}))}
    A_std, E_std = condition("std", "RC23 stage 2 — prospective primary comparison, fresh DEV repeats 51–58, standard startup", U, M, T, None)
    rob = {}; reps = tuple(range(35, 43)); Tr = {(t["repeat"], t["fold"]): t for t in P.tasks(reps)}; UR = _load("h-rob")
    for st in ("STD", "RAND8", "LOCAL8"):
        Ux = [u for u in UR if u.get("startup") == st] + _reuse_ref(st, reps)
        rob[st] = condition(f"rob_{st.lower()}", f"RC23 stage 3 — robustness, startup {st} (repeats 35–42; PHR_NRMAP reused from RC21B / RC22)", Ux, M, Tr, None)[0]
    TB = {(t["repeat"], t["fold"]): t for t in C22.block_tasks(range(1, 9), M)}; UB = _load("h-block") + _reuse_ref("BLOCK", range(1, 9))
    rob["BLOCK"] = condition("block", "RC23 stage 3 — geometry blocks (each block withheld from fitting and querying; PHR_NRMAP reused from RC22)", UB, M, TB, None)[0]
    dec, det = E.decide(A_std, E_std, rob)
    (OUT / "DECISION.json").write_text(json.dumps({"decision": dec, "detail": det}, indent=1, default=str), encoding="utf-8"); print(dec)
    return dec


def smoke():
    U = _load("h-smoke")
    for u in U:
        print(u["arm"], u.get("startup"), u.get("block"), u["queries"], round(u["cpu_s"], 1), sorted(set(e.get("how", "") for e in u["evals"])))


if __name__ == "__main__":
    RC.limit_threads(1); {"match": match, "all": all_, "smoke": smoke}[sys.argv[1]]()
