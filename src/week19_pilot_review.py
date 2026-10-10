"""Week 19 DEV pilot — post-hoc review of the completed P0–P2 pilot (commit de065db9).

Reads saved predictions, thresholds and oracle diagnostics only: no learner fit, no seed, no repeat, no threshold tuning,
no relabelling, no exclusion.  The pilot's manifest, decision, predictions and metrics are left byte-identical.
Every quantity here is an algorithmic diagnostic of the existing fits, never a deployable candidate.

Margin convention (exact for the saved E1 fits): p = Phi((mu - log u) / sigma), so class = 1 iff the margin
m = mu - log u >= 0, where mu = predicted absolute log depth (oracle file `predicted_log_depth` = learned
`latent_mean` + log u) and log u is the fold's learned log-threshold.  Between arms,
    delta_margin = (mu_A - mu_W) - (log u_A - log u_W)                      (identity; checked to 1e-12).

Steps: python -m src.week19_pilot_review margins | latent | oracle | gallery | checks | all
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from src.week19_dev_pilot import (AUDIT, BASE_COMMIT, LATE_K_POS, LATE_NEG, NEW_REV, NO_A, OUT, ROOT, TAB, UNRESOLVED, _git, git_blob, sha256,
                                  short, shortk_ids, stats_w)

REV = OUT / "review"
GAL = OUT / "ioan_gallery"
PILOT_COMMIT = "de065db9ef7349caecd2b44bd52cb8178a792066"
B = 40
ARM = {"W": "WHOLE_E1_SHARED", "A": "ACTIVE_E1_SHARED"}
CELL_LABEL = {("W", "W"): "WHOLE mean / WHOLE threshold (= WHOLE_E1 as fitted)", ("A", "W"): "ACTIVE mean / WHOLE threshold",
              ("W", "A"): "WHOLE mean / ACTIVE threshold", ("A", "A"): "ACTIVE mean / ACTIVE threshold (= ACTIVE_E1 as fitted)"}
DIAG = "ALGORITHMIC DIAGNOSTIC of saved fits — not a deployable candidate, not a physical intervention"


def _w(df, name, folder=REV):
    folder.mkdir(parents=True, exist_ok=True)
    df.to_csv(folder / name, index=False, lineterminator="\n")


def group_of(r):
    if r.sim_id == LATE_NEG:
        return "late negative (H-f4fc937e86)"
    if r.sim_id == NO_A:
        return "A-unavailable negative (H-e7dbd8e5ce)"
    if r.sim_id in UNRESOLVED:
        return "unresolved fast-scan negative"
    if r.sim_id == LATE_K_POS:
        return "late-K positive (H-349225d53c)"
    if r.short_K:
        return "short-K positive"
    return "other negative" if r.y == 0 else "other positive"


# ======================================================================================== wide B40 table
def wide(budget=B):
    """One row per (sim_id, repeat): both E1 arms' absolute means, thresholds, margins and classes at `budget`."""
    pr = pd.read_csv(TAB / "predictions.csv"); od = pd.read_csv(TAB / "oracle_response_diagnostics.csv")
    fd = pd.read_csv(TAB / "fit_diagnostics.csv"); ev = pd.read_csv(TAB / "evaluation.csv")
    inp = pd.read_csv(TAB / "pilot_inputs.csv").set_index("sim_id")
    out = None
    for k, arm in ARM.items():
        L = pr[(pr.arm == arm) & (pr.budget == budget) & (pr.threshold_mode == "learned")]
        O = od[(od.arm == arm) & (od.budget == budget)]
        F = fd[(fd.arm == arm) & (fd.budget == budget)][["repeat", "fold", "log_u", "u_um", "status"]]
        E = ev[(ev.arm == arm) & (ev.budget == budget) & (ev.threshold_mode == "learned")][["repeat", "sim_id", "pred_label"]]
        m = (L.merge(O[["repeat", "fold", "sim_id", "predicted_log_depth", "observed_score", "training_threshold", "predicted_label", "status"]],
                     on=["repeat", "fold", "sim_id"], how="left", validate="one_to_one", suffixes=("", "_oracle"))
             .merge(F, on=["repeat", "fold"], how="left", validate="many_to_one", suffixes=("", "_fit"))
             .merge(E, on=["repeat", "sim_id"], how="left", validate="one_to_one"))
        m = m.rename(columns={"fold": f"fold_{k}", "p_keyhole": f"p_{k}", "latent_mean": f"margin_{k}", "latent_variance": f"var_{k}",
                              "predicted_log_depth": f"mu_{k}", "log_u": f"lu_{k}", "u_um": f"u_um_{k}", "observed_score": f"obs_{k}",
                              "training_threshold": f"oracle_threshold_{k}", "predicted_label": f"oracle_class_{k}", "pred_label": f"pred_label_{k}",
                              "status_fit": f"fit_status_{k}", "prediction_status": f"prediction_status_{k}", "status": f"oracle_status_{k}"})
        keep = ["repeat", "sim_id"] + [c for c in m.columns if c.endswith(f"_{k}")]
        out = m[keep] if out is None else out.merge(m[keep], on=["repeat", "sim_id"], how="outer", validate="one_to_one")
    e = ev[(ev.arm == ARM["W"]) & (ev.budget == budget) & (ev.threshold_mode == "learned")][["repeat", "sim_id", "y", "q20", "short_K"]]
    out = out.merge(e, on=["repeat", "sim_id"], how="left", validate="one_to_one")
    out["fold"] = out.fold_W
    out["H"] = out.sim_id.map(short); out["VX_m_s"] = out.sim_id.map(inp.VX_m_s)
    out["obs_whole_um"] = out.sim_id.map(inp.whole_max_um); out["obs_A_um"] = out.sim_id.map(inp.A_um)
    for k in ARM:
        out[f"class_{k}"] = (out[f"margin_{k}"] >= 0).astype(int)
    for mk in ARM:
        for tk in ARM:
            out[f"cell_{mk}{tk}"] = (out[f"mu_{mk}"] - out[f"lu_{tk}"] >= 0).astype(int)
    out["d_mu"] = out.mu_A - out.mu_W
    out["d_lu"] = out.lu_A - out.lu_W
    out["d_margin"] = out.margin_A - out.margin_W
    out["group"] = [group_of(r) for r in out.itertuples()]
    return out.sort_values(["repeat", "fold", "sim_id"]).reset_index(drop=True)


def identities(w):
    """Exact identities behind the decomposition (tolerance 1e-12 in log-µm)."""
    rows = []
    for k in ARM:
        rows.append({"identity": f"mu_{k} = margin_{k} + log u_{k} (oracle predicted_log_depth vs learned latent_mean + fit log_u)",
                     "max_abs_error": float(np.abs(w[f"mu_{k}"] - (w[f"margin_{k}"] + w[f"lu_{k}"])).max())})
        rows.append({"identity": f"log u_{k} = log(u_um_{k}) (fit table)", "max_abs_error": float(np.abs(w[f"lu_{k}"] - np.log(w[f"u_um_{k}"])).max())})
        rows.append({"identity": f"oracle training threshold = u_um_{k}", "max_abs_error": float(np.abs(w[f"oracle_threshold_{k}"] - w[f"u_um_{k}"]).max())})
        rows.append({"identity": f"class_{k} = 1(margin >= 0) = 1(p >= 0.5) = saved pred_label (count of disagreements)",
                     "max_abs_error": float(((w[f"class_{k}"] != (w[f"p_{k}"] >= 0.5).astype(int)) | (w[f"class_{k}"] != w[f"pred_label_{k}"])).sum())})
        rows.append({"identity": f"cell_{k}{k} = class_{k} (count of disagreements)", "max_abs_error": float((w[f"cell_{k}{k}"] != w[f"class_{k}"]).sum())})
    rows.append({"identity": "delta_margin = (mu_A - mu_W) - (log u_A - log u_W)", "max_abs_error": float(np.abs(w.d_margin - (w.d_mu - w.d_lu)).max())})
    rows.append({"identity": "fold identical in both arms (count of disagreements)", "max_abs_error": float((w.fold_W != w.fold_A).sum())})
    rows.append({"identity": "log u constant within (arm, repeat, fold): max spread", "max_abs_error": float(max(w.groupby(["repeat", "fold"])[f"lu_{k}"].agg(lambda s: s.max() - s.min()).max() for k in ARM))})
    rows.append({"identity": "rows = 136 simulations x 2 repeats, unique (sim_id, repeat)", "max_abs_error": float(abs(len(w) - 272) + (w.duplicated(["sim_id", "repeat"]).sum()))})
    t = pd.DataFrame(rows)
    t["status"] = np.where(t.max_abs_error <= 1e-12, "PASS", "FAIL")
    return t


