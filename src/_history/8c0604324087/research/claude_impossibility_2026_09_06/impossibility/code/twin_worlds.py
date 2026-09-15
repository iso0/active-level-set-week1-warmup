"""Theorem-level round: empirical twin-world instantiation on the old development data.

Same 80 states as oracle_values.csv.gz (P1 prefixes of the committed M3-margin paths, B in
{16,24,32,40}, 20 runs) and the same eligible candidates. For each eligible candidate x and each
hypothetical label y in {0,1}: exact M3 refit on revealed + {(x,y)}, decisions on the outer test
fold, flip set F_y(x) on the reference set R (Fold-B1-q20 rows; also the full fold), the
correctness signs e_u = +1 (current decision right) / -1 (wrong) of the flipped rows, and the
model's own posterior at those rows before (p_n) and after (p_{n+1}) the refit.
Outputs one row per (state, cand, label) with the flip set encoded as a string.
"""
import sys, time, json, numpy as np, pandas as pd
sys.path.insert(0, "/home/claude/rnd")
from joblib import Parallel, delayed
from core import *

d = Data(); pop = d.population; y = d.labels; lh = d.logh; x4 = d.x4
band = (lh >= 20.3621) & (lh <= 21.2533)
paths = pd.read_csv(REPO / "outputs/week9_phase1_14_m3_margin_acquisition/m3_margin_paths.csv.gz")
P1 = {r: g.sort_values("query_order").population_row_index.astype(int).tolist() for r, g in paths[paths.path.eq("P1")].groupby("run_id")}
BUD = (16, 24, 32, 40)
# candidate restriction (compute budget): all candidates whose counterfactual test value is non-zero under at least one label
# (inventions_features.csv.gz, A_Vtest0/1), plus the margin pick, plus a 10% seeded sample of the remaining zero-valued candidates
INV = pd.read_csv("/home/claude/rnd/followup/results/inventions_features.csv.gz")
NZ = {(r.run_id, int(r.budget), int(r.cand)) for r in INV.itertuples() if r.A_Vtest0 != 0 or r.A_Vtest1 != 0}


def run(spec):
    tr = np.asarray(spec.train_indices); te = np.asarray(spec.test_indices); fl = d.flags(spec)
    R = np.where(fl["B1_q20"])[0]            # positions within te
    path = P1[spec.run_id]; rows = []
    for b in BUD:
        rev = np.asarray(path[:b]); m3 = M3(d, spec).fit(rev, b)
        cand = np.setdiff1d(tr, rev); pc = m3.proba(cand); elig = cand[band[cand] | ((pc > 0.02) & (pc < 0.98))]
        p0 = m3.proba(te); dec0 = (p0 >= .5).astype(int); e = np.where(dec0 == y[te], 1, -1)   # correctness sign of current decisions
        acc0 = float((dec0[R] == y[te][R]).mean()); accF0 = float((dec0 == y[te]).mean())
        xm = margin_select(elig, m3.proba(elig)); rng = np.random.default_rng(seed_u32("twin", spec.run_id, b))
        keep = [int(c) for c in elig if (spec.run_id, b, int(c)) in NZ or int(c) == xm or rng.random() < 0.10]
        for c in keep:
            i = int(np.where(cand == c)[0][0])
            for lab in (0, 1):
                ylab = y.copy(); ylab[c] = lab
                physics = p11.fit_physics_mean(lh, ylab, np.r_[rev, c], p13.seed_u32("shared_physics", spec.run_id, b + 1))
                fit = p13.fit_hybrid(x4, lh, ylab, np.r_[rev, c], spec.train_indices, physics, "M3", 100.0)
                p1 = p13.components(fit, x4[te], lh[te])["probability"]; dec1 = (p1 >= .5).astype(int)
                flip = np.where(dec1 != dec0)[0]; fR = [int(u) for u in flip if u in set(R.tolist())]
                rows.append({"run_id": spec.run_id, "repeat": spec.repeat, "budget": b, "cand": int(c), "lab": lab, "true_y": int(y[c]), "m3_p": float(pc[i]),
                             "nR": len(R), "nF": len(te), "is_margin_pick": int(int(c) == xm), "in_nz": int((spec.run_id, b, int(c)) in NZ), "acc0_R": acc0, "acc0_full": accF0,
                             "FR": ";".join(map(str, fR)), "eR": ";".join(str(int(e[u])) for u in fR),
                             "p0R": ";".join(f"{p0[u]:.4f}" for u in fR), "p1R": ";".join(f"{p1[u]:.4f}" for u in fR),
                             "FF": ";".join(map(str, flip.tolist())), "eF": ";".join(str(int(e[u])) for u in flip),
                             "p0F": ";".join(f"{p0[u]:.4f}" for u in flip), "p1F": ";".join(f"{p1[u]:.4f}" for u in flip),
                             "V_R": -sum(int(e[u]) for u in fR) / len(R), "V_full": -sum(int(e[u]) for u in flip) / len(te),
                             "V_R_direct": float((dec1[R] == y[te][R]).mean()) - acc0})
    return rows


if __name__ == "__main__":
    specs = [s for s in d.specs if s.fold == ((s.repeat - 1) % 5) + 1]
    t0 = time.time(); out = Parallel(n_jobs=2, verbose=5, backend="multiprocessing")(delayed(run)(s) for s in specs)
    df = pd.DataFrame([r for rows in out for r in rows]); df.to_csv("/home/claude/rnd/followup/results/twin_worlds_flips.csv.gz", index=False); print("elapsed", time.time() - t0, df.shape)
