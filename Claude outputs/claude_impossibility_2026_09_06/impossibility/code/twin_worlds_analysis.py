"""Analysis of twin_worlds_flips.csv.gz: identity check, per-state oracle geometry, minimal reversing
twin worlds, model-posterior plausibility of the twin, label-blind rule regret / P(oracle-best),
symmetry of the correctness signs at flip rows, and the reference-side proxy accuracy curve."""
import itertools, json, numpy as np, pandas as pd
from scipy.stats import spearmanr
OUT = "/home/claude/rnd/followup/results/"
df = pd.read_csv(OUT + "twin_worlds_flips.csv.gz", keep_default_na=False)
df["state"] = df.run_id + "|" + df.budget.astype(str)
def lst(s, f=int): return [f(t) for t in s.split(";")] if s else []
df["F"] = df.FR.map(lambda s: lst(s)); df["e"] = df.eR.map(lambda s: lst(s)); df["p0"] = df.p0R.map(lambda s: lst(s, float)); df["p1"] = df.p1R.map(lambda s: lst(s, float))
df["k"] = df.F.map(len)
res = {}
# ---- 1. identity V = -|R|^-1 sum e_u  and agreement with oracle_values.csv.gz
res["identity_max_abs_dev"] = float((df.V_R - df.V_R_direct).abs().max())
o = pd.read_csv(OUT + "oracle_values.csv.gz"); o = o[o.eligible == 1][["run_id", "budget", "cand", "V_q20_acc", "m3_margin"]]; o["state"] = o.run_id + "|" + o.budget.astype(str); VRAND = o.groupby("state").V_q20_acc.mean(); NELIG = o.groupby("state").size()
tv = df[df.lab == df.true_y].merge(o.drop(columns=["state"]), on=["run_id", "budget", "cand"]); res["oracle_values_agreement_max_abs_dev"] = float((tv.V_R - tv.V_q20_acc).abs().max()); res["n_states"] = int(tv.state.nunique()); res["n_candidates"] = int(len(tv))
# ---- 2. flip-set geometry and symmetry of e at flip rows
allE = np.concatenate(df.e.values); res["flip_rows_total_(cand,label)"] = int(len(allE)); res["mean_e_at_flip_rows_all_labels"] = float(allE.mean())
tE = np.concatenate(tv.e.values); res["mean_e_at_flip_rows_true_label"] = float(tE.mean()); res["P(e=-1 | flip row, true label)"] = float((tE == -1).mean())
tP0 = np.concatenate(tv.p0.values); conf0 = np.abs(2 * tP0 - 1)
bins = pd.cut(conf0, [0, .1, .2, .4, .6, 1.0], include_lowest=True); sym = pd.DataFrame({"conf": bins, "e": tE}).groupby("conf", observed=True).e.agg(["mean", "count"]); res["e_by_model_confidence_true_label"] = {str(k): {"mean_e": float(v["mean"]), "n": int(v["count"])} for k, v in sym.iterrows()}
res["flip_set_size_dist_true_label"] = {int(k): int(v) for k, v in tv.k.value_counts().sort_index().items()}
res["frac_candidates_nonempty_flip_true_label"] = float((tv.k > 0).mean())
# posterior-expected correctness after refit at flip rows (model's own belief that the flip helps)
tP1 = np.concatenate(tv.p1.values); res["mean_model_conf_after_flip_|2p1-1|"] = float(np.abs(2 * tP1 - 1).mean()); res["mean_model_conf_before_flip_|2p0-1|"] = float(conf0.mean())
# ---- 3. per-state rules
def EQ(row):   # model-Bayes expected value under its own posterior, S3-like, restricted to R, expectation over y_x with p_n(x)
    return float(sum(abs(2 * q - 1) for q in row.p1)) / row.nR