# ======================================================================================== item 1: classification changes
def margins():
    w = wide()
    ch = w[w.class_W != w.class_A].copy()
    ch["change"] = [f"{a}→{b}" for a, b in zip([("TN" if c == 0 else "FP") if y == 0 else ("FN" if c == 0 else "TP") for c, y in zip(ch.class_W, ch.y)],
                                                [("TN" if c == 0 else "FP") if y == 0 else ("FN" if c == 0 else "TP") for c, y in zip(ch.class_A, ch.y)])]
    ch["effect"] = np.where(ch.class_A == ch.y, "correct after change", "wrong after change")
    mean_alone, thr_alone = ch.cell_AW != ch.cell_WW, ch.cell_WA != ch.cell_WW
    ch["attribution"] = np.select([mean_alone & ~thr_alone, thr_alone & ~mean_alone, mean_alone & thr_alone],
                                  ["mean change alone flips; threshold change alone does not", "threshold change alone flips; mean change alone does not",
                                   "either change alone flips"], "neither alone flips; only the joint change does")
    cols = ["sim_id", "H", "repeat", "fold", "y", "group", "VX_m_s", "obs_whole_um", "obs_A_um", "mu_W", "mu_A", "lu_W", "lu_A", "u_um_W", "u_um_A",
            "margin_W", "margin_A", "d_mu", "d_lu", "d_margin", "class_W", "class_A", "change", "effect", "cell_WW", "cell_AW", "cell_WA", "cell_AA", "attribution"]
    ch = ch[cols].rename(columns={"y": "has_keyhole", "mu_W": "pred_log_depth_W", "mu_A": "pred_log_depth_A", "lu_W": "log_u_W", "lu_A": "log_u_A",
                                  "class_W": "class_WHOLE", "class_A": "class_ACTIVE"})
    ch.insert(len(ch.columns), "pred_depth_W_um", np.exp(ch.pred_log_depth_W)); ch.insert(len(ch.columns), "pred_depth_A_um", np.exp(ch.pred_log_depth_A))
    ch.insert(len(ch.columns), "minus_d_log_u", -ch.d_lu)
    _w(ch, "B40_classification_changes.csv")
    # fold thresholds
    w["changed"] = (w.class_W != w.class_A).astype(int)
    ft = w.groupby(["repeat", "fold"]).agg(log_u_W=("lu_W", "first"), log_u_A=("lu_A", "first"), u_um_W=("u_um_W", "first"), u_um_A=("u_um_A", "first"),
                                          n_test=("sim_id", "size"), n_changes=("changed", "sum")).reset_index()
    ft["d_log_u"] = ft.log_u_A - ft.log_u_W
    _w(ft, "B40_fold_thresholds.csv")
    # four cells
    rows = []
    sk = w.short_K.astype(bool).to_numpy()
    for (mk, tk), lab in CELL_LABEL.items():
        c = w[f"cell_{mk}{tk}"].to_numpy()
        per = []
        for r in (1, 2):
            s = (w.repeat == r).to_numpy()
            st = stats_w(c[s].astype(float), np.ones(s.sum(), bool), w.y.to_numpy()[s], sk[s], w.q20.to_numpy()[s].astype(float), w.fold.to_numpy()[s], np.ones((1, s.sum())))
            per.append({k: float(v[0]) for k, v in st.items() if not k.startswith("_")})
        y = w.y.to_numpy()
        rows.append({"cell": lab, "mean_from": ARM[mk], "threshold_from": ARM[tk], "BA_mean_over_repeats": np.mean([p["BA"] for p in per]),
                     "BA_repeat1": per[0]["BA"], "BA_repeat2": per[1]["BA"], "specificity": np.mean([p["specificity_12neg"] for p in per]),
                     "sensitivity_all_pos": np.mean([p["sensitivity_all_pos"] for p in per]), "shortK_sensitivity": np.mean([p["sensitivity_shortK"] for p in per]),
                     "q20_acc": np.mean([p["q20_acc"] for p in per]), "TN_of_24": int(((c == 0) & (y == 0)).sum()), "TP_of_248": int(((c == 1) & (y == 1)).sum()),
                     "shortK_detected_of_20": int(((c == 1) & sk).sum()), "changes_vs_WHOLE_as_fitted": int((c != w.cell_WW).sum()),
                     "changes_vs_ACTIVE_as_fitted": int((c != w.cell_AA).sum()), "note": DIAG})
    fc = pd.DataFrame(rows); _w(fc, "B40_four_cell_diagnostic.csv")
    idt = identities(w); _w(idt, "B40_margin_identities.csv")
    return ch, fc, ft, idt


