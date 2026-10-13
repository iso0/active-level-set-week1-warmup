"""Stage M mechanism diagnostics (pre-declared list in STUDY_MANIFEST.json).  Reads the Stage M cache; the only new
computations are the pre-declared Laplace-error check (elliptical slice sampling for J at NEW repeat 1, folds 1-5,
B40, which refits the deterministic J model to recover its prior matrices) and descriptive tables.  Evaluation-only
strata (negatives, fast scans, short-K, incomplete support) never feed back into any model.

Step: python -m src.jdl_mechanism
"""
from __future__ import annotations

import json
from dataclasses import replace

import numpy as np
import pandas as pd
from scipy.special import log_ndtr, ndtr

import src.jdl_model as JM
from src.jdl_evaluate import population_frame
from src.jdl_stage_m import (ARMS, BUDGETS, FAST_VX, OUT, POPS, REPEATS, SM, Oracle, build_tasks, load_cache, standardizer)

MECH = OUT / "mechanism"


def _w(df, name):
    MECH.mkdir(parents=True, exist_ok=True)
    df.to_csv(MECH / name, index=False, lineterminator="\n")


def strata(F):
    return {"negative": F["y"] == 0, "positive": F["y"] == 1, "fast_scan_VX_gt_0.85": F["VX"] > FAST_VX, "short_K": F["shortk"],
            "A_missing": ~np.isfinite(F["A"]), "early_end_record": F["early_end"]}


def errors_by_id(preds, tasks):
    rows = []
    for pop in POPS:
        F = population_frame(pop, tasks); S = strata(F)
        pos = {s: i for i, s in enumerate(F["ids"])}
        g = preds[preds.population == pop]
        for r in g.itertuples():
            i = pos[r.sim_id]
            if not np.isfinite(r.p):
                continue
            yhat = int(r.p >= 0.5)
            if yhat != F["y"][i]:
                rows.append({"population": pop, "arm": r.arm, "repeat": r.repeat, "budget": r.budget, "sim_id": r.sim_id, "label": int(F["y"][i]),
                             "error": "false_positive" if F["y"][i] == 0 else "false_negative", "p": r.p, "A_um": F["A"][i], "VX_m_s": F["VX"][i],
                             **{k: bool(v[i]) for k, v in S.items() if k not in ("negative", "positive")}})
    return pd.DataFrame(rows)


def stratum_rates(preds, tasks):
    rows = []
    for pop in POPS:
        F = population_frame(pop, tasks); S = strata(F)
        pos = {s: i for i, s in enumerate(F["ids"])}
        for (arm, rep, b), g in preds[preds.population == pop].groupby(["arm", "repeat", "budget"]):
            idx = g.sim_id.map(pos).to_numpy(int); p = g.p.to_numpy(float); y = F["y"][idx]
            for name, m in S.items():
                mm = m[idx] & np.isfinite(p)
                if mm.sum() == 0:
                    continue
                rows.append({"population": pop, "arm": arm, "repeat": rep, "budget": b, "stratum": name, "n": int(mm.sum()),
                             "n_negative": int((y[mm] == 0).sum()), "error_rate": float(np.mean((p[mm] >= 0.5) != (y[mm] == 1))),
                             "mean_p": float(np.mean(p[mm]))})
    return pd.DataFrame(rows)


def new_negatives_table(preds, tasks):
    F = population_frame("NEW", tasks)
    neg = F["ids"][F["y"] == 0]
    g = preds[(preds.population == "NEW") & preds.sim_id.isin(neg)]
    keep = ["arm", "repeat", "budget", "sim_id", "p", "h_mean", "f_mean", "theta_mean", "delta_mean", "margin", "p_theta_conditioned", "p_oracle_response_NOT_DEPLOYABLE"]
    t = g[[c for c in keep if c in g.columns]].copy()
    inp = dict(zip(F["ids"], zip(F["A"], F["VX"])))
    t["A_um"] = t.sim_id.map(lambda s: inp[s][0]); t["VX_m_s"] = t.sim_id.map(lambda s: inp[s][1])
    t["z_observed"] = np.log(t.A_um / 111.0)
    return t.sort_values(["sim_id", "arm", "budget", "repeat"])