df["EQ_lab"] = df.apply(EQ, axis=1)
g = df.groupby(["state", "cand"]); piv = df.pivot_table(index=["state", "cand"], columns="lab", values=["V_R", "EQ_lab", "k"]); piv.columns = [f"{a}{b}" for a, b in piv.columns]
piv = piv.reset_index().merge(tv[["state", "cand", "V_R", "m3_p", "true_y", "m3_margin", "repeat", "budget", "k"]].rename(columns={"V_R": "V", "k": "k_true"}), on=["state", "cand"])
piv["EQ"] = piv.m3_p * piv.EQ_lab1 + (1 - piv.m3_p) * piv.EQ_lab0                     # label-blind model-Bayes value (XSUR-S3 on R)
piv["EQ_yx"] = np.where(piv.true_y == 1, piv.EQ_lab1, piv.EQ_lab0)                    # candidate-label-informed (y_x known), e unknown
piv["Vother"] = np.where(piv.true_y == 1, piv.V_R0, piv.V_R1)
piv["Vmax_lab"] = piv[["V_R0", "V_R1"]].max(1)
rows = []; rng = np.random.default_rng(0)
for st, gg in piv.groupby("state"):
    V = gg.V.values; vmax, vmin = V.max(), V.min(); best = gg.cand.values[np.argmax(V)]
    def pick(score): o_ = np.lexsort((gg.cand.values, -score)); return o_[0]
    im = pick(gg.m3_margin.values); iq = pick(gg.EQ.values); iy = pick(gg.EQ_yx.values)
    rows.append({"state": st, "repeat": gg.repeat.iloc[0], "budget": gg.budget.iloc[0], "n_cand": len(gg), "n_pos": int((V > 0).sum()), "n_neg": int((V < 0).sum()),
                 "Vmax": vmax, "Vmin": vmin, "range": vmax - vmin, "minimax_bound": (vmax - vmin) / 2, "Vmean": float(VRAND[st]), "Vmedian": float(np.median(V)),
                 "V_margin": V[im], "V_EQ": V[iq], "V_EQyx": V[iy], "V_random_mean": float(VRAND[st]), "n_elig_all": int(NELIG[st]),
                 "margin_is_best": int(V[im] == vmax and vmax > 0), "EQ_is_best": int(V[iq] == vmax and vmax > 0), "EQyx_is_best": int(V[iy] == vmax and vmax > 0),
                 "frac_cand_best": float((V == vmax).mean()) if vmax > 0 else np.nan,
                 "rho_EQ_V": spearmanr(gg.EQ, V)[0] if gg.EQ.nunique() > 1 else np.nan, "rho_EQyx_V": spearmanr(gg.EQ_yx, V)[0] if gg.EQ_yx.nunique() > 1 else np.nan,
                 "rho_margin_V": spearmanr(gg.m3_margin, V)[0], "corr_V_Vother": np.corrcoef(gg.V, gg.Vother)[0, 1] if gg.Vother.nunique() > 1 and gg.V.nunique() > 1 else np.nan})