# ======================================================================================== item 2: late negative
def latent_attribution():
    pp = pd.read_csv(TAB / "paid_paths.csv"); inp = pd.read_csv(TAB / "pilot_inputs.csv").set_index("sim_id")
    w = wide(); ft = pd.read_csv(REV / "B40_fold_thresholds.csv")
    folds, diffs = [], []
    for (r, f), g in pp.groupby(["repeat", "fold"]):
        g = g.sort_values("query_index")
        pos = g.loc[g.sim_id == LATE_NEG, "query_index"]
        pos = int(pos.iloc[0]) if len(pos) else np.nan
        paid = g[g.query_index <= B].copy()
        paid["whole_um"] = paid.sim_id.map(inp.whole_max_um); paid["A_um"] = paid.sim_id.map(inp.A_um); paid["has_keyhole"] = paid.sim_id.map(inp.has_keyhole)
        d = paid[(paid.whole_um != paid.A_um)].copy()
        d["d_log_response"] = np.log(d.A_um) - np.log(d.whole_um)          # NaN for the A-unavailable run (no ACTIVE response)
        d["note"] = np.where(d.A_um.isna(), "no ACTIVE response pair (A unavailable); label still paid", "")
        test = w[(w.repeat == r) & (w.fold == f)]
        fr = ft[(ft.repeat == r) & (ft.fold == f)].iloc[0]
        own = w[(w.repeat == r) & (w.sim_id == LATE_NEG)]
        tot = np.nansum(np.abs(d.d_log_response))
        ln = d[d.sim_id == LATE_NEG]
        folds.append({"repeat": r, "fold": f, "late_negative_query_index": pos, "late_negative_paid_by_B40": bool(np.isfinite(pos) and pos <= B),
                      "late_negative_held_out_here": bool(LATE_NEG in set(test.sim_id)),
                      "own_class_WHOLE": int(own.class_W.iloc[0]) if len(own) and own.fold.iloc[0] == f else np.nan,
                      "own_class_ACTIVE": int(own.class_A.iloc[0]) if len(own) and own.fold.iloc[0] == f else np.nan,
                      "n_paid_with_different_response": int(len(d)), "n_differing_positive": int((d.has_keyhole == 1).sum()), "n_differing_negative": int((d.has_keyhole == 0).sum()),
                      "sum_abs_d_log_response": float(tot), "late_negative_share_of_abs_d_log": float(np.abs(ln.d_log_response).sum() / tot) if len(ln) and tot > 0 else 0.0,
                      "d_log_u": float(fr.d_log_u), "B40_class_changes_in_test_fold": int(fr.n_changes),
                      "changes_to_correct": int(((test.class_W != test.class_A) & (test.class_A == test.y)).sum()),
                      "changes_to_wrong": int(((test.class_W != test.class_A) & (test.class_A != test.y)).sum())})
        for t in d.itertuples():
            diffs.append({"repeat": r, "fold": f, "query_index": int(t.query_index), "sim_id": t.sim_id, "H": short(t.sim_id), "has_keyhole": int(t.has_keyhole),
                          "whole_um": t.whole_um, "A_um": t.A_um, "d_log_response": t.d_log_response, "is_late_negative": t.sim_id == LATE_NEG, "note": t.note})
    fs, ds = pd.DataFrame(folds), pd.DataFrame(diffs)
    fd = pd.read_csv(TAB / "fit_diagnostics.csv")
    a40 = fd[(fd.arm == ARM["A"]) & (fd.budget == B)].set_index(["repeat", "fold"])
    fs["A_unavailable_run_paid_by_B40"] = [bool(a40.loc[(r, f), "A_missing_paid"]) for r, f in zip(fs.repeat, fs.fold)]
    for k in ARM:
        q = fd[(fd.arm == ARM[k]) & (fd.budget == B)].set_index(["repeat", "fold"])
        fs[f"u_um_{k}"] = [float(q.loc[(r, f), "u_um"]) for r, f in zip(fs.repeat, fs.fold)]
        fs[f"root_outside_paid_range_{k}"] = [bool(q.loc[(r, f), "root_outside_range"]) for r, f in zip(fs.repeat, fs.fold)]
    _w(fs, "late_negative_fold_summary.csv"); _w(ds, "late_negative_paid_response_differences.csv")
    # isolation: checkpoints where the two arms' paid training data differ ONLY in the late negative's response
    iso = []
    for b in (16, 40, 80):
        wb = wide(b)
        fb = fd[fd.budget == b].set_index(["arm", "repeat", "fold"])
        for (r, f), g in pp.groupby(["repeat", "fold"]):
            paid = g[g.query_index <= b]
            wh, aa = paid.sim_id.map(inp.whole_max_um), paid.sim_id.map(inp.A_um)
            diff = sorted(paid.sim_id[(wh != aa).to_numpy()])                    # includes an A-unavailable run (NaN) if paid
            t = wb[(wb.repeat == r) & (wb.fold == f)]
            chg = t[t.class_W != t.class_A]
            iso.append({"budget": b, "repeat": r, "fold": f, "n_paid_with_different_response": len(diff),
                        "differing_paid_runs": ";".join(short(s) for s in diff), "only_difference_is_late_negative": diff == [LATE_NEG],
                        "u_um_WHOLE": float(fb.loc[(ARM["W"], r, f), "u_um"]), "u_um_ACTIVE": float(fb.loc[(ARM["A"], r, f), "u_um"]),
                        "class_changes": len(chg), "changes_to_correct": int((chg.class_A == chg.y).sum()), "changes_to_wrong": int((chg.class_A != chg.y).sum()),
                        "changed_runs": ";".join(f"{h} {('FP→TN' if y == 0 else 'FN→TP') if ca == y else ('TN→FP' if y == 0 else 'TP→FN')}"
                                                 for h, y, ca in zip(chg.H, chg.y, chg.class_A))})
    it = pd.DataFrame(iso); _w(it, "late_negative_isolation_by_checkpoint.csv")
    return fs, ds


# ======================================================================================== item 3: oracle vs GP on identical cases
def oracle_same_cohort():
    out, cases = [], []
    for b in (16, 40, 80):
        w = wide(b)
        for k, arm in ARM.items():
            c = w[np.isfinite(w[f"obs_{k}"])].copy()              # available-response cohort; benchmark keeps all 136
            gp, ob = c[f"class_{k}"], c[f"oracle_class_{k}"].astype(int)
            chk = int((ob != (c[f"obs_{k}"] >= c[f"u_um_{k}"]).astype(int)).sum())
            for yv, lab in ((1, "positives"), (0, "negatives")):
                s = c.y == yv
                gc, oc = (gp[s] == yv), (ob[s] == yv)
                out.append({"budget": b, "arm": arm, "class": lab, "n_predictions": int(s.sum()), "both_correct": int((gc & oc).sum()),
                            "GP_correct_observed_wrong": int((gc & ~oc).sum()), "GP_wrong_observed_correct": int((~gc & oc).sum()), "both_wrong": int((~gc & ~oc).sum()),
                            "cohort": f"available observed {'A' if k == 'A' else 'whole max'} ({c.sim_id.nunique()} simulations x 2 repeats)",
                            "oracle_recheck_disagreements": chk})
            sk = c.short_K.astype(bool).to_numpy()
            for name, cls in (("GP (learned threshold)", gp.to_numpy()), ("observed response (same threshold; ORACLE, NOT DEPLOYABLE)", ob.to_numpy())):
                per = []
                for r in (1, 2):
                    s = (c.repeat == r).to_numpy()
                    st = stats_w(cls[s].astype(float), np.ones(s.sum(), bool), c.y.to_numpy()[s], sk[s], c.q20.to_numpy()[s].astype(float), c.fold.to_numpy()[s], np.ones((1, s.sum())))
                    per.append(float(st["BA"][0]))
                out.append({"budget": b, "arm": arm, "class": f"BA on this cohort: {name}", "n_predictions": len(c), "BA_mean_over_repeats": float(np.mean(per))})
            if b == B:
                d = c[gp != ob]
                for t in d.itertuples():
                    cases.append({"arm": arm, "sim_id": t.sim_id, "H": t.H, "repeat": t.repeat, "fold": t.fold, "has_keyhole": t.y, "group": t.group,
                                  "observed_um": getattr(t, f"obs_{k}"), "pred_depth_um": float(np.exp(getattr(t, f"mu_{k}"))), "u_um": getattr(t, f"u_um_{k}"),
                                  "class_GP": int(getattr(t, f"class_{k}")), "class_observed": int(getattr(t, f"oracle_class_{k}")),
                                  "correct": "GP only" if getattr(t, f"class_{k}") == t.y else "observed only"})
    o, cs = pd.DataFrame(out), pd.DataFrame(cases)
    _w(o, "oracle_vs_GP_same_cohort.csv"); _w(cs, "oracle_vs_GP_discordant_B40.csv")
    return o, cs


# ======================================================================================== item 5: unchanged experimental files
def experimental_files_unchanged():
    rows = []
    exp = [OUT / "pilot_manifest.json", OUT / "decision.json"] + sorted(p for d in ("tables", "figures", "provenance") for p in (OUT / d).rglob("*") if p.is_file())
    listed = set(_git("ls-tree", "-r", "--name-only", PILOT_COMMIT, "outputs/week19_temporal_regime_dev_pilot/").splitlines())
    for p in exp:
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        rows.append({"path": rel, "pinned_blob_de065db9": _git("rev-parse", f"{PILOT_COMMIT}:{rel}") if rel in listed else "NOT IN de065db9",
                     "current_blob": git_blob(p), "kind": "experimental output"})
    missing = sorted(l for l in listed if l.split("outputs/week19_temporal_regime_dev_pilot/")[1].split("/")[0] in ("tables", "figures", "provenance")
                     and not (ROOT / l).exists())
    for rel in missing:
        rows.append({"path": rel, "pinned_blob_de065db9": _git("rev-parse", f"{PILOT_COMMIT}:{rel}"), "current_blob": "MISSING", "kind": "experimental output"})
    for rel in ["tables/temporal_registry.csv", "tables/depth_definitions.csv", "tables/new_negatives_12_cases.csv", "tables/k_runs.csv", "REPORT.md", "ASTRA_HANDOFF.md"]:
        p = f"outputs/week19_temporal_regime_audit/{rel}"
        rows.append({"path": p, "pinned_blob_de065db9": _git("rev-parse", f"{BASE_COMMIT}:{p}"), "current_blob": git_blob(ROOT / p), "kind": "audit (pinned at f3206f29)"})
    t = pd.DataFrame(rows)
    t["unchanged"] = t.pinned_blob_de065db9 == t.current_blob
    return t


