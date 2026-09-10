"""Hostile-review round: (1) independent re-check of the twin-world numbers from the raw refit file,
(2) physical-compatibility audit of the local twins under progressively stronger structural constraints,
(3) exact-marginal (k=1) plausibility numbers and identification of independence approximations.
Reads only development data and the existing results; no new refits."""
import sys, json, itertools, numpy as np, pandas as pd
sys.path.insert(0, "/home/claude/rnd")
from core import *
OUT = "/home/claude/rnd/followup/results/"
d = Data(); pop = d.population; y = d.labels; lh = d.logh
meta = pd.read_csv("/home/claude/rnd/pop_meta.csv"); cfg = meta.cfg.to_numpy(); MAIN = "0.0002|0.0014|0.0012|0.0021"
X = pop[["P", "VX", "LS"]].to_numpy(float)
# dominance: j more keyhole-favouring than i  iff P_j>=P_i, VX_j<=VX_i, LS_j<=LS_i, at least one strict (Phase 1.19A definition)
more = (X[None, :, 0] >= X[:, None, 0]) & (X[None, :, 1] <= X[:, None, 1]) & (X[None, :, 2] <= X[:, None, 2]); strict = np.any(X[None, :, :] != X[:, None, :], axis=2)
DOM = more & strict   # DOM[i, j] = j dominates i (j more KH-favouring)
def violations(lab, mask=None):
    """directed violation pairs (i KH, j C, j dominates i); restrict both ends to mask if given"""
    m = np.ones(len(lab), bool) if mask is None else mask
    return int((DOM & (lab[:, None] == 1) & (lab[None, :] == 0) & m[:, None] & m[None, :]).sum())
V0 = violations(y); print("truth violations (full 405):", V0)
BAND = (lh >= 20.3621) & (lh <= 21.2533)
paths = pd.read_csv(REPO / "outputs/week9_phase1_14_m3_margin_acquisition/m3_margin_paths.csv.gz")
P1 = {r: g.sort_values("query_order").population_row_index.astype(int).tolist() for r, g in paths[paths.path.eq("P1")].groupby("run_id")}

df = pd.read_csv(OUT + "twin_worlds_flips.csv.gz", keep_default_na=False); df["state"] = df.run_id + "|" + df.budget.astype(str)
L = lambda s, f=int: [f(t) for t in s.split(";")] if s else []
for c, src, f in (("F", "FR", int), ("e", "eR", int), ("p0", "p0R", float), ("p1", "p1R", float)): df[c] = df[src].map(lambda s, f=f: L(s, f))
rep = {}
# ---------- (1) independent re-check
rep["identity_max_dev"] = float((df.V_R + df.FR.map(lambda s: 0) - df.V_R_direct).abs().max())
tv = df[df.lab == df.true_y].copy(); tv["V"] = tv.V_R
# e-frequency at the most uncertain flip rows (true label)
E = np.concatenate(tv.e.values); P0 = np.concatenate(tv.p0.values); c0 = np.abs(2 * P0 - 1)
rep["P(e=-1 | flip row)"] = float((E == -1).mean()); rep["P(e=-1 | flip row, |2p-1|<=0.1)"] = float((E[c0 <= .1] == -1).mean()); rep["n_flip_rows"] = int(len(E)); rep["n_flip_rows_conf<=0.1"] = int((c0 <= .1).sum())
# binomial CI for the 0.504
from scipy.stats import binomtest
bt = binomtest(int((E[c0 <= .1] == -1).sum()), int((c0 <= .1).sum())); rep["CI95_P(e=-1|conf<=0.1)"] = [bt.proportion_ci().low, bt.proportion_ci().high]
# But flip rows repeat across candidates within a state (same reference row flipped by many candidates): count UNIQUE (state,row) pairs
uq = {}
for r in tv.itertuples():
    for u, e, p in zip(r.F, r.e, r.p0): uq[(r.state, u)] = (e, p)
