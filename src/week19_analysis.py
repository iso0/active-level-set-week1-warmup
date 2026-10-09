"""Week 19 Phases 2-3 and the out-of-fold diagnostics (descriptive; no model is fitted).

Phase 2: OLD vs NEW regime descriptors, K fractions, switch timing and input-region concentrations
         (simulation-level summaries; monitor rows are not treated as independent experiments).
Phase 3: separability of the depth definitions (frozen whole-record maximum, A, B, C, D).  A threshold chosen on the
         same population is a descriptive ORACLE separation, never held-out performance.  Transfer thresholds are
         chosen on OLD only.  B and D_postforming use manual labels (annotation-dependent, POST-HOC).
OOF:     existing Week 18 DEV out-of-fold predictions (repeats 1-8; E1 = GPR_depth|mlii|straddle from
         phase3/depth3, reference G3|mlii|margin from phase2).  No retraining.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from src.week19_sources import OUT

TAB = OUT / "tables"
W18 = OUT.parent / "week18_independent_research"
INCOMPLETE = ("bounds_time_row_mismatch", "frame_timing_unmappable", "no_active_regime_label")
VX_BINS = [0.2, 0.4, 0.6, 0.8, 0.9, 1.0001]
P_BINS = [50, 150, 250, 350, 450.0001]


def _w(df, name):
    TAB.mkdir(parents=True, exist_ok=True)
    df.to_csv(TAB / name, index=False, lineterminator="\n")


# ------------------------------------------------------------------ helpers
def auc(y, s):
    m = np.isfinite(s)
    y, s = np.asarray(y)[m], np.asarray(s)[m]
    return float(roc_auc_score(y, s)) if len(np.unique(y)) == 2 else np.nan


def ba_at(y, s, c):
    m = np.isfinite(s); y, s = np.asarray(y)[m], np.asarray(s)[m]
    if len(np.unique(y)) < 2:
        return np.nan
    pred = s >= c
    return float(0.5 * (pred[y == 1].mean() + (~pred[y == 0]).mean()))


def confusion(y, s, c):
    m = np.isfinite(s); y, s = np.asarray(y)[m], np.asarray(s)[m]
    pred = s >= c
    return {"TP": int((pred & (y == 1)).sum()), "FN": int((~pred & (y == 1)).sum()), "TN": int((~pred & (y == 0)).sum()),
            "FP": int((pred & (y == 0)).sum())}


def oracle(y, s):
    """Descriptive best single threshold (rule s >= c) on the same population (ORACLE, not held-out)."""
    m = np.isfinite(s); y, s = np.asarray(y)[m], np.asarray(s)[m]
    if len(np.unique(y)) < 2:
        return np.nan, np.nan
    best = max(((ba_at(y, s, c), c) for c in np.unique(s)))
    return best


def e1_rule(y, v):
    """E1's learned-threshold rule (src/week18_engine.py::DepthGPR.fit) on log values: midpoint of the separated gap,
    else 1-D logistic regression (C=1e6)."""
    from sklearn.linear_model import LogisticRegression
    m = np.isfinite(v) & (np.asarray(v) > 0)
    y, t = np.asarray(y)[m], np.log(np.asarray(v)[m])
    kh, nk = t[y == 1], t[y == 0]
    if not (len(kh) and len(nk)):
        return np.nan
    if nk.max() < kh.min():
        return float(np.exp(.5 * (nk.max() + kh.min())))
    lr = LogisticRegression(C=1e6, max_iter=5000).fit(t[:, None], y)
    return float(np.exp(-lr.intercept_[0] / lr.coef_[0, 0]))


DEFS = [  # (column, label, uses_manual_labels, is_depth_um)
    ("max_depth_whole_um", "frozen: whole-record maximum (E1 target)", False, True),
    ("A_active_max_um", "A: max in pipeline active window (startup retained)", False, True),
    ("B_postforming_max_um", "B: max after first C/K frame, before cutoff (annotation-dependent)", True, True),
    ("G3_persistent_depth_um", "C: G3 persistent depth (50 um rolling median, adaptive interior)", False, True),
    ("T0_depth_um", "C: T0 depth (median, final 20% of active window)", False, True),
    ("D_whole_frac_above_uref", "D: fraction of valid-row time >= u_ref, whole record", False, False),
    ("D_active_frac_above_uref", "D: fraction of time >= u_ref, active window", False, False),
    ("D_postforming_frac_above_uref", "D: fraction of time >= u_ref, after first C/K frame (annotation-dependent)", True, False),
    ("D_interior_frac_above_uref", "D: fraction of time >= u_ref, adaptive interior", False, False),
    ("D_active_ms_above_uref", "D: time >= u_ref in active window (ms)", False, False),
]


# ------------------------------------------------------------------ Phase 3: depth comparison and separability
def depth_tables(reg, u):
    uref = u["u_ref_um"]
    pop = pd.read_csv(OUT.parent / "week7_06_real_data_boundary_active_level_set/primary_common_population.csv",
                      usecols=["experiment_name", "max_depth_um", "G3_persistent_depth_um", "T0_depth_um", "max_depth_time_s",
                               "laser_exit_time_s", "active_cutoff_time_s", "T0_start_time_s", "T0_end_time_s"]).rename(columns={"experiment_name": "sim_id"})
    nd = pd.read_csv(W18 / "phase1/new_depth.csv", usecols=["sim_id", "max_depth_um", "max_depth_row_index"])
    frozen = pd.concat([pop[["sim_id", "max_depth_um"]], nd[["sim_id", "max_depth_um"]]]).rename(columns={"max_depth_um": "max_depth_frozen_um"})
    d = reg.merge(frozen, on="sim_id", how="left").merge(pop.drop(columns=["max_depth_um"]).rename(columns=lambda c: c if c == "sim_id" else f"w7_{c}"), on="sim_id", how="left")
    d["max_depth_abs_diff_vs_frozen"] = (d.max_depth_whole_um - d.max_depth_frozen_um).abs()
    d["G3_abs_diff_vs_week7"] = (d.G3_persistent_depth_um - d.w7_G3_persistent_depth_um).abs()
    d["T0_abs_diff_vs_week7"] = (d.T0_depth_um - d.w7_T0_depth_um).abs()
    d["exit_abs_diff_vs_week7_ms"] = (d.derived_exit_ms - d.w7_laser_exit_time_s * 1e3).abs()
    d["cutoff_abs_diff_vs_week7_ms"] = (d.active_cutoff_ms - d.w7_active_cutoff_time_s * 1e3).abs()
    d["y"] = d.has_keyhole_frozen.astype(int)
    d["incomplete_flag"] = d.record_flags.fillna("").apply(lambda f: int(any(k in f for k in INCOMPLETE)))
    d["early_end_flag"] = d.record_flags.fillna("").str.contains("recording_ends_before_90pct_domain").astype(int)
    keep = ["sim_id", "campaign", "partition", "y", "descriptor", "frac_K_FCK", "frac_K_KC", "P", "VX", "LS_um_radius", "ST",
            "max_depth_frozen_um", "max_depth_whole_um", "max_depth_abs_diff_vs_frozen", "max_depth_whole_ms", "max_depth_whole_location",
            "max_depth_whole_in_interior", "max_depth_whole_label_phase", "max_frames_after_first_active_frame", "A_max_label_phase",
            "A_max_frames_after_first_active_frame", "G3_event_label_phase",
            "max_depth_whole_is_last_row", "A_active_max_um", "A_active_max_ms", "B_postforming_max_um", "B_postforming_max_ms",
            "G3_persistent_depth_um", "G3_event_ms", "w7_G3_persistent_depth_um", "G3_abs_diff_vs_week7", "T0_depth_um", "w7_T0_depth_um",
            "T0_abs_diff_vs_week7", "D_whole_frac_above_uref", "D_whole_ms_above_uref", "D_active_frac_above_uref", "D_active_ms_above_uref",
            "D_postforming_frac_above_uref", "D_postforming_ms_above_uref", "D_interior_frac_above_uref", "D_interior_ms_above_uref",
            "first_active_frame_ms", "last_F_ms", "active_cutoff_ms", "derived_exit_ms", "recording_end_ms", "first_SS_ms",
            "exit_abs_diff_vs_week7_ms", "cutoff_abs_diff_vs_week7_ms", "rows_ge300", "episodes_ge300", "longest_episode_ge300_ms",
            "rows_ge_uref", "episodes_ge_uref", "longest_episode_ge_uref_ms", "frac_C_frames_depth_ge_uref", "depth_at_C_frames_max_um",
            "frac_K_frames_depth_ge_uref", "depth_at_K_frames_median_um", "incomplete_flag", "early_end_flag", "record_flags", "failure"]
    d = d[[c for c in keep if c in d.columns]]
    d.insert(d.columns.get_loc("B_postforming_max_um"), "B_uses_manual_labels", 1)
    _w(d, "depth_definitions.csv")
    rows = []
    old = d[d.campaign == "OLD"]
    for col, label, manual, is_depth in DEFS:
        thr_old_oracle = oracle(old.y, old[col].to_numpy(float))[1]
        thr_old_e1 = e1_rule(old.y.to_numpy(), old[col].to_numpy(float)) if is_depth else np.nan
        for popname, sub in [("OLD", old), ("NEW", d[d.campaign == "NEW"]), ("POOLED", d)]:
            for variant, s2 in [("full", sub), ("excluding_incomplete", sub[sub.incomplete_flag == 0]),
                                ("excluding_incomplete_and_early_end", sub[(sub.incomplete_flag == 0) & (sub.early_end_flag == 0)])]:
                y = s2.y.to_numpy(); v = s2[col].to_numpy(float)
                fin = np.isfinite(v)
                r = {"definition": col, "label": label, "uses_manual_labels": int(manual), "population": popname, "variant": variant,
                     "n": int(len(s2)), "n_available": int(fin.sum()), "n_pos": int((y[fin] == 1).sum()), "n_neg": int((y[fin] == 0).sum()),
                     "unavailable_ids": ";".join(s2.sim_id[~fin].tolist()) if (~fin).sum() <= 5 else f"{int((~fin).sum())} ids",
                     "AUC": auc(y, v)}
                if fin.any() and (y[fin] == 1).any() and (y[fin] == 0).any():
                    pv, nv = v[fin & (y == 1)], v[fin & (y == 0)]
                    r.update({"pos_min": float(pv.min()), "pos_median": float(np.median(pv)), "neg_median": float(np.median(nv)), "neg_max": float(nv.max()),
                              "neg_at_or_above_pos_min": int((nv >= pv.min()).sum()), "pos_at_or_below_neg_max": int((pv <= nv.max()).sum())})
                ob, oc = oracle(y, v)
                r.update({"oracle_BA_same_population": ob, "oracle_threshold_same_population": oc})
                if is_depth:
                    cf = confusion(y, v, u["u_ref_um"]); r.update({f"uref_{k}": x for k, x in cf.items()}); r["uref_BA"] = ba_at(y, v, u["u_ref_um"])
                    r["old_e1_rule_threshold"] = thr_old_e1
                    cf = confusion(y, v, thr_old_e1); r.update({f"oldE1thr_{k}": x for k, x in cf.items()}); r["oldE1thr_BA"] = ba_at(y, v, thr_old_e1)
                r["old_oracle_threshold"] = thr_old_oracle
                cf = confusion(y, v, thr_old_oracle); r.update({f"oldOracleThr_{k}": x for k, x in cf.items()}); r["oldOracleThr_BA"] = ba_at(y, v, thr_old_oracle)
                rows.append(r)
    sep = pd.DataFrame(rows)
    _w(sep, "separability.csv")
    return d, sep


def negative_cases(d, reg, u):
    """All 12 NEW negatives, one row each, with a mechanism category relative to the OLD reference threshold."""
    uref = u["u_ref_um"]
    R = reg.set_index("sim_id")
    neg = d[(d.campaign == "NEW") & (d.y == 0)].copy()
    pos_new = d[(d.campaign == "NEW") & (d.y == 1)]
    old = d[d.campaign == "OLD"]
    rows = []
    for r in neg.itertuples(index=False):
        g = R.loc[r.sim_id]
        mx, A, B, G3 = r.max_depth_whole_um, r.A_active_max_um, r.B_postforming_max_um, r.G3_persistent_depth_um
        if not mx >= uref:
            mech, status = "no_disagreement_under_frozen_target", "agrees"
        elif "bounds_time_row_mismatch" in str(r.record_flags) or not np.isfinite(A):
            mech, status = "incomplete_observation", "accounted_for_as_incomplete"
        elif A < uref:
            mech, status = "late_window_maximum", "accounted_for_by_window"
        elif not (np.isfinite(B) and B >= uref):
            mech = "startup_related_event" + ("__also_passes_G3" if (np.isfinite(G3) and G3 >= uref) else "")
            status = "accounted_for_by_manual_forming_window"
        else:
            persistent = np.isfinite(G3) and G3 >= uref and g.G3_event_label_phase == "at_or_after_first_C_or_K_frame"
            mech = "active_elevated_depth_after_first_C_frame__" + ("persistent_G3_ge_uref" if persistent else "transient_G3_lt_uref")
            status = "unresolved_mechanism"
        rows.append({"sim_id": r.sim_id, "H": r.sim_id.split("_H-")[-1], "P_W": r.P, "VX_m_s": r.VX, "LS_um_radius": r.LS_um_radius, "ST_K": r.ST,
                     "label_counts": f"IE={g.n_IE},F={g.n_F},C={g.n_C},K={g.n_K},SS={g.n_SS},SoS={g.n_SoS}",
                     "descriptor": g.descriptor, "collapsed_sequence": g.collapsed_sequence, "record_flags": r.record_flags,
                     "max_depth_frozen_um": r.max_depth_frozen_um, "max_depth_whole_um": mx, "max_ms": r.max_depth_whole_ms,
                     "max_pipeline_window": r.max_depth_whole_location, "max_in_adaptive_interior": g.max_depth_whole_in_interior,
                     "max_label_phase": g.max_depth_whole_label_phase, "max_frames_after_first_C_or_K_frame": g.max_frames_after_first_active_frame,
                     "A_max_frames_after_first_C_or_K_frame": g.A_max_frames_after_first_active_frame,
                     "G3_event_ms": g.G3_event_ms, "G3_event_label_phase": g.G3_event_label_phase, "max_in_last_row": r.max_depth_whole_is_last_row,
                     "A_active_max_um": A, "B_postforming_max_um": B, "G3_um": G3, "T0_um": r.T0_depth_um,
                     "D_active_frac_above_uref": r.D_active_frac_above_uref, "D_active_ms_above_uref": r.D_active_ms_above_uref,
                     "frac_C_frames_depth_ge_uref": r.frac_C_frames_depth_ge_uref, "max_depth_at_C_frames_um": r.depth_at_C_frames_max_um,
                     "first_active_frame_ms": r.first_active_frame_ms, "last_F_ms": r.last_F_ms, "active_cutoff_ms": r.active_cutoff_ms,
                     "derived_exit_ms": r.derived_exit_ms, "recording_end_ms": r.recording_end_ms, "first_SS_ms": r.first_SS_ms,
                     "rows_ge300": r.rows_ge300, "episodes_ge300": r.episodes_ge300, "longest_episode_ge300_ms": r.longest_episode_ge300_ms,
                     "new_positives_with_max_at_or_below": int((pos_new.max_depth_whole_um <= mx).sum()) if np.isfinite(mx) else np.nan,
                     "mechanism_vs_uref": mech, "mechanism_status": status})
    cases = pd.DataFrame(rows).sort_values("max_depth_whole_um", ascending=False)
    _w(cases, "new_negatives_12_cases.csv")
    # Positives disagreeing with the frozen threshold, and positives under the other definitions
    pos = d[d.y == 1]
    pdis = []
    for col in ["max_depth_whole_um", "A_active_max_um", "B_postforming_max_um", "G3_persistent_depth_um"]:
        for camp in ("OLD", "NEW"):
            s = pos[(pos.campaign == camp)]
            low = s[s[col] < uref]
            pdis.append({"definition": col, "campaign": camp, "n_pos": len(s), "n_available": int(s[col].notna().sum()),
                         "n_below_uref": len(low), "ids_below_uref": ";".join(low.sim_id) if len(low) <= 12 else f"{len(low)} ids (see depth_definitions.csv)"})
    _w(pd.DataFrame(pdis), "positives_below_uref_by_definition.csv")
    mech = cases.groupby(["mechanism_vs_uref", "mechanism_status"]).size().rename("n").reset_index()
    _w(mech, "new_negatives_mechanism_summary.csv")
    return cases, mech


# ------------------------------------------------------------------ Phase 2: OLD vs NEW descriptors and input regions
def phase2_tables(reg, trans):
    reg = reg.copy()
    reg["group"] = np.where(reg.campaign == "NEW", "NEW_OCT", "OLD:" + reg.partition)
    cnt = []
    for grp, sub in list(reg.groupby("campaign")) + list(reg[reg.campaign == "OLD"].groupby("partition")):
        vc = sub.descriptor.value_counts()
        for desc, n in vc.items():
            cnt.append({"group": grp, "descriptor": desc, "n": int(n), "share": n / len(sub), "group_n": len(sub)})
        cnt.append({"group": grp, "descriptor": "ANY_with_keyhole", "n": int(sub.has_keyhole_frozen.sum()), "share": sub.has_keyhole_frozen.mean(), "group_n": len(sub)})
        cnt.append({"group": grp, "descriptor": "K_then_only_C (subset)", "n": int(sub.K_then_only_C.sum()), "share": sub.K_then_only_C.mean(), "group_n": len(sub)})
        cnt.append({"group": grp, "descriptor": "alternation (>=2 K blocks)", "n": int(sub.alternation.sum()), "share": sub.alternation.mean(), "group_n": len(sub)})
        cnt.append({"group": grp, "descriptor": "K_ongoing_at_observation_end", "n": int(sub.K_ongoing_at_observation_end.sum()), "share": sub.K_ongoing_at_observation_end.mean(), "group_n": len(sub)})
        cnt.append({"group": grp, "descriptor": "last_frame_is_K", "n": int(sub.last_frame_is_K.sum()), "share": sub.last_frame_is_K.mean(), "group_n": len(sub)})
    _w(pd.DataFrame(cnt), "descriptor_counts.csv")
    # K fractions among positives (frame-based and time-weighted)
    q = []
    for camp, sub in reg[reg.has_keyhole_frozen == 1].groupby("campaign"):
        for col in ("frac_K_FCK", "frac_K_KC", "K_time_frac_FCK_midpoint", "K_time_frac_KC_midpoint", "n_K", "longest_K_run_frames", "longest_K_run_observed_ms"):
            v = sub[col].dropna()
            q.append({"campaign": camp, "quantity": col, "n": len(v), "min": v.min(), "q10": v.quantile(.1), "q25": v.quantile(.25), "median": v.median(),
                      "q75": v.quantile(.75), "max": v.max(), "n_below_0.05": int((v < .05).sum()) if col.startswith(("frac", "K_time")) else np.nan,
                      "n_below_0.10": int((v < .10).sum()) if col.startswith(("frac", "K_time")) else np.nan})
    _w(pd.DataFrame(q), "positive_K_fraction_summary.csv")
    # Alternative labels: class changes (positives only can change)
    ch = []
    for c in ("alt_K_FCK_ge05", "alt_K_FCK_ge10", "alt_K_KC_ge05", "alt_K_KC_ge10"):
        for camp, sub in reg.groupby("campaign"):
            ids = sub.sim_id[sub[f"class_change_{c}"] == 1].tolist()
            ch.append({"alternative_label": c, "campaign": camp, "n_class_changes_1_to_0": len(ids), "n_undefined": int(sub[c].isna().sum()),
                       "n_positive_frozen": int(sub.has_keyhole_frozen.sum()), "ids": ";".join(ids)})
    _w(pd.DataFrame(ch), "alternative_label_class_changes.csv")
    # Switch timing, simulation level (first and last K->C switch per simulation)
    kc = trans[trans.type == "K_to_C"]
    t1 = []
    for camp, sub in kc.groupby("campaign"):
        first = sub.sort_values("from_pos").groupby("sim_id").head(1); last = sub.sort_values("from_pos").groupby("sim_id").tail(1)
        for nm, s in (("first_K_to_C", first), ("last_K_to_C", last), ("all_K_to_C_switches", sub)):
            vc = s.location.value_counts()
            t1.append({"campaign": camp, "set": nm, "n": len(s), "n_sims": s.sim_id.nunique(), **{f"loc_{k}": int(v) for k, v in vc.items()},
                       "from_over_exit_median": s.from_over_exit.median(), "bracket_width_ms_median": s.bracket_width_ms.median(),
                       "bracket_width_ms_max": s.bracket_width_ms.max(), "n_with_intermediate_frames": int((s.intermediate_labels != "none").sum())})
    _w(pd.DataFrame(t1), "switch_timing_summary.csv")
    # Input-region concentrations
    reg["VX_bin"] = pd.cut(reg.VX, VX_BINS, right=False).astype(str)
    reg["P_bin"] = pd.cut(reg.P, P_BINS, right=False).astype(str)
    ir = []
    for (camp, vb), sub in reg.groupby(["campaign", "VX_bin"]):
        ir.append({"campaign": camp, "VX_bin": vb, "n": len(sub), "n_keyhole": int(sub.has_keyhole_frozen.sum()),
                   "n_conduction_only": int((sub.descriptor == "conduction_only").sum()),
                   "n_K_then_C_no_later_K": int((sub.descriptor == "K_then_C__no_later_K").sum()),
                   "n_K_then_only_C": int(sub.K_then_only_C.sum()), "n_alternation": int(sub.alternation.sum()),
                   "n_K_at_end": int(sub.K_ongoing_at_observation_end.sum()),
                   "median_frac_K_FCK_positives": sub.frac_K_FCK[sub.has_keyhole_frozen == 1].median(),
                   "P_range": f"{sub.P.min():.0f}-{sub.P.max():.0f}", "LS_um_range": f"{sub.LS_um_radius.min():.1f}-{sub.LS_um_radius.max():.1f}"})
    _w(pd.DataFrame(ir), "input_region_by_VX.csv")
    # Common-support comparison: the intersection of the OLD and NEW input boxes
    o, n = reg[reg.campaign == "OLD"], reg[reg.campaign == "NEW"]
    box = {k: (max(o[k].min(), n[k].min()), min(o[k].max(), n[k].max())) for k in ("P", "VX", "LS", "ST")}
    reg["in_common_box"] = np.all([(reg[k] >= lo) & (reg[k] <= hi) for k, (lo, hi) in box.items()], axis=0).astype(int)
    cs = []
    for camp, sub in reg[reg.in_common_box == 1].groupby("campaign"):
        for vb, s2 in [("all", sub), ("VX>=0.85", sub[sub.VX >= .85]), ("VX<0.85", sub[sub.VX < .85])]:
            cs.append({"campaign": camp, "subset": vb, "n": len(s2), "n_keyhole": int(s2.has_keyhole_frozen.sum()),
                       "n_conduction_only": int((s2.descriptor == "conduction_only").sum()), "n_K_then_C": int(s2.descriptor.isin(["K_then_C__no_later_K", "alternating__terminal_C"]).sum()),
                       "n_K_at_end": int(s2.K_ongoing_at_observation_end.sum()), "n_alternation": int(s2.alternation.sum()),
                       "ids_negative": ";".join(s2.sim_id[s2.has_keyhole_frozen == 0]) if (s2.has_keyhole_frozen == 0).sum() <= 12 else f"{int((s2.has_keyhole_frozen == 0).sum())} ids"})
    _w(pd.DataFrame(cs).assign(box=json.dumps({k: [float(a), float(b)] for k, (a, b) in box.items()})), "common_support_comparison.csv")
    # Like-for-like fast-scan cases inside the common box (frame spacing in units of the spot-crossing time LS/VX)
    k1 = None
    runs_path = TAB / "k_runs.csv"
    if runs_path.exists():
        kr = pd.read_csv(runs_path)
        k1 = kr.sort_values("run_number").groupby("sim_id").head(1).set_index("sim_id")
    fc = reg[(reg.in_common_box == 1) & (reg.VX >= 0.85)].copy()
    fc["frame_dt_times_VX_over_LS"] = fc.frame_dt_median_us * 1e-6 * fc.VX / fc.LS
    if k1 is not None:
        fc["first_K_run_frames"] = fc.sim_id.map(k1.frames); fc["first_K_run_observed_us"] = fc.sim_id.map(k1.observed_duration_ms) * 1e3
    fc["first_K_minus_first_active_frame_us"] = (fc.first_K_ms - fc.first_active_frame_ms) * 1e3
    keepc = ["sim_id", "campaign", "has_keyhole_frozen", "descriptor", "P", "VX", "LS_um_radius", "ST", "frame_dt_median_us", "frame_dt_times_VX_over_LS",
             "n_F", "n_C", "n_K", "first_K_run_frames", "first_K_run_observed_us", "first_K_minus_first_active_frame_us", "first_active_frame_ms",
             "max_depth_whole_um", "A_active_max_um", "A_max_label_phase", "A_max_frames_after_first_active_frame", "B_postforming_max_um", "G3_persistent_depth_um"]
    _w(fc[[c for c in keepc if c in fc.columns]].sort_values(["campaign", "has_keyhole_frozen", "A_active_max_um"]), "fast_scan_common_support_cases.csv")
    # Two "K then only C" populations: where the last K->C switch sits relative to the recording end
    kc = trans[trans.type == "K_to_C"].sort_values("from_pos").groupby("sim_id").tail(1).set_index("sim_id")
    kt = reg[reg.descriptor.isin(["K_then_C__no_later_K", "alternating__terminal_C"])].copy()
    kt["last_K_to_C_ms"] = kt.sim_id.map(kc.from_ms)
    kt["frames_after_last_K"] = kt.n_frames - 1 - kt.last_K_pos          # labelled frames (any label) after the last Keyhole frame
    kt["recording_end_minus_last_K_to_C_ms"] = kt.recording_end_ms - kt.last_K_to_C_ms
    kt["VX_group"] = np.where(kt.VX >= 0.85, "fast VX>=0.85", np.where(kt.VX < 0.4, "slow VX<0.4", "mid 0.4<=VX<0.85"))
    sub = kt.groupby(["campaign", "VX_group"]).agg(n=("sim_id", "size"), median_VX=("VX", "median"), median_frac_K_FCK=("frac_K_FCK", "median"),
                                                  median_first_K_ms=("first_K_ms", "median"), median_last_K_to_C_ms=("last_K_to_C_ms", "median"),
                                                  median_frames_after_last_K=("frames_after_last_K", "median"),
                                                  median_recording_end_minus_switch_ms=("recording_end_minus_last_K_to_C_ms", "median"),
                                                  n_recording_ends_before_90pct=("recording_ends_before_90pct_domain", "sum"),
                                                  median_max_depth_um=("max_depth_whole_um", "median"), median_T0_depth_um=("T0_depth_um", "median")).reset_index()
    _w(sub, "K_then_C_subgroups.csv")
    _w(kt[["sim_id", "campaign", "descriptor", "VX_group", "P", "VX", "LS_um_radius", "ST", "n_K", "n_C", "frac_K_FCK", "first_active_frame_ms", "first_K_ms",
           "last_K_to_C_ms", "frames_after_last_K", "recording_end_ms", "recording_end_minus_last_K_to_C_ms", "derived_exit_ms",
           "recording_ends_before_90pct_domain", "max_depth_whole_um", "G3_persistent_depth_um", "T0_depth_um"]].sort_values(["campaign", "VX"]), "K_then_C_cases.csv")
    return reg, box


def nearest_neighbours(reg, d, ids):
    """For each listed NEW run: nearest NEW positive and nearest OLD run in scaled (log P, log VX, log LS, ST)."""
    X = np.c_[np.log(reg.P), np.log(reg.VX), np.log(reg.LS), reg.ST / 100.0]
    mu, sd = X.mean(0), X.std(0)
    Z = (X - mu) / sd
    idx = {s: i for i, s in enumerate(reg.sim_id)}
    D = d.set_index("sim_id")
    rows = []
    for s in ids:
        i = idx[s]
        dist = np.sqrt(((Z - Z[i]) ** 2).sum(1))
        for label, mask in [("nearest_NEW_positive", (reg.campaign == "NEW") & (reg.has_keyhole_frozen == 1)),
                            ("nearest_OLD_any", reg.campaign == "OLD"), ("nearest_OLD_negative", (reg.campaign == "OLD") & (reg.has_keyhole_frozen == 0))]:
            m = mask.to_numpy() & (np.arange(len(reg)) != i)
            j = int(np.flatnonzero(m)[np.argmin(dist[m])])
            sj = reg.sim_id.iloc[j]
            rows.append({"sim_id": s, "neighbour_kind": label, "neighbour_id": sj, "scaled_distance": float(dist[j]),
                         "neighbour_has_keyhole": int(reg.has_keyhole_frozen.iloc[j]), "neighbour_descriptor": reg.descriptor.iloc[j],
                         "neighbour_P": reg.P.iloc[j], "neighbour_VX": reg.VX.iloc[j], "neighbour_LS_um": reg.LS_um_radius.iloc[j], "neighbour_ST": reg.ST.iloc[j],
                         "neighbour_max_depth_um": D.loc[sj, "max_depth_whole_um"], "neighbour_G3_um": D.loc[sj, "G3_persistent_depth_um"],
                         "neighbour_frac_K_FCK": reg.frac_K_FCK.iloc[j]})
    nn = pd.DataFrame(rows)
    _w(nn, "nearest_neighbours_new_negatives.csv")
    return nn


# ------------------------------------------------------------------ OOF diagnostics (existing predictions only)
def _task_ids():
    from src.week12_development_common import load_new, load_old
    new, old = load_new(), load_old()
    return {"R3_NEW": new.sim_id.tolist(), "R3_OLD": old.sim_id.tolist(), "R1_POOLED": old.sim_id.tolist() + new.sim_id.tolist()}


def oof(reg):
    ids = _task_ids()
    arms = {"E1": (W18 / "phase3/depth3/cache_real", ("GPR_depth", "mlii", "straddle")), "G3": (W18 / "phase2/cache_real", ("G3", "mlii", "margin"))}
    recs = []
    for task, idlist in ids.items():
        for arm, (cdir, key) in arms.items():
            for rep in range(1, 9):
                for fold in range(1, 6):
                    f = cdir / f"{task}__r{rep:03d}_f{fold}.json"
                    if not f.exists():
                        continue
                    data = [r for r in json.loads(f.read_text()) if (r["model"], r["hyper"], r["rule"]) == key]
                    if not data:
                        continue
                    budgets = sorted({r["budget"] for r in data})
                    for r in data:
                        rows = [int(x) for x in str(r["rows"]).split(",") if x != ""]
                        p = [float(x) for x in str(r["p"]).split(",") if x != ""]
                        for ri, pi in zip(rows, p):
                            recs.append((task, arm, rep, fold, r["budget"], r["budget"] == budgets[-1], idlist[ri], pi, r.get("u", np.nan)))
    P = pd.DataFrame(recs, columns=["task", "arm", "repeat", "fold", "budget", "final_budget", "sim_id", "p", "u_cached"])
    R = reg.set_index("sim_id")
    P["y"] = P.sim_id.map(R.has_keyhole_frozen).astype(int)
    P["frac_K_FCK"] = P.sim_id.map(R.frac_K_FCK); P["frac_K_KC"] = P.sim_id.map(R.frac_K_KC)
    P["pred"] = (P.p >= 0.5).astype(int)
    fin = P[P.final_budget]
    fin.to_csv(TAB / "oof_predictions_final_budget.csv.gz", index=False, compression="gzip", lineterminator="\n")
    out = []
    for (task, arm), sub in fin.groupby(["task", "arm"]):
        ba_rep = [0.5 * (s.pred[s.y == 1].mean() + (1 - s.pred[s.y == 0]).mean()) for _, s in sub.groupby("repeat")]
        base = {"task": task, "arm": arm, "budget": int(sub.budget.iloc[0]), "repeats": sub.repeat.nunique(), "n_predictions": len(sub),
                "BA_pooled_over_all_oof": 0.5 * (sub.pred[sub.y == 1].mean() + (1 - sub.pred[sub.y == 0]).mean()),
                "BA_mean_of_repeats": float(np.mean(ba_rep))}
        for ratio in ("frac_K_FCK", "frac_K_KC"):
            v = sub[ratio]
            bins = [("negatives (K=0)", sub.y == 0, "specificity"), ("(0, .05)", (sub.y == 1) & (v > 0) & (v < .05), "sensitivity"),
                    ("[.05, .10)", (sub.y == 1) & (v >= .05) & (v < .10), "sensitivity"), ("[.10, 1]", (sub.y == 1) & (v >= .10), "sensitivity")]
            for name, m, kind in bins:
                s2 = sub[m]
                val = (1 - s2.pred.mean()) if kind == "specificity" else s2.pred.mean()
                ids_ = sorted(s2.sim_id.unique())
                out.append({**base, "ratio": ratio, "bin": name, "metric": kind, "value": val if len(s2) else np.nan,
                            "n_sims": len(ids_), "n_predictions": len(s2),
                            "sim_ids": ";".join(ids_) if len(ids_) <= 15 else f"{len(ids_)} sims"})
    diag = pd.DataFrame(out)
    _w(diag, "oof_diagnostics_by_K_fraction.csv")
    # Per-simulation error rates for NEW negatives and low-K positives (E1 and G3, final budget)
    per = fin.groupby(["task", "arm", "sim_id"]).agg(n=("p", "size"), mean_p=("p", "mean"), error_rate=("pred", lambda s: np.nan)).reset_index()
    err = fin.assign(err=(fin.pred != fin.y).astype(int)).groupby(["task", "arm", "sim_id"]).err.mean().rename("error_rate")
    per = per.drop(columns=["error_rate"]).merge(err.reset_index(), on=["task", "arm", "sim_id"])
    per = per.merge(reg[["sim_id", "campaign", "has_keyhole_frozen", "descriptor", "frac_K_FCK"]], on="sim_id", how="left")
    _w(per, "oof_per_simulation_final_budget.csv")
    # Fold-level link between E1's learned threshold and the late-window 312 um negative (existing caches only)
    pull = []
    late = [s for s in ids["R3_NEW"] if s.endswith("H-f4fc937e86")][0]
    for task in ("R3_NEW", "R1_POOLED"):
        li = ids[task].index(late)
        for rep in range(1, 9):
            for fold in range(1, 6):
                recs_e = [r for r in json.loads((W18 / f"phase3/depth3/cache_real/{task}__r{rep:03d}_f{fold}.json").read_text()) if r["model"] == "GPR_depth"]
                recs_g = [r for r in json.loads((W18 / f"phase2/cache_real/{task}__r{rep:03d}_f{fold}.json").read_text()) if (r["model"], r["hyper"], r["rule"]) == ("G3", "mlii", "margin")]
                test = [int(x) for x in recs_e[0]["rows"].split(",")]
                y = np.array([int(reg.set_index("sim_id").has_keyhole_frozen[ids[task][i]]) for i in test])

                def ba(rec):
                    p = np.array([float(x) for x in rec["p"].split(",")]) >= .5
                    return 0.5 * (p[y == 1].mean() + (~p[y == 0]).mean()) if (y == 0).any() and (y == 1).any() else np.nan
                ve = [ba(r) for r in recs_e]; vg = [ba(r) for r in recs_g]
                # BA is undefined when the test fold holds a single class; such folds stay NaN (no warning noise)
                be = float(np.nanmean(ve)) if np.isfinite(ve).any() else np.nan
                bg = float(np.nanmean(vg)) if np.isfinite(vg).any() else np.nan
                us = [r["u"] for r in recs_e]
                pull.append({"task": task, "repeat": rep, "fold": fold, "late_negative_in_test": int(li in test), "u_max_um": max(us), "u_final_um": us[-1],
                             "budgets_with_u_ge_200um": int(sum(u_ >= 200 for u_ in us)), "n_budgets": len(us),
                             "E1_mean_BA_over_budgets": be, "G3_mean_BA_over_budgets": bg, "E1_minus_G3": be - bg})
    pull = pd.DataFrame(pull)
    _w(pull, "oof_E1_threshold_pull_by_fold.csv")
    # Learned thresholds u (stored in um in the caches) on the tasks: what E1 actually used
    uu = P[(P.arm == "E1") & P.final_budget].groupby(["task", "repeat", "fold"]).u_cached.first().reset_index()
    # the cache stores u in um (e.g. 101.03); a log-scale value would be < 10
    uu["u_learned_um"] = np.where(uu.u_cached < 10, np.exp(uu.u_cached), uu.u_cached)
    _w(uu, "oof_E1_learned_threshold_final_budget.csv")
    return diag, per, uu