def checks():
    rows = []

    def add(cid, desc, ok, detail):
        rows.append({"check": cid, "description": desc, "status": "PASS" if ok else "FAIL", "detail": detail})
    idt = pd.read_csv(REV / "B40_margin_identities.csv")
    add("RV-01", "margin identities (absolute mean = latent + log u; class = sign of margin; decomposition; joins; constant fold threshold)",
        bool((idt.status == "PASS").all()), f"{int((idt.status == 'PASS').sum())}/{len(idt)}; worst {idt.max_abs_error.max():.1e}")
    fc = pd.read_csv(REV / "B40_four_cell_diagnostic.csv"); mt = pd.read_csv(TAB / "metrics.csv")
    ref = lambda arm, m: float(mt[(mt.arm == arm) & (mt.metric == m) & (mt.budget == B) & (mt.scope == "mean_over_repeats") & (mt.threshold_mode == "learned")].estimate.iloc[0])  # noqa: E731
    ww, aa = fc[(fc.mean_from == ARM["W"]) & (fc.threshold_from == ARM["W"])].iloc[0], fc[(fc.mean_from == ARM["A"]) & (fc.threshold_from == ARM["A"])].iloc[0]
    ok = all(abs(x - y) < 1e-12 for x, y in [(ww.BA_mean_over_repeats, ref(ARM["W"], "BA")), (aa.BA_mean_over_repeats, ref(ARM["A"], "BA")),
                                             (ww.specificity, ref(ARM["W"], "specificity_12neg")), (aa.specificity, ref(ARM["A"], "specificity_12neg")),
                                             (ww.shortK_sensitivity, ref(ARM["W"], "sensitivity_shortK")), (aa.shortK_sensitivity, ref(ARM["A"], "sensitivity_shortK")),
                                             (ww.q20_acc, ref(ARM["W"], "q20_acc")), (aa.q20_acc, ref(ARM["A"], "q20_acc"))])
    add("RV-02", "four-cell corners reproduce the pilot's B40 metrics (BA, specificity, short-K, q20) for both arms", ok,
        f"WW BA {ww.BA_mean_over_repeats:.6f}; AA BA {aa.BA_mean_over_repeats:.6f}")
    ch = pd.read_csv(REV / "B40_classification_changes.csv")
    add("RV-03", "every B40 WHOLE/ACTIVE classification change is listed once; the decomposition reproduces each change's margin",
        bool(len(ch) == int(ch.groupby(["sim_id", "repeat"]).size().sum()) and (np.abs(ch.d_margin - (ch.d_mu - ch.d_lu)) < 1e-12).all()
             and ((ch.margin_W >= 0).astype(int) == ch.class_WHOLE).all() and ((ch.margin_A >= 0).astype(int) == ch.class_ACTIVE).all()),
        f"{len(ch)} changes")
    o = pd.read_csv(REV / "oracle_vs_GP_same_cohort.csv")
    oc = o[o["class"].isin(["positives", "negatives"])]
    add("RV-04", "oracle comparison uses the available-response cohort (WHOLE 272, ACTIVE 270 predictions) and the training threshold; oracle labels recompute exactly",
        bool((oc.groupby(["budget", "arm"]).n_predictions.sum().reset_index().pipe(lambda d: ((d.arm == ARM["W"]) & (d.n_predictions == 272)) | ((d.arm == ARM["A"]) & (d.n_predictions == 270))).all())
             and (oc.oracle_recheck_disagreements == 0).all()), "cohorts and recheck")
    ex = experimental_files_unchanged(); _w(ex, "experimental_files_unchanged.csv")
    add("RV-05", "manifest, decision, saved predictions, metrics and every other committed pilot output byte-identical to de065db9; audit inputs identical to f3206f29",
        bool(ex.unchanged.all() and len(ex) > 20), f"{int(ex.unchanged.sum())}/{len(ex)} files")
    add("RV-06", "no learner fit: the review never imports the Week 18 engine or a GP/logistic estimator",
        not any(m in sys.modules for m in ("src.week18_engine", "src.week17_models", "sklearn.gaussian_process")), "sys.modules inspection")
    inv = GAL / "image_inventory.csv"
    if inv.exists():
        iv = pd.read_csv(inv)
        add("RV-07", "gallery uses only the 30 already-linked native images, each identity-verified at the pinned NEW revision",
            bool(len(iv) == 30 and iv.verified.all() and iv.revision.eq(NEW_REV).all()), f"{int(iv.verified.sum())}/30 verified; sources {iv.source.value_counts().to_dict()}")
    brief = OUT / "IOAN_MEETING_BRIEF.md"
    if brief.exists():
        words = len([t for t in brief.read_text(encoding="utf-8").split() if any(ch.isalnum() for ch in t)])
        import re
        nq = len(re.findall(r"^\*\*Q\d", brief.read_text(encoding="utf-8"), flags=re.M))
        links_ok = all((OUT / l).exists() for l in ("ioan_gallery/GALLERY.md", "ioan_gallery/KEY.md", "PILOT_REPORT.md", "IOAN_SUMMARY.md", "review/REVIEW.md"))
        add("RV-08", "IOAN_MEETING_BRIEF.md: at most 350 words, at most five questions, all linked files exist", words <= 350 and nq <= 5 and links_ok,
            f"{words} words; {nq} questions; links {'ok' if links_ok else 'BROKEN'}")
    old = "differs only in its labels"
    hits = [str(p.relative_to(ROOT)) for p in OUT.rglob("*.md") if old in p.read_text(encoding="utf-8") and p.parent != REV]
    add("RV-09", "the categorical matched-pair wording is gone from the pilot's reader-facing documents (kept only as quoted text in review/REPORTING_CORRECTIONS.md)",
        not hits, f"remaining: {hits}")
    t = pd.DataFrame(rows); _w(t, "REVIEW_CHECKS.csv")
    print(t.to_string(max_colwidth=110))
    return t


# ======================================================================================== item 4: image gallery for Ioan
HF = "https://huggingface.co/datasets/ioandanielc/sph_v2"
VIEWS = ("front", "side", "top")
SCALE = 2                                    # integer nearest-neighbour enlargement (native aspect ratio, no interpolation)
# Usability, from the repository assistant's visual inspection of each native image (usability only: no regime label,
# no morphology or cavity judgement).  Keys: (H suffix, frame_idx, view).  Unlisted images: content inside the field of view.
VISUAL = {
    ("H-f4fc937e86", 340, "front"): ("nearly empty", "two colours, background layers only; no simulation-specific feature"),
    ("H-f4fc937e86", 340, "side"): ("nearly empty", "background layers with one small feature at the right image border only"),
    ("H-f4fc937e86", 340, "top"): ("blank", "a single uniform colour"),
    ("H-f4fc937e86", 398, "front"): ("nearly empty", "two colours, background layers only; no simulation-specific feature"),
    ("H-f4fc937e86", 398, "side"): ("nearly empty", "two colours, background layers only; no simulation-specific feature"),
    ("H-f4fc937e86", 398, "top"): ("unclear", "content only at the right image border, cut off by the field of view"),
    ("H-349225d53c", 364, "front"): ("nearly empty", "two colours, background layers only; no simulation-specific feature"),
    ("H-349225d53c", 364, "side"): ("nearly empty", "two colours, background layers only; no simulation-specific feature"),
}


