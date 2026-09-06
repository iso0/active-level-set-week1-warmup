"""Section 4: candidate-level oracle value dataset (development data only).

For states along the committed Phase 1.14 M3-margin paths (P1) at budgets B in {16,24,32,40}
(20 runs: one fold per repeat), for every candidate x in the eligible set (physical band OR
current M3 p in (0.02,0.98)) compute
   V_oracle^m(x) = metric_m(M3 refit on revealed+{x with TRUE label}) - metric_m(current M3)
for m in {q20 acc, q20 BA, q20 KH recall, q30 acc, full acc, full BA}.
Also record ALLOWED pre-query features (inputs, revealed data, revealed-label models, geometry)
and, separately, descriptive TRUE-label fields (used only for composition tables).
"""
import sys, math, json, time, numpy as np, pandas as pd
sys.path.insert(0, "/home/claude/rnd")
from joblib import Parallel, delayed
from scipy.spatial import distance
from scipy.special import ndtr
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from core import *
from tmodel import TModel, acq_threshold_variance
from xsur import acq_xsur_semantics
import acq_replay as AR

d = Data(); pop = d.population; y = d.labels; lh = d.logh; x4 = d.x4
Zraw = np.c_[np.log(pop.VX), np.log(pop.LS), pop.ST]
meta = pd.read_csv("/home/claude/rnd/pop_meta.csv"); cfg = meta.cfg.to_numpy(); part = pop.partition.to_numpy()
per = pd.read_csv("/home/claude/rnd/results/diag_fulltrain_pointwise.csv").set_index("idx"); exc = set(per[per.err >= .5].index)
late = pop.collapsed_physical_sequence.astype(str).str.contains("Conduction -> Keyhole").to_numpy() & y.astype(bool)
transient = (pop.keyhole_persistence_group.astype(str) == "transient Keyhole").to_numpy()
band = (lh >= 20.3621) & (lh <= 21.2533)
paths = pd.read_csv(REPO / "outputs/week9_phase1_14_m3_margin_acquisition/m3_margin_paths.csv.gz")
P1 = {r: g.sort_values("query_order").population_row_index.astype(int).tolist() for r, g in paths[paths.path.eq("P1")].groupby("run_id")}
BUD = (16, 24, 32, 40)


def metrics(prob, te, fl):
    out = {}
    for name, f in (("q20", fl["B1_q20"]), ("q30", fl["B1_q30"]), ("full", np.ones(len(te), bool))):
        m = metric_values(y[te][f], prob[f]); out[f"{name}_acc"] = m["accuracy"]; out[f"{name}_ba"] = m["balanced_accuracy"]; out[f"{name}_khrec"] = m["keyhole_recall"]
    return out


