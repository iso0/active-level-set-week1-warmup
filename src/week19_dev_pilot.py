"""Week 19 bounded DEV pilot: active-window E1 target vs whole-record E1 vs G3 on identical paid paths (R3_NEW).

POST-HOC EXPLORATORY — NOT PRE-REGISTERED CONFIRMATORY EVIDENCE.  Implements P0–P2 of Astra's
outputs/astra_week19_rnd/OPUS_IMPLEMENTATION_REQUEST.md with the owner's changes of 2026-10-10:
  * primary contrast = ACTIVE_E1 − WHOLE_E1 pooled-per-repeat BA at B40 (advance: mean ≥ 0.01 and paired 95 % lower
    bound > 0, no mean specificity decline and no short-K sensitivity loss > 0.05 versus either comparator);
    q20 at B40 is a reported co-endpoint (no improved-boundary claim if q20 deteriorates);
  * a falsifiable prediction is written into pilot_manifest.json before any fit;
  * P3 and the morphology fallback are not started; C3 is not used.
No adaptive acquisition: every arm sees the same label-blind maximin path.  Fits call the pinned Week 18 engine
(src/week18_engine.py: DepthGPR, fit_learner) unchanged; the learner receives labels/responses of paid rows only.

Steps: python -m src.week19_dev_pilot p0 | p1 | p2 | all
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_k, "2")          # resource cap: <= 2 CPU threads

import datetime as dt
import hashlib
import json
import subprocess
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "outputs" / "week19_temporal_regime_audit"
OUT = ROOT / "outputs" / "week19_temporal_regime_dev_pilot"
TAB, FIG, PROV = OUT / "tables", OUT / "figures", OUT / "provenance"
ASTRA = ROOT / "outputs" / "astra_week19_rnd"
W18 = ROOT / "outputs" / "week18_independent_research"
SPLITS = ROOT / "outputs/week12_startup_and_transfer_development/audit/original_splits.json"
Q20_CACHE = W18 / "phase2" / "cache_real"
BASE_COMMIT = "f3206f292f48db79d9c4af496e7c7aed40c0ce62"
OLD_REV = "b6dc254a2b607a31cb9f97b40990339c3d5ca1e8"
NEW_REV = "2e1eec9c98fd57609d2815f174586336ab59da07"
UREF = 110.9641179189907
PULL_UM = 200.0
LATE_NEG = "P-353p784791664_VX-0p953661701626_LS-4p00659722232e-05_ST-310p795032219_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p05852399734e-06_H-f4fc937e86"
NO_A = "P-423p267621988_VX-0p332154005524_LS-4p22725332613e-05_ST-473p308549274_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-1p45237465838e-05_H-e7dbd8e5ce"
LATE_K_POS = "P-351p92267109_VX-0p98107853237_LS-4p98248594664e-05_ST-477p481832276_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-4p91716049617e-06_H-349225d53c"
UNRESOLVED = ["P-426p768553369_VX-0p970152058637_LS-4p12602194162e-05_ST-379p997827854_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-4p97254070645e-06_H-b2eec677b1",
              "P-387p361336282_VX-0p960187357846_LS-4p72484046084e-05_ST-390p52586458_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p02414509376e-06_H-b302fc6cbd",
              "P-376p749294588_VX-0p89878118514_LS-4p48900537333e-05_ST-301p683894272_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p36740274805e-06_H-2e066980ca",
              "P-372p400266258_VX-0p904171786761_LS-4p46899874615e-05_ST-344p55726366_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p3354027118e-06_H-1d4ea0f649"]
UNDEFINED_KC_SUFFIX = {"OLD": "H-bf889bf790", "NEW": "H-e7dbd8e5ce"}
REPEATS = [1, 2]
BUDGETS = [16, 40, 80]
PRIMARY_BUDGET = 40
PATH_LEN = 80
ARMS = ["WHOLE_E1_SHARED", "ACTIVE_E1_SHARED", "G3_SHARED"]
E1_ARMS = ARMS[:2]
BOOT_DRAWS, BOOT_SEED = 2000, 191026
CAPS = {"max_learner_fits": 90, "optimizer_starts_per_fit": 1, "cpu_threads": 2, "max_resident_bytes": 8 * 1024 ** 3, "max_elapsed_s": 4 * 3600}
FP_RULE = 1e-6            # Week 18 BENCHMARK_SPEC.md: a fit with Laplace fixed-point error > 1e-6 is not converged
PINNED_TABLES = ["tables/temporal_registry.csv", "tables/depth_definitions.csv", "tables/k_runs.csv", "tables/regime_switches.csv",
                 "tables/separability.csv", "tables/representative_cases.csv", "tables/new_negatives_12_cases.csv",
                 "tables/oof_E1_threshold_pull_by_fold.csv"]
CODE_FILES = ["src/week19_dev_pilot.py", "src/week18_engine.py", "src/week17_models.py", "src/week17_audit_impact.py", "src/week13_synthetic_al.py",
              "src/week18_tasks.py", "src/week12_development_common.py", "src/week9_phase1_11_fixed_mean_discrepancy_gp.py",
              "src/week7_phase2_sph_v2_physical_target_extraction.py", "src/week19_series.py"]
FIT_FIELDS = ["arm", "repeat", "fold", "budget", "n_paid", "n_response_available", "n_positive_pairs", "n_negative_pairs", "threshold_branch", "a", "b",
              "log_u", "u_um", "root_outside_range", "late_negative_revealed", "late_negative_query_index", "converged", "status", "wall_seconds", "peak_memory_bytes"]
PRED_FIELDS = ["arm", "threshold_mode", "repeat", "fold", "budget", "sim_id", "p_keyhole", "latent_mean", "latent_variance", "response_available", "prediction_status"]
ORACLE_FIELDS = ["target", "repeat", "fold", "budget", "sim_id", "observed_score", "training_threshold", "predicted_label", "status", "oracle_flag"]
ORACLE_FLAG = "ORACLE RESPONSE — NOT DEPLOYABLE"
ORACLE_MODE = "oracle_response_NOT_DEPLOYABLE"


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def git_blob(path) -> str:
    data = Path(path).read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data, usedforsecurity=False).hexdigest()


def _git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True, cwd=ROOT).stdout.strip()


def short(sid) -> str:
    return "H-" + str(sid).split("_H-")[-1]


def peak_memory_bytes() -> int:
    """Peak working set of this process (Windows GetProcessMemoryInfo; ru_maxrss elsewhere)."""
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes as w

        class PMC(ctypes.Structure):
            _fields_ = [("cb", w.DWORD), ("PageFaultCount", w.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
        k32, psapi = ctypes.WinDLL("kernel32"), ctypes.WinDLL("psapi")
        k32.GetCurrentProcess.restype = w.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [w.HANDLE, ctypes.POINTER(PMC), w.DWORD]
        psapi.GetProcessMemoryInfo.restype = w.BOOL
        pmc = PMC(); pmc.cb = ctypes.sizeof(PMC)
        if not psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb):
            return -1
        return int(pmc.PeakWorkingSetSize)
    import resource
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024


def _w(df, name):
    TAB.mkdir(parents=True, exist_ok=True)
    df.to_csv(TAB / name, index=False, lineterminator="\n")


def auc(y, s):
    y, s = np.asarray(y), np.asarray(s, float)
    m = np.isfinite(s); y, s = y[m], s[m]
    pos, neg = s[y == 1], s[y == 0]
    if not len(pos) or not len(neg):
        return np.nan
    return float(((pos[:, None] > neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum()) / (len(pos) * len(neg)))


def ba_at(y, s, c):
    y, s = np.asarray(y), np.asarray(s, float)
    m = np.isfinite(s); y, s = y[m], s[m]
    if len(np.unique(y)) < 2:
        return np.nan
    p = s >= c
    return float(0.5 * (p[y == 1].mean() + (~p[y == 0]).mean()))


def confusion(y, s, c):
    y, s = np.asarray(y), np.asarray(s, float)
    m = np.isfinite(s); y, s = y[m], s[m]; p = s >= c
    return {"TP": int((p & (y == 1)).sum()), "FN": int((~p & (y == 1)).sum()), "TN": int((~p & (y == 0)).sum()), "FP": int((p & (y == 0)).sum())}


# ======================================================================================== P0
def pilot_inputs():
    reg = pd.read_csv(AUDIT / "tables/temporal_registry.csv")
    dd = pd.read_csv(AUDIT / "tables/depth_definitions.csv")
    m = reg.merge(dd[["sim_id", "max_depth_frozen_um"]], on="sim_id", how="left", validate="one_to_one")
    src = (f"temporal_registry.csv={sha256(AUDIT / 'tables/temporal_registry.csv')};"
           f"depth_definitions.csv={sha256(AUDIT / 'tables/depth_definitions.csv')}")
    return pd.DataFrame({
        "sim_id": m.sim_id, "campaign": m.campaign, "partition": m.partition, "P_W": m.P, "VX_m_s": m.VX, "LS_radius_m": m.LS, "ST_K": m.ST,
        "has_keyhole": m.has_keyhole_frozen.astype(int), "whole_max_um": m.max_depth_frozen_um, "A_um": m.A_active_max_um,
        "A_available": m.A_active_max_um.notna(), "A_failure": np.where(m.A_active_max_um.notna(), "", m.failure.fillna("unavailable")),
        "first_valid_ms": m.first_valid_ms, "recording_end_ms": m.recording_end_ms, "derived_exit_ms": m.derived_exit_ms,
        "active_cutoff_ms": m.active_cutoff_ms, "early_end": m.recording_ends_before_90pct_domain.astype(bool),
        "frac_K_FCK": m.frac_K_FCK, "frac_K_KC": m.frac_K_KC, "n_K_frames": m.n_K.astype(int), "n_C_frames": m.n_C.astype(int),
        "source_revision": np.where(m.campaign == "OLD", OLD_REV, NEW_REV), "source_table_sha256": src})


def c3_inventory():
    """Every file under outputs/ (outside this pilot) whose name marks repeats 17-20 (C3); recorded before and after."""
    pat = [f"r{k:03d}" for k in range(17, 21)] + [f"rep{k}" for k in range(17, 21)] + [f"repeat{k}" for k in range(17, 21)]
    hits = []
    for p in (ROOT / "outputs").rglob("*"):
        if p.is_file() and OUT not in p.parents:
            n = p.name.lower()
            if any(f"__{k}_" in n or f"_{k}." in n or f"_{k}_" in n for k in pat):
                hits.append(str(p.relative_to(ROOT)).replace("\\", "/"))
    return sorted(hits)


def shortk_ids(inp):
    new = inp[inp.campaign == "NEW"]
    return new.sim_id[(new.has_keyhole == 1) & (new.frac_K_FCK > 0) & (new.frac_K_FCK < 0.10)].tolist()


def step_p0():
    OUT.mkdir(parents=True, exist_ok=True)
    checks = []

    def add(cid, desc, ok, detail):
        checks.append({"check": cid, "description": desc, "status": ok if isinstance(ok, str) else ("PASS" if ok else "FAIL"), "detail": detail})
    astra = json.loads((ASTRA / "ASTRA_REVIEW_CHECKS.json").read_text())
    rows = []
    rels = list(dict.fromkeys([f"outputs/week19_temporal_regime_audit/{r}" for r in PINNED_TABLES] + list(astra["provenance"])))
    for rel in rels:
        p = ROOT / rel
        a = astra["provenance"].get(rel, {})
        rows.append({"path": rel, "sha256": sha256(p), "git_blob": git_blob(p), "pinned_git_blob": _git("rev-parse", f"{BASE_COMMIT}:{rel}"),
                     "astra_sha256": a.get("sha256", ""), "astra_git_blob": a.get("git_blob", "")})
    hp = pd.DataFrame(rows)
    hp["unchanged_since_pin"] = hp.git_blob == hp.pinned_git_blob
    hp["matches_astra"] = np.where(hp.astra_sha256 == "", "not_recorded", np.where((hp.sha256 == hp.astra_sha256) & (hp.git_blob == hp.astra_git_blob), "yes", "NO"))
    _w(hp, "P0_input_hashes.csv")
    add("P0-01", "pinned audit tables and Astra-listed code unchanged since f3206f29; SHA-256 and git blob equal to Astra's record where recorded",
        bool(hp.unchanged_since_pin.all() and (hp.matches_astra != "NO").all()),
        f"{int(hp.unchanged_since_pin.sum())}/{len(hp)} unchanged; Astra matches {int((hp.matches_astra == 'yes').sum())}/{int((hp.matches_astra != 'not_recorded').sum())}")
    inp = pilot_inputs()
    _w(inp, "pilot_inputs.csv")
    old, new = inp[inp.campaign == "OLD"], inp[inp.campaign == "NEW"]
    add("P0-02", "populations OLD 405/73 and NEW 136/124 positive; 541 unique full simulation names",
        len(old) == 405 and old.has_keyhole.sum() == 73 and len(new) == 136 and new.has_keyhole.sum() == 124 and inp.sim_id.is_unique and len(inp) == 541,
        f"OLD {len(old)}/{int(old.has_keyhole.sum())}; NEW {len(new)}/{int(new.has_keyhole.sum())}; unique {inp.sim_id.is_unique}")
    reg = pd.read_csv(AUDIT / "tables/temporal_registry.csv").set_index("sim_id")
    import src.week12_development_common as W12
    pop = pd.read_csv(ROOT / "outputs/week7_06_real_data_boundary_active_level_set/primary_common_population.csv", usecols=["experiment_name", "has_keyhole"])
    n136 = pd.read_csv(ROOT / "outputs/week12_startup_and_transfer_development/audit/new136.csv", usecols=["sim_id", "has_keyhole"])
    ln = W12.load_new()
    src_old = dict(zip(pop.experiment_name, pop.has_keyhole.astype(int)))
    src_n136 = dict(zip(n136.sim_id, n136.has_keyhole.astype(int))); src_ln = dict(zip(ln.sim_id, ln.has_keyhole.astype(int)))
    rep = reg.has_keyhole_reproduced.astype(int).to_dict()
    agree = []
    for r in inp.itertuples():
        refs = [rep[r.sim_id]] + ([src_old.get(r.sim_id, -1)] if r.campaign == "OLD" else [src_n136.get(r.sim_id, -1), src_ln.get(r.sim_id, -1)])
        agree.append(all(v == r.has_keyhole for v in refs))
    add("P0-03", "canonical label agreement (OLD frozen Week 7 population; NEW Week 12 new136 and load_new oracle; Week 19 re-derivation), full-name joins only",
        all(agree) and set(ln.sim_id) == set(new.sim_id) and set(src_old) == set(old.sim_id),
        f"{sum(agree)}/{len(inp)} agree; name sets equal: NEW {set(ln.sim_id) == set(new.sim_id)}, OLD {set(src_old) == set(old.sim_id)}")
    miss_a = inp.sim_id[~inp.A_available].tolist()
    undef = inp[inp.frac_K_KC.isna()][["sim_id", "campaign"]]
    undef_ok = len(undef) == 2 and all(short(s) == UNDEFINED_KC_SUFFIX[c] for s, c in zip(undef.sim_id, undef.campaign))
    add("P0-04", "exactly one unavailable A (H-e7dbd8e5ce, kept as an observed-label negative, not a new exclusion) and two undefined K/(K+C) (OLD H-bf889bf790, NEW H-e7dbd8e5ce)",
        miss_a == [NO_A] and undef_ok and int(inp.set_index("sim_id").loc[NO_A, "has_keyhole"]) == 0,
        f"A unavailable: {[short(s) for s in miss_a]}; K/(K+C) undefined: {[(c, short(s)) for s, c in zip(undef.sim_id, undef.campaign)]}")
    y = new.has_keyhole.to_numpy(); w = new.whole_max_um.to_numpy(float); a = new.A_um.to_numpy(float); common = np.isfinite(a)
    ok5, det5 = True, []
    for key, (yy, ss) in {"new_whole_all": (y, w), "new_whole_common_A": (y[common], w[common]), "new_A_common": (y[common], a[common])}.items():
        ref = astra[key]
        got = {"n": len(yy), "positive": int(yy.sum()), "negative": int((yy == 0).sum()), "auc": auc(yy, ss), "BA": ba_at(yy, ss, UREF), **confusion(yy, ss, UREF)}
        good = all(abs(float(got[k]) - float(ref[k])) <= 1e-10 for k in ref)
        ok5 &= good
        det5.append(f"{key}: AUC {got['auc']:.13f} BA {got['BA']:.13f} TP/FN/TN/FP {got['TP']}/{got['FN']}/{got['TN']}/{got['FP']} ({'=' if good else '!='} Astra)")
    add("P0-05", "Astra's paired-cohort AUC/BA/confusion at u_ref reproduced from table values (tolerance 1e-10): common cohort whole FP 6 vs A FP 5, FN 1 in both",
        ok5, "; ".join(det5))
    sep = pd.read_csv(AUDIT / "tables/separability.csv")
    thr = float(sep.query("definition=='A_active_max_um' and population=='NEW' and variant=='full'").oracle_threshold_same_population.iloc[0])
    cf = confusion(y[common], a[common], thr); ba = ba_at(y[common], a[common], thr)
    sk = new[new.sim_id.isin(shortk_ids(inp))]
    sens = float((sk.A_um >= thr).mean())
    missed = sorted(new.sim_id[(new.has_keyhole == 1) & new.A_available & (new.A_um < thr)])
    ref = astra["A_oracle_confusion"]
    add("P0-06", "A at the existing NEW oracle threshold 142.2322 um: TP/FN/TN/FP 114/10/11/0, BA 0.9596774193548387, short-K sensitivity 1/10; missed positives equal Astra's list",
        (cf["TP"], cf["FN"], cf["TN"], cf["FP"]) == (114, 10, 11, 0) and abs(ba - ref["BA"]) <= 1e-10 and abs(sens - 0.1) <= 1e-10 and len(sk) == 10
        and missed == sorted(r["sim_id"] for r in astra["A_oracle_missed_positives"]),
        f"threshold {thr!r}; {cf}; BA {ba:.13f}; short-K {int((sk.A_um >= thr).sum())}/{len(sk)}; missed {len(missed)}")
    pull = pd.read_csv(AUDIT / "tables/oof_E1_threshold_pull_by_fold.csv")
    g = pull[pull.task == "R3_NEW"].copy(); g["in_test"] = g.late_negative_in_test == 1
    pulled = ~g.in_test & (g.budgets_with_u_ge_200um > 0)
    ts = astra["threshold_summary"]
    got = {"n_folds": len(g), "train_candidate_pool": int((~g.in_test).sum()), "test_fold_count": int(g.in_test.sum()), "u_ge200_folds": int(pulled.sum()),
           "u_ge200_budget_steps": int(g.budgets_with_u_ge_200um.sum()), "max_u_um": float(g.u_max_um.max())}
    means = {"pulled": g[pulled].E1_minus_G3, "not_pulled_train": g[~g.in_test & ~pulled].E1_minus_G3, "test": g[g.in_test].E1_minus_G3, "all_nonpulled": g[~pulled].E1_minus_G3}
    ok7 = all(abs(float(got[k]) - float(ts[k])) <= 1e-10 for k in got) and all(
        abs(v.mean() - ts[k]["mean_E1_minus_G3"]) <= 1e-10 and int(v.notna().sum()) == ts[k]["n_defined"] for k, v in means.items())
    add("P0-07", "fold table maximum learned threshold 309.619080770828 um (the audit report's 309.3 um is the final-budget maximum); Astra's threshold-pull summary reproduced",
        ok7 and abs(got["max_u_um"] - 309.619080770828) <= 1e-9,
        f"{got}; means " + ", ".join(f"{k} {v.mean():+.13f} (n={int(v.notna().sum())})" for k, v in means.items()))
    rc = astra["registry_counts"]
    ok8, det8 = True, []
    for camp in ("OLD", "NEW"):
        r = reg[reg.campaign == camp]
        got = {"n": len(r), "positive": int(r.has_keyhole_frozen.sum()), "early_end": int(r.recording_ends_before_90pct_domain.sum()), "alternation": int(r.alternation.sum()),
               "K_then_only_C": int(r.K_then_only_C.sum()), "undefined_KC": int(r.frac_K_KC.isna().sum()), "ongoing_K_end": int(r.K_ongoing_at_observation_end.sum())}
        ok8 &= got == rc[camp]; det8.append(f"{camp} {got}")
    add("P0-08", "Astra's registry counts reproduced (early end, alternation, K then only C, undefined K/(K+C), K ongoing at observation end)", ok8, "; ".join(det8))
    import src.week18_tasks as T
    dm = T.depth_map(True)
    dif = np.abs(inp.whole_max_um.to_numpy(float) - inp.sim_id.map(dm).to_numpy(float))
    add("P0-09", "WHOLE target equals the Week 18 E1 response (src.week18_tasks.depth_map: Week 7 OLD table, phase1/new_depth.csv NEW) for all 541",
        bool(np.isfinite(dif).all() and dif.max() == 0.0), f"max abs difference {dif.max()!r} um")
    geo = inp.sim_id.str.extract(r"_XF-([0-9pe-]+)_XL-([0-9pe-]+)_").apply(lambda c: c.str.replace("p", ".").astype(float))
    exit_ms = (np.minimum(geo[0], geo[1]) + 12e-6) / inp.VX_m_s * 1e3
    cut = np.minimum(inp.recording_end_ms, 0.9 * exit_ms)
    e1 = float(np.nanmax(np.abs(exit_ms / inp.derived_exit_ms - 1))); e2 = float(np.nanmax(np.abs(cut / inp.active_cutoff_ms - 1)))
    add("P0-10", "target contract arithmetic from table values: derived exit = (min(XF,XL)+12e-6)/VX and active cutoff = min(recording end, 0.9 exit) for all 541 (relative 1e-12)",
        bool(e1 <= 1e-12 and e2 <= 1e-12 and inp.active_cutoff_ms.notna().all()), f"max relative error exit {e1:.2e}, cutoff {e2:.2e}")
    logs = sorted(str(p.relative_to(ROOT)) for p in W18.rglob("*") if p.is_file() and any(k in p.name.lower() for k in ("query_order", "paid_path", "acquisition_log", "query_ledger", "paid_queries")))
    add("P0-11", "historical paid-query logs absent (Week 18 caches store test rows, probabilities, q20 flags and u per budget; src/week18_dev_arms.py discards the query order): "
        "historical acquisition timing UNAVAILABLE; the causal threshold-pull claim stays unresolved", "INFO", f"{len(logs)} candidate log files")
    c3 = c3_inventory()
    add("P0-12", "initial C3 inventory (repeats 17-20) recorded before any fit", "INFO", f"{len(c3)} files")
    ck = pd.DataFrame(checks); _w(ck, "P0_CHECKS.csv")
    print(ck[["check", "status", "detail"]].to_string(max_colwidth=150))
    if (ck.status == "FAIL").any():
        _w(ck[ck.status == "FAIL"], "P0_DISCREPANCIES.csv")
        raise SystemExit("P0 stopped: discrepancy (no model work)")
    write_manifest(inp, c3, hp, ln)
    return ck


def write_manifest(inp, c3, hashes, new):
    splits = [s for s in json.loads(SPLITS.read_text()) if int(s["repeat"]) in REPEATS]
    sk = shortk_ids(inp)
    man = {
        "status": "POST-HOC EXPLORATORY — NOT PRE-REGISTERED CONFIRMATORY EVIDENCE",
        "created_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(), "written_before_any_fit": True,
        "base_commit": BASE_COMMIT, "head_at_manifest": _git("rev-parse", "HEAD"), "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "specification": {
            "astra_request": "outputs/astra_week19_rnd/OPUS_IMPLEMENTATION_REQUEST.md", "astra_request_sha256": sha256(ASTRA / "OPUS_IMPLEMENTATION_REQUEST.md"),
            "astra_memo_sha256": sha256(ASTRA / "ASTRA_RND_MEMO.md"), "astra_checks_sha256": sha256(ASTRA / "ASTRA_REVIEW_CHECKS.json"),
            "scope": "P0-P2 only; P3 and the morphology fallback machinery are not started; C3 unused; Astra's statements are hypotheses, not evidence",
            "owner_changes_2026_10_10": [
                "Primary decision: pooled-per-repeat BA at B40, ACTIVE_E1 minus WHOLE_E1, together with specificity over the 12 negatives and short-K sensitivity; q20 at B40 is a co-endpoint, not the sole gate.",
                "Advance only if mean delta BA(B40) >= 0.01 with a paired 95% lower bound > 0, no mean specificity decline and no short-K sensitivity loss > 0.05 versus either comparator (WHOLE_E1, G3), all B40 comparisons available and all checks pass.",
                "q20 is secondary: if q20 deteriorates, no improved boundary performance is claimed.",
                "The expected benefit of ACTIVE_E1 is a falsifiable hypothesis; historical threshold-pull associations do not establish causation without acquisition logs.",
                "Descriptive tables carry positive/negative, missing-target and undefined-ratio counts; VX > 0.85 analyses are exploratory; original benchmark labels are preserved."]},
        "falsifiable_prediction": {
            "statement": "ACTIVE_E1 removes the late-negative threshold pull and moves toward G3 on NEW; the fast-scan ambiguity remains.",
            "H1_threshold_pull_removed": {
                "test": f"among E1 fits whose paid prefix contains the late negative, WHOLE_E1 has learned u >= {PULL_UM:.0f} um in at least one fit and ACTIVE_E1 has u < {PULL_UM:.0f} um in every such fit",
                "falsified_if": f"ACTIVE_E1 u >= {PULL_UM:.0f} um in any such fit",
                "untestable_if": "the late negative is never paid within B80, or WHOLE_E1 shows no pull in any such fit",
                "late_negative": LATE_NEG},
            "H2_moves_toward_G3": {"test": "at B40 (mean over repeats of pooled BA): BA(ACTIVE) - BA(WHOLE) > 0 and |BA(ACTIVE) - BA(G3)| < |BA(WHOLE) - BA(G3)|",
                                   "falsified_if": "either inequality fails"},
            "H3_fast_scan_ambiguity_remains": {
                "test": "at B40, ACTIVE_E1 misclassifies the four unresolved fast-scan negatives in at least half of their 8 held-out predictions (mean error >= 0.5) and its short-K sensitivity exceeds WHOLE_E1's by at most 0.05",
                "falsified_if": "mean error over the four < 0.5, or short-K sensitivity gain > 0.05", "unresolved_negatives": UNRESOLVED},
            "note": "Basis: Week 19 audit association (E1 learned threshold >= 200 um only in folds whose training pool held the late negative; A of that run is 110.755 um vs whole 312.0 um). No acquisition log exists, so the association is not causal; this pilot tests the mechanism on fixed, logged, label-blind paths only."},
        "data": {
            "task": "R3_NEW only: all 136 eligible NEW simulations; no NEW prior labels, no OLD warm start; OLD is descriptive reference only",
            "population_order": new.sim_id.tolist(), "population_order_source": "src.week12_development_common.load_new() (the row index of src.week18_tasks.r3_new_tasks)",
            "dev_repeat_allowlist": REPEATS, "folds_source": "outputs/week12_startup_and_transfer_development/audit/original_splits.json",
            "folds": [{"repeat": int(s["repeat"]), "fold": int(s["fold"]), "split_id": s.get("split_id", ""), "n_train": len(s["train_indices"]), "n_test": len(s["test_indices"]),
                       "test_sha256": hashlib.sha256(",".join(map(str, s["test_indices"])).encode()).hexdigest()} for s in splits],
            "inputs_csv": "tables/pilot_inputs.csv", "inputs_sha256": sha256(TAB / "pilot_inputs.csv"),
            "input_hashes": hashes[["path", "sha256", "git_blob"]].to_dict("records"),
            "short_K_group": {"definition": "NEW positives with 0 < K/(F+C+K) < 0.10 (evaluator only)", "n": len(sk), "ids": sk},
            "negatives_12": inp[(inp.campaign == "NEW") & (inp.has_keyhole == 0)].sim_id.tolist(),
            "named_cases": {"late_negative": LATE_NEG, "A_unavailable_negative": NO_A, "late_K_positive_low_depth": LATE_K_POS}},
        "path": {"routine": "src.week13_synthetic_al.maximin_order on raw [P, VX, LS, ST] of the training pool (standardized within the pool)",
                 "seed": "np.random.default_rng([1820, repeat, fold, 2]) (the Week 18 R3_NEW startup seed)", "length": PATH_LEN,
                 "label_blind": True, "shared_by_all_arms": True, "no_seed_selection_reordering_or_forced_inclusion": True},
        "arms": {"WHOLE_E1_SHARED": "src.week18_engine.fit_learner(('GPR_depth','mlii')) on log whole-record max depth; learned threshold from paid valid depth/label pairs",
                 "ACTIVE_E1_SHARED": "same code on log A; the unavailable A of H-e7dbd8e5ce contributes no regression target or threshold pair (its label stays available to G3 and is evaluated when held out)",
                 "G3_SHARED": "src.week18_engine.fit_learner(('G3','mlii')): safeguarded fixed-mean Laplace GPC (ARD Matern-3/2), Week 18 FP_TOL 1e-9"},
        "budgets": BUDGETS, "primary_budget": PRIMARY_BUDGET, "max_learner_fits": 3 * len(BUDGETS) * 10,
        "targets": {"whole_max_um": "frozen whole-record maximum of 1e6*max(0,-z_min) over valid bounds rows (Week 18 E1 response)",
                    "A_um": "max of the same depth over valid mapped rows with t <= min(recording end, 0.9*(min(XF,XL)+12e-6)/VX); startup retained; observed-window endpoint; pinned valid-row/sentinel rules",
                    "B": "not used (annotation-dependent audit target)",
                    "units": {"depth": "um", "time": "ms", "LS": "m (radius, as in the folder name)", "P": "W", "VX": "m/s", "ST": "K"}},
        "preprocessing": {"E1": "StandardScaler on log(pool X) (label-blind candidate pool); log response standardized on paid valid responses only; ConstantKernel*Matern(ARD,nu=1.5)+WhiteKernel, one L-BFGS-B start",
                          "G3": "StandardScaler on raw pool X and pool log h; Laplace GPC with ML-II, one L-BFGS-B start (maxiter 150)",
                          "leakage_guard": "the learner receives a copy of y and response arrays in which every unpaid row is masked (y=-1, response=NaN)",
                          "threads": "OMP/OPENBLAS/MKL/NUMEXPR = 2 and threadpoolctl limit 2"},
        "q20_source": "src.week18_tasks.q20_for (src.external_validation.analysis.boundary_flags, entire_evaluation_batch) on each NEW test fold; must equal the Week 18 phase2 cache flags; evaluator only",
        "metrics": {"BA": "pooled per repeat over the five test folds (136 predictions), then mean over repeats 1-2",
                    "q20": "Week 18 construction: accuracy on q20-flagged test points per fold, mean over folds with flagged points, then mean over repeats",
                    "specificity": "over the 12 observed-label negatives, pooled per repeat, mean over repeats",
                    "sensitivity": "all 124 positives; short-K: the fixed ten positives (sensitivity only, never BA)",
                    "other": "Brier, AUC (Mann-Whitney, ties 0.5), observed-response error (E1 only, log scale)",
                    "class_rule": "p >= 0.5", "secondary_budgets": [16, 80]},
        "decision_rule": {"primary": "mean over repeats of BA(ACTIVE_E1) - BA(WHOLE_E1) at B40",
                          "advance_if_all": ["mean delta BA >= 0.01", "paired bootstrap 95% lower bound > 0",
                                             "mean specificity of ACTIVE_E1 >= that of WHOLE_E1 and of G3",
                                             "short-K sensitivity of ACTIVE_E1 >= WHOLE_E1 - 0.05 and >= G3 - 0.05",
                                             "every B40 arm/fold fit available", "all P0/P1 checks pass"],
                          "INCONCLUSIVE": "a B40 fit is unavailable, or mean delta BA >= 0.01 with lower bound <= 0",
                          "NO_ADVANCE": "otherwise",
                          "q20_rule": "delta q20 at B40 is reported as a co-endpoint; if it is negative, no improved-boundary claim is made",
                          "no_extra_repeats": True},
        "bootstrap": {"draws": BOOT_DRAWS, "seed": BOOT_SEED, "unit": "unique simulation", "strata": "original has_keyhole", "paired": True,
                      "carry": "each sampled simulation carries all its predictions (both repeats, all arms, budgets and threshold modes)",
                      "q20_membership": "fixed", "undefined_draws": "reported with reason (e.g. no short-K positive drawn; every q20 fold empty)",
                      "interpretation": "conditional on these fitted DEV models and two historical split repeats; not refitting, independent-fold or external uncertainty"},
        "failure_rules": [
            "single-class paid prefix (G3) or single-class usable depth/label pairs (E1): arm/checkpoint unavailable; the engine's 111 um single-class fallback is never reached",
            "nonpositive paid response under the log transform: E1 fit failed",
            "non-finite predictions, non-positive variances or probabilities outside [0,1]: fit failed",
            "logistic threshold branch with slope <= 0: fit failed (no clipping, rebalancing or substitute estimator); |slope| < 1e-6 is flagged",
            f"failed convergence: G3 Laplace fixed-point error > {FP_RULE:g} (Week 18 BENCHMARK_SPEC.md rule), optimizer exception or initial-kernel fallback, or non-finite log marginal likelihood; E1 optimizer exception or non-finite log marginal likelihood. L-BFGS-B stopping messages are recorded for every fit as diagnostics (Week 18 practice) and a sensitivity line reports the decision if they were counted as failures",
            "an unavailable or failed B40 fit blocks the advancement decision", "no reseeding, extra queries, score interpolation or deletion of affected simulations",
            "a leakage-invariant violation or an exceeded resource cap stops the whole run; the partial log is saved and no primary claim is made"],
        "resource_ceilings": CAPS, "c3_inventory_initial": c3, "c3_inventory_sha256": hashlib.sha256("\n".join(c3).encode()).hexdigest(),
        "historical_acquisition_timing": "UNAVAILABLE: Week 18 caches store test rows, probabilities, q20 flags and u per budget; the paid query order is not saved. No historical run is regenerated; the scalar-only late-negative replacement check (needs a saved ledger) is therefore not run.",
        "code_sha256": {c: sha256(ROOT / c) for c in CODE_FILES}}
    (OUT / "pilot_manifest.json").write_text(json.dumps(man, indent=1, ensure_ascii=False), encoding="utf-8")
    print("manifest written", sha256(OUT / "pilot_manifest.json"))
    return man


# ======================================================================================== P1
def threshold_details(t, y):
    """Replicates DepthGPR.fit's threshold branch to record its coefficients (E1 learned-threshold rule, C=1e6)."""
    from sklearn.linear_model import LogisticRegression
    kh, nk = t[y == 1], t[y == 0]
    if len(kh) and len(nk) and nk.max() < kh.min():
        return {"threshold_branch": "midpoint", "a": np.nan, "b": np.nan, "log_u": float(.5 * (nk.max() + kh.min()))}
    if len(kh) and len(nk):
        lr = LogisticRegression(C=1e6, max_iter=5000).fit(t[:, None], y)
        a, b = float(lr.intercept_[0]), float(lr.coef_[0, 0])
        return {"threshold_branch": "logistic", "a": a, "b": b, "log_u": float(-a / b)}
    return {"threshold_branch": "single_class", "a": np.nan, "b": np.nan, "log_u": np.nan}