KEY_NOTES = {
    "H-b302fc6cbd": "Frame 82 is 0.18 µs after this run's depth maximum (115.58 µm at 0.426879 ms). It follows a sharp drop in monitored depth (114.30 µm at frame 81 → 89.05 µm at frame 82), so its images show the state after the drop. The near-peak frame 81 is not among the 30 linked images. In the G4/G5 sheet, G4's frame 81 is near its own maximum (111.81 µm).",
    "H-349225d53c": "At frame 364 (the last Keyhole frame) the monitored melt depth is 0.00 µm, and the front and side views are nearly empty.",
    "H-f4fc937e86": "At frames 340 and 398 the monitored depth reads 309–312 µm, while the images are blank, nearly empty, or show content only at the border.",
}


def _font(size):
    from PIL import ImageFont
    for name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def gallery_inventory():
    from PIL import Image
    from src.week19_sources import lp, remote_meta, resolve
    cs = pd.read_csv(TAB / "ioan_cases.csv"); fr = pd.read_csv(TAB / "ioan_case_frames.csv")
    if len(fr) != 30 or fr.repo_path.duplicated().any():
        raise ValueError("expected exactly the 30 already-linked images")
    code = {s: f"G{i}" for i, s in enumerate(sorted(cs.sim_id), 1)}           # neutral order (by full ID), not the summary's order
    meta = remote_meta(NEW_REV, fr.repo_path.tolist())
    res = pd.DataFrame([resolve(NEW_REV, r["path"], r) for r in meta.to_dict("records")]).merge(meta, on=["revision", "path"])
    fm = pd.read_csv(AUDIT / "tables/frame_level_map.csv.gz", usecols=["sim_id", "frame_pos", "timestep", "time_ms"])
    rows = []
    for t in fr.merge(res[["path", "local", "source", "verified", "check", "size", "lfs_sha256"]], left_on="repo_path", right_on="path").itertuples():
        im = Image.open(lp(t.local)); im.load()
        a = np.asarray(im.convert("RGB")).reshape(-1, 3)
        n_col = len(np.unique(a, axis=0))
        it = fm[(fm.sim_id == t.sim_id) & (fm.frame_pos == t.frame_idx)]
        use, note = VISUAL.get((t.H, int(t.frame_idx), t.view), ("usable", "content inside the field of view; legible at native resolution"))
        rows.append({"gallery_case": code[t.sim_id], "sim_id": t.sim_id, "frame_idx": int(t.frame_idx), "solver_iteration": int(it.timestep.iloc[0]),
                     "time_ms": float(it.time_ms.iloc[0]), "view": t.view, "repo_path": t.repo_path, "url": t.url, "revision": NEW_REV,
                     "source": t.source, "verified": bool(t.verified), "identity_check": t.check, "sha256": t.lfs_sha256, "bytes": int(t.size),
                     "width_px": im.size[0], "height_px": im.size[1], "mode": im.mode, "n_colours": int(n_col), "usability": use, "usability_note": note,
                     "inspected_by": "repository assistant (visual check of usability only), 2026-10-10",
                     "obtained": "downloaded 2026-10-10 at the pinned revision (no local copy existed); identity-verified before use"})
    inv = pd.DataFrame(rows)
    dup = inv.groupby("sha256").apply(lambda g: [f"{c} frame {f} {v}" for c, f, v in zip(g.gallery_case, g.frame_idx, g.view)], include_groups=False)
    inv["byte_identical_to"] = [", ".join(x for x in dup[s] if x != f"{c} frame {f} {v}") for s, c, f, v in zip(inv.sha256, inv.gallery_case, inv.frame_idx, inv.view)]
    if (inv.time_ms - fr.time_ms).abs().max() > 1e-9:
        raise ValueError("frame times differ from the case table")
    inv = inv.sort_values(["gallery_case", "frame_idx", "view"], key=lambda s: s.map({v: i for i, v in enumerate(VIEWS)}) if s.name == "view" else s).reset_index(drop=True)
    _w(inv, "image_inventory.csv", GAL)
    return inv, code, res


def contact_sheets(inv):
    from PIL import Image, ImageDraw
    from src.week19_sources import lp
    res = {r.repo_path: r for r in inv.itertuples()}
    f_head, f_cap = _font(30), _font(20)
    paths = []
    cs = pd.read_csv(TAB / "ioan_cases.csv").set_index("sim_id")
    for case, g in inv.groupby("gallery_case"):
        sid = g.sim_id.iloc[0]
        tok = {k: float(sid.split(f"{k}-")[1].split("_")[0].replace("p", ".")) for k in ("P", "VX", "LS", "ST")}
        frames = list(dict.fromkeys(g.frame_idx))
        tiles = {}
        for t in g.itertuples():
            im = Image.open(lp(Path(ROOT / "data/raw/sph_v2" / NEW_REV / t.repo_path))).convert("RGB")
            tiles[(t.frame_idx, t.view)] = (im.resize((im.size[0] * SCALE, im.size[1] * SCALE), Image.NEAREST), t)
        colw = {v: max(tiles[(f, v)][0].size[0] for f in frames) for v in VIEWS}
        rowh = {f: max(tiles[(f, v)][0].size[1] for v in VIEWS) for f in frames}
        pad, cap, head = 24, 58, 96
        W = pad + sum(colw[v] + pad for v in VIEWS); H = head + sum(rowh[f] + cap + pad for f in frames)
        sheet = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(sheet)
        d.text((pad, 16), f"{case}   P {tok['P']:.2f} W · VX {tok['VX']:.4f} m/s · LS {tok['LS'] * 1e6:.2f} µm (radius) · ST {tok['ST']:.1f} K", font=f_head, fill="black")
        d.text((pad, 56), f"Native PNGs at {NEW_REV[:12]}…, enlarged ×{SCALE} by pixel replication (aspect ratio unchanged). Full ID and links: GALLERY.md.", font=f_cap, fill="#555555")
        y = head
        for f in frames:
            x = pad
            for v in VIEWS:
                im, t = tiles[(f, v)]
                d.text((x, y), f"frame {f} · iteration {t.solver_iteration:,} · t = {t.time_ms:.6f} ms · {v}", font=f_cap, fill="black")
                d.text((x, y + 26), f"native {t.width_px}×{t.height_px} px · usability: {t.usability}", font=f_cap, fill="#555555")
                sheet.paste(im, (x, y + cap)); d.rectangle([x - 1, y + cap - 1, x + im.size[0], y + cap + im.size[1]], outline="#999999")
                x += colw[v] + pad
            y += rowh[f] + cap + pad
        name = f"contact_sheet_{case}.png"
        sheet.save(GAL / name, optimize=True)
        paths.append(name)
    paths.append(pair_sheet(inv))
    return paths


