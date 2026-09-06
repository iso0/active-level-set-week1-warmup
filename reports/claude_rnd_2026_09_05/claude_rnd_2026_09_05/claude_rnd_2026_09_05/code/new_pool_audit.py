#!/usr/bin/env python
"""Label-free feasibility audit of a NEW simulation pool (Phase 8).

INPUT  : a manifest of the new simulations — either a text file with one sph_v2-style
         experiment-folder name per line, or a CSV with columns
         experiment_name[, P, VX, LS, ST, XI, XF, XL, TE, DT, M].
         The file must NOT contain a label column; if one is present the script refuses to run.
OUTPUT : new_pool_audit.json + new_pool_audit.md with the gate decision.

Everything used here was fixed on the old 405 cases (development data):
  * physical h-overlap band  [min KH log h, max C log h] = [20.3621, 21.2533]
  * M3 fitted to all 405 old labels (old-model uncertainty of new candidates)
  * old-pool nearest-neighbour distance quantiles in standardised (log P, log VX, log LS, ST)
  * feasibility thresholds derived in NEW_POOL_FEASIBILITY_SPEC.md (results/feasibility_power_by_N.csv)
"""
from __future__ import annotations
import sys, json, math, re, hashlib
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent))          # rnd/  (core.py)

BAND = (20.3621, 21.2533)
MAIN_CFG = "0.0002|0.0014|0.0012|0.0021"
FORBIDDEN = re.compile(r"label|keyhole|conduction|regime|class|target|depth", re.I)


def parse_names(names):
    from src.week7_sph_v2_common import parse_experiment_name
    return pd.DataFrame([parse_experiment_name(n) for n in names])


