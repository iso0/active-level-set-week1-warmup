"""Week 13 checks of two elementary propositions on already-open data (EXPLORATORY).

Proposition D (geometric discovery certificate).  Let S_b be any design inside a
finite pool U, h_b = max_{u in U} min_{s in S_b} |u - s| its fill distance and,
for a minority pool point x, rho(x) its distance to the nearest majority pool
point.  If h_b < rho* = max_x rho(x), then S_b contains a minority point.

Proposition S (score-ordered discovery).  If after k seed queries only the
majority class has been observed and further queries follow a fixed score
order, the number of extra queries until the first minority label is at most
1 + #{majority remaining ranked before the best-ranked remaining minority}
<= 1 + n_maj * (1 - AUC), AUC computed on the remaining pool.

Proposition A (anchoring bound for a fixed-mean logistic Laplace GPC).  The
predictive latent mean is mu(x) = m(x) + sum_i k(x, x_i) (y_i - pi_i) with
|y_i - pi_i| < 1, hence a point can be predicted in class 0 only if
m(x) < sum_{i: y_i = 0} k(x, x_i) = sigma^2 * S0(x), S0 = correlation-weighted
count of labelled class-0 neighbours.  We check how many NEW rare cases are
certified unreachable for M3 under its fitted amplitude.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

from src import week9_phase1_11_fixed_mean_discrepancy_gp as p11
from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13
from src.week12_development_common import FEATURES, load_new, load_old, load_splits, original_order
from src import week12_startup as w12s

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/week13_boundary_evaluation_and_mechanisms/theory_checks"


def fill_distances(z, order):
    """h_b for b = 1..len(order) for a nested design given by ``order`` (local indices)."""
    n = len(z)
    nearest = np.full(n, np.inf)
    out = []
    for idx in order:
        nearest = np.minimum(nearest, np.linalg.norm(z - z[idx], axis=1))
        out.append(nearest.max())
    return np.asarray(out)


def hypergeom_expected_discovery(n0, n1, horizon):
    n = n0 + n1
    total = 0.0
    for b in range(0, horizon):
        if b == 0:
            p = 1.0
        else:
            p = ((math.comb(n0, b) if n0 >= b else 0) + (math.comb(n1, b) if n1 >= b else 0)) / math.comb(n, b)
        total += p
    return total  # E[T] = sum_{b>=0} P(T > b) with T = first budget with both classes


def discovery_checks():
    new = load_new()
    x = new[FEATURES].to_numpy(float)
    y = new.has_keyhole.to_numpy(int)
    logh = new.log_h.to_numpy(float)
    splits = load_splits()
    rows = []
    for s in splits:
        train = np.asarray(s["train_indices"], int)
        z = StandardScaler().fit_transform(x[train])
        yt = y[train]
        order_global = original_order(x, s)
        pos = {g: i for i, g in enumerate(train)}
        order = np.asarray([pos[g] for g in order_global])
        h = fill_distances(z, order)
        minority = np.nonzero(yt == 0)[0]
        majority = np.nonzero(yt == 1)[0]
        rho = cdist(z[minority], z[majority]).min(axis=1)
        rho_star = float(rho.max())
        guar = int(np.argmax(h < rho_star) + 1) if (h < rho_star).any() else None
        labels_in_order = yt[order]
        first_both = int(np.argmax([len(set(labels_in_order[:b])) == 2 for b in range(1, len(order) + 1)]) + 1)
        # adaptive physics rule cost, exact replay of Week 12 rule
        seen = labels_in_order[:8]
        if len(set(seen)) == 2:
            adaptive = first_both if first_both <= 8 else None
            adaptive = first_both
            extra_bound = None
            auc_rem = None
        else:
            remaining = np.setdiff1d(np.arange(len(train)), order[:8])
            direction = 1 if seen[0] == 1 else -1  # only Keyhole seen -> ascend log h
            rem_scores = logh[train][remaining]
            rk = remaining[np.argsort(direction * rem_scores, kind="stable")]
            target = 0 if seen[0] == 1 else 1
            first = int(np.argmax(yt[rk] == target)) + 1
            adaptive = 8 + first
            maj_rem = int((yt[remaining] != target).sum())
            lab = (yt[remaining] == target).astype(int)
            auc_rem = float(roc_auc_score(lab, -direction * rem_scores))
            extra_bound = 1 + maj_rem * (1 - auc_rem)
        rows.append({"split_id": s["split_id"], "n_pool": len(train), "n_minority": len(minority),
                     "rho_star": rho_star, "rho_median": float(np.median(rho)),
                     "h_8": float(h[7]), "h_16": float(h[15]), "h_24": float(h[23]),
                     "guarantee_budget": guar, "maximin_first_both": first_both,
                     "certificate_holds": guar is None or first_both <= guar,
                     "adaptive_first_both": adaptive, "adaptive_extra_bound": extra_bound,
                     "auc_remaining_logh": auc_rem,
                     "uniform_expected_first_both": hypergeom_expected_discovery(len(minority), len(majority), len(train)),
                     "fill_slope_loglog_b8_64": float(np.polyfit(np.log(np.arange(8, 65)), np.log(h[7:64]), 1)[0])})
    return pd.DataFrame(rows)


def old_discovery_reference():
    """Same quantities on the OLD Week 8.5 training pools (minority = Keyhole there)."""
    from src import week8_5_frozen_sample_efficiency_confirmation as w85
    old = load_old()
    x = old[FEATURES].to_numpy(float)
    y = old.has_keyhole.to_numpy(int)
    man = pd.read_csv(ROOT / "outputs/week8_5_frozen_confirmation/split_manifest.csv", usecols=["run_id", "role", "population_row_index"])
    rows = []
    for run, g in man[man.role.eq("training_pool")].groupby("run_id"):
        train = g.population_row_index.to_numpy(int)
        z = StandardScaler().fit_transform(x[train])
        yt = y[train]
        key = w85.seed_u32(w85.seed_key("run", run, "initial_design"))
        from src.external_validation.runner import feature_only_maximin
        og = feature_only_maximin(x, train, key, 64)
        pos = {gg: i for i, gg in enumerate(train)}
        order = np.asarray([pos[gg] for gg in og])
        h = fill_distances(z, order)
        minority = np.nonzero(yt == 1)[0]
        majority = np.nonzero(yt == 0)[0]
        rho = cdist(z[minority], z[majority]).min(axis=1)
        lab = yt[order]
        first_both = int(np.argmax([len(set(lab[:b])) == 2 for b in range(1, 65)]) + 1)
        rows.append({"run_id": run, "n_pool": len(train), "n_minority": len(minority), "rho_star": float(rho.max()),
                     "rho_median": float(np.median(rho)), "h_8": float(h[7]), "h_16": float(h[15]),
                     "guarantee_budget": int(np.argmax(h < rho.max()) + 1) if (h < rho.max()).any() else None,
                     "maximin_first_both": first_both,
                     "uniform_expected_first_both": hypergeom_expected_discovery(len(minority), len(majority), len(train))})
    return pd.DataFrame(rows)


def anchoring_rows(fit, x_all, logh_all, y_all, train_idx, test_idx, scope, split_id):
    """Per test point: physics mean, achieved latent, and the rare-side anchoring bound."""
    xs_test = fit.x_scaler.transform(x_all[test_idx])
    m = fit.physics.latent(logh_all[test_idx])
    mu, _ = fit.gp.latent_mean_and_variance(xs_test, m)
    K = fit.gp.kernel_(fit.gp.X_train_, xs_test)  # sigma^2 * correlation
    ytr = fit.gp.y_train_
    resid = (ytr - fit.gp.pi_)[:, None]
    push_rare_max = K[ytr == 0].sum(axis=0)  # sum_{labelled rare} k(x, x_i)
    push_rare_actual = -(K * resid)[ytr == 0].sum(axis=0)
    push_kh_actual = (K * resid)[ytr == 1].sum(axis=0)
    sigma2 = float(fit.residual_sd ** 2)
    out = []
    for j, gi in enumerate(test_idx):
        out.append({"scope": scope, "split_id": split_id, "row_index": int(gi), "truth": int(y_all[gi]),
                    "physics_latent": float(m[j]), "final_latent": float(mu[j]),
                    "rare_push_bound": float(push_rare_max[j]), "rare_push_actual": float(push_rare_actual[j]),
                    "keyhole_push_actual": float(push_kh_actual[j]), "sigma2": sigma2,
                    "rare_corr_count": float(push_rare_max[j] / sigma2),
                    "certified_unreachable_as_rare": bool(m[j] >= push_rare_max[j]),
                    "unreachable_even_at_amplitude_cap": bool(m[j] >= 1.0 * push_rare_max[j] / sigma2),
                    "predicted_rare": bool(mu[j] < 0)})
    return out


def anchoring_checks():
    new = load_new()
    old = load_old()
    rows = []
    # strict OLD -> NEW transfer (deployment fit on all OLD, scored on NEW)
    xo = old[FEATURES].to_numpy(float); yo = old.has_keyhole.to_numpy(int); lo = old.log_h.to_numpy(float)
    xn = new[FEATURES].to_numpy(float); yn = new.has_keyhole.to_numpy(int); ln = new.log_h.to_numpy(float)
    allo = np.arange(len(old))
    phys = p11.fit_physics_mean(lo, yo, allo, 0)
    fit = p13.fit_hybrid(xo, lo, yo, allo, allo, phys, "M3", 100.0)
    # score NEW points with OLD-fitted scalers: build a joint array so indices work
    xj = np.vstack([xo, xn]); lj = np.concatenate([lo, ln]); yj = np.concatenate([yo, yn])
    rows += anchoring_rows(fit, xj, lj, yj, allo, np.arange(len(old), len(old) + len(new)), "OLD_to_NEW", "full_OLD")
    # NEW-only: one fit per original partition on its full training pool
    for s in load_splits():
        tr = np.asarray(s["train_indices"], int); te = np.asarray(s["test_indices"], int)
        ph = p11.fit_physics_mean(ln, yn, tr, 0)
        f = p13.fit_hybrid(xn, ln, yn, tr, tr, ph, "M3", 100.0)
        rows += anchoring_rows(f, xn, ln, yn, tr, te, "NEW_only_full_pool", s["split_id"])
    frame = pd.DataFrame(rows)
    frame["row_index_new"] = np.where(frame.scope.eq("OLD_to_NEW"), frame.row_index - len(old), frame.row_index)
    return frame


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    d = discovery_checks()
    d.to_csv(OUT / "new_discovery_certificates.csv", index=False)
    o = old_discovery_reference()
    o.to_csv(OUT / "old_discovery_reference.csv", index=False)
    a = anchoring_checks()
    a.to_csv(OUT / "m3_anchoring_points.csv.gz", index=False)
    rare = a[a.truth.eq(0)]
    summ = {
        "NEW_discovery": {
            "certificate_holds_all": bool(d.certificate_holds.all()),
            "splits_with_guarantee_le_16": int((d.guarantee_budget.fillna(999) <= 16).sum()),
            "median_guarantee_budget": float(d.guarantee_budget.median()),
            "median_rho_star": float(d.rho_star.median()), "median_h16": float(d.h_16.median()),
            "maximin_first_both_mean": float(d.maximin_first_both.mean()),
            "uniform_expected_mean": float(d.uniform_expected_first_both.mean()),
            "adaptive_mean": float(d.adaptive_first_both.mean()),
            "adaptive_bound_mean_when_used": float(d.adaptive_extra_bound.dropna().add(8).mean()) if d.adaptive_extra_bound.notna().any() else None,
            "adaptive_actual_mean_when_used": float(d.loc[d.adaptive_extra_bound.notna(), "adaptive_first_both"].mean()) if d.adaptive_extra_bound.notna().any() else None,
            "fill_distance_loglog_slope_mean": float(d.fill_slope_loglog_b8_64.mean())},
        "OLD_discovery": {
            "median_rho_star": float(o.rho_star.median()), "median_h16": float(o.h_16.median()),
            "splits_with_guarantee_le_16": int((o.guarantee_budget.fillna(999) <= 16).sum()), "n_splits": len(o),
            "maximin_first_both_mean": float(o.maximin_first_both.mean()), "maximin_first_both_max": int(o.maximin_first_both.max()),
            "uniform_expected_mean": float(o.uniform_expected_first_both.mean())},
        "anchoring": {}}
    for scope, g in rare.groupby("scope"):
        summ["anchoring"][scope] = {
            "rare_point_evaluations": len(g), "predicted_rare": int(g.predicted_rare.sum()),
            "certified_unreachable": int(g.certified_unreachable_as_rare.sum()),
            "misses": int((~g.predicted_rare).sum()),
            "misses_certified": int((~g.predicted_rare & g.certified_unreachable_as_rare).sum()),
            "certificate_violations": int((g.predicted_rare & g.certified_unreachable_as_rare).sum()),
            "median_physics_latent": float(g.physics_latent.median()),
            "median_rare_push_bound": float(g.rare_push_bound.median()),
            "median_sigma2": float(g.sigma2.median())}
    (OUT / "summary.json").write_text(json.dumps(summ, indent=2, default=float))
    print(json.dumps(summ, indent=2, default=float))


if __name__ == "__main__":
    main()