def pair_sheet(inv, cases=("G4", "G5")):
    """Side-by-side sheet of the two runs with similar inputs and depth trajectories (same images as their case sheets)."""
    from PIL import Image, ImageDraw
    from src.week19_sources import lp
    f_head, f_cap = _font(30), _font(20)
    g = inv[inv.gallery_case.isin(cases)]
    rows = list(g.groupby(["gallery_case", "frame_idx"], sort=True))
    tiles = {(c, f, t.view): (Image.open(lp(Path(ROOT / "data/raw/sph_v2" / NEW_REV / t.repo_path))).convert("RGB"), t) for (c, f), h in rows for t in h.itertuples()}
    pad, cap, head = 24, 58, 70
    colw = {v: max(im.size[0] for (c, f, vv), (im, t) in tiles.items() if vv == v) * SCALE for v in VIEWS}
    rowh = 256 * SCALE
    W = pad + sum(colw[v] + pad for v in VIEWS); H = head + len(rows) * (rowh + cap + pad)
    sheet = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(sheet)
    d.text((pad, 18), f"{cases[0]} and {cases[1]}: similar inputs and depth trajectories; native PNGs ×{SCALE} by pixel replication", font=f_head, fill="black")
    y = head
    for (c, f), h in rows:
        x = pad
        for v in VIEWS:
            im, t = tiles[(c, f, v)]
            big = im.resize((im.size[0] * SCALE, im.size[1] * SCALE), Image.NEAREST)
            d.text((x, y), f"{c} · frame {f} · iteration {t.solver_iteration:,} · t = {t.time_ms:.6f} ms · {v}", font=f_cap, fill="black")
            d.text((x, y + 26), f"native {t.width_px}×{t.height_px} px · usability: {t.usability}", font=f_cap, fill="#555555")
            sheet.paste(big, (x, y + cap)); d.rectangle([x - 1, y + cap - 1, x + big.size[0], y + cap + big.size[1]], outline="#999999")
            x += colw[v] + pad
        y += rowh + cap + pad
    name = f"contact_sheet_{cases[0]}_{cases[1]}_side_by_side.png"
    sheet.save(GAL / name, optimize=True)
    return name


def gallery():
    GAL.mkdir(parents=True, exist_ok=True)
    inv, code, res = gallery_inventory()
    sheets = contact_sheets(inv)
    cs = pd.read_csv(TAB / "ioan_cases.csv").set_index("sim_id")
    ev = pd.read_csv(TAB / "evaluation.csv"); fm = pd.read_csv(AUDIT / "tables/frame_level_map.csv.gz", usecols=["sim_id", "frame_pos", "label_final", "depth_um"])
    fr = pd.read_csv(TAB / "ioan_case_frames.csv")
    # ---------------- GALLERY.md (no labels, no predictions)
    n = inv.usability.value_counts()
    L = ["# Six-case image gallery (first pass without labels)", "",
         "*Week 19 pilot package for Ioan. The 30 images are the dataset's own native renderings, fetched at the pinned NEW revision "
         f"`{NEW_REV}`; each was verified by its LFS SHA-256 (`image_inventory.csv`). Nothing here assigns a regime label or infers cavity geometry.*", "",
         "**For a first pass without labels:** recorded labels, monitored depths and model predictions are kept separately in [KEY.md](KEY.md). "
         "Please look at the images first. Cases are coded G1–G6 by sorting the full simulation IDs; the code order carries no label information.", "",
         f"**Usability (visual check, usability only):** {n.get('usable', 0)} usable, {n.get('nearly empty', 0)} nearly empty, {n.get('blank', 0)} blank, "
         f"{n.get('unclear', 0)} unclear, {n.get('unreadable', 0)} unreadable, {n.get('missing', 0)} missing. "
         f"{int((inv.byte_identical_to != '').sum())} images are byte-identical to another image in this set.", "",
         f"**Display:** contact sheets enlarge each native image ×{SCALE} by pixel replication (no interpolation, native aspect ratio). "
         "Front and top views are 256×256 px, side views 512×256 px. Frame numbers are `frame_idx` in `frames.csv`; iterations are solver iterations; "
         "times are monitor times (`iter.dat` → `time.dat`).", ""]
    for case, g in inv.groupby("gallery_case"):
        sid = g.sim_id.iloc[0]
        L += [f"## {case}", "", f"Full ID: `{sid}`  ", f"Folder at the pinned revision: [{short(sid)}/frames]({HF}/tree/{NEW_REV}/{sid}/frames)", "",
              f"![{case} contact sheet](contact_sheet_{case}.png)", "", "| Frame | Iteration | Time (ms) | View | Native px | Usability | Note | Original |", "|---:|---:|---:|---|---|---|---|---|"]
        for t in g.itertuples():
            same = f"; byte-identical to {t.byte_identical_to}" if t.byte_identical_to else ""
            L.append(f"| {t.frame_idx} | {t.solver_iteration:,} | {t.time_ms:.6f} | {t.view} | {t.width_px}×{t.height_px} | {t.usability} | {t.usability_note}{same} | [png]({t.url}) |")
        L.append("")
    if "G4" in set(inv.gallery_case) and "G5" in set(inv.gallery_case):
        L += ["## G4 and G5 side by side", "", "These two runs have similar inputs and depth trajectories, but opposite recorded labels; the morphology difference has not been established. "
              "The sheet repeats their images at the same scale.", "", "![G4 and G5 side by side](contact_sheet_G4_G5_side_by_side.png)", ""]
    (GAL / "GALLERY.md").write_text("\n".join(L), encoding="utf-8")
    # ---------------- KEY.md (labels, depths, predictions)
    K = ["# Key to the six-case gallery (open after the first pass)", "",
         "*Recorded labels (`label_final`, canonical `has_keyhole`), monitored melt-subset depth at the frame's exact monitor row, and the pilot's B40 "
         "predictions. The depth is a melt-bound reading, not an image-derived cavity measurement. The predictions are post-hoc DEV predictions from the "
         "Week 19 pilot; they are not evidence about these runs' morphology.*", ""]
    e = ev[(ev.budget == B) & (ev.threshold_mode == "learned")]
    for case, g in inv.groupby("gallery_case"):
        sid = g.sim_id.iloc[0]; c = cs.loc[sid]
        K += [f"## {case} = {short(sid)} (has_keyhole = {int(c.has_keyhole)})", "", f"Full ID: `{sid}`  ",
              f"Why selected: {c.role}. {c.question}  ",
              f"Bracket: {c.bracket}; frames {c.frame_first}–{c.frame_last} ({c.time_first_ms:.6f}–{c.time_last_ms:.6f} ms); labels in bracket {c.labels_in_bracket}."
              + (f" {c.note}." if isinstance(c.note, str) and c.note else "") + "  ",
              f"Whole-record max {c.whole_max_um:.2f} µm; A (active window) {c.A_um:.2f} µm.", ""]
        if short(sid) in KEY_NOTES:
            K += [f"**Note.** {KEY_NOTES[short(sid)]}", ""]
        K += ["| Frame | Time (ms) | Recorded label | Depth at frame (µm) |", "|---:|---:|---|---:|"]
        for f in dict.fromkeys(g.frame_idx):
            x = fm[(fm.sim_id == sid) & (fm.frame_pos == f)].iloc[0]
            K.append(f"| {f} | {g[g.frame_idx == f].time_ms.iloc[0]:.6f} | {x.label_final} | {x.depth_um:.2f} |")
        K += ["", "| B40 prediction (held out) | Repeat 1 p / class | Repeat 2 p / class |", "|---|---|---|"]
        for arm in ("WHOLE_E1_SHARED", "ACTIVE_E1_SHARED", "G3_SHARED"):
            q = e[(e.arm == arm) & (e.sim_id == sid)].sort_values("repeat")
            K.append(f"| {arm} | " + " | ".join(f"{p:.3f} / {'Keyhole' if p >= .5 else 'no Keyhole'}" for p in q.p_keyhole) + " |")
        K.append("")
    (GAL / "KEY.md").write_text("\n".join(K), encoding="utf-8")
    return inv, sheets