def run(spec):
    tr = np.asarray(spec.train_indices); te = np.asarray(spec.test_indices); fl = d.flags(spec)
    scz = StandardScaler().fit(Zraw[tr]); Z = scz.transform(Zraw); sc4 = StandardScaler().fit(x4[tr]); X4 = sc4.transform(x4)
    path = P1[spec.run_id]; rows = []
    for b in BUD:
        rev = np.asarray(path[:b]); revset = set(rev.tolist())
        m3 = M3(d, spec).fit(rev, b); base = metrics(m3.proba(te), te, fl)
        cand = np.setdiff1d(tr, rev); mc, vc, pc = m3.latent(cand)
        elig = cand[band[cand] | ((pc > 0.02) & (pc < 0.98))]
        # ---- allowed features (revealed data / label-free geometry / revealed-label models)
        physics = m3.fit_.physics; h_lat = physics.latent(lh[cand]); p_h = 1 / (1 + np.exp(-h_lat))
        thr = -physics.model.intercept_[0] / physics.model.coef_[0, 0]; thr_logh = physics.scaler.inverse_transform([[thr]])[0, 0]
        T = AR.frozen_T(lh[rev], Z[rev], y[rev], lh[rev].mean()); idx = np.r_[tr, cand]
        mm, vv, CC = T.latent(lh[idx], Z[idx], return_cov=True); nr = len(tr); Cc = CC[nr:, :nr]
        tv = acq_threshold_variance(mm[nr:], vv[nr:], Cc); xs2, fl2 = acq_xsur_semantics(mm[:nr], vv[:nr], mm[nr:], vv[nr:], Cc, "S2")
        pT = T.p(lh[cand], Z[cand]); tau_m, tau_s = T.tau(Z[cand])
        Dall = distance.cdist(X4[cand], X4[tr]); Drev = distance.cdist(X4[cand], X4[rev]); Dkh = Drev[:, y[rev] == 1]; Dc = Drev[:, y[rev] == 0]
        # standalone ARD-free GPC proxy: logistic on 4-D revealed
        lr4 = LogisticRegression(C=1.0, max_iter=2000).fit(X4[rev], y[rev]); p4 = lr4.predict_proba(X4[cand])[:, 1]
        # local revealed-label stats (k=5 nearest revealed)
        knn = np.argsort(Drev, axis=1)[:, :5]; ylocal = y[rev][knn]; frac_kh_local = ylocal.mean(1)
        ent = -(frac_kh_local * np.log(np.clip(frac_kh_local, 1e-9, 1)) + (1 - frac_kh_local) * np.log(np.clip(1 - frac_kh_local, 1e-9, 1)))
        # physics-order conflict: among revealed neighbours, fraction whose label disagrees with the sign of (logh - thr)
        pred_phys = (lh[cand] > thr_logh).astype(int); conflict = (ylocal != pred_phys[:, None]).mean(1)
        # candidate-influence proxy: sum of M3 kernel covariances (kernel only, label-free) to unrevealed pool
        feats = pd.DataFrame({
            "cand": cand, "logh": lh[cand], "dist_thr_logh": lh[cand] - thr_logh, "abs_dist_thr": np.abs(lh[cand] - thr_logh), "in_band": band[cand].astype(int),
            "logVX": Zraw[cand, 0], "logLS": Zraw[cand, 1], "ST": Zraw[cand, 2], "ST_z": Z[cand, 2],
            "nn_revealed": Drev.min(1), "nn_revealed_kh": Dkh.min(1) if Dkh.shape[1] else np.nan, "nn_revealed_c": Dc.min(1) if Dc.shape[1] else np.nan,
            "pool_density_r05": (Dall < 0.5).sum(1), "revealed_density_r05": (Drev < 0.5).sum(1), "revealed_density_r10": (Drev < 1.0).sum(1),
            "local_frac_kh": frac_kh_local, "local_label_entropy": ent, "local_phys_conflict": conflict,
            "m3_p": pc, "m3_margin": 1 - 2 * np.abs(pc - .5), "m3_latent_m": mc, "m3_latent_v": vc, "m3_pi_margin": 1 - 2 * np.abs(ndtr(mc / np.sqrt(vc)) - .5),
            "h_p": p_h, "m3_minus_h": pc - p_h, "abs_m3_minus_h": np.abs(pc - p_h), "lr4_p": p4, "abs_m3_minus_lr4": np.abs(pc - p4),
            "T_p": pT, "abs_m3_minus_T": np.abs(pc - pT), "T_tau_sd": tau_s, "T_tv": tv, "T_xsur2": xs2, "T_flips2": fl2,
            "cfg_main": (cfg[cand] == "0.0002|0.0014|0.0012|0.0021").astype(int), "partition": part[cand],
            # descriptive true-label fields (NOT allowed as predictors)
            "true_y": y[cand], "is_exception": [int(c in exc) for c in cand], "is_late_kh": late[cand].astype(int), "is_transient_kh": transient[cand].astype(int),
        })
        feats["eligible"] = np.isin(cand, elig).astype(int)
        # ---- oracle values for eligible candidates
        vals = {}
        for c in elig:
            m2 = M3(d, spec).fit(np.r_[rev, c], b + 1); mt = metrics(m2.proba(te), te, fl)
            vals[c] = {f"V_{k}": mt[k] - base[k] for k in base}
        V = pd.DataFrame.from_dict(vals, orient="index"); V.index.name = "cand"; V = V.reset_index()
        out = feats.merge(V, on="cand", how="left"); out["run_id"] = spec.run_id; out["repeat"] = spec.repeat; out["budget"] = b
        for k, v in base.items(): out[f"base_{k}"] = v
        rows.append(out)
    return pd.concat(rows, ignore_index=True)


if __name__ == "__main__":
    specs = [s for s in d.specs if s.fold == ((s.repeat - 1) % 5) + 1]
    t0 = time.time(); out = Parallel(n_jobs=2, verbose=5, backend="multiprocessing")(delayed(run)(s) for s in specs)
    df = pd.concat(out, ignore_index=True); df.to_csv("/home/claude/rnd/followup/results/oracle_values.csv.gz", index=False); print("elapsed", time.time() - t0, df.shape)
