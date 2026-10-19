"""RC19 pooled from-scratch benchmark: ONE pool of the 541 eligible SPH simulations (405 + 136), a paid-only reveal interface,
pooled splits and evaluator-only fields (owner instruction of 2026-10-19; research campaign 20261018 budget).

Information contract (enforced by `Reveal`; validated by `python -m src.rc19_pool validate`):
  * before any query the learner sees the public inputs x = (P, VX, LS, ST) of every candidate and nothing else;
  * one revealed simulation costs ONE query and exposes its label, active-window depth, physical summaries and its own
    record quality (missing channels and truncated records keep their cost); unpaid and test outcomes are never held by
    the learner (its arrays are NaN / -1 outside the paid rows);
  * source batch (OLD/NEW) and source revision are provenance only: no learner, prior, threshold or acquisition reads them;
  * the common feature-only startup (first B0 points of the label-free maximin path) is PAID and counted.
Evaluator-only fields: test labels and outputs, q20 (pooled semantics, below), short-Keyhole membership (pooled rule, below).

Data (reused audited extractions; nothing re-extracted):
  inputs / canonical label: src.week18_data_audit.load (541; the 49 Bug-withheld NEW entries stay excluded);
  active-window depth A: Week 19 table A_active_max_um (src.jdl_physical_pilot.W19_DEPTH) = PHYS_AL's log_A_um;
  physical summaries: src.rc18_campaign.targets (PHYS_AL definitions, same summarize code for both batches; OLD log KE T0
  completed by the channel-independent RC18 loader, fix A2); record quality: RC18 data layer (data/SUMMARIES.csv).
q20 (pooled, evaluator only): src.external_validation.analysis.boundary_flags on the POOLED batch (541 runs; standardised raw
  inputs; nearest opposite-class distance), the 20 % of each test fold closest to the boundary.
short-Keyhole (pooled, evaluator only): has_keyhole = 1 and 0 < frac_K_FCK < 0.10, applied to every run (the original Week 19
  rule restricted it to NEW; that NEW-only set is kept as a continuity column).
    python -m src.rc19_pool manifest | checks | validate
"""
from __future__ import annotations

import hashlib
import json
import sys

import numpy as np
import pandas as pd

import src.rc18_common as RC

OUT = RC.ROOT / "outputs" / "research_campaign_20261018" / "opus_pooled"
DATA = OUT / "data"
TARGETS = ("log_A_um", "log_ke_T0_nJ", "vmax_spike_logratio", "vmax_spike_us", "laser_T0_W", "tmax_T0_K", "log_etot_T0_J", "log_npart_T0")
INPUTS = ("P", "VX", "LS", "ST")
B0 = 8                                   # common feature-only startup (paid, counted)
SPLIT_SEED = 1919
DEV_REPEATS = (1, 2)
FINAL_REPEATS = (3, 4, 5, 6, 7, 8, 9, 10)
W_SHORT = 1e4


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