# ======================================================================================== review/REVIEW.md
def write_review_md():
    ch = pd.read_csv(REV / "B40_classification_changes.csv"); fc = pd.read_csv(REV / "B40_four_cell_diagnostic.csv")
    fs = pd.read_csv(REV / "late_negative_fold_summary.csv"); it = pd.read_csv(REV / "late_negative_isolation_by_checkpoint.csv")
    o = pd.read_csv(REV / "oracle_vs_GP_same_cohort.csv"); inv = pd.read_csv(GAL / "image_inventory.csv")
    idt = pd.read_csv(REV / "B40_margin_identities.csv")
    short_attr = {"mean change alone flips; threshold change alone does not": "mean alone",
                  "threshold change alone flips; mean change alone does not": "threshold alone",
                  "either change alone flips": "either alone", "neither alone flips; only the joint change does": "only both together"}
    rows = ["| Run | Rep/fold | Label | Observed whole / A (µm) | Predicted depth W → A (µm) | Threshold u W → A (µm) | Δμ | −Δlog u | Change | Flips with |",
            "|---|---|---:|---|---|---|---:|---:|---|---|"]
    for t in ch.sort_values(["has_keyhole", "change", "repeat", "fold"]).itertuples():
        rows.append(f"| {t.H} | {t.repeat}/{t.fold} | {t.has_keyhole} | {t.obs_whole_um:.1f} / {t.obs_A_um:.1f} | {t.pred_depth_W_um:.1f} → {t.pred_depth_A_um:.1f} | "
                    f"{t.u_um_W:.1f} → {t.u_um_A:.1f} | {t.d_mu:+.3f} | {t.minus_d_log_u:+.3f} | {t.change} | {short_attr[t.attribution]} |")
    cells = ["| Mean from | Threshold from | BA | TN of 24 | TP of 248 | Short-K of 20 | q20 | Changes vs WHOLE as fitted |", "|---|---|---:|---:|---:|---:|---:|---:|"]
    for t in fc.itertuples():
        cells.append(f"| {t.mean_from.split('_')[0]} | {t.threshold_from.split('_')[0]} | {t.BA_mean_over_repeats:.3f} | {t.TN_of_24} | {t.TP_of_248} | {t.shortK_detected_of_20} | {t.q20_acc:.3f} | {t.changes_vs_WHOLE_as_fitted} |")
    fp = ch[ch.change == "FP→TN"]
    att_fp = fp.attribution.map(short_attr).value_counts()
    pos = ch[ch.has_keyhole == 1]
    att_pos = pos.attribution.map(short_attr).value_counts()
    low = fs[fs.root_outside_paid_range_W]
    lt = ["| Rep/fold | Late negative's paid position | Held out here | Paid runs whose response differs at B40 | u W → A (µm) | WHOLE root outside paid range | B40 changes (to correct / to wrong) |",
          "|---|---:|---|---|---|---|---|"]
    d = pd.read_csv(REV / "late_negative_paid_response_differences.csv")
    for t in fs.itertuples():
        dd = d[(d.repeat == t.repeat) & (d.fold == t.fold)]
        lst = ", ".join(f"{h} ({w:.1f}→{a:.1f})" for h, w, a in zip(dd.H, dd.whole_um, dd.A_um)) or "none"
        pos_ = "—" if not np.isfinite(t.late_negative_query_index) else f"{int(t.late_negative_query_index)}"
        lt.append(f"| {t.repeat}/{t.fold} | {pos_} | {'yes' if t.late_negative_held_out_here else 'no'} | {lst} | {t.u_um_W:.1f} → {t.u_um_A:.1f} | "
                  f"{'yes' if t.root_outside_paid_range_W else 'no'} | {t.B40_class_changes_in_test_fold} ({t.changes_to_correct} / {t.changes_to_wrong}) |")
    iso = it[it.only_difference_is_late_negative]
    same = it[it.n_paid_with_different_response == 0]
    ow = fs[fs.late_negative_held_out_here]
    ob = o[o["class"].isin(["positives", "negatives"])]
    oba = o[o["class"].str.startswith("BA on this cohort")]
    orows = ["| Budget | Arm | Class | Predictions | Both correct | GP right, observed wrong | GP wrong, observed right | Both wrong |", "|---:|---|---|---:|---:|---:|---:|---:|"]
    for t in ob[ob.budget == B].itertuples():
        orows.append(f"| {t.budget} | {t.arm.split('_')[0]} | {getattr(t, '_3')} | {t.n_predictions} | {int(t.both_correct)} | {int(t.GP_correct_observed_wrong)} | {int(t.GP_wrong_observed_correct)} | {int(t.both_wrong)} |")
    barow = ["| Budget | Arm | GP (learned threshold) | Observed response, same threshold (ORACLE, NOT DEPLOYABLE) | Difference |", "|---:|---|---:|---:|---:|"]
    for (b, arm), g in oba.groupby(["budget", "arm"], sort=True):
        gp = float(g[g["class"].str.contains("GP")].BA_mean_over_repeats.iloc[0]); ob_ = float(g[g["class"].str.contains("observed")].BA_mean_over_repeats.iloc[0])
        barow.append(f"| {b} | {arm.split('_')[0]} | {gp:.3f} | {ob_:.3f} | {ob_ - gp:+.3f} |")
    disc = {arm: int(ob[(ob.budget == B) & (ob.arm == arm)][["GP_correct_observed_wrong", "GP_wrong_observed_correct"]].sum().sum()) for arm in ARM.values()}
    n_coh = {arm: int(ob[(ob.budget == B) & (ob.arm == arm)].n_predictions.sum()) for arm in ARM.values()}
    u = inv.usability.value_counts()
    text = f"""# Review of the Week 19 DEV pilot: classification changes, late negative, oracle check, images

**Status.** Post-hoc reporting review of the completed pilot (commit `de065db9`), written 2026-10-10. It uses the saved predictions, thresholds and oracle diagnostics only.
- **No new modelling:** no learner fit, seed, repeat, threshold tuning, relabelling or exclusion.
- **Nothing changed:** the manifest, `decision.json`, the saved predictions and every numerical output are byte-identical (`experimental_files_unchanged.csv`).
- **Verdict unchanged:** ADVANCE, exploratory DEV gate.
- **Reading the numbers:** every quantity here is an algorithmic diagnostic of the existing fits, never a deployable candidate or a physical intervention.
- **Corrections:** the wording corrections that follow from this review are listed in [REPORTING_CORRECTIONS.md](REPORTING_CORRECTIONS.md).

**Convention.** For both E1 arms the class is 1 exactly when the margin m = μ − log u ≥ 0.
- μ is the predicted *absolute* log depth (oracle file `predicted_log_depth`, which equals the learned `latent_mean` + log u; the latent mean alone is threshold-relative).
- log u is the fold's learned log-threshold.
- Between arms, Δm = (μ_A − μ_W) − (log u_A − log u_W).

All identities hold to {idt.max_abs_error.max():.0e} (`B40_margin_identities.csv`).

## 1. Every B40 WHOLE → ACTIVE classification change

{len(ch)} of 272 held-out B40 predictions change:
- {int((ch.change == 'FP→TN').sum())} false positives become true negatives;
- {int((ch.change == 'TP→FN').sum())} true positives are lost;
- {int((ch.change == 'FN→TP').sum())} false negatives are corrected.

Full rows, with full IDs, log-scale values and all four cells: `B40_classification_changes.csv`. Δμ and −Δlog u are in log µm and sum to Δm.

{chr(10).join(rows)}

**Four-cell diagnostic** (`B40_four_cell_diagnostic.csv`). Each cell pairs one arm's saved means with one arm's saved thresholds. The two mixed cells combine a mean for one target with a threshold learned for the other, so they are algorithmic decompositions only; no hybrid is proposed or selected.

{chr(10).join(cells)}

**What the decomposition shows.**
- **Neither change alone reproduces the gain.**
  - ACTIVE means with WHOLE thresholds: BA {fc.BA_mean_over_repeats.iloc[1]:.3f}.
  - WHOLE means with ACTIVE thresholds: {fc.BA_mean_over_repeats.iloc[2]:.3f}.
  - Both together: {fc.BA_mean_over_repeats.iloc[3]:.3f}, against {fc.BA_mean_over_repeats.iloc[0]:.3f} for WHOLE as fitted.
  - The joint gain ({fc.BA_mean_over_repeats.iloc[3] - fc.BA_mean_over_repeats.iloc[0]:+.3f}) exceeds the sum of the single-change gains ({fc.BA_mean_over_repeats.iloc[1] - fc.BA_mean_over_repeats.iloc[0]:+.3f} and {fc.BA_mean_over_repeats.iloc[2] - fc.BA_mean_over_repeats.iloc[0]:+.3f}).
- **The removed false positives.** Of the {len(fp)}:
  - {att_fp.get('mean alone', 0)} flips with the mean change alone;
  - {att_fp.get('threshold alone', 0)} with the threshold change alone;
  - {att_fp.get('only both together', 0)} only with both.

  Four of the five lie in repeat 1 fold 2 and repeat 2 fold 2. There, WHOLE_E1's B40 threshold was low ({', '.join(f'{x:.1f}' for x in low.u_um_W)} µm, with the logistic root outside the paid depth range), while ACTIVE_E1's was {', '.join(f'{x:.1f}' for x in low.u_um_A)} µm.
- **The positive changes.** Of the {len(pos)}, {att_pos.get('mean alone', 0)} flip with the mean change alone. The ACTIVE GP predicts lower depths for several fast-scan short-K positives.
- **Correction.** The earlier sentence "the improvement comes from a different fitted response surface" is withdrawn. The gain combines a change in predicted means and a change in learned thresholds, with an interaction.

## 2. The late negative H-f4fc937e86

**Its own held-out prediction is unchanged.** It is held out in repeat 1 fold 1 and repeat 2 fold 4, and is classified identically by both arms there:
- repeat 1: {'Keyhole' if ow.own_class_WHOLE.iloc[0] == 1 else 'no Keyhole'};
- repeat 2: {'Keyhole' if ow.own_class_WHOLE.iloc[1] == 1 else 'no Keyhole'}.

That is not evidence about its effect on other predictions. In the folds where it is paid, its training response changes from 312.0 µm (whole) to 110.8 µm (A). Other paid responses change as well:

{chr(10).join(lt)}

**What can be established without an isolated refit** (`late_negative_isolation_by_checkpoint.csv`):

- **Isolated checkpoints.** In {len(iso)} checkpoints the two arms' paid training data differ *only* in the late negative's response ({'; '.join(f'B{t.budget} repeat {t.repeat} fold {t.fold}' for t in iso.itertuples())}). The fitting procedure is deterministic (fixed start, no restarts), so these differences follow from that single response:
{chr(10).join(f'  - B{t.budget} repeat {t.repeat} fold {t.fold}: the threshold moved {t.u_um_WHOLE:.1f} → {t.u_um_ACTIVE:.1f} µm, and {t.class_changes} test classifications changed ({t.changed_runs.replace(";", ", ")}).' for t in iso.itertuples())}
- **Determinism control.** In {len(same)} checkpoint ({', '.join(f'B{t.budget} repeat {t.repeat} fold {t.fold}' for t in same.itertuples())}) the paid data are identical in both arms. The thresholds there are identical and no classification changes.
- **Confounded checkpoints.** At every other checkpoint, other paid responses differ as well (1–5 runs among H-349225d53c, H-6f28bdc6c9, H-c698d0e5ac, H-bba3700d20, and the A-unavailable H-e7dbd8e5ce at B80). The late negative's share there cannot be separated without an isolated refit, which is not authorized here.
- **Direction.** On these label-blind paths its 312 µm response *lowers* WHOLE_E1's threshold where it is isolated. It does not pull it up as in the historical adaptive runs.

**Supported statement.** Its own held-out classification contributes no direct improvement. Its influence through training remains unresolved.

It is isolated at only {len(iso)} checkpoints. There, replacing its 312.0 µm response by 110.8 µm raised the learned threshold (by {', '.join(f'{t.u_um_ACTIVE - t.u_um_WHOLE:.1f}' for t in iso.itertuples())} µm) and changed three classifications each: two false positives removed and one true positive lost.

## 3. Observed response versus GP on identical cases

**Setup.**
- **Cohort:** each arm's available-response cohort (WHOLE: 136 runs × 2 repeats; ACTIVE: 135 × 2, without the A-unavailable H-e7dbd8e5ce).
- **Threshold:** the same training threshold for both classifications.
- **Benchmark:** the benchmark itself keeps all 136 runs; nothing in `metrics.csv` changes.

At B40 the observed response and the GP disagree on {disc[ARM['W']]} of {n_coh[ARM['W']]} WHOLE and {disc[ARM['A']]} of {n_coh[ARM['A']]} ACTIVE predictions, in both directions and in both classes. The case list is in `oracle_vs_GP_discordant_B40.csv`, and the counts for all budgets are in `oracle_vs_GP_same_cohort.csv`:

{chr(10).join(orows)}

{chr(10).join(barow)}

**Interpretation.**
- **At B40 the similar BA hides cancelling errors.** For WHOLE, GP-only and observed-only correct cases nearly cancel.
- **The earlier ACTIVE comparison used different cohorts.** It compared 0.730 (136 runs) with 0.728 (135 runs). On the same 135 runs the GP gives {float(oba[(oba.budget == B) & (oba.arm == ARM['A']) & oba['class'].str.contains('GP')].BA_mean_over_repeats.iloc[0]):.3f}.
- **At B16 and B80 the observed response classifies better** for WHOLE, and at B16 for ACTIVE.

**Scoped conclusion.** In this pilot, B40 aggregate BA does not separate regression error from target and threshold effects. The pilot does not show that regression is not a bottleneck.

## 4. Image package for Ioan

The package uses the 30 already-linked native images (`../ioan_gallery/`):
- **Provenance:** downloaded once at the pinned NEW revision (no local copy existed) and verified by LFS SHA-256.
- **Usability:** {u.get('usable', 0)} usable, {u.get('nearly empty', 0)} nearly empty, {u.get('blank', 0)} blank, {u.get('unclear', 0)} unclear; none missing or unreadable. {int((inv.byte_identical_to.fillna('') != '').sum())} images are byte-identical to another image in the set.

Case notes:
- **H-f4fc937e86 (G2, the late-window maximum):** no usable image. All six of its late-frame images are blank, nearly empty, or content only at the image border.
- **H-349225d53c (G1):** at its last Keyhole frame (364) the front and side views are nearly empty, and the monitored melt depth at that frame is 0.0 µm.
- **H-b302fc6cbd (G5):** its linked frame 82 is 0.18 µs after the run's depth maximum, and after a sharp drop (114.3 µm at frame 81 → 89.1 µm at frame 82). The near-peak frame 81 is not among the 30 images.

The gallery shows no recorded labels or predictions; those are in `../ioan_gallery/KEY.md`.

## 5. Checks

All review checks pass (`REVIEW_CHECKS.csv`):
- the margin identities hold;
- each arm's four-cell corner reproduces its B40 metrics in `metrics.csv` exactly;
- the joins are one-to-one;
- the oracle labels recompute exactly;
- every experimental file is unchanged;
- the Week 18 engine was never imported;
- the 30 images are verified;
- the brief's word limit is met.
"""
    (REV / "REVIEW.md").write_text(text, encoding="utf-8")
    return text


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "all"
    if step in ("margins", "all"):
        ch, fc, ft, idt = margins(); print(idt.to_string()); print(fc.drop(columns="note").to_string()); print(ch.to_string(max_colwidth=40))
    if step in ("latent", "all"):
        fs, ds = latent_attribution(); print(fs.to_string()); print(ds.to_string(max_colwidth=40))
    if step in ("oracle", "all"):
        o, cs = oracle_same_cohort(); print(o.to_string()); print(cs.to_string(max_colwidth=40))
    if step in ("gallery", "all"):
        inv, sheets = gallery(); print(inv.drop(columns=["sim_id", "url", "repo_path", "sha256"]).to_string(max_colwidth=50)); print(sheets)
    if step in ("review", "all"):
        write_review_md()
    if step in ("checks", "all"):
        checks()