def build_tasks():
    """Only the allowed tasks: R3_NEW, repeats 1-2, the five original folds, no prior (src.week18_tasks ordering)."""
    import src.week12_development_common as W12
    import src.week18_tasks as T
    new = W12.load_new()
    inp = pd.read_csv(TAB / "pilot_inputs.csv").set_index("sim_id")
    X = new[["P", "VX", "LS", "ST"]].to_numpy(float); y = new.has_keyhole.to_numpy(int); ids = new.sim_id.astype(str).to_numpy()
    whole = inp.loc[ids, "whole_max_um"].to_numpy(float); A = inp.loc[ids, "A_um"].to_numpy(float)
    tasks = []
    for s in json.loads(SPLITS.read_text()):
        if int(s["repeat"]) not in REPEATS:
            continue
        te = np.asarray(s["test_indices"]); tr = np.asarray(s["train_indices"])
        tasks.append({"task": "R3_NEW", "repeat": int(s["repeat"]), "fold": int(s["fold"]), "X": X, "y": y, "ids": ids, "pool": tr, "test": te,
                      "prior": np.array([], int), "q20": np.asarray(T.q20_for(X, y, ids, te), bool), "seed": [1820, int(s["repeat"]), int(s["fold"])],
                      "whole": whole, "A": A})
    return tasks