def decomposition_summary(preds, tasks):
    """Latent decomposition h = f - theta + delta for J-family arms by population, budget and class."""
    rows = []
    for pop in POPS:
        F = population_frame(pop, tasks); yv = dict(zip(F["ids"], F["y"]))
        g = preds[(preds.population == pop) & preds.arm.isin(["J", "J_fixed_theta", "J_no_delta", "Binary_matched"])].copy()
        g["label"] = g.sim_id.map(yv)
        for (arm, b, lab), h in g.groupby(["arm", "budget", "label"]):
            rows.append({"population": pop, "arm": arm, "budget": b, "label": int(lab), "n": len(h), "f_mean": h.f_mean.mean(), "theta_mean": h.theta_mean.mean(),
                         "delta_mean": h.delta_mean.mean(), "abs_delta_mean": h.delta_mean.abs().mean(), "delta_sd_mean": np.sqrt(h.delta_var).mean(),
                         "h_mean": h.h_mean.mean(), "share_p_ge_0.5": float((h.p >= 0.5).mean()), "theta_sd_mean": np.sqrt(h.theta_var).mean()})
    return pd.DataFrame(rows)


def theta_conditioning(preds, tasks):
    """Astra's diagnostic (condition the fitted joint on theta = its posterior mean) vs the J_fixed_theta refit."""
    rows = []
    for pop in POPS:
        F = population_frame(pop, tasks); yv = dict(zip(F["ids"], F["y"]))
        j = preds[(preds.population == pop) & (preds.arm == "J")].set_index(["repeat", "budget", "sim_id"])
        ft = preds[(preds.population == pop) & (preds.arm == "J_fixed_theta")].set_index(["repeat", "budget", "sim_id"])
        for b in BUDGETS:
            jj = j.xs(b, level="budget"); ff = ft.xs(b, level="budget").reindex(jj.index)
            y = np.array([yv[s] for s in jj.index.get_level_values("sim_id")])
            p, pc, pf = jj.p.to_numpy(), jj.p_theta_conditioned.to_numpy(), ff.p.to_numpy()
            for name, q in (("theta_conditioned_diagnostic", pc), ("J_fixed_theta_refit", pf)):
                rows.append({"population": pop, "budget": b, "comparison": f"{name} vs J", "max_abs_dp": float(np.max(np.abs(q - p))), "mean_abs_dp": float(np.mean(np.abs(q - p))),
                             "classification_changes": int(((q >= 0.5) != (p >= 0.5)).sum()), "changes_on_negatives": int((((q >= 0.5) != (p >= 0.5)) & (y == 0)).sum()),
                             "false_positives_J": int(((p >= 0.5) & (y == 0)).sum()), "false_positives_other": int(((q >= 0.5) & (y == 0)).sum()),
                             "false_negatives_J": int(((p < 0.5) & (y == 1)).sum()), "false_negatives_other": int(((q < 0.5) & (y == 1)).sum()),
                             "n_predictions": len(p)})
    return pd.DataFrame(rows)


def oracle_comparison(preds, orc, tasks):
    """Same simulations: GP decision (p >= 0.5) vs response-oracle decision (held-out A; NOT deployable) for J and ACTIVE_E1."""
    rows = []
    for pop in POPS:
        F = population_frame(pop, tasks); yv = dict(zip(F["ids"], F["y"]))
        j = preds[(preds.population == pop) & (preds.arm == "J")]
        e = orc[(orc.population == pop) & (orc.arm == "ACTIVE_E1") & (orc.status == "ok")]
        ep = preds[(preds.population == pop) & (preds.arm == "ACTIVE_E1")]
        for b in BUDGETS:
            for rep in REPEATS:
                jj = j[(j.budget == b) & (j.repeat == rep)].set_index("sim_id"); ee = e[(e.budget == b) & (e.repeat == rep)].set_index("sim_id")
                epp = ep[(ep.budget == b) & (ep.repeat == rep)].set_index("sim_id")
                common = jj.index.intersection(ee.index).intersection(epp.index)
                common = [s for s in common if np.isfinite(jj.loc[s, "p_oracle_response_NOT_DEPLOYABLE"])]
                y = np.array([yv[s] for s in common])

                def ba(dec):
                    return 0.5 * (np.mean(dec[y == 1]) + np.mean(~dec[y == 0]))
                rows.append({"population": pop, "budget": b, "repeat": rep, "n_common": len(common), "n_negative": int((y == 0).sum()),
                             "BA_J_gp": ba(jj.loc[common, "p"].to_numpy() >= 0.5), "BA_J_oracle_response": ba(jj.loc[common, "p_oracle_response_NOT_DEPLOYABLE"].to_numpy() >= 0.5),
                             "BA_E1_gp": ba(epp.loc[common, "p"].to_numpy() >= 0.5), "BA_E1_oracle_response": ba(ee.loc[common, "predicted_label"].to_numpy() >= 0.5)})
    return pd.DataFrame(rows)