S = pd.DataFrame(rows); S.to_csv(OUT + "twin_worlds_states.csv", index=False)
blk = S.groupby("repeat")
res["per_state"] = {c: float(S[c].mean()) for c in ["Vmax", "Vmin", "range", "minimax_bound", "Vmean", "V_margin", "V_EQ", "V_EQyx", "margin_is_best", "EQ_is_best", "EQyx_is_best", "frac_cand_best", "rho_EQ_V", "rho_EQyx_V", "rho_margin_V", "corr_V_Vother"]}
res["per_state_block_sd"] = {c: float(blk[c].mean().std(ddof=1)) for c in ["Vmax", "Vmin", "V_margin", "V_EQ", "V_EQyx", "margin_is_best", "EQ_is_best"]}
res["per_state_by_budget"] = {int(b): {c: float(v) for c, v in gg[["Vmax", "Vmin", "V_margin", "V_EQ", "V_EQyx", "margin_is_best", "EQ_is_best"]].mean().items()} for b, gg in S.groupby("budget")}
# ---- 4. minimal reversing twin worlds for (oracle-best x*, margin pick x_m) and (x*, oracle-worst)
tw = []
for st, gg in piv.groupby("state"):
    V = gg.V.values; ib = int(np.argmax(V)); im = int(np.lexsort((gg.cand.values, -gg.m3_margin.values))[0]); iw = int(np.argmin(V))
    if V[ib] <= V[im]: continue
    rb = tv[(tv.state == st) & (tv.cand == gg.cand.values[ib])].iloc[0]
    for tag, j in (("margin", im), ("worst", iw)):
        rj = tv[(tv.state == st) & (tv.cand == gg.cand.values[j])].iloc[0]
        Fb = dict(zip(rb.F, zip(rb.e, rb.p0))); Fj = dict(zip(rj.F, zip(rj.e, rj.p0))); nR = rb.nR
        D = int(round(nR * (V[ib] - V[j])))            # integer sign-count gap
        # rows whose flip lowers the gap by 2: helpful rows of x* not in F(x_j); harmful rows of x_j not in F(x*)
        avail = [(u, p) for u, (e, p) in Fb.items() if e == -1 and u not in Fj] + [(u, p) for u, (e, p) in Fj.items() if e == 1 and u not in Fb]
        kmin = D // 2 + 1
        if len(avail) < kmin: tw.append({"state": st, "pair": tag, "D": D, "feasible": 0}); continue
        # choose the kmin rows with the smallest |posterior log-odds| (most plausible reversal under the model itself)
        # log-likelihood ratio of W2 vs W1 for flipping row u: model prob of the flipped label / prob of the true label.
        # e_u=+1 -> current decision equals truth; the flipped label is the model's minority label: LR = min(p,1-p)/max(p,1-p);  e_u=-1 -> flipped label is the model's majority: LR = max/min
        def llr(u, p):
            e = Fb[u][0] if u in Fb else Fj[u][0]; p = min(max(p, 5e-5), 1 - 5e-5); a, b = max(p, 1 - p), min(p, 1 - p); return np.log(b / a) if e == 1 else np.log(a / b)
        items = sorted([(llr(u, p), u, p) for u, p in avail], key=lambda t: -t[0])[:kmin]   # most plausible first (largest llr)
        L = float(sum(t[0] for t in items)); pw2 = 1 / (1 + np.exp(-L))
        # exact posterior probability (under independent Bernoulli(p_n(u)) on the symmetric difference) that V(x_j) >= V(x*) given the true candidate labels
        Sd = [(u, Fb[u][0], Fb[u][1], +1) for u in Fb if u not in Fj] + [(u, Fj[u][0], Fj[u][1], -1) for u in Fj if u not in Fb]   # sign: +1 rows count for x*, -1 for x_j
        if len(Sd) <= 16:
            prob_rev = 0.0; prob_tie = 0.0
            for bits in itertools.product([0, 1], repeat=len(Sd)):
                pr = 1.0; gap = 0
                for (u, e, p, s), bt in zip(Sd, bits):
                    # bt = hidden label at u; current decision is the model's majority; e_bt = +1 if bt == majority
                    maj = 1 if p >= .5 else 0; eb = 1 if bt == maj else -1; pr *= (min(max(p, 5e-5), 1 - 5e-5) if bt == 1 else 1 - min(max(p, 5e-5), 1 - 5e-5)); gap += -eb * s
                if gap < 0: prob_rev += pr
                elif gap == 0: prob_tie += pr
        else: prob_rev = prob_tie = np.nan
        tw.append({"state": st, "pair": tag, "D": D, "feasible": 1, "kmin": kmin, "n_avail": len(avail), "|F*|": len(Fb), "|Fj|": len(Fj), "symdiff": len(Sd),
                   "flipped_rows_p0": ";".join(f"{t[2]:.3f}" for t in items), "logLR_W2_vs_W1": L, "P_model(W2|{W1,W2})": pw2,
                   "P_model(rank reversed)": prob_rev, "P_model(tie)": prob_tie, "V_best": V[ib], "V_j": V[j]})
TW = pd.DataFrame(tw); TW.to_csv(OUT + "twin_worlds_pairs.csv", index=False)
for tag in ("margin", "worst"):
    t = TW[(TW.pair == tag) & (TW.feasible == 1)]
    res[f"twin_{tag}"] = {"n_states": int(len(t)), "feasible_frac": float(TW[TW.pair == tag].feasible.mean()), "kmin_dist": {int(k): int(v) for k, v in t.kmin.value_counts().sort_index().items()},
                          "median_logLR": float(t.logLR_W2_vs_W1.median()), "mean_P_model_W2": float(t["P_model(W2|{W1,W2})"].mean()), "min_P_model_W2": float(t["P_model(W2|{W1,W2})"].min()),
                          "mean_P_model_rank_reversed": float(t["P_model(rank reversed)"].mean()), "mean_P_model_reversed_or_tie": float((t["P_model(rank reversed)"] + t["P_model(tie)"]).mean()),
                          "median_symdiff": float(t.symdiff.median()), "mean_D": float(t.D.mean())}