def q20_cache_check(tasks):
    rows = []
    for t in tasks:
        f = Q20_CACHE / f"R3_NEW__r{t['repeat']:03d}_f{t['fold']}.json"
        recs = json.loads(f.read_text())
        rr = {(r["rows"], r["q20"]) for r in recs}
        test = ",".join(map(str, t["test"])); q = ",".join("1" if v else "0" for v in t["q20"])
        rows.append({"repeat": t["repeat"], "fold": t["fold"], "cache_file": str(f.relative_to(ROOT)).replace("\\", "/"), "cache_records": len(recs),
                     "distinct_row_q20_pairs": len(rr), "test_rows_equal": all(r[0] == test for r in rr), "q20_equal": all(r[1] == q for r in rr),
                     "n_test": len(t["test"]), "n_q20": int(t["q20"].sum())})
    return pd.DataFrame(rows)


def _status_rec(rec, status):
    rec.update({"status": status, "converged": None, "wall_seconds": 0.0, "peak_memory_bytes": peak_memory_bytes()})
    return rec


def fit_one(E, t, arm, b, L, n_fits):
    """One learner fit on the paid prefix L.  Returns (fit record, prediction rows, oracle rows, leakage_ok)."""
    from scipy.special import ndtr
    y, ids, n = t["y"], t["ids"], len(t["y"])
    resp = t["whole"] if arm == "WHOLE_E1_SHARED" else (t["A"] if arm == "ACTIVE_E1_SHARED" else None)
    lq = np.flatnonzero(ids[t["path"]] == LATE_NEG)
    late_q = int(lq[0]) + 1 if len(lq) else np.nan
    rec = {"arm": arm, "repeat": t["repeat"], "fold": t["fold"], "budget": b, "n_paid": len(L), "late_negative_revealed": bool(len(lq) and late_q <= b),
           "late_negative_query_index": late_q, "prefix_sha256": hashlib.sha256("\n".join(ids[L]).encode()).hexdigest(),
           "A_missing_paid": bool(NO_A in set(ids[L]))}
    yL = y[L]
    # leakage guard: the learner sees labels/responses of paid rows only
    y_m = np.full(n, -1, int); y_m[L] = yL
    if resp is not None:
        ok = np.isfinite(resp[L])
        r_m = np.full(n, np.nan); r_m[L] = resp[L]
        rec.update({"n_response_available": int(ok.sum()), "n_positive_pairs": int((yL[ok] == 1).sum()), "n_negative_pairs": int((yL[ok] == 0).sum())})
        usable = rec["n_positive_pairs"] > 0 and rec["n_negative_pairs"] > 0
    else:
        r_m = np.full(n, np.nan)
        rec.update({"n_response_available": len(L), "n_positive_pairs": int((yL == 1).sum()), "n_negative_pairs": int((yL == 0).sum())})
        usable = len(set(yL.tolist())) == 2
    rec["labels_passed"] = int((y_m >= 0).sum()); rec["responses_passed"] = int(np.isfinite(r_m).sum())
    leak_ok = rec["labels_passed"] == len(L) and set(np.flatnonzero(y_m >= 0).tolist()) == set(L.tolist()) and (resp is None or rec["responses_passed"] == rec["n_response_available"])
    preds, orc = [], []
    target = "whole_max_um" if arm == "WHOLE_E1_SHARED" else "A_um"

    def emit(status, f=None, p=None, mu=None, var=None):
        for j, i in enumerate(t["test"]):
            base = {"arm": arm, "repeat": t["repeat"], "fold": t["fold"], "budget": b, "sim_id": ids[i],
                    "response_available": bool(resp is None or np.isfinite(resp[i])), "prediction_status": status}
            if status != "ok":
                preds.append({**base, "threshold_mode": "learned", "p_keyhole": np.nan, "latent_mean": np.nan, "latent_variance": np.nan})
                if resp is not None:
                    preds.append({**base, "threshold_mode": "fixed_uref_diagnostic", "p_keyhole": np.nan, "latent_mean": np.nan, "latent_variance": np.nan})
                    orc.append({"target": target, "arm": arm, "repeat": t["repeat"], "fold": t["fold"], "budget": b, "sim_id": ids[i],
                                "observed_score": float(resp[i]), "training_threshold": np.nan, "predicted_label": np.nan, "predicted_log_depth": np.nan,
                                "status": status, "oracle_flag": ORACLE_FLAG})
                continue
            preds.append({**base, "threshold_mode": "learned", "p_keyhole": float(p[j]), "latent_mean": float(mu[j]), "latent_variance": float(var[j])})
            if resp is not None:
                mu_abs = float(mu[j] + f.u)                 # predicted log depth (the latent is relative to log u)
                lat = mu_abs - float(np.log(UREF))
                preds.append({**base, "threshold_mode": "fixed_uref_diagnostic", "p_keyhole": float(ndtr(lat / np.sqrt(var[j]))), "latent_mean": lat, "latent_variance": float(var[j])})
                obs = resp[i]; u_um = float(np.exp(f.u))
                orc.append({"target": target, "arm": arm, "repeat": t["repeat"], "fold": t["fold"], "budget": b, "sim_id": ids[i],
                            "observed_score": float(obs), "training_threshold": u_um, "predicted_label": float(obs >= u_um) if np.isfinite(obs) else np.nan,
                            "predicted_log_depth": mu_abs, "status": "ok" if np.isfinite(obs) else "observed_score_unavailable", "oracle_flag": ORACLE_FLAG})
    if not leak_ok:
        return _status_rec(rec, "stopped_leakage_guard"), preds, orc, False
    if not usable:
        rec["threshold_branch"] = "single_class" if resp is not None else ""
        _status_rec(rec, "unavailable_single_class"); emit("unavailable_single_class")
        return rec, preds, orc, True
    if resp is not None and (resp[L][ok] <= 0).any():
        _status_rec(rec, "failed_nonpositive_response"); emit("failed_nonpositive_response")
        return rec, preds, orc, True
    task = {"X": t["X"], "y": y_m, "pool": t["pool"], "prior": t["prior"], "depth": r_m}
    learner = ("G3", "mlii") if arm == "G3_SHARED" else ("GPR_depth", "mlii")
    t0 = time.time()
    with warnings.catch_warnings(record=True) as wl:
        warnings.simplefilter("always")
        try:
            f = E.fit_learner(learner, task, list(L), None, {"kernel": None, "b0": len(L)})
            err = ""
        except Exception as e:  # recorded, not repaired
            f, err = None, f"{type(e).__name__}: {e}"
    msgs = [str(x.message) for x in wl]
    rec["warnings"] = " | ".join(sorted({m[:150] for m in msgs}))[:500]
    rec["fit_counter"] = n_fits + 1
    status = "ok"
    if f is None:
        status = "failed_exception"; rec["error"] = err[:300]
    elif arm == "G3_SHARED":
        fp = float(getattr(f.gp, "mode_fp_", np.nan)); dg = f.gp.diagnostics_
        lml = float(f.gp.log_marginal_likelihood_value_)
        rec.update({"laplace_fixed_point_error": fp, "optimizer_success": bool(dg.optimizer_converged), "optimizer_message": str(dg.optimizer_message)[:150],
                    "optimizer_iterations": int(dg.optimizer_iterations), "fallback": str(dg.fallback_status), "log_marginal_likelihood": lml})
        if not np.isfinite(fp) or fp > FP_RULE or rec["fallback"] != "none" or not np.isfinite(lml):
            status = "failed_convergence"
    else:
        tt = np.log(resp[L][ok]); yy = yL[ok]
        rec.update(threshold_details(tt, yy))
        rec["u_um"] = float(np.exp(f.u)); rec["threshold_replication_abs_diff"] = abs(rec["log_u"] - float(f.u))
        rec["root_outside_range"] = bool(f.u < tt.min() or f.u > tt.max())
        rec["near_zero_slope"] = bool(rec["threshold_branch"] == "logistic" and abs(rec["b"]) < 1e-6)
        rec["optimizer_success"] = not any("failed to converge" in m.lower() or "abnormal" in m.lower() for m in msgs)
        rec["bound_warnings"] = int(sum("close to the specified" in m for m in msgs))
        lml = float(f.gp.log_marginal_likelihood_value_); rec["log_marginal_likelihood"] = lml
        rec["kernel"] = str(f.gp.kernel_)[:300]
        if rec["threshold_branch"] == "logistic" and not rec["b"] > 0:
            status = "failed_nonpositive_slope"
        elif not np.isfinite(lml):
            status = "failed_convergence"
    if status == "ok":
        Xt = t["X"][t["test"]]
        p = np.asarray(E.proba(f, Xt), float); mu, var = (np.asarray(v, float) for v in E.latent(f, Xt))
        if not (np.isfinite(p).all() and np.isfinite(mu).all() and np.isfinite(var).all() and (var > 0).all() and ((p >= 0) & (p <= 1)).all()):
            status = "failed_nonfinite_prediction"
    rec.update({"status": status, "converged": status == "ok", "wall_seconds": time.time() - t0, "peak_memory_bytes": peak_memory_bytes()})
    if status == "ok":
        emit("ok", f, p, mu, var)
    else:
        emit(status)
    return rec, preds, orc, True