ue = np.array([v[0] for v in uq.values()]); up = np.array([abs(2 * v[1] - 1) for v in uq.values()])
rep["unique_(state,row)_flip_rows"] = int(len(ue)); rep["distinct_population_rows_flipped"] = int(len(set(int(d.spec_by_id[st.split("|")[0]].test_indices[u]) for (st, u) in uq))); rep["P(e=-1 | unique flip row)"] = float((ue == -1).mean()); rep["P(e=-1 | unique flip row, conf<=0.1)"] = float((ue[up <= .1] == -1).mean()); rep["n_unique_conf<=0.1"] = int((up <= .1).sum())
bt2 = binomtest(int((ue[up <= .1] == -1).sum()), int((up <= .1).sum())); rep["CI95_unique_conf<=0.1"] = [bt2.proportion_ci().low, bt2.proportion_ci().high]
# distinct reference rows overall (17 per fold, 5 folds): how many distinct population rows carry the flips?
# per-state rules (independent implementation)
o = pd.read_csv(OUT + "oracle_values.csv.gz"); o = o[o.eligible == 1].copy(); o["state"] = o.run_id + "|" + o.budget.astype(str)
S = []
for st, g in tv.groupby("state"):
    og = o[o.state == st]; V = g.V.values; cands = g.cand.values
    xm = int(og.cand.values[np.lexsort((og.cand.values, -og.m3_margin.values))[0]])   # margin pick over ALL eligible
    Vm = float(g[g.cand == xm].V.iloc[0]) if xm in set(cands) else 0.0
    # model-Bayes: p_n(x) * sum|2p1-1| over F_1 + (1-p) * ... using both-label rows
    gb = df[df.state == st]; eq = {}
    for c, gc in gb.groupby("cand"):
        r0 = gc[gc.lab == 0].iloc[0]; r1 = gc[gc.lab == 1].iloc[0]; p = r0.m3_p
        eq[c] = (p * sum(abs(2 * q - 1) for q in r1.p1) + (1 - p) * sum(abs(2 * q - 1) for q in r0.p1)) / r0.nR
    cq = sorted(eq, key=lambda c: (-eq[c], c))[0]; Vq = float(g[g.cand == cq].V.iloc[0])
    S.append({"state": st, "Vmax": V.max(), "Vmin": V.min(), "V_margin": Vm, "V_EQ": Vq, "V_random": float(og.V_q20_acc.mean()), "best_beats_margin": int(V.max() > Vm), "Vmax_pos": int(V.max() > 0)})
S = pd.DataFrame(S); rep["states"] = int(len(S)); rep["states_best_beats_margin"] = int(S.best_beats_margin.sum()); rep["states_Vmax_pos"] = int(S.Vmax_pos.sum())
rep["means"] = {k: float(S[k].mean()) for k in ("Vmax", "Vmin", "V_margin", "V_EQ", "V_random")}; rep["regret"] = {k: float((S.Vmax - S[k]).mean()) for k in ("V_margin", "V_EQ", "V_random")}; rep["Delta/2"] = float(((S.Vmax - S.Vmin) / 2).mean())
# ---------- (2) local twins: independent construction + physical admissibility
rows = []
for st, g in tv.groupby("state"):
    run_id, b = st.split("|"); b = int(b); spec = d.spec_by_id[run_id]; te = np.asarray(spec.test_indices); tr = np.asarray(spec.train_indices); rev = np.asarray(P1[run_id][:b])
    og = o[o.state == st]; xm = int(og.cand.values[np.lexsort((og.cand.values, -og.m3_margin.values))[0]])
    V = g.V.values; xs = int(g.cand.values[np.argmax(V)]); Vm = float(g[g.cand == xm].V.iloc[0]) if xm in set(g.cand) else 0.0
    if V.max() <= Vm: continue
    rb = g[g.cand == xs].iloc[0]; rm = g[g.cand == xm].iloc[0] if xm in set(g.cand) else None
    Fb = dict(zip(rb.F, zip(rb.e, rb.p0))); Fm = dict(zip(rm.F, zip(rm.e, rm.p0))) if rm is not None else {}
    D = int(round(17 * (V.max() - Vm))); k = D // 2 + 1
    avail = [(u, Fb[u][1]) for u in Fb if Fb[u][0] == -1 and u not in Fm] + [(u, Fm[u][1]) for u in Fm if Fm[u][0] == 1 and u not in Fb]
    # per-row admissibility attributes
    attrs = []
    for u, p in avail:
        row = int(te[u]); newlab = 1 - y[row]
        lab_rev = y.copy(); lab_rev[row] = newlab
        revmask = np.zeros(len(y), bool); revmask[rev] = True; revmask[row] = True
        v_rev = violations(lab_rev, revmask) - violations(y, revmask)       # new violations against REVEALED labels (label-blind check)
        v_all = violations(lab_rev) - V0                                     # new violations against all other true labels
        # sign-consistent flips within the same fold's reference set are what the twin changes; other hidden rows keep truth
        attrs.append({"u": u, "row": row, "p0": p, "conf": abs(2 * p - 1), "band": bool(BAND[row]), "main_cfg": bool(cfg[row] == MAIN), "v_rev": int(v_rev), "v_all": int(v_all), "logh": float(lh[row]), "newlab": int(newlab), "e": -1 if u in Fb and Fb[u][0] == -1 else 1})
    A = pd.DataFrame(attrs)
    def joint_ok(sel, level):
        # joint check: flipping all selected rows together must not create violations among themselves either
        lab2 = y.copy()
        for r in sel: lab2[r] = 1 - y[r]
        if level == "rev":
            m = np.zeros(len(y), bool); m[rev] = True; m[list(sel)] = True; return violations(lab2, m) - violations(y, m) == 0
        return violations(lab2) - V0 == 0
    def feasible(cond, joint=None):
        c = A[cond] if cond is not None else A
        if len(c) < k: return 0
        for combo in itertools.combinations(c.row.tolist(), k):
            if joint is None or joint_ok(combo, joint): return 1
        return 0
    rec = {"state": st, "D": D, "k": k, "n_avail": len(A), "acc0_R": float(rb.acc0_R),
           "L0_any": feasible(None), "L1_rev_consistent": feasible(A.v_rev == 0, "rev"), "L2_rev_consistent_band": feasible((A.v_rev == 0) & A.band, "rev"),
           "L3_all_consistent": feasible(A.v_all == 0, "all"), "L4_all_consistent_band": feasible((A.v_all == 0) & A.band, "all"), "L5_all_band_main_conf<=0.5": feasible((A.v_all == 0) & A.band & A.main_cfg & (A.conf <= .5), "all"),
           "min_conf_avail": float(A.conf.min()), "frac_avail_band": float(A.band.mean()), "frac_avail_v_all0": float((A.v_all == 0).mean()), "frac_avail_v_rev0": float((A.v_rev == 0).mean()),
           "k1_exact_marginal_P_W2": float(max((max(pp, 1 - pp) if e == -1 else min(pp, 1 - pp)) for pp, e in zip(A.p0, A.e))) if k == 1 else np.nan, "k1_n_avail_e_minus1": int((A.e == -1).sum()) if k == 1 else -1}
    rows.append(rec)
