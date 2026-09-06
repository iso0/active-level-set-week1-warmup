"""Prospective acquisition replay on the frozen 100 outer runs (development).

Arms (all start from the same feature-only B16 maximin design as Phase 1.14):
  T_MARGIN : T model, select argmax 1-2|p-0.5| (predictive probability margin)
  T_SUR    : T model, select argmax expected reduction of finite-pool latent-set risk (eq. 8)
  T_TV     : T model, select argmax expected threshold-variance reduction (eq. 9)
Evaluation: T model on its own path (q20/q30/full81), plus M3 evaluated on the T_MARGIN path
(model contrast on an identical path).  Ranking-novelty statistics recorded at every step.
"""
import numpy as np, pandas as pd, time, math, sys, json
from joblib import Parallel, delayed
from scipy.stats import spearmanr
from sklearn.preprocessing import StandardScaler
from core import *
from tmodel import TModel, acq_global_sur_pi, acq_global_sur_p, acq_threshold_variance

HYPER = dict(c=7.0, su=0.2, ls=[1.7, 30.0, 30.0])
ARMS = sys.argv[1].split(",") if len(sys.argv) > 1 else ["T_MARGIN", "T_SUR", "T_TV"]
TAG = sys.argv[2] if len(sys.argv) > 2 else "dev"
LIMIT = int(sys.argv[3]) if len(sys.argv) > 3 else 100

d = Data(); pop = d.population; y = d.labels; lh = d.logh
Zraw = np.c_[np.log(pop.VX), np.log(pop.LS), pop.ST]
band = (lh >= 20.3621) & (lh <= 21.2533)


def frozen_T(l, Z, yy, mu0, c=HYPER["c"], su=HYPER["su"], ls=HYPER["ls"]):
    m = TModel(mu0=mu0, optimize=False); m.dim = 3
    m.theta = np.r_[math.log(c), math.log(su), np.log(ls)]
    m.l, m.Z, m.y = l, Z, yy; m.mean_, m.K = m._build(m.theta, l, Z)
    m.f, m.alpha, m.w, m.sw, m.L, m.lml = m._mode(m.K, m.mean_, yy, return_all=True); m.c = c
    return m


def scores_all(m, cand, ref, Z):
    """All acquisition scores for the candidate set (rows of pool)."""
    idx = np.r_[ref, cand]
    mm, vv, CC = m.latent(lh[idx], Z[idx], return_cov=True)
    nr = len(ref); m_ref, v_ref = mm[:nr], vv[:nr]; m_c, v_c = mm[nr:], vv[nr:]
    C = CC[nr:, :nr]
    p = m.p(lh[cand], Z[cand])
    out = {"margin": 1 - 2 * np.abs(p - .5),
           "sur_pi": acq_global_sur_pi(m_ref, v_ref, m_c, v_c, C),
           "sur_p": acq_global_sur_p(m_ref, v_ref, m_c, v_c, C),
           "tv": acq_threshold_variance(m_c, v_c, C)}
    return out, p


def run(spec):
    tr = np.asarray(spec.train_indices); te = np.asarray(spec.test_indices); fl = d.flags(spec)
    scz = StandardScaler().fit(Zraw[tr]); Z = scz.transform(Zraw)
    init = list(map(int, w85.initial_design(spec, d.population)))
    metrics, steps, paths = [], [], {}
    for arm in ARMS:
        queried = list(init)
        for b in BUDGETS:
            rev = np.asarray(queried); mu0 = lh[rev].mean()
            m = frozen_T(lh[rev], Z[rev], y[rev], mu0)
            pi_te = m.pi(lh[te], Z[te])
            for subset, flag in (("full81", np.ones(len(te), bool)), ("B1_q20", fl["B1_q20"]), ("B1_q30", fl["B1_q30"])):
                metrics.append({"run_id": spec.run_id, "repeat": spec.repeat, "arm": arm, "model": "T", "budget": b, "subset": subset, **metric_values(y[te][flag], pi_te[flag])})
            if b < 80:
                cand = np.setdiff1d(tr, rev)
                sc, p = scores_all(m, cand, tr, Z)
                key = {"T_MARGIN": "margin", "T_SUR": "sur_pi", "T_SURP": "sur_p", "T_TV": "tv"}[arm]
                chosen = argmax_select(cand, sc[key])
                mchosen = margin_select(cand, p)
                rho = spearmanr(sc[key], sc["margin"])[0] if arm != "T_MARGIN" else 1.0
                top5 = set(cand[np.argsort(-sc[key])[:5]]); top5m = set(cand[np.argsort(-sc["margin"])[:5]])
                steps.append({"run_id": spec.run_id, "arm": arm, "budget": b, "chosen": chosen, "margin_choice": mchosen, "same_as_margin": chosen == mchosen,
                              "rho_vs_margin": rho, "top5_overlap": len(top5 & top5m) / 5, "chosen_p": float(p[cand == chosen][0]),
                              "chosen_band": bool(band[chosen]), "chosen_kh": int(y[chosen]), "n_p_uncertain": int(((p > .2) & (p < .8)).sum())})
                queried.append(chosen)
        paths[arm] = queried
        if True:  # M3 evaluated on every arm's path (model held fixed, path varies)
            for b in BUDGETS:
                m3 = M3(d, spec).fit(np.asarray(queried[:b]), b); pr = m3.proba(te)
                for subset, flag in (("full81", np.ones(len(te), bool)), ("B1_q20", fl["B1_q20"]), ("B1_q30", fl["B1_q30"])):
                    metrics.append({"run_id": spec.run_id, "repeat": spec.repeat, "arm": arm, "model": "M3", "budget": b, "subset": subset, **metric_values(y[te][flag], pr[flag])})
    return metrics, steps, {"run_id": spec.run_id, **{a: p for a, p in paths.items()}}


if __name__ == "__main__":
    t0 = time.time()
    out = Parallel(n_jobs=1, verbose=5)(delayed(run)(s) for s in d.specs[:LIMIT])
    pd.DataFrame([r for m, s, p in out for r in m]).to_csv(f"results/acq_{TAG}_metrics.csv.gz", index=False)
    pd.DataFrame([r for m, s, p in out for r in s]).to_csv(f"results/acq_{TAG}_steps.csv.gz", index=False)
    json.dump([p for m, s, p in out], open(f"results/acq_{TAG}_paths.json", "w"))
    print("elapsed", time.time() - t0)