# ======================================================================================== manifest (one table, one row per run)
def build_manifest():
    import src.jdl_physical_pilot as PP
    import src.jdl_stage_m as SMM
    import src.rc18_campaign as C
    import src.week18_data_audit as DA
    from src.week19_dev_pilot import shortk_ids
    D = DA.load().set_index("sim_id"); inp = SMM.inputs_table(); W = pd.read_csv(PP.W19_DEPTH).set_index("sim_id")
    ids = sorted(D.index.astype(str))
    M = pd.DataFrame(index=pd.Index(ids, name="sim_id"))
    M["source_batch"] = np.where(D.loc[ids, "campaign"].to_numpy() == 1, "NEW", "OLD")            # provenance only
    M["source_revision"] = inp.reindex(ids)["source_revision"].astype(str).to_numpy()            # provenance only
    for c in INPUTS:
        M[c] = D.loc[ids, c].astype(float).to_numpy()
    M["TE_ms"] = pd.Series(ids, index=ids).str.extract(r"_TE-([0-9p]+)_")[0].str.replace("p", ".").astype(float).to_numpy() * 1e3
    M["XI_mm"] = pd.Series(ids, index=ids).str.extract(r"_XI-(-?[0-9p]+)_")[0].str.replace("p", ".").astype(float).to_numpy() * 1e3
    M["y"] = D.loc[ids, "has_keyhole"].astype(int).to_numpy()
    M["A_um"] = W.reindex(ids)["A_active_max_um"].astype(float).to_numpy()
    T = pd.concat([C.targets("NEW"), C.targets("OLD")]); T = T[~T.index.duplicated()]
    for c in TARGETS:
        M[c] = T.reindex(ids)[c].astype(float).to_numpy()
    S = pd.read_csv(RC.CAMP / "data" / "SUMMARIES.csv").set_index("sim_id")
    M["t_end_ms"] = S.reindex(ids)["time_t_end_ms"].astype(float).to_numpy()
    M["short_record"] = np.where(np.isfinite(M.t_end_ms), M.t_end_ms < 0.95 * M.TE_ms, False)
    M["early_end"] = inp.reindex(ids)["early_end"].astype(bool).to_numpy()
    M["frac_K_FCK"] = inp.reindex(ids)["frac_K_FCK"].astype(float).to_numpy()
    M["shortK_pooled"] = (M.y == 1) & (M.frac_K_FCK > 0) & (M.frac_K_FCK < 0.10)
    M["shortK_NEW_original"] = M.index.isin(shortk_ids(inp.reset_index()))
    DATA.mkdir(parents=True, exist_ok=True)
    M.to_csv(DATA / "POOLED_MANIFEST.csv", lineterminator="\n")
    meta = {"rows": len(M), "sha256_csv": hashlib.sha256((DATA / "POOLED_MANIFEST.csv").read_bytes()).hexdigest(), "utc": RC.utc(),
            "sources": {"inputs_labels": "src.week18_data_audit.load", "depth": str(PP.W19_DEPTH.relative_to(RC.ROOT)),
                        "summaries": "src.rc18_campaign.targets (PHYS_AL + RC18 fix A2)", "quality": "outputs/research_campaign_20261018/opus/data/SUMMARIES.csv",
                        "evaluator": "pilot_inputs.csv (frac_K_FCK, early_end, source_revision)"}}
    (DATA / "POOLED_MANIFEST.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return M


def manifest():
    return pd.read_csv(DATA / "POOLED_MANIFEST.csv", index_col=0)


# ======================================================================================== data checks (descriptive, all DEV)
def checks():
    import src.jdl_physical_pilot as PP
    import src.jdl_stage_m as SMM
    import src.week18_data_audit as DA
    from scipy.spatial.distance import cdist
    M = manifest(); D = DA.load().set_index("sim_id"); inp = SMM.inputs_table(); W = pd.read_csv(PP.W19_DEPTH).set_index("sim_id")
    R = {"utc": RC.utc(), "rows": len(M)}
    ids = M.index.to_numpy(str)
    R["unique_sim_ids"] = bool(M.index.is_unique) and len(M) == 541
    R["source_counts"] = M.source_batch.value_counts().to_dict()
    R["labels_agree_audit_pilot_W19"] = bool((inp.reindex(ids).has_keyhole.astype(int).to_numpy() == M.y.to_numpy()).all()
                                            and (W.reindex(ids).y.astype(int).to_numpy() == M.y.to_numpy()).all())
    R["depth_agree_pilot_A_um"] = float(np.nanmax(np.abs(inp.reindex(ids).A_um.to_numpy(float) - M.A_um.to_numpy())))
    R["depth_equals_log_A_target"] = float(np.nanmax(np.abs(np.log(M.A_um.where(M.A_um > 0)) - M.log_A_um)))
    X = np.log(M[list(INPUTS)].to_numpy(float)); Z = (X - X.mean(0)) / X.std(0); d = cdist(Z, Z); np.fill_diagonal(d, np.inf)
    R["duplicate_conditions"] = {"exact_repeats_of_(P,VX,LS,ST)": int(len(M) - M[list(INPUTS)].round(9).drop_duplicates().shape[0]),
                                 "min_nn_distance_std_log_inputs": float(d.min()), "pairs_below_0.02": int((d < 0.02).sum() // 2),
                                 "grouping": "none needed: every run is its own group"}
    R["H_codes_repeated"] = int((M.index.str.extract(r"_H-([0-9a-f]+)")[0].value_counts() > 1).sum())
    R["input_ranges"] = {b: {c: [float(g[c].min()), float(g[c].max())] for c in INPUTS} for b, g in M.groupby("source_batch")}
    R["settings"] = {"TE_ms": {f"{b}:{k}": int(v) for (b, k), v in M.groupby(["source_batch", "TE_ms"]).size().items()},
                     "XI_mm": {f"{b}:{k}": int(v) for (b, k), v in M.groupby(["source_batch", "XI_mm"]).size().items()}}
    R["class_balance"] = {"pooled_keyhole_share": float(M.y.mean()), **{f"{b}_keyhole_share": float(g.y.mean()) for b, g in M.groupby("source_batch")}}
    R["coverage"] = {c: {"pooled": int(np.isfinite(M[c]).sum()), **{b: int(np.isfinite(g[c]).sum()) for b, g in M.groupby("source_batch")}} for c in ("A_um",) + TARGETS}
    R["quality"] = {"short_record": {b: int(g.short_record.sum()) for b, g in M.groupby("source_batch")}, "early_end": {b: int(g.early_end.sum()) for b, g in M.groupby("source_batch")}}
    R["shortK"] = {"pooled_rule": int(M.shortK_pooled.sum()), "pooled_rule_by_batch": {b: int(g.shortK_pooled.sum()) for b, g in M.groupby("source_batch")},
                   "NEW_original": int(M.shortK_NEW_original.sum()), "NEW_original_subset_of_pooled": bool((~M.shortK_NEW_original | M.shortK_pooled).all())}
    # definition consistency: PHYS_AL summaries vs the independent RC18 loader, per batch (same physical quantity, two codes)
    S = pd.read_csv(RC.CAMP / "data" / "SUMMARIES.csv").set_index("sim_id").reindex(ids)
    pairs = {"log_ke_T0_nJ": np.log(S["ke__row_median_T0"].where(S["ke__row_median_T0"] > 0)), "laser_T0_W": S["laser__row_mean_T0"],
             "tmax_T0_K": S["tmax__row_median_T0"], "log_etot_T0_J": np.log(S["etot__row_median_T0"].where(S["etot__row_median_T0"] > 0)),
             "log_npart_T0": np.log(S["npart__row_median_T0"].where(S["npart__row_median_T0"] > 0))}
    cons = {}
    for c, alt in pairs.items():
        for b in ("OLD", "NEW"):
            m = (M.source_batch == b).to_numpy(); a = M[c].to_numpy(float)[m]; o = np.asarray(alt, float)[m]; ok = np.isfinite(a) & np.isfinite(o)
            cons[f"{c}|{b}"] = {"n": int(ok.sum()), "max_abs_diff": float(np.max(np.abs(a[ok] - o[ok]))) if ok.any() else None,
                                "median_abs_diff": float(np.median(np.abs(a[ok] - o[ok]))) if ok.any() else None}
    R["definition_consistency_PHYS_AL_vs_RC18_loader"] = cons
    # cross-source compatibility where the batches overlap: NEW run vs its 3 nearest OLD runs, against OLD vs its 3 nearest OLD
    new, old = np.flatnonzero(M.source_batch == "NEW"), np.flatnonzero(M.source_batch == "OLD")
    dNO = cdist(Z[new], Z[old]); dOO = cdist(Z[old], Z[old]); np.fill_diagonal(dOO, np.inf)
    comp = {}
    for c in TARGETS:
        y = M[c].to_numpy(float)
        def local(dm, rows, cols_):
            out = []
            for i, r in enumerate(rows):
                k = np.argsort(dm[i])[:3]
                if dm[i, k].max() <= 0.6 and np.isfinite(y[r]) and np.isfinite(y[cols_[k]]).all():
                    out.append(y[r] - y[cols_[k]].mean())
            return np.asarray(out)
        cr, wi = local(dNO, new, old), local(dOO, old, old)
        comp[c] = {"n_NEW_matched": int(len(cr)), "NEW_minus_OLDnn_median": float(np.median(cr)) if len(cr) else None,
                   "NEW_minus_OLDnn_IQR": float(np.subtract(*np.percentile(cr, [75, 25]))) if len(cr) else None,
                   "OLD_minus_OLDnn_IQR_baseline": float(np.subtract(*np.percentile(wi, [75, 25]))) if len(wi) else None,
                   "n_OLD_baseline": int(len(wi))}
    R["cross_source_overlap_check"] = comp
    R["missingness_vs_batch"] = {c: {b: float(np.mean(~np.isfinite(g[c]))) for b, g in M.groupby("source_batch")} for c in TARGETS}
    (DATA / "POOLED_CHECKS.json").write_text(json.dumps(R, indent=1, default=str), encoding="utf-8")
    return R


# ======================================================================================== pooled splits, startup paths, evaluator fields
def tasks(repeats):
    """Pooled task-folds: per repeat a seeded random 5-fold partition of all 541 runs (no stratification by batch or label;
    no grouping needed, see checks); pool = 4 folds, test = 1 fold. Startup path = label-free maximin order of the pool's
    inputs (src.week13_synthetic_al.maximin_order, rng [SPLIT_SEED, repeat, fold, 2]); its first B0 points are the common
    PAID startup of every arm. q20: pooled boundary flags (evaluator only)."""
    from src.external_validation.analysis import boundary_flags
    from src.week13_synthetic_al import maximin_order
    M = manifest(); ids = M.index.to_numpy(str); X = M[list(INPUTS)].to_numpy(float); n = len(M); out = []
    for r in repeats:
        rng = np.random.default_rng([SPLIT_SEED, r]); perm = rng.permutation(n); folds = np.empty(n, int); folds[perm] = np.arange(n) % 5
        for f in range(5):
            test = np.flatnonzero(folds == f); pool = np.flatnonzero(folds != f)
            order = maximin_order(X[pool], np.random.default_rng([SPLIT_SEED, r, f + 1, 2])); path = pool[order]
            q20 = boundary_flags(X, M.y.to_numpy(int), test, ids, "entire_evaluation_batch")[20]
            out.append({"repeat": int(r), "fold": f + 1, "ids": ids, "X": X, "pool": pool, "test": test, "path": path, "q20": q20,
                        "split_sha256": _sha(",".join(ids[test])), "path_sha256": _sha(",".join(ids[path]))})
    return out


def zstd(task):
    """Public standardisation: log inputs, mean/sd of the candidate pool's inputs (features only; known before any query)."""
    lx = np.log(task["X"]); mu, sd = lx[task["pool"]].mean(0), lx[task["pool"]].std(0)
    return (lx - mu) / sd


# ======================================================================================== the reveal interface
class Reveal:
    """The only route from hidden outcomes to a learner. The hidden table is held in a closure; a learner can ask for
    `reveal(i)` (one query, counted, candidates only, never twice) and read back ONLY what was revealed through `paid_*`.
    Missing channels / truncated records are revealed as such and keep their cost."""

    def __init__(self, task, M=None):
        M = manifest() if M is None else M
        ids = list(task["ids"]); H = M.reindex(ids)
        hidden = {"y": H.y.to_numpy(int), "A": H.A_um.to_numpy(float), "Y": H[list(TARGETS)].to_numpy(float),
                  "short": H.short_record.to_numpy(bool), "t_end_ms": H.t_end_ms.to_numpy(float), "TE_ms": H.TE_ms.to_numpy(float)}
        candidates = frozenset(int(i) for i in task["pool"]); n = len(ids)
        self.n, self.order, self.queries = n, [], 0
        self._y = np.full(n, -1, int); self._A = np.full(n, np.nan); self._Y = np.full((n, len(TARGETS)), np.nan); self._short = np.zeros(n, bool)

        def _reveal(i):
            i = int(i)
            if i not in candidates:
                raise PermissionError(f"row {i} is not a query candidate (test or unknown row)")
            if i in self.order:
                raise ValueError(f"row {i} was already paid")
            self.order.append(i); self.queries += 1
            self._y[i] = hidden["y"][i]; self._A[i] = hidden["A"][i]; self._Y[i] = hidden["Y"][i]; self._short[i] = hidden["short"][i]
            return {"y": int(hidden["y"][i]), "A": float(hidden["A"][i]), "Y": hidden["Y"][i].copy(), "short": bool(hidden["short"][i])}
        self.reveal = _reveal

    # learner-visible arrays (NaN / -1 / False outside the paid rows)
    @property
    def paid(self):
        return np.asarray(self.order, int)

    def paid_y(self):
        return self._y.copy()

    def paid_A(self):
        return self._A.copy()

    def paid_Y(self):
        return self._Y.copy()

    def paid_short(self):
        return self._short.copy()


class Evaluator:
    """Evaluator-only truths of one task (test rows): never passed to a learner."""

    def __init__(self, task, M=None):
        M = manifest() if M is None else M
        H = M.reindex(list(task["ids"])); t = task["test"]
        self.test = t; self.y = H.y.to_numpy(int)[t]; self.A = H.A_um.to_numpy(float)[t]; self.Y = H[list(TARGETS)].to_numpy(float)[t]
        self.q20 = np.asarray(task["q20"], bool); self.shortK = H.shortK_pooled.to_numpy(bool)[t]; self.shortK_NEW = H.shortK_NEW_original.to_numpy(bool)[t]
        self.batch = H.source_batch.to_numpy(str)[t]                         # diagnostics only (failed-corner reporting)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "manifest":
        M = build_manifest(); print(len(M), "rows ->", DATA / "POOLED_MANIFEST.csv")
    elif cmd == "checks":
        print(json.dumps(checks(), indent=1, default=str)[:6000])
    else:
        raise SystemExit(f"unknown command {cmd}")