def load_manifest(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
        bad = [c for c in df.columns if FORBIDDEN.search(c)]
        if bad:
            raise SystemExit(f"REFUSED: manifest contains label-like columns {bad}; supply an input-only manifest.")
        if "experiment_name" in df.columns and not {"P", "VX", "LS", "ST"}.issubset(df.columns):
            df = parse_names(df.experiment_name.astype(str))
    else:
        names = [l.strip() for l in path.read_text().splitlines() if l.strip()]
        df = parse_names(names)
    for c in ("P", "VX", "LS", "ST"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def main(manifest: str, out_dir: str = "."):
    from core import Data, M3, w85  # old population + frozen M3
    from sklearn.preprocessing import StandardScaler
    from scipy.spatial import distance
    new = load_manifest(Path(manifest))
    N = len(new)
    new["logh"] = np.log(new.P / np.sqrt(new.VX * new.LS ** 3))
    new["cfg"] = new[["XI", "XF", "XL", "TE"]].astype(str).agg("|".join, axis=1) if "TE" in new.columns else "unknown"
    d = Data(); old = d.population
    U_old = np.c_[np.log(old.P), np.log(old.VX), np.log(old.LS), old.ST]
    U_new = np.c_[np.log(new.P), np.log(new.VX), np.log(new.LS), new.ST]
    sc = StandardScaler().fit(U_old); Zo, Zn = sc.transform(U_old), sc.transform(U_new)
    nn_old = np.sort(distance.cdist(Zo, Zo), axis=1)[:, 1]
    nn_new_to_old = distance.cdist(Zn, Zo).min(axis=1)
    nn_new_within = np.sort(distance.cdist(Zn, Zn), axis=1)[:, 1] if N > 1 else np.array([np.nan])
    # old-model (M3 fitted to all 405 old labels) predictions for new inputs
    class _Spec: pass
    spec = _Spec(); spec.train_indices = tuple(range(len(old))); spec.run_id = "audit"; spec.test_indices = ()
    m3 = M3(d, spec).fit(np.arange(len(old)), 405)
    # M3 needs population rows: emulate by temporarily appending new rows to the data arrays
    x_all = np.r_[d.x4, new[["P", "VX", "LS", "ST"]].to_numpy(float)]
    lh_all = np.r_[d.logh, new.logh.to_numpy(float)]
    from core import p13
    comp = p13.components(m3.fit_, x_all[len(old):], lh_all[len(old):])
    p_new = comp["probability"]
    in_band = (new.logh >= BAND[0]) & (new.logh <= BAND[1])
    dup_old = pd.Series(new.experiment_name).isin(set(old.experiment_name)).sum() if "experiment_name" in new.columns else 0
    dup_within = int(new[["P", "VX", "LS", "ST"]].round(9).duplicated().sum())
    cfg_counts = new.cfg.value_counts().to_dict()
    # fold rule (frozen): largest K in {5,4,3,2} with N/K >= 85; else K=2 and 'small benchmark'
    Ks = [K for K in (5, 4, 3, 2) if N / K >= 85]; K = Ks[0] if Ks else 2
    n_test = N // K; n_train = N - n_test; H = min(80, int(math.floor(0.8 * n_train)))
    # expected band candidates in a training pool (label-free: physical band)
    N_band = int(in_band.sum()); N_band_train = N_band * n_train / N
    n_unc = int(((p_new > 0.1) & (p_new < 0.9)).sum()); n_unc_train = n_unc * n_train / N
    frac_far = float((nn_new_to_old > np.quantile(nn_old, 0.95)).mean())
    frac_main_cfg = float((new.cfg == MAIN_CFG).mean()) if "TE" in new.columns else float("nan")
    # ---- gate decision (thresholds derived in NEW_POOL_FEASIBILITY_SPEC.md)
    reasons = []
    if H < 40: reasons.append(f"horizon H={H} < 40: primary window 16-40 not reachable with 20% unrevealed")
    if N_band_train < 24: reasons.append(f"expected band candidates per training pool {N_band_train:.1f} < 24: margin exhausts the band inside the primary window")
    if n_unc_train < 12: reasons.append(f"expected old-model-uncertain candidates per training pool {n_unc_train:.1f} < 12")
    if frac_far > 0.5: reasons.append(f"{frac_far:.0%} of new inputs are farther from old support than the old 95% NN quantile: transfer of frozen hyperparameters doubtful")
    if not Ks: level = "SMALL_EXTERNAL_BENCHMARK"
    level = "TOO_WEAK_FOR_ACQUISITION_CLAIM" if reasons else ("FULL_LOCKED_PROTOCOL" if Ks else "SMALL_EXTERNAL_BENCHMARK")
    if level == "FULL_LOCKED_PROTOCOL" and N_band_train < 45: level = "SMALL_EXTERNAL_BENCHMARK"; reasons.append(f"band candidates per training pool {N_band_train:.1f} in [24,45): underpowered for a +0.01 early effect")
    report = {
        "manifest_sha256": hashlib.sha256(Path(manifest).read_bytes()).hexdigest(), "N_new": N, "K_folds": K, "n_test": n_test, "n_train": n_train, "horizon_H": H,
        "N_band": N_band, "N_band_per_training_pool": round(N_band_train, 1), "old_model_uncertain_0.1_0.9": n_unc, "old_model_uncertain_per_training_pool": round(n_unc_train, 1),
        "old_model_predicted_KH_fraction": float((p_new >= 0.5).mean()), "duplicates_of_old_experiments": int(dup_old), "duplicate_input_tuples_within_new": dup_within,
        "logh_range_new": [float(new.logh.min()), float(new.logh.max())], "logh_range_old": [float(d.logh.min()), float(d.logh.max())],
        "input_ranges_new": {c: [float(new[c].min()), float(new[c].max())] for c in ("P", "VX", "LS", "ST")},
        "nn_distance_new_to_old_quantiles": np.quantile(nn_new_to_old, [.5, .9, .95]).round(3).tolist(), "old_nn_quantiles": np.quantile(nn_old, [.5, .9, .95]).round(3).tolist(),
        "fraction_new_beyond_old_95pct_nn": frac_far, "within_new_nn_median": float(np.nanmedian(nn_new_within)),
        "configurations": cfg_counts, "fraction_main_configuration": frac_main_cfg, "unique_contexts_VX_LS_ST": int(new[["VX", "LS", "ST"]].round(9).drop_duplicates().shape[0]),
        "gate_level": level, "gate_reasons": reasons,
    }
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    (out / "new_pool_audit.json").write_text(json.dumps(report, indent=2))
    md = ["# New-pool label-free audit", "", f"Gate: **{level}**", ""] + [f"- {r}" for r in reasons] + ["", "```", json.dumps(report, indent=2), "```"]
    (out / "new_pool_audit.md").write_text("\n".join(md))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: new_pool_audit.py <manifest.txt|manifest.csv> [out_dir]")
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ".")