def threshold_alignment(preds, tasks):
    """POST-HOC (added after the Stage M result was seen): decisions at p >= 0.5 vs at the paid-prevalence threshold
    (train-only: the share of positives among the paid labels of that checkpoint) vs the held-out-optimal threshold
    (NOT deployable; an upper reference).  Separates ranking quality from the decision rule."""
    paths = pd.read_csv(SM / "paths.csv")
    rows = []
    for pop in POPS:
        F = population_frame(pop, tasks); yv = dict(zip(F["ids"], F["y"]))
        for (arm, rep, b), g in preds[preds.population == pop].groupby(["arm", "repeat", "budget"]):
            g = g[np.isfinite(g.p)]
            y = g.sim_id.map(yv).to_numpy(); p = g.p.to_numpy()
            thr = {}
            for f, gf in g.groupby("fold"):
                paid = paths[(paths.population == pop) & (paths.repeat == rep) & (paths.fold == f)].sort_values("query_index").sim_id.iloc[:b]
                thr[f] = float(np.mean([yv[s] for s in paid]))
            tp = g.fold.map(thr).to_numpy()

            def ba(dec):
                return 0.5 * (np.mean(dec[y == 1]) + np.mean(~dec[y == 0]))
            cands = np.unique(np.r_[p, 0.0, 1.0])
            best = max(ba(p >= c) for c in cands)
            rows.append({"population": pop, "arm": arm, "repeat": rep, "budget": b, "BA_at_0.5": ba(p >= 0.5), "BA_at_paid_prevalence": ba(p >= tp),
                         "BA_heldout_optimal_NOT_DEPLOYABLE": best, "mean_paid_prevalence": float(np.mean(list(thr.values()))),
                         "specificity_at_0.5": float(np.mean(p[y == 0] < 0.5)), "specificity_at_paid_prevalence": float(np.mean(p[y == 0] < tp[y == 0])),
                         "sensitivity_at_0.5": float(np.mean(p[y == 1] >= 0.5)), "sensitivity_at_paid_prevalence": float(np.mean(p[y == 1] >= tp[y == 1]))})
    return pd.DataFrame(rows)


def reliability(preds, tasks, bins=10):
    rows = []
    edges = np.linspace(0, 1, bins + 1)
    for pop in POPS:
        F = population_frame(pop, tasks); yv = dict(zip(F["ids"], F["y"]))
        for (arm, b), g in preds[(preds.population == pop)].groupby(["arm", "budget"]):
            g = g[np.isfinite(g.p)]
            y = g.sim_id.map(yv).to_numpy(); p = g.p.to_numpy()
            k = np.clip(np.digitize(p, edges) - 1, 0, bins - 1)
            for i in range(bins):
                m = k == i
                rows.append({"population": pop, "arm": arm, "budget": b, "bin": f"[{edges[i]:.1f},{edges[i+1]:.1f})", "n": int(m.sum()), "n_negative": int((y[m] == 0).sum()),
                             "mean_p": float(p[m].mean()) if m.any() else np.nan, "observed_positive_rate": float(y[m].mean()) if m.any() else np.nan})
    return pd.DataFrame(rows)