T = pd.DataFrame(rows); T.to_csv(OUT + "review_local_twins.csv", index=False)
rep["local_twins"] = {"n": int(len(T)), "k_dist": {int(a): int(b) for a, b in T.k.value_counts().sort_index().items()},
                      **{c: int(T[c].sum()) for c in ["L0_any", "L1_rev_consistent", "L2_rev_consistent_band", "L3_all_consistent", "L4_all_consistent_band", "L5_all_band_main_conf<=0.5"]},
                      "frac_avail_rows_band": float(T.frac_avail_band.mean()), "frac_avail_rows_all_consistent": float(T.frac_avail_v_all0.mean()),
                      "k1_states": int((T.k == 1).sum()), "k1_exact_marginal_P_W2_mean": float(T.k1_exact_marginal_P_W2.mean()), "k1_exact_marginal_P_W2_median": float(T.k1_exact_marginal_P_W2.median()), "k1_frac_P_W2>=0.5": float((T.k1_exact_marginal_P_W2 >= .5).mean())}
# ---------- (3) proxy curve re-implementation (independent RNG, 100 draws)
rng = np.random.default_rng(12345); curve = []
for q in (0.5, 0.6, 0.7, 0.8, 0.9, 1.0):
    vals = []
    for st, g in tv.groupby("state"):
        rowsU = sorted(set(u for F in g.F for u in F))
        if not rowsU: vals.extend([float(g.V.mean())] * 100); continue
        pos = {u: i for i, u in enumerate(rowsU)}; A_ = np.zeros((len(g), len(rowsU))); e_ = np.zeros(len(rowsU))
        for i, (F, E) in enumerate(zip(g.F, g.e)):
            for u, e in zip(F, E): A_[i, pos[u]] = 1; e_[pos[u]] = e
        V = g.V.values; cands = g.cand.values
        for _ in range(100):
            s = e_ * np.where(rng.random(len(rowsU)) < q, 1, -1); Vt = -(A_ @ s) / 17; vals.append(V[np.lexsort((cands, -Vt))[0]])
    curve.append({"q": q, "E_V_proxy_yx_known": float(np.mean(vals))})
rep["proxy_curve_recheck"] = curve
json.dump(rep, open(OUT + "review_recheck.json", "w"), indent=1, default=float); print(json.dumps(rep, indent=1, default=float))