def step_p1():
    from threadpoolctl import threadpool_info, threadpool_limits
    import src.week18_engine as E
    from src.week13_synthetic_al import maximin_order
    if not (OUT / "pilot_manifest.json").exists():
        raise SystemExit("pilot_manifest.json must exist before any fit")
    man = json.loads((OUT / "pilot_manifest.json").read_text(encoding="utf-8"))
    man_sha = sha256(OUT / "pilot_manifest.json")
    started = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    t_start = time.time()
    tasks = build_tasks()
    # ---- paths: label-blind, saved before any label is revealed
    paths = []
    for t in tasks:
        pos = maximin_order(t["X"][t["pool"]], np.random.default_rng([1820, t["repeat"], t["fold"], 2]))
        t["path"] = t["pool"][pos][:PATH_LEN]
        sids = t["ids"][t["path"]].tolist()
        psha = hashlib.sha256("\n".join(sids).encode()).hexdigest()
        for q, sid in enumerate(sids, 1):
            paths.append({"task": "R3_NEW", "repeat": t["repeat"], "fold": t["fold"], "query_index": q, "sim_id": sid,
                          "path_seed": f"[1820,{t['repeat']},{t['fold']},2]", "path_sha256": psha})
    _w(pd.DataFrame(paths), "paid_paths.csv")
    # ---- pre-fit invariants
    pre = []
    for t in tasks:
        pre.append({"repeat": t["repeat"], "fold": t["fold"], "train_test_disjoint": len(np.intersect1d(t["pool"], t["test"])) == 0,
                    "path_in_pool": bool(np.isin(t["path"], t["pool"]).all()), "path_unique": len(set(t["path"].tolist())) == PATH_LEN,
                    "path_disjoint_from_test": len(np.intersect1d(t["path"], t["test"])) == 0, "test_folds_partition_136": np.nan})
    for r in REPEATS:
        te = np.concatenate([t["test"] for t in tasks if t["repeat"] == r])
        pre.append({"repeat": r, "fold": 0, "test_folds_partition_136": sorted(te.tolist()) == list(range(136))})
    pre = pd.DataFrame(pre); _w(pre, "P1_prefit_invariants.csv")
    q20c = q20_cache_check(tasks); _w(q20c, "P1_q20_cache_check.csv")
    flags = pre.drop(columns=["repeat", "fold"]).to_numpy(object)
    if not (all(bool(v) for v in flags.ravel() if not (isinstance(v, float) and np.isnan(v))) and q20c.test_rows_equal.all() and q20c.q20_equal.all()):
        raise SystemExit("P1 stopped before fitting: path/split/q20 invariant failed")
    fits, preds, orc, stop = [], [], [], ""
    n_fits = 0
    with threadpool_limits(limits=2):
        thr = threadpool_info()
        for t in tasks:
            for b in BUDGETS:
                L = t["path"][:b]
                for arm in ARMS:
                    over = (n_fits >= CAPS["max_learner_fits"] and "learner-fit cap") or (time.time() - t_start > CAPS["max_elapsed_s"] and "elapsed cap") \
                        or (peak_memory_bytes() > CAPS["max_resident_bytes"] and "memory cap")
                    if over:
                        stop = over; break
                    rec, pr, oc, leak_ok = fit_one(E, t, arm, b, L, n_fits)
                    n_fits += int("fit_counter" in rec)
                    fits.append(rec); preds += pr; orc += oc
                    print(f"r{t['repeat']} f{t['fold']} B{b} {arm:17s} {rec['status']:26s} u={rec.get('u_um', np.nan):8.2f} {rec['wall_seconds']:6.2f}s", flush=True)
                    if not leak_ok:
                        stop = "leakage guard"; break
                if stop:
                    break
            if stop:
                break
    fd = pd.DataFrame(fits)
    fd = fd.reindex(columns=FIT_FIELDS + [c for c in fd.columns if c not in FIT_FIELDS])
    _w(fd, "fit_diagnostics.csv")
    pdf = pd.DataFrame(preds); _w(pdf.reindex(columns=PRED_FIELDS), "predictions.csv")
    od = pd.DataFrame(orc); _w(od.reindex(columns=ORACLE_FIELDS + ["arm", "predicted_log_depth"]), "oracle_response_diagnostics.csv")
    import scipy
    import sklearn
    run = {"manifest_sha256_at_fit_time": man_sha, "manifest_created_utc": man["created_utc"], "p1_started_utc": started,
           "p1_finished_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(), "learner_fits": n_fits, "elapsed_s": time.time() - t_start,
           "peak_memory_bytes": peak_memory_bytes(), "threadpools": [{k: d.get(k) for k in ("user_api", "internal_api", "num_threads")} for d in thr],
           "stopped": stop or None, "python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__,
           "scipy": scipy.__version__, "sklearn": sklearn.__version__, "env_threads": {k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")}}
    PROV.mkdir(parents=True, exist_ok=True)
    (PROV / "p1_run.json").write_text(json.dumps(run, indent=1))
    print(json.dumps(run, indent=1))
    print(fd.groupby(["arm", "budget", "status"]).size().to_string())
    if stop:
        raise SystemExit(f"P1 stopped: {stop} (partial diagnostic log saved; no primary claim)")
    return fd


# ======================================================================================== P2
def _order_and_groups():
    import src.week12_development_common as W12
    new = W12.load_new()
    inp = pd.read_csv(TAB / "pilot_inputs.csv")
    ids = new.sim_id.astype(str).to_numpy()
    y = new.has_keyhole.to_numpy(int)
    sk = np.isin(ids, shortk_ids(inp))
    return ids, y, sk, inp.set_index("sim_id")


def series_arrays(df, ids, value="p_keyhole"):
    """Per repeat: value vector over the 136 population-ordered sims (NaN where unavailable) and the fold vector."""
    out = {}
    pos = {s: i for i, s in enumerate(ids)}
    for r, g in df.groupby("repeat"):
        v = np.full(len(ids), np.nan); fold = np.zeros(len(ids), int)
        ii = g.sim_id.map(pos).to_numpy()
        if len(set(ii.tolist())) != len(ii) or len(ii) != len(ids):
            raise ValueError("not exactly one prediction per simulation and repeat")
        v[ii] = g[value].to_numpy(float); fold[ii] = g.fold.to_numpy(int)
        out[int(r)] = (v, fold)
    return out


def stats_w(p, avail, y, sk, q20, fold, W, resp_err=None):
    """Weighted metrics for one repeat; W: (D, n) multiplicity weights (row 0 = observed sample).  Returns dict of (D,) arrays."""
    pred = (np.nan_to_num(p, nan=-1.0) >= 0.5).astype(float)
    av = avail.astype(float)
    pos, neg = av * (y == 1), av * (y == 0)
    out = {}
    with np.errstate(invalid="ignore", divide="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        tp, pw = W @ (pos * pred), W @ pos
        tn, nw = W @ (neg * (1 - pred)), W @ neg
        sens, spec = tp / pw, tn / nw
        out.update({"BA": 0.5 * (sens + spec), "specificity_12neg": spec, "sensitivity_all_pos": sens})
        skm = av * sk
        out["sensitivity_shortK"] = (W @ (skm * pred)) / (W @ skm)
        pe = np.nan_to_num(p, nan=0.0)
        out["brier"] = (W @ (av * (pe - y) ** 2)) / (W @ av)
        correct = (pred == y).astype(float)
        accs, skipped = [], np.zeros(W.shape[0], int)
        for f in np.unique(fold):
            m = av * q20 * (fold == f)
            if m.sum() == 0:
                continue                        # Week 18: folds without q20 points are skipped (membership fixed)
            den = W @ m
            accs.append(np.where(den > 0, (W @ (m * correct)) / np.where(den > 0, den, 1), np.nan))
            skipped += (den == 0)
        out["q20_acc"] = np.nanmean(np.vstack(accs), axis=0) if accs else np.full(W.shape[0], np.nan)
        out["_q20_folds_skipped"] = skipped
        P, N = np.flatnonzero(pos > 0), np.flatnonzero(neg > 0)
        if len(P) and len(N):
            C = (p[P][:, None] > p[N][None, :]) + 0.5 * (p[P][:, None] == p[N][None, :])
            out["AUC"] = np.einsum("di,ij,dj->d", W[:, P], C, W[:, N]) / (W[:, P].sum(1) * W[:, N].sum(1))
        else:
            out["AUC"] = np.full(W.shape[0], np.nan)
        if resp_err is not None:
            ra = np.isfinite(resp_err).astype(float) * av; e = np.nan_to_num(resp_err)
            out["response_rmse_log"] = np.sqrt((W @ (ra * e ** 2)) / (W @ ra))
    return out


def boot_weights(y, draws=BOOT_DRAWS, seed=BOOT_SEED):
    """Row 0: observed sample (all ones).  Rows 1..draws: stratified multiplicities (positives, then negatives, per draw)."""
    rng = np.random.default_rng(seed)
    pos, neg = np.flatnonzero(y == 1), np.flatnonzero(y == 0)
    W = np.zeros((draws + 1, len(y)))
    W[0] = 1.0
    for d in range(1, draws + 1):
        W[d] += np.bincount(rng.choice(pos, len(pos), replace=True), minlength=len(y))
        W[d] += np.bincount(rng.choice(neg, len(neg), replace=True), minlength=len(y))
    return W


METRICS = ["BA", "q20_acc", "specificity_12neg", "sensitivity_all_pos", "sensitivity_shortK", "brier", "AUC", "response_rmse_log"]


def _ci(est, draws):
    dd = draws[np.isfinite(draws)]
    lo, hi = (np.percentile(dd, [2.5, 97.5]) if len(dd) else (np.nan, np.nan))
    return float(est), float(lo), float(hi), int((~np.isfinite(draws)).sum())


def step_p2():
    ids, y, sk, inp = _order_and_groups()
    pr = pd.read_csv(TAB / "predictions.csv"); fd = pd.read_csv(TAB / "fit_diagnostics.csv"); od = pd.read_csv(TAB / "oracle_response_diagnostics.csv")
    tasks = build_tasks()
    q20_of = {(t["repeat"], ids[i]): bool(q) for t in tasks for i, q in zip(t["test"], t["q20"])}
    # ---- evaluator-only join (never seen by the path or the learners)
    ev = pr.copy()
    yo = dict(zip(ids, y)); sko = dict(zip(ids, sk))
    ev["y"] = ev.sim_id.map(yo); ev["q20"] = [q20_of[(r, s)] for r, s in zip(ev.repeat, ev.sim_id)]
    ev["campaign"] = "NEW"; ev["short_K"] = ev.sim_id.map(sko); ev["negative_12"] = ev.y == 0
    ev["unresolved_fast_scan_negative"] = ev.sim_id.isin(UNRESOLVED); ev["late_negative"] = ev.sim_id == LATE_NEG
    ev["late_K_positive_low_depth"] = ev.sim_id == LATE_K_POS; ev["A_unavailable"] = ev.sim_id == NO_A
    ev["pred_label"] = np.where(ev.p_keyhole.notna(), (ev.p_keyhole >= 0.5).astype(float), np.nan)
    ev["observed_whole_um"] = ev.sim_id.map(inp.whole_max_um); ev["observed_A_um"] = ev.sim_id.map(inp.A_um)
    _w(ev, "evaluation.csv")
    q20v = {r: np.array([q20_of[(r, s)] for s in ids], float) for r in REPEATS}
    W = boot_weights(y)
    resp_err = {}
    for arm in E1_ARMS:
        o = od[od.arm == arm].copy()
        with np.errstate(divide="ignore", invalid="ignore"):
            o["err"] = o.predicted_log_depth - np.log(o.observed_score)
        for b in BUDGETS:
            resp_err[(arm, b)] = series_arrays(o[o.budget == b], ids, "err")
    S = {}
    for (arm, mode, b), g in ev.groupby(["arm", "threshold_mode", "budget"]):
        for r, va in series_arrays(g, ids).items():
            S[(arm, mode, b, r)] = va
    for arm in E1_ARMS:
        for b in BUDGETS:
            o = od[(od.arm == arm) & (od.budget == b)].assign(p_keyhole=lambda d: d.predicted_label)
            for r, va in series_arrays(o, ids).items():
                S[(arm, ORACLE_MODE, b, r)] = va

    def compute(key, mask=None):
        arm, mode, b = key
        out = {}
        for r in REPEATS:
            v, fold = S[(arm, mode, b, r)]
            av = np.isfinite(v) if mask is None else mask[r]
            re = resp_err[(arm, b)][r][0] if (arm, b) in resp_err and mode == "learned" else None
            out[r] = stats_w(v, av, y, sk, q20v[r], fold, W, re)
        return out

    def counts(av):
        return {"n_unique_simulations": len(ids), "n_positive": int((y == 1).sum()), "n_negative": int((y == 0).sum()),
                "n_available": int(av.sum()), "n_missing": int((~av).sum())}
    rows, undefined = [], []
    scopes = [("mean_over_repeats", REPEATS)] + [(f"repeat_{r}", [r]) for r in REPEATS]
    for key in sorted({k[:3] for k in S}):
        st = compute(key)
        avs = {r: np.isfinite(S[(*key, r)][0]) for r in REPEATS}
        sk_rows = [st[r]["_q20_folds_skipped"][1:] for r in REPEATS]
        undefined.append({"arm": key[0], "threshold_mode": key[1], "contrast": "", "budget": key[2], "metric": "q20_acc", "undefined_draws": 0,
                          "draws_with_a_fold_without_sampled_q20_points": int(((sk_rows[0] + sk_rows[1]) > 0).sum()), "reason": "such folds are skipped (Week 18 rule)"})
        for m in METRICS:
            if m not in st[REPEATS[0]]:
                continue
            for scope, reps in scopes:
                vec = np.mean([st[r][m] for r in reps], axis=0)
                est, lo, hi, nund = _ci(vec[0], vec[1:])
                rows.append({"arm": key[0], "threshold_mode": key[1], "contrast": "", "budget": key[2], "metric": m, "estimate": est, "lo95": lo, "hi95": hi,
                             **counts(np.concatenate([avs[r] for r in reps])), "scope": scope, "undefined_draws": nund})
                if nund and scope == "mean_over_repeats":
                    undefined.append({"arm": key[0], "threshold_mode": key[1], "contrast": "", "budget": key[2], "metric": m, "undefined_draws": nund,
                                      "reason": "no short-K positive drawn" if m == "sensitivity_shortK" else "statistic undefined in draw"})
    for a1, a2 in [("ACTIVE_E1_SHARED", "WHOLE_E1_SHARED"), ("ACTIVE_E1_SHARED", "G3_SHARED"), ("WHOLE_E1_SHARED", "G3_SHARED")]:
        for b in BUDGETS:
            mask = {r: np.isfinite(S[(a1, "learned", b, r)][0]) & np.isfinite(S[(a2, "learned", b, r)][0]) for r in REPEATS}
            s1, s2 = compute((a1, "learned", b), mask), compute((a2, "learned", b), mask)
            for m in METRICS[:-1]:
                for scope, reps in scopes:
                    vec = np.mean([s1[r][m] - s2[r][m] for r in reps], axis=0)
                    est, lo, hi, nund = _ci(vec[0], vec[1:])
                    rows.append({"arm": "", "threshold_mode": "learned", "contrast": f"{a1} - {a2}", "budget": b, "metric": m, "estimate": est, "lo95": lo, "hi95": hi,
                                 **counts(np.concatenate([mask[r] for r in reps])), "scope": scope, "undefined_draws": nund})
                    if nund and scope == "mean_over_repeats":
                        undefined.append({"arm": "", "threshold_mode": "learned", "contrast": f"{a1} - {a2}", "budget": b, "metric": m, "undefined_draws": nund,
                                          "reason": "no short-K positive drawn" if m == "sensitivity_shortK" else "statistic undefined in draw"})
    mt = pd.DataFrame(rows)
    mt = mt[["arm", "contrast", "budget", "metric", "estimate", "lo95", "hi95", "n_unique_simulations", "n_positive", "n_negative", "n_available", "n_missing",
             "scope", "threshold_mode", "undefined_draws"]]
    _w(mt, "metrics.csv")
    _w(pd.DataFrame(undefined), "bootstrap_undefined_draws.csv")
    negatives_summary(ev, inp)
    named_cases(ev, inp)
    checks = p2_checks(ev, fd, pr, od, W)
    dec = decide(mt, fd, checks, ev)
    hyp = hypotheses(mt, fd, ev)
    (OUT / "decision.json").write_text(json.dumps({"status": "POST-HOC EXPLORATORY DEV PILOT", "decision": dec, "prediction_vs_outcome": hyp}, indent=1, default=float))
    print(json.dumps(dec, indent=1, default=float)); print(json.dumps(hyp, indent=1, default=float))
    return mt


def _get(mt, metric, b, arm=None, contrast=None, scope="mean_over_repeats", mode="learned"):
    q = mt[(mt.metric == metric) & (mt.budget == b) & (mt.scope == scope) & (mt.threshold_mode == mode)]
    q = q[q.contrast == contrast] if contrast else q[(q.arm == arm) & (q.contrast.fillna("") == "")]
    if len(q) != 1:
        return {"estimate": np.nan, "lo95": np.nan, "hi95": np.nan}
    return {k: float(v) for k, v in q.iloc[0][["estimate", "lo95", "hi95"]].items()}


EXACT_TOL = 1e-12         # gate comparisons are evaluated in exact arithmetic: the metrics are fractions k/20 or k/24


def decide(mt, fd, checks, ev=None):
    b = PRIMARY_BUDGET
    d = _get(mt, "BA", b, contrast="ACTIVE_E1_SHARED - WHOLE_E1_SHARED")
    spec = {a: _get(mt, "specificity_12neg", b, a)["estimate"] for a in ARMS}
    skv = {a: _get(mt, "sensitivity_shortK", b, a)["estimate"] for a in ARMS}
    q = _get(mt, "q20_acc", b, contrast="ACTIVE_E1_SHARED - WHOLE_E1_SHARED")
    f40 = fd[fd.budget == b]
    avail = bool(len(f40) == 3 * 10 and (f40.status == "ok").all())
    lbfgs = int((f40.optimizer_success.astype("boolean") == False).sum()) if "optimizer_success" in f40 else 0  # noqa: E712
    p0 = pd.read_csv(TAB / "P0_CHECKS.csv")
    checks_ok = bool((p0.status != "FAIL").all() and (checks.status != "FAIL").all())
    ge = lambda x, y: bool(x >= y - EXACT_TOL)  # noqa: E731
    cond = {"mean_delta_BA_ge_0.01": ge(d["estimate"], 0.01), "lower_bound_gt_0": bool(d["lo95"] > 0),
            "specificity_ACTIVE_ge_WHOLE": ge(spec["ACTIVE_E1_SHARED"], spec["WHOLE_E1_SHARED"]),
            "specificity_ACTIVE_ge_G3": ge(spec["ACTIVE_E1_SHARED"], spec["G3_SHARED"]),
            "shortK_ACTIVE_ge_WHOLE_minus_0.05": ge(skv["ACTIVE_E1_SHARED"], skv["WHOLE_E1_SHARED"] - 0.05),
            "shortK_ACTIVE_ge_G3_minus_0.05": ge(skv["ACTIVE_E1_SHARED"], skv["G3_SHARED"] - 0.05),
            "all_B40_fits_available": avail, "all_checks_pass": checks_ok}
    if not avail or not checks_ok:
        verdict = "INCONCLUSIVE"
    elif all(cond.values()):
        verdict = "ADVANCE"
    elif cond["mean_delta_BA_ge_0.01"] and not cond["lower_bound_gt_0"]:
        verdict = "INCONCLUSIVE"
    else:
        verdict = "NO_ADVANCE"
    cnt = {}
    if ev is not None:
        e = ev[(ev.threshold_mode == "learned") & (ev.budget == b)]
        for a in ARMS:
            g = e[e.arm == a]
            cnt[a] = {"true_negatives_of_24": int(((g.y == 0) & (g.pred_label == 0)).sum()), "short_K_detected_of_20": int((g.short_K & (g.pred_label == 1)).sum())}
    margin = {"shortK_loss_vs_WHOLE": skv["WHOLE_E1_SHARED"] - skv["ACTIVE_E1_SHARED"], "shortK_loss_vs_G3": skv["G3_SHARED"] - skv["ACTIVE_E1_SHARED"],
              "BA_lower_bound": d["lo95"]}
    return {"verdict": verdict, "meaning": "exploratory DEV gate of the owner-modified rule; not confirmation. P3 and the fallback are not started (owner instruction); C3 stays reserved.",
            "conditions": cond, "comparison_tolerance": f"{EXACT_TOL:g} (exact-arithmetic evaluation of k/20 and k/24 fractions)",
            "delta_BA_B40_ACTIVE_minus_WHOLE": d, "delta_q20_B40_ACTIVE_minus_WHOLE": q,
            "q20_deteriorated": bool(q["estimate"] < 0),
            "boundary_statement": "q20 did not deteriorate, but its interval includes 0: no boundary improvement is claimed" if q["estimate"] >= 0 and q["lo95"] <= 0
                                  else ("q20 deteriorated: no improved-boundary claim" if q["estimate"] < 0 else "q20 improved with lower bound > 0"),
            "specificity_B40": spec, "shortK_sensitivity_B40": skv, "counts_B40_two_repeats": cnt, "margins": margin,
            "lbfgs_sensitivity": f"{lbfgs} B40 fits carry an L-BFGS-B non-success message; counted as failures, the verdict would be "
                                 + ("INCONCLUSIVE (B40 unavailable)" if lbfgs else "unchanged")}


def hypotheses(mt, fd, ev):
    b = PRIMARY_BUDGET
    ok = fd[fd.arm.isin(E1_ARMS) & (fd.status == "ok")]
    lr = ok.late_negative_revealed.astype(bool)
    w, a = ok[lr & (ok.arm == "WHOLE_E1_SHARED")], ok[lr & (ok.arm == "ACTIVE_E1_SHARED")]
    nw, na = ok[~lr & (ok.arm == "WHOLE_E1_SHARED")], ok[~lr & (ok.arm == "ACTIVE_E1_SHARED")]
    whole_pull, active_pull = int((w.u_um >= PULL_UM).sum()), int((a.u_um >= PULL_UM).sum())
    if len(w) == 0 and len(a) == 0:
        h1 = "UNTESTABLE (late negative never paid)"
    elif active_pull > 0:
        h1 = "FALSIFIED"
    elif whole_pull == 0:
        h1 = "UNTESTABLE (WHOLE_E1 shows no pull on the shared paths)"
    else:
        h1 = "SUPPORTED"
    ba = {x: _get(mt, "BA", b, x)["estimate"] for x in ARMS}
    h2_ok = (ba["ACTIVE_E1_SHARED"] - ba["WHOLE_E1_SHARED"] > 0) and (abs(ba["ACTIVE_E1_SHARED"] - ba["G3_SHARED"]) < abs(ba["WHOLE_E1_SHARED"] - ba["G3_SHARED"]))
    u4 = ev[(ev.arm == "ACTIVE_E1_SHARED") & (ev.threshold_mode == "learned") & (ev.budget == b) & ev.unresolved_fast_scan_negative]
    err4 = float(u4.pred_label.mean()) if len(u4) and u4.pred_label.notna().all() else np.nan
    skv = {x: _get(mt, "sensitivity_shortK", b, x)["estimate"] for x in ARMS}
    gain = skv["ACTIVE_E1_SHARED"] - skv["WHOLE_E1_SHARED"]
    h3 = "UNTESTABLE (prediction unavailable)" if not np.isfinite(err4) else ("SUPPORTED" if (err4 >= 0.5 - EXACT_TOL and gain <= 0.05 + EXACT_TOL) else "FALSIFIED")
    mx = lambda d: float(d.u_um.max()) if len(d) else np.nan  # noqa: E731
    return {"H1_threshold_pull_removed": {"result": h1, "fits_with_late_negative_paid": {"WHOLE": len(w), "ACTIVE": len(a)},
                                          "fits_with_u_ge_200um_late_negative_paid": {"WHOLE": whole_pull, "ACTIVE": active_pull},
                                          "fits_with_u_ge_200um_late_negative_not_paid": {"WHOLE": int((nw.u_um >= PULL_UM).sum()), "ACTIVE": int((na.u_um >= PULL_UM).sum())},
                                          "max_u_um_late_negative_paid": {"WHOLE": mx(w), "ACTIVE": mx(a)},
                                          "max_u_um_late_negative_not_paid": {"WHOLE": mx(nw), "ACTIVE": mx(na)}},
            "H2_moves_toward_G3": {"result": "SUPPORTED" if h2_ok else "FALSIFIED", "BA_B40": ba},
            "H3_fast_scan_ambiguity_remains": {"result": h3, "ACTIVE_mean_error_unresolved_4": err4, "shortK_gain_ACTIVE_minus_WHOLE": gain},
            "overall_prediction": "SUPPORTED" if (h1 == "SUPPORTED" and h2_ok and h3 == "SUPPORTED") else "NOT SUPPORTED AS STATED (see components)"}


def negatives_summary(ev, inp):
    neg = pd.read_csv(AUDIT / "tables/new_negatives_12_cases.csv").set_index("sim_id")
    rows = []
    for sid in neg.index:
        for (arm, mode, b), g in ev[ev.sim_id == sid].groupby(["arm", "threshold_mode", "budget"]):
            g = g.sort_values("repeat")
            rows.append({"sim_id": sid, "H": short(sid), "arm": arm, "threshold_mode": mode, "budget": b,
                         "p_repeat1": g.p_keyhole.iloc[0], "p_repeat2": g.p_keyhole.iloc[1] if len(g) > 1 else np.nan,
                         "fold_repeat1": g.fold.iloc[0], "fold_repeat2": g.fold.iloc[1] if len(g) > 1 else np.nan,
                         "n_predicted_keyhole": int((g.p_keyhole >= 0.5).sum()), "n_available": int(g.p_keyhole.notna().sum()),
                         "whole_max_um": inp.loc[sid, "whole_max_um"], "A_um": inp.loc[sid, "A_um"], "VX_m_s": inp.loc[sid, "VX_m_s"],
                         "unresolved_fast_scan": sid in UNRESOLVED, "mechanism_status": neg.loc[sid, "mechanism_status"]})
    d = pd.DataFrame(rows); _w(d, "negatives_12_predictions.csv")
    return d


def named_cases(ev, inp):
    skl = shortk_ids(inp.reset_index())
    ids = skl + [LATE_K_POS, NO_A, LATE_NEG]
    g = ev[ev.sim_id.isin(ids) & (ev.threshold_mode == "learned")]
    t = g.groupby(["sim_id", "arm", "budget"]).agg(n_pred=("p_keyhole", "size"), n_available=("p_keyhole", "count"),
                                                   n_predicted_keyhole=("pred_label", "sum"), mean_p=("p_keyhole", "mean")).reset_index()
    t["H"] = t.sim_id.map(short)
    t["group"] = np.select([t.sim_id.isin(skl), t.sim_id == LATE_K_POS, t.sim_id == NO_A, t.sim_id == LATE_NEG],
                           ["short_K_positive", "late_K_positive_low_depth", "A_unavailable_negative", "late_negative"], "")
    t["y"] = t.sim_id.map(inp.has_keyhole); t["whole_max_um"] = t.sim_id.map(inp.whole_max_um); t["A_um"] = t.sim_id.map(inp.A_um)
    t["frac_K_FCK"] = t.sim_id.map(inp.frac_K_FCK)
    _w(t, "named_case_predictions.csv")
    return t


def p2_checks(ev, fd, pr, od, W):
    rows = []

    def add(cid, desc, ok, detail):
        rows.append({"check": cid, "description": desc, "status": ok if isinstance(ok, str) else ("PASS" if ok else "FAIL"), "detail": detail})
    paths = pd.read_csv(TAB / "paid_paths.csv")
    pf = pd.read_csv(TAB / "P1_prefit_invariants.csv"); qc = pd.read_csv(TAB / "P1_q20_cache_check.csv")
    flags = pf.drop(columns=["repeat", "fold"]).to_numpy(object).ravel()
    add("P1-01", "train/test disjoint; the 5 test folds partition the 136 per repeat; path inside the training pool, unique and disjoint from test",
        all(bool(v) for v in flags if not (isinstance(v, float) and np.isnan(v))), f"{len(pf)} rows")
    gp = paths.groupby(["repeat", "fold"])
    add("P1-02", "paid_paths.csv: 80 unique paid simulations per (repeat, fold) and one path hash each",
        bool((gp.sim_id.nunique() == PATH_LEN).all() and (gp.path_sha256.nunique() == 1).all() and (gp.query_index.max() == PATH_LEN).all()), f"{gp.ngroups} paths")
    same = fd.groupby(["repeat", "fold", "budget"]).prefix_sha256.nunique()
    add("P1-03", "exact path equality across arms (identical paid-prefix hash for the three arms at every checkpoint)",
        bool((same == 1).all() and (fd.n_paid == fd.budget).all() and len(fd) == 90), f"{len(same)} checkpoints, {len(fd)} arm-checkpoints")
    add("P1-04", "no future-query label or response in fitting: learner arrays carry labels of the paid prefix only and responses of its valid rows only",
        bool((fd.labels_passed == fd.n_paid).all() and ((fd.arm == "G3_SHARED") | (fd.responses_passed == fd.n_response_available)).all()
             and (fd.status != "stopped_leakage_guard").all()), "leakage guard per fit")
    add("P1-05", "q20 flags and test rows identical to the pinned Week 18 phase2 cache (R3_NEW repeats 1-2, folds 1-5)",
        bool(qc.test_rows_equal.all() and qc.q20_equal.all() and len(qc) == 10), f"{int(qc.q20_equal.sum())}/10 folds; q20 points per fold {qc.n_q20.tolist()}")
    one = pr.groupby(["arm", "threshold_mode", "repeat", "budget"]).sim_id.agg(["size", "nunique"])
    add("P1-06", "exactly one prediction per simulation per (arm, threshold mode, repeat, checkpoint)", bool(((one["size"] == 136) & (one["nunique"] == 136)).all() and len(one) == 30),
        f"{len(one)} series")
    act, g3 = fd[fd.arm == "ACTIVE_E1_SHARED"], fd[fd.arm == "G3_SHARED"]
    o = od[(od.sim_id == NO_A) & (od.target == "A_um")]
    acc_ok = bool(((act.n_paid - act.n_response_available) == act.A_missing_paid.astype(int)).all()
                  and ((g3.n_positive_pairs + g3.n_negative_pairs) == g3.n_paid).all()
                  and (~pr[(pr.sim_id == NO_A) & (pr.arm == "ACTIVE_E1_SHARED")].response_available.astype(bool)).all()
                  and o.observed_score.isna().all() and o.predicted_label.isna().all() and len(o) > 0)
    add("P1-07", "missing-target accounting: the A-unavailable negative costs one query without an ACTIVE response pair, keeps its label for G3, and is evaluated (unscored by the oracle diagnostic) when held out",
        acc_ok, f"ACTIVE fits with H-e7dbd8e5ce paid: {int(act.A_missing_paid.astype(bool).sum())}/{len(act)}; oracle rows {len(o)}")
    okp = pr[pr.prediction_status == "ok"]
    add("P1-08", "positive finite variances and probabilities in [0,1] for every available prediction",
        bool(np.isfinite(okp.p_keyhole).all() and okp.p_keyhole.between(0, 1).all() and (okp.latent_variance > 0).all() and np.isfinite(okp.latent_mean).all()), f"{len(okp)} predictions")
    e1 = fd[fd.arm.isin(E1_ARMS) & (fd.status == "ok")]
    add("P1-09", "E1 threshold: engine u equals the replicated rule (|diff| < 1e-12); every fitted E1 used the midpoint or logistic branch (the 111 um fallback is never used)",
        bool((e1.threshold_replication_abs_diff < 1e-12).all() and e1.threshold_branch.isin(["midpoint", "logistic"]).all()),
        f"{len(e1)} fits; branches {e1.threshold_branch.value_counts().to_dict()}; near-zero slopes {int(e1.near_zero_slope.astype(bool).sum())}; roots outside range {int(e1.root_outside_range.astype(bool).sum())}")
    run = json.loads((PROV / "p1_run.json").read_text())
    thr_ok = all((d.get("num_threads") or 0) <= 2 for d in run["threadpools"])
    add("P1-10", "resource caps: <= 90 learner fits, one optimizer start per fit, <= 2 threads, <= 8 GiB peak working set, <= 4 h, not stopped",
        bool(run["learner_fits"] <= 90 and thr_ok and 0 < run["peak_memory_bytes"] <= CAPS["max_resident_bytes"] and run["elapsed_s"] <= CAPS["max_elapsed_s"] and not run["stopped"]),
        f"fits {run['learner_fits']}; peak {run['peak_memory_bytes'] / 2**30:.2f} GiB; {run['elapsed_s']:.0f} s; threads {[d.get('num_threads') for d in run['threadpools']]}")
    man = json.loads((OUT / "pilot_manifest.json").read_text(encoding="utf-8"))
    add("P1-11", "manifest written before any fit and unchanged since (hash recorded at fit time)",
        bool(run["manifest_sha256_at_fit_time"] == sha256(OUT / "pilot_manifest.json") and man["created_utc"] <= run["p1_started_utc"]),
        f"manifest {man['created_utc']} <= P1 start {run['p1_started_utc']}")
    inp = pd.read_csv(TAB / "pilot_inputs.csv")
    hp = pd.read_csv(TAB / "P0_input_hashes.csv")
    unchanged = all(git_blob(ROOT / p) == b for p, b in zip(hp.path, hp.pinned_git_blob))
    dirty = [l[3:] for l in _git("status", "--porcelain", "--untracked-files=no").splitlines()
             if l[3:].startswith(("outputs/", "data/")) and not l[3:].startswith("outputs/week19_temporal_regime_dev_pilot/")]
    c3 = c3_inventory()
    add("P1-12", "labels, eligibility, pinned audit inputs, tracked historical outputs and the C3 inventory unchanged",
        bool(unchanged and inp.has_keyhole.sum() == 197 and len(inp) == 541 and not dirty and c3 == man["c3_inventory_initial"] and sha256(TAB / "pilot_inputs.csv") == man["data"]["inputs_sha256"]),
        f"tracked historical modifications: {dirty[:5]}; C3 files {len(c3)}")
    add("P2-01", "bootstrap: 2000 stratified draws (seed 191026), 124 positives and 12 negatives per draw, observed sample in row 0",
        bool(W.shape == (BOOT_DRAWS + 1, 136) and (W[1:].sum(1) == 136).all()), f"{W.shape}")
    ck = pd.DataFrame(rows); _w(ck, "P1_CHECKS.csv")
    print(ck[["check", "status", "detail"]].to_string(max_colwidth=140))
    return ck


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "all"
    if step in ("p0", "all"):
        step_p0()
    if step in ("p1", "all"):
        step_p1()
    if step in ("p2", "all"):
        step_p2()
