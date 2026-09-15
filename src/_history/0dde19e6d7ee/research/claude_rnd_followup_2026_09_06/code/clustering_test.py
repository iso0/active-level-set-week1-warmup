"""Section 6: are persistent exception rows spatially clustered beyond what campaign/class
composition implies?  Permutation tests with matched controls.

Exception set E: rows misclassified by full-label M3 in >= 50% of folds (13 rows).
Statistics (in standardised (log P, log VX, log LS, ST) distance, in (log h, tangent) coordinates,
and in log h alone):
  T1 = mean over e in E of the distance to the nearest OTHER exception
  T2 = mean over e in E of the number of exceptions among its 10 nearest neighbours (excluding itself)
  T3 = local odds ratio: P(neighbour is exception | row is exception) / base rate
Null: E* drawn uniformly among rows with the same (campaign partition, class) composition as E
(stratified permutation), 20,000 draws.  Also within-class-only and unconditioned nulls, and
subgroup tests (late-onset KH, transient KH, alt-configuration KH, depth-marginal C)."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, "/home/claude/rnd")
from scipy.spatial import distance
from sklearn.preprocessing import StandardScaler
from core import *

d = Data(); pop = d.population; y = d.labels; lh = d.logh
meta = pd.read_csv("/home/claude/rnd/pop_meta.csv"); cfg = meta.cfg.to_numpy(); part = pop.partition.to_numpy()
per = pd.read_csv("/home/claude/rnd/results/diag_fulltrain_pointwise.csv").set_index("idx")
E = np.array(sorted(per[per.err >= .5].index)); N = len(pop)
late = pop.collapsed_physical_sequence.astype(str).str.contains("Conduction -> Keyhole").to_numpy() & y.astype(bool)
transient = (pop.keyhole_persistence_group.astype(str) == "transient Keyhole").to_numpy()
altcfg = cfg != "0.0002|0.0014|0.0012|0.0021"
D = pop.value__max_depth.to_numpy(float)
groups = {"all_exceptions": E, "late_onset_KH": np.array([e for e in E if late[e]]), "transient_KH": np.array([e for e in E if transient[e]]),
          "altcfg_KH": np.array([e for e in E if altcfg[e] and y[e] == 1]), "depth_marginal_C": np.array([e for e in E if y[e] == 0 and abs(D[e] - 112) < 15]), "other": np.array([e for e in E if not (late[e] or transient[e] or (altcfg[e] and y[e] == 1) or (y[e] == 0 and abs(D[e] - 112) < 15))])}
U4 = StandardScaler().fit_transform(np.c_[np.log(pop.P), np.log(pop.VX), np.log(pop.LS), pop.ST])
tang = StandardScaler().fit_transform(np.c_[lh, np.log(pop.VX), np.log(pop.LS), pop.ST])
spaces = {"std4_loginputs": distance.cdist(U4, U4), "logh_tangent": distance.cdist(tang, tang), "logh_only": np.abs(lh[:, None] - lh[None, :])}
for k in spaces: np.fill_diagonal(spaces[k], np.inf)
rng = np.random.default_rng(2026); NDRAW = 3000


def stats(S, Dm):
    if len(S) < 2: return np.nan, np.nan
    sub = Dm[np.ix_(S, S)]; t1 = sub.min(1).mean()
    nn10 = np.argsort(Dm[S], axis=1)[:, :10]; t2 = np.isin(nn10, S).sum(1).mean()
    return t1, t2


def sample_null(S, mode):
    """Draw |S| rows matched on strata."""
    if mode == "unconditioned": return rng.choice(N, len(S), replace=False)
    if mode == "class": strata = y
    elif mode == "class_partition": strata = np.array([f"{a}|{b}" for a, b in zip(y, part)])
    elif mode == "class_partition_cfg": strata = np.array([f"{a}|{b}|{c}" for a, b, c in zip(y, part, cfg)])
    out = []
    for s in np.unique(strata[S]):
        k = (strata[S] == s).sum(); pool = np.flatnonzero(strata == s); out.extend(rng.choice(pool, k, replace=False))
    return np.array(out)


rows = []
for gname, S in groups.items():
    if len(S) < 2: continue
    for sname, Dm in spaces.items():
        t1, t2 = stats(S, Dm)
        for mode in ("unconditioned", "class", "class_partition", "class_partition_cfg"):
            null1 = []; null2 = []
            for _ in range(NDRAW):
                Sn = sample_null(S, mode); a, b = stats(Sn, Dm); null1.append(a); null2.append(b)
            null1 = np.array(null1); null2 = np.array(null2)
            rows.append({"group": gname, "n": len(S), "space": sname, "null": mode, "T1_nn_exception_dist": t1, "T1_null_mean": null1.mean(), "T1_p_smaller": (null1 <= t1).mean(),
                         "T2_exceptions_in_10nn": t2, "T2_null_mean": null2.mean(), "T2_p_larger": (null2 >= t2).mean(), "T2_enrichment": t2 / max(null2.mean(), 1e-9)})
        print(gname, sname, "done")
res = pd.DataFrame(rows); res.to_csv("/home/claude/rnd/followup/results/exception_clustering_tests.csv", index=False)
pd.set_option("display.width", 250); print(res.round(3).to_string())
