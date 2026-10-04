"""Week 15 development benchmark on the Week 13 generator (designated DEVELOPMENT family)."""
import argparse, json
from pathlib import Path
import numpy as np, pandas as pd
from joblib import Parallel, delayed
from src.week13_synthetic import latent, physics_score
from src.week13_synthetic_al import calibrated, noisy_labels, to_box
from src.week15_al import POLICIES, DenseEval, knn_graph, run_path, start_design, N_REF, K_REF

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/week15_boundary_acquisition/development"
HYP = json.loads((ROOT / "outputs/week14_research_program/synthetic/noise_acquisition/hyperparameters.json").read_text())


def job(scn, sigma, rep, policy, n_pool=108):
    sc = calibrated(scn); hyp = HYP[f"{scn}_s{sigma}"]
    rng = np.random.default_rng([15, int(sigma * 10), n_pool, rep, ("BAL", "OLD", "NEW").index(scn)])
    u_pool, u_eval = sc.sample(n_pool, rng), sc.sample(int(round(n_pool / .8)), rng)
    y_pool, y_eval = noisy_labels(u_pool, sc, sigma, rng), noisy_labels(u_eval, sc, sigma, rng)
    z_pool, z_eval = to_box(u_pool, sc), to_box(u_eval, sc)
    ud = sc.sample(8000, np.random.default_rng(5)); dense = DenseEval(to_box(ud, sc), (latent(ud, sc) > 0).astype(int))
    Zref = np.random.default_rng([15, 99]).random((N_REF, 4)); Eref = knn_graph(Zref, K_REF)
    start = start_design(z_pool, y_pool, [15, rep, 2])
    gen = {"family": "dev_week13", "scenario": scn, "sigma": sigma, "n_pool": n_pool, "rep": rep, "startup": len(start)}
    return run_path(gen, policy, z_pool, u_pool, y_pool, latent(u_pool, sc), physics_score(u_pool), z_eval, y_eval,
                    dense, Zref, Eref, hyp, start, [15, rep, POLICIES.index(policy)])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--reps", type=int, default=8); ap.add_argument("--tag", default="dev")
    ap.add_argument("--policies", default=",".join(POLICIES)); a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = [(s, g, r, p) for p in a.policies.split(",") for s in ("BAL", "OLD", "NEW") for g in (0.0, 0.5, 1.0) for r in range(a.reps)]
    res = Parallel(n_jobs=7, verbose=2)(delayed(job)(*j) for j in jobs)
    df = pd.DataFrame([x for rows in res for x in rows]); df.to_csv(OUT / f"al_{a.tag}.csv", index=False)
    au = df.groupby(["scenario", "sigma", "rep", "policy"]).apply(lambda g: pd.Series({c: np.trapezoid(g.sort_values("budget")[c], g.sort_values("budget").budget) / 64
                                                                                    for c in ("NSD_0.1", "ASSD", "q20_accuracy", "BA")}), include_groups=False).reset_index()
    au.to_csv(OUT / f"aulc_{a.tag}.csv", index=False)
    print(au.groupby(["scenario", "sigma", "policy"])[["NSD_0.1", "ASSD", "q20_accuracy"]].mean().unstack("policy").round(3).to_string())
    print(df[df.budget == 80].groupby(["scenario", "sigma", "policy"])[["flipped_acquired", "median_abs_latent_acquired"]].mean().unstack("policy").round(3).to_string())


if __name__ == "__main__":
    main()