def laplace_error(tasks, n_iter=120000, burn=20000, thin=10, seed=20261013):
    """Pre-declared: elliptical slice sampling of the J posterior (NEW, repeat 1, folds 1-5, B40) vs the Laplace predictions."""
    rows = []
    cfg = JM.STAGE_M_CONFIG
    for t in [t for t in tasks if t["population"] == "NEW" and t["repeat"] == 1]:
        paths = pd.read_csv(SM / "paths.csv")
        g = paths[(paths.population == "NEW") & (paths.repeat == 1) & (paths.fold == t["fold"])].sort_values("query_index")
        pos = {s: i for i, s in enumerate(t["ids"])}
        L = g.sim_id.map(pos).to_numpy(int)[:40]
        std, _ = standardizer(t)
        paid = Oracle(t).reveal(L)
        m = JM.JointDepthLabelGP(std(t["X"][t["pool"]]), cfg).fit(std(paid.X), paid.y, paid.z)
        Xt = std(t["X"][t["test"]])
        lap = m.marginals(Xt)
        # prior after z over (h_P, h_test): use the label-free posterior (labels off) at the paid + test points
        prior = JM.JointDepthLabelGP(std(t["X"][t["pool"]]), cfg).fit(std(paid.X), paid.y, paid.z, use_labels=False)
        pts = np.vstack([std(paid.X), Xt])
        q = prior.posterior(pts)
        mu, C = q["h_mean"], q["h_cov"]
        nP = len(L)
        KPP = C[:nP, :nP] + 1e-10 * np.eye(nP); LP = np.linalg.cholesky(KPP)
        KtP = C[nP:, :nP]; A = np.linalg.solve(KPP, KtP.T).T
        vt = np.maximum(np.diag(C[nP:, nP:]) - np.einsum("ij,ij->i", A, KtP), 0.0)
        s = 2 * paid.y - 1
        rng = np.random.default_rng(seed + t["fold"])
        cur = mu[:nP].copy(); ll = float(log_ndtr(s * cur / cfg.probit_scale).sum()); acc = []
        for it in range(n_iter):
            nu = LP @ rng.standard_normal(nP)
            logy = ll + np.log(rng.uniform()); ang = rng.uniform(0, 2 * np.pi); lo, hi = ang - 2 * np.pi, ang
            while True:
                prop = mu[:nP] + (cur - mu[:nP]) * np.cos(ang) + nu * np.sin(ang)
                lp = float(log_ndtr(s * prop / cfg.probit_scale).sum())
                if lp > logy:
                    cur, ll = prop, lp; break
                lo, hi = (ang, hi) if ang < 0 else (lo, ang)
                ang = rng.uniform(lo, hi)
            if it >= burn and it % thin == 0:
                mt = mu[nP:] + A @ (cur - mu[:nP])
                acc.append(ndtr(mt / np.sqrt(cfg.probit_scale ** 2 + vt)))
        acc = np.array(acc); pe = acc.mean(0)
        nb = 20; bl = len(acc) // nb; se = acc[:nb * bl].reshape(nb, bl, -1).mean(1).std(0, ddof=1) / np.sqrt(nb)
        y = t["y"][t["test"]]
        rows.append({"fold": t["fold"], "n_test": len(y), "max_abs_dp_laplace_vs_ess": float(np.max(np.abs(lap["p"] - pe))), "mean_abs_dp": float(np.mean(np.abs(lap["p"] - pe))),
                     "max_ess_mc_se": float(np.max(se)), "classification_changes": int(((lap["p"] >= 0.5) != (pe >= 0.5)).sum()),
                     "changes_on_negatives": int((((lap["p"] >= 0.5) != (pe >= 0.5)) & (y == 0)).sum()), "ess_samples": len(acc),
                     "laplace_false_positives": int(((lap["p"] >= 0.5) & (y == 0)).sum()), "ess_false_positives": int(((pe >= 0.5) & (y == 0)).sum())})
        print("laplace error fold", t["fold"], rows[-1], flush=True)
    return pd.DataFrame(rows)


def conditioning(fits):
    j = fits[fits.arm.isin(["J", "J_fixed_theta", "J_no_delta", "Binary_matched"])]
    return j.groupby(["population", "budget", "arm"]).agg(fits=("status", "size"), max_gradient=("gradient_inf", "max"), max_newton_iterations=("newton_iterations", "max"),
                                                          min_hessian_eig=("min_whitened_hessian_eigenvalue", "min"), max_condition_number_K=("condition_number_K", "max"),
                                                          solver_statuses=("solver_status", lambda s: json.dumps(s.value_counts().to_dict()))).reset_index()


def main():
    fits, preds, orc = load_cache()
    tasks = build_tasks()
    out = {"errors_by_full_id.csv": errors_by_id(preds, tasks), "stratum_error_rates.csv": stratum_rates(preds, tasks),
           "NEW_negatives_by_arm.csv": new_negatives_table(preds, tasks), "latent_decomposition_by_class.csv": decomposition_summary(preds, tasks),
           "theta_conditioning_vs_fixed_theta_refit.csv": theta_conditioning(preds, tasks), "oracle_response_vs_gp_same_simulations.csv": oracle_comparison(preds, orc, tasks),
           "POSTHOC_threshold_alignment.csv": threshold_alignment(preds, tasks), "reliability_bins.csv": reliability(preds, tasks),
           "conditioning_and_convergence.csv": conditioning(fits)}
    for k, v in out.items():
        _w(v, k)
    le = laplace_error(tasks); _w(le, "laplace_error_NEW_r1_B40_ess.csv")
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    for k in ("latent_decomposition_by_class.csv", "theta_conditioning_vs_fixed_theta_refit.csv", "oracle_response_vs_gp_same_simulations.csv"):
        print(k); print(out[k].round(3).to_string())
    ta = out["POSTHOC_threshold_alignment.csv"]
    print(ta.groupby(["population", "budget", "arm"])[["BA_at_0.5", "BA_at_paid_prevalence", "BA_heldout_optimal_NOT_DEPLOYABLE", "specificity_at_0.5", "specificity_at_paid_prevalence"]].mean().round(3).to_string())
    print(le.round(4).to_string())


if __name__ == "__main__":
    main()