# ---- 5. reference-side proxy accuracy curve: s_u = e_u * xi_u, P(xi=1)=q, independent; rule picks argmax -sum_{F_{y_x}(x)} s_u (y_x known) ;
#         and the label-blind-y_x variant using p_n(x) for the flip set expectation. Realised V of the pick, averaged over states; 200 draws per q.
Q = [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.9, 1.0]; NS = 200; curve = []
byst = {st: gg for st, gg in tv.groupby("state")}
piv_i = piv.set_index(["state", "cand"])
for q in Q:
    vals_y = []; vals_b = []; hits_y = []
    for st, gg in byst.items():
        V = gg.V_R.values; vmax = V.max(); nR = gg.nR.iloc[0]
        # pre-extract per-candidate flip structures for both labels
        g0 = df[(df.state == st) & (df.lab == 0)].set_index("cand"); g1 = df[(df.state == st) & (df.lab == 1)].set_index("cand")
        cands = gg.cand.values; ty = gg.true_y.values; pn = gg.m3_p.values
        Rrows = sorted(set(u for r in (g0, g1) for L in r.F for u in L)); pos = {u: i for i, u in enumerate(Rrows)}
        # sign of the current decision correctness per reference row (consistent across candidates): take from any occurrence
        eR = {}
        for r in (g0, g1):
            for L, E in zip(r.F, r.e):
                for u, e in zip(L, E): eR[u] = e
        evec = np.array([eR[u] for u in Rrows]) if Rrows else np.zeros(0)
        # candidate incidence matrices A_y[x, u] = 1 if u in F_y(x)
        A0 = np.zeros((len(cands), len(Rrows))); A1 = np.zeros_like(A0)
        for i, c in enumerate(cands):
            for u in g0.loc[c].F: A0[i, pos[u]] = 1
            for u in g1.loc[c].F: A1[i, pos[u]] = 1
        Atrue = np.where(ty[:, None] == 1, A1, A0); Aexp = pn[:, None] * A1 + (1 - pn[:, None]) * A0
        if len(Rrows) == 0: vals_y.append(V.mean()); vals_b.append(V.mean()); hits_y.append(0); continue
        for s in range(NS):
            xi = np.where(rng.random(len(Rrows)) < q, 1, -1); sig = evec * xi
            sy = -(Atrue @ sig) / nR; sb = -(Aexp @ sig) / nR
            iy = np.lexsort((cands, -sy))[0]; ib = np.lexsort((cands, -sb))[0]
            vals_y.append(V[iy]); vals_b.append(V[ib]); hits_y.append(int(V[iy] == vmax and vmax > 0))
    curve.append({"q": q, "E_V_proxy_yx_known": float(np.mean(vals_y)), "E_V_proxy_label_blind_yx": float(np.mean(vals_b)), "P_oracle_best_proxy_yx_known": float(np.mean(hits_y))})
C = pd.DataFrame(curve); C.to_csv(OUT + "twin_worlds_proxy_curve.csv", index=False); res["proxy_curve"] = C.to_dict(orient="records")
res["reference"] = {"E_Vmax": float(S.Vmax.mean()), "E_V_margin": float(S.V_margin.mean()), "E_V_EQ": float(S.V_EQ.mean()), "E_V_EQyx": float(S.V_EQyx.mean()), "E_V_random": float(S.Vmean.mean())}
json.dump(res, open(OUT + "twin_worlds_results.json", "w"), indent=1, default=float)
pd.set_option("display.width", 250); print(json.dumps({k: v for k, v in res.items() if k not in ("proxy_curve",)}, indent=1, default=float)); print(C.round(4).to_string())
