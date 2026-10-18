"""RC18 main line: physical-output models (simple vs rich) x acquisition (old vs new), regression and region learning.

Data (DEV, inspected before): NEW (136) and OLD (405) never pooled in evaluation. Tasks = Week 18 DEV task-folds
(week18_tasks via SMM.build_tasks), label-free feature-only maximin paths (SMM.make_paths, seed + [2]); development repeats
1-2, final repeats 5-8 (frozen in the RC18 protocol before any final run).

Models (one GP engine, src/rc18_gp.py):
  M0   simple GP: Matern 3/2 ARD on fold-standardised log inputs, constant mean, homoskedastic, ML-II = PHYS_AL's model.
  SH   partial sharing across outputs: the K physical targets of the paid runs share ARD lengthscales (sum of the K
       marginal likelihoods; per-output signal and noise variance). Addresses why ICM struggled at small budgets: ICM added
       coregionalisation parameters, while with isotopic outputs and a common kernel cokriging equals kriging, so the only
       gain left is better-identified hyperparameters.
  TR   cross-campaign transfer (NEW only): prior mean = the OLD-campaign emulator mu_OLD(x) (GP fitted once on ALL OLD runs,
       which exist before any NEW run; only x is needed at a NEW run), plus a residual GP on the paid NEW runs (with < 5 paid
       finite values: offset only). Variant TRs adds a slope correction h = mu_OLD - c with a Gaussian prior (b = 1).
Acquisitions: MAXIMIN (frozen path), RANDOM, MOIVR (sum over primary targets of IVR / paid variance; one simulation reveals
all outputs), STRADDLE, TRUVAR (LSE), ASTRA_SURPRISE / ASTRA_STRADDLE_GLOBAL (Astra's ask/tell selector, same global
schedule with the local reaction on / off).
    python -m src.rc18_campaign emulators | dev-reg | dev-region | ...
"""
from __future__ import annotations

import hashlib
import json
import sys
import time

import numpy as np
import pandas as pd

import src.jdl_phys_al as PAL
import src.jdl_stage_m as SMM
import src.rc18_common as RC
import src.rc18_gp as G

OUT = RC.CAMP / "main"
EMU = OUT / "old_emulators"
PRIMARY = {"NEW": ["log_A_um", "log_ke_T0_nJ", "vmax_spike_logratio", "vmax_spike_us", "laser_T0_W", "tmax_T0_K"],
           "OLD": ["log_A_um", "log_ke_T0_nJ", "vmax_spike_logratio", "laser_T0_W", "tmax_T0_K", "log_etot_T0_J", "log_npart_T0"]}
ALL_T = list(PAL.PRIMARY) + list(PAL.SECONDARY)
B0, B1 = 8, 60
SPIKE_TAU = float(np.log(2.0))          # region: 99.9th percentile of melt velocity above twice its median (fixed a priori)


# ==================================================================================================== tasks and targets
def tasks(pop, repeats):
    old = SMM.REPEATS; SMM.REPEATS = tuple(repeats)
    try:
        T = [t for t in SMM.build_tasks() if t["population"] == pop]
    finally:
        SMM.REPEATS = old
    SMM.make_paths(T)
    return sorted(T, key=lambda t: (t["repeat"], t["fold"]))


def targets(pop):
    """PHYS_AL targets; OLD log KE T0 from the channel-independent RC18 loader where PHYS_AL had none (fix A2)."""
    T = PAL.targets(pop).copy()
    if pop == "OLD":
        S = pd.read_csv(RC.CAMP / "data" / "SUMMARIES.csv"); S = S[S.population == "OLD"].set_index("sim_id")
        ke = np.log(S["ke__row_median_T0"]); common = T.index.intersection(ke.index)
        both = T.loc[common, "log_ke_T0_nJ"].notna() & ke.loc[common].notna()
        T.attrs["ke_consistency_max_abs_diff"] = float(np.max(np.abs(T.loc[common][both].log_ke_T0_nJ - ke.loc[common][both])))
        add = T.index.isin(ke.index) & T.log_ke_T0_nJ.isna()
        T.loc[add, "log_ke_T0_nJ"] = ke.reindex(T.index[add]).to_numpy()
        T.attrs["ke_added_by_rc18_loader"] = int(np.isfinite(T.loc[add, "log_ke_T0_nJ"]).sum())
    return T


def zstd(task):
    std = SMM.standardizer(task)[0]; X = task["X"]; Z = np.zeros((len(X), 4)); Z[task["pool"]] = std(X[task["pool"]]); Z[task["test"]] = std(X[task["test"]])
    return Z


# ==================================================================================================== OLD emulators (TR)
def fit_emulators():
    """One GP per target on ALL OLD runs (historical campaign); predictions at every NEW run are cached."""
    RC.limit_threads(1); EMU.mkdir(parents=True, exist_ok=True)
    TO = targets("OLD"); TN = PAL.targets("NEW")
    W = pd.read_csv(PAL.PP.W19_DEPTH).set_index("sim_id")
    def X(ids):
        w = W.loc[ids]; return np.c_[w.P, w.VX, w.LS_um_radius * 1e-6, w.ST].astype(float)
    XO, XN = np.log(X(TO.index)), np.log(X(TN.index)); mu, sd = XO.mean(0), XO.std(0); ZO, ZN = (XO - mu) / sd, (XN - mu) / sd
    rows = {"input_standardisation": {"mean": mu.tolist(), "sd": sd.tolist()}, "targets": {}}
    pred = pd.DataFrame(index=TN.index)
    for c in ALL_T:
        y = TO[c].to_numpy(float); ok = np.isfinite(y); t0 = time.time()
        g = G.GP().fit(ZO[ok], y[ok]); m, lat, obs = g.predict(ZN)
        pred[f"{c}__mu"] = m; pred[f"{c}__lat"] = lat
        rows["targets"][c] = {"n_old": int(ok.sum()), "theta": g.theta.tolist(), "opt": g.opt, "seconds": time.time() - t0}
        print(json.dumps({"emulator": c, "n": int(ok.sum()), "s": round(time.time() - t0, 1)}), flush=True)
    pred.to_csv(EMU / "mu_OLD_at_NEW.csv", lineterminator="\n"); (EMU / "EMULATORS.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")


def emulator_at(ids):
    P = pd.read_csv(EMU / "mu_OLD_at_NEW.csv", index_col=0); return P.reindex(ids)


# ==================================================================================================== model wrappers
class Fitted:
    """predict(idx) -> mean, latent var, observation var for one target, on task row indices."""
    def __init__(self, g, Z, extra=None):
        self.g, self.Z, self.extra = g, Z, extra or {}

    def predict(self, idx):
        e = self.extra; m0 = e.get("m0"); H = e.get("H")
        return self.g.predict(self.Z[idx], Hs=None if H is None else H[idx], m0s=None if m0 is None else m0[idx])


def qa_short(ids):
    """Learner-visible QA of a PAID run: its record ended before 95 % of the planned end time (TE in the run's setup).
    Such a run's T0 summaries describe an earlier, truncated stage. Q-models give its regression row a noise multiplier
    of 1e4 (the run stays paid, keeps its label and is evaluated like every other run)."""
    S = pd.read_csv(RC.CAMP / "data" / "SUMMARIES.csv", usecols=["sim_id", "time_t_end_ms"]).set_index("sim_id")
    te = pd.Series(ids, index=ids).str.extract(r"_TE-([0-9p]+)_")[0].str.replace("p", ".").astype(float).to_numpy() * 1e3
    tend = S.reindex(ids).time_t_end_ms.to_numpy(float)
    return np.where(np.isfinite(tend), tend < 0.95 * te, False)


W_SHORT = 1e4


def fit_model(model, Z, Y, paid, cols, emu=None, short=None):
    """Fit `model` on paid rows for every target in cols. Y: (n, K) all targets (NaN = unavailable). Returns {col: fit}.
    model = base + optional 'Q' (QA-aware noise): base in M0, SH (shared ARD lengthscales across targets), TR (transfer:
    OLD-emulator prior mean + residual GP; offset only with < 5 usable paid rows), TRS (transfer + shared lengthscales)."""
    q = model.endswith("Q"); base = model[:-1] if q else model
    W = np.where(short, W_SHORT, 1.0) if (q and short is not None) else np.ones(len(Z))
    out = {}
    M0s = None
    if base in ("TR", "TRS"):
        M0s = {c: emu[f"{c}__mu"] for c in cols}
    R = Y if base in ("M0", "SH") else Y - np.column_stack([M0s[c] for c in cols])
    shared = {}
    if base in ("SH", "TRS"):
        common = paid[np.all(np.isfinite(R[np.ix_(paid, range(len(cols)))]), axis=1)]
        if (W[common] <= 100).sum() >= 5:
            gs, _ = G.fit_shared(Z[common], R[np.ix_(common, range(len(cols)))], w=W[common])
            shared = {c: gs[k].theta for k, c in enumerate(cols)}
    for k, c in enumerate(cols):
        L = paid[np.isfinite(R[paid, k])]; good = L[W[L] <= 100]
        m0 = None if M0s is None else M0s[c]
        if base in ("TR", "TRS") and len(good) < 5:                       # offset-only transfer
            off = float(np.mean(R[good, k])) if len(good) else 0.0
            sd_r = float(np.std(R[good, k], ddof=1)) if len(good) >= 3 else float(np.sqrt(np.median(emu[f"{c}__lat"])) + 1e-6)
            f = OffsetOnly(m0 + off, sd_r); f.choice = "offset"; out[c] = f; continue
        if len(good) < 3:
            out[c] = None; continue
        th = shared.get(c)
        g = G.GP().fit(Z[L], Y[L, k], m0=None if m0 is None else m0[L], w=W[L], theta0=th, optimize=th is None)
        f = Fitted(g, Z, {} if m0 is None else {"m0": m0}); f.choice = "shared" if th is not None else "own"; out[c] = f
    return out


class OffsetOnly:
    def __init__(self, mean, sd):
        self.mean, self.sd = mean, sd

    def predict(self, idx):
        v = np.full(len(idx), self.sd ** 2); return self.mean[idx], v, v


# ==================================================================================================== regression trajectories
def mo_ivr(fits, cols, Z, paid, unpaid, pool, Y):
    s = np.zeros(len(unpaid))
    for k, c in enumerate(cols):
        f = fits.get(c)
        if f is None or not isinstance(f, Fitted):
            continue
        e = f.extra; H = e.get("H")
        sc = G.ivr(f.g, None, None, Z[unpaid], None if H is None else H[unpaid], Z[pool], None if H is None else H[pool])
        var = np.nanvar(Y[paid, k]) if np.isfinite(Y[paid, k]).sum() > 1 else 1.0
        s += sc / max(var, 1e-12)
    return s


def run_reg(task, pop, model, acq, Tt, emu=None, budgets=None, record_from=None):
    """One trajectory: predictions of every target on the test rows at each budget. acq in MAXIMIN, RANDOM, MOIVR."""
    ids = np.asarray(task["ids"]).astype(str); Z = zstd(task); pool, test = task["pool"], task["test"]
    cols = ALL_T; Y = Tt.reindex(ids)[cols].to_numpy(float); short = qa_short(ids)
    E = None
    if model.startswith("TR"):
        e = emulator_at(ids); E = {k: e[k].to_numpy(float) for k in e.columns}
    rng = np.random.default_rng(51000 + 100 * task["repeat"] + task["fold"] + (17 if pop == "OLD" else 0))
    start = 0 if model.startswith("TR") and acq == "MAXIMIN" else B0
    L = [int(i) for i in task["path"][:start]]; evals = []; t0 = time.time(); prim = PRIMARY[pop]
    for b in range(start, B1 + 1):
        paid = np.asarray(L, int); fits = fit_model(model, Z, Y, paid, cols, emu=E, short=short)
        pr = {}
        for c in cols:
            f = fits.get(c)
            if f is None:
                pr[c] = None; continue
            m, lat, obs = f.predict(test); pr[c] = [m.tolist(), lat.tolist(), obs.tolist()]
        evals.append({"budget": b, "pred": pr, "choice": {c: getattr(f, "choice", None) for c, f in fits.items() if f is not None}})
        if b == B1:
            break
        unpaid = np.setdiff1d(pool, L)
        if acq == "MAXIMIN" or (acq == "MOIVR" and b < B0):
            nxt = int([i for i in task["path"] if i not in set(L)][0])
        elif acq == "RANDOM":
            nxt = int(rng.choice(unpaid))
        elif acq == "MOIVR":
            sc = mo_ivr(fits, cols, Z, paid, unpaid, pool, Y[:, :]) if True else None
            sc = mo_ivr({c: fits[c] for c in prim if c in fits}, [c for c in prim], Z, paid, unpaid, pool, Y[:, [cols.index(c) for c in prim]])
            nxt = int(unpaid[int(np.argmax(sc))])
        else:
            raise ValueError(acq)
        L.append(nxt)
    return {"population": pop, "repeat": task["repeat"], "fold": task["fold"], "model": model, "acq": acq, "paid": L,
            "paid_ids": [ids[i] for i in L], "test_ids": [ids[i] for i in test], "evals": evals, "seconds": time.time() - t0}


# ==================================================================================================== region trajectories
def unit_box(task):
    X = np.log(task["X"]); p = task["pool"]; lo, hi = X[p].min(0), X[p].max(0)
    return np.clip((X - lo) / np.where(hi > lo, hi - lo, 1.0), 0.0, 1.0)


def run_region(task, pop, model, acq, Tt, response="vmax_spike_logratio", tau=SPIKE_TAU, budget_max=40):
    """Level-set learning of {x: response >= tau}. Every pool run is a candidate; invalid (NaN) responses are paid, kept
    in the paid ledger, and never used as regression rows. Returns test predictions per budget and the paid path."""
    ids = np.asarray(task["ids"]).astype(str); Z = zstd(task); pool, test = task["pool"], task["test"]
    y = Tt.reindex(ids)[response].to_numpy(float); cols = [response]; Y = y[:, None]; short = qa_short(ids)
    E = None
    if model.startswith("TR"):
        e = emulator_at(ids); E = {k: e[k].to_numpy(float) for k in e.columns}
    rng = np.random.default_rng(61000 + 100 * task["repeat"] + task["fold"] + (17 if pop == "OLD" else 0))
    L = [int(i) for i in task["path"][:B0]]; evals = []; t0 = time.time(); log = []
    astra = None
    if acq.startswith("ASTRA_"):
        import importlib.util
        spec = importlib.util.spec_from_file_location("astra_discovery", RC.ROOT / "outputs" / "research_campaign_20261018" / "astra_pilot" /
                                                      "astra_monitor_discovery_20261016" / "discovery.py")
        AD = importlib.util.module_from_spec(spec); sys.modules["astra_discovery"] = AD; spec.loader.exec_module(AD)
        U = unit_box(task)[pool]; pos = {int(i): k for k, i in enumerate(pool)}
        astra = AD.SurpriseLocalDiscovery(U.tolist(), paid_indices=[pos[i] for i in L], seed=int(task["repeat"] * 100 + task["fold"]),
                                          mode="surprise" if acq == "ASTRA_SURPRISE" else "straddle_global", config=AD.Config(threshold=tau))
    for b in range(B0, budget_max + 1):
        paid = np.asarray(L, int); fits = fit_model(model, Z, Y, paid, cols, emu=E, short=short); f = fits.get(response)
        m, lat, obs = f.predict(test) if f is not None else (np.full(len(test), np.nan),) * 3
        evals.append({"budget": b, "mean": m.tolist(), "lat": lat.tolist()})
        if b == budget_max:
            break
        unpaid = np.setdiff1d(pool, L)
        if acq == "MAXIMIN" or f is None:
            nxt = int([i for i in task["path"] if i not in set(L)][0]); how = "path"
        elif acq == "RANDOM":
            nxt = int(rng.choice(unpaid)); how = "random"
        elif acq == "STRADDLE":
            mu, lv, _ = f.predict(unpaid); nxt = int(unpaid[int(np.argmax(G.straddle(mu, lv, tau)))]); how = "straddle"
        elif acq == "TRUVAR":
            mu, lv, _ = f.predict(unpaid)
            Hc = None if not isinstance(f, Fitted) or f.extra.get("H") is None else f.extra["H"][unpaid]
            sc, M = G.truvar_lse(f.g, Z[unpaid], Hc, mu, lv, tau) if isinstance(f, Fitted) else (G.straddle(mu, lv, tau), None)
            nxt = int(unpaid[int(np.argmax(sc))]) if np.any(sc > 0) else int(unpaid[int(np.argmax(G.straddle(mu, lv, tau)))]); how = "truvar"
        elif astra is not None:
            mu, lv, ov = f.predict(pool)
            noise = np.maximum(ov - lv, 0.0)
            P = AD.Predictions(model_id=hashlib.sha1(f"{task['repeat']}|{task['fold']}|{model}|{len(L)}".encode()).hexdigest(), paid_count=len(L),
                               mean=tuple(float(v) for v in mu), latent_sd=tuple(float(np.sqrt(v)) for v in lv), noise_sd=tuple(float(np.sqrt(v)) for v in noise))
            ch = astra.ask(P); nxt = int(pool[ch.index]); how = ch.reason
            val = y[nxt]; ok = bool(np.isfinite(val))
            ev = astra.tell(AD.Observation(index=ch.index, value=float(val) if ok else None, quality_ok=ok, quality_note="ok" if ok else "unavailable",
                                           canonical_label=None))
            log.append({"budget": b + 1, "how": how, "triggered": ev.get("triggered"), "z": ev.get("raw_z")})
        else:
            raise ValueError(acq)
        L.append(nxt)
    return {"population": pop, "repeat": task["repeat"], "fold": task["fold"], "model": model, "acq": acq, "response": response, "tau": tau,
            "paid": L, "paid_ids": [ids[i] for i in L], "test_ids": [ids[i] for i in test], "evals": evals, "astra_log": log, "seconds": time.time() - t0}


# ==================================================================================================== Keyhole label arm
def _u_rule(t, yl):
    """E1's online threshold on log depth from paid (log A, label) pairs (week18_engine.DepthGPR, unchanged)."""
    from sklearn.linear_model import LogisticRegression
    kh, nk = t[yl == 1], t[yl == 0]
    if len(kh) and len(nk) and nk.max() < kh.min():
        return .5 * (nk.max() + kh.min())
    if len(kh) and len(nk):
        lr = LogisticRegression(C=1e6, max_iter=5000).fit(t[:, None], yl); return float(-lr.intercept_[0] / lr.coef_[0, 0])
    return float(np.log(111.0))


def run_label(task, pop, arm, budget_max=40):
    """Keyhole label arms on the same feature-only start (first 8 path points). One-class rule (as TRAINED_AL): while the
    usable paid labels contain one class, every arm continues the frozen label-free path; G3 then predicts the paid class.
    Arms: G3_MARGIN, ACTIVE_E1_STRADDLE (frozen Week 18 E1: GPR on log A + paid-pair threshold), TR_E1_STRADDLE (same
    threshold rule and acquisition, depth model = TR transfer GP), and the *_MAXIMIN design controls."""
    import warnings
    from scipy.special import ndtr
    import src.week18_engine as E
    X, y, ids, pool, test = task["X"], task["y"], np.asarray(task["ids"]).astype(str), task["pool"], task["test"]
    A = np.asarray(task["A"], float); Z = zstd(task); logA = np.log(A)
    emu = emulator_at(ids)["log_A_um__mu"].to_numpy(float) if arm.startswith("TR_") else None
    L = [int(i) for i in task["path"][:B0]]; evals = []; t0 = time.time(); oneclass = 0
    for b in range(B0, budget_max + 1):
        Lr = np.asarray(L); usable = np.isfinite(A[Lr]) if "E1" in arm else np.ones(len(Lr), bool)
        two = len(set(y[Lr][usable].tolist())) == 2; p = None; score_c = None; cands = np.setdiff1d(pool, Lr)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if arm.startswith("G3"):
                if two:
                    ym = np.full(len(y), -1, int); ym[Lr] = y[Lr]
                    f = E.fit_learner(("G3", "mlii"), {"X": X, "y": ym, "pool": pool, "prior": np.array([], int)}, L, None, {"kernel": None, "b0": len(L)})
                    p = np.asarray(E.proba(f, X[test]), float); score_c = -np.abs(np.asarray(E.proba(f, X[cands]), float) - 0.5)
                else:
                    p = np.full(len(test), float(np.mean(y[Lr])))
            elif arm.startswith("ACTIVE_E1"):
                ym = np.full(len(y), -1, int); ym[Lr] = y[Lr]; dm = np.full(len(y), np.nan); dm[Lr] = A[Lr]
                f = E.fit_learner(("GPR_depth", "mlii"), {"X": X, "y": ym, "pool": pool, "prior": np.array([], int), "depth": dm}, L, None, {"kernel": None, "b0": len(L)})
                p = np.asarray(E.proba(f, X[test]), float); mc, vc = E.latent(f, X[cands]); score_c = 1.96 * np.sqrt(vc) - np.abs(mc)
            else:                                                             # TR_E1: transfer depth model + the same rule
                Lu = Lr[usable]; u = _u_rule(logA[Lu], y[Lu])
                if len(Lu) >= 5:
                    g = G.GP().fit(Z[Lu], logA[Lu], m0=emu[Lu]); mt_, lt_, _ = g.predict(Z[test], m0s=emu[test]); mc, lc, _ = g.predict(Z[cands], m0s=emu[cands])
                else:
                    off = float(np.mean(logA[Lu] - emu[Lu])) if len(Lu) else 0.0; s2 = float(np.var(logA[Lu] - emu[Lu])) if len(Lu) > 1 else 0.05
                    mt_, lt_ = emu[test] + off, np.full(len(test), s2); mc, lc = emu[cands] + off, np.full(len(cands), s2)
                p = ndtr((mt_ - u) / np.sqrt(lt_)); score_c = 1.96 * np.sqrt(lc) - np.abs(mc - u)
        evals.append({"budget": b, "p": p.tolist(), "two_classes": bool(two)})
        if b == budget_max:
            break
        if not two or arm.endswith("_MAXIMIN") or score_c is None:
            nxt = int([i for i in task["path"] if i not in set(L)][0]); oneclass += int(not two)
        else:
            nxt = int(cands[int(np.argmax(score_c))])
        L.append(nxt)
    return {"population": pop, "repeat": task["repeat"], "fold": task["fold"], "arm": arm, "paid": L, "paid_ids": [ids[i] for i in L],
            "test_ids": [ids[i] for i in test], "evals": evals, "oneclass_steps": oneclass, "seconds": time.time() - t0}


# ==================================================================================================== development driver
DEV = OUT / "dev"


def _units_reg(pops, repeats, models, acqs):
    for pop in pops:
        for t in tasks(pop, repeats):
            for model in models:
                if model.startswith("TR") and pop != "NEW":
                    continue
                for acq in acqs:
                    yield pop, t, model, acq


def dev_reg(pops=("NEW", "OLD"), repeats=(1, 2), models=("M0", "SH", "TR", "TRs"), acqs=("MAXIMIN",), tag="reg"):
    RC.limit_threads(1); T = {p: targets(p) for p in pops}
    U = {f"{pop}__r{t['repeat']}_f{t['fold']}__{m}__{a}": (pop, t, m, a) for pop, t, m, a in _units_reg(pops, repeats, models, acqs)}
    def fn(name):
        pop, t, m, a = U[name]; return run_reg(t, pop, m, a, T[pop])
    RC.run_units(list(U), fn, DEV / tag / "units", DEV / tag / "locks", DEV / tag / "failed", log=lambda s: print(s, flush=True))


def full_r2(pop, repeats):
    """Attainable accuracy of M0 with the whole fold pool paid (pooled out-of-fold R2 per repeat), per target."""
    Tt = targets(pop); out = {}
    for t in tasks(pop, repeats):
        ids = np.asarray(t["ids"]).astype(str); Z = zstd(t); Y = Tt.reindex(ids)[ALL_T].to_numpy(float)
        fits = fit_model("M0", Z, Y, np.asarray(t["pool"]), ALL_T)
        for k, c in enumerate(ALL_T):
            if fits.get(c) is None:
                continue
            m = fits[c].predict(t["test"])[0]; yv = Y[t["test"], k]; ok = np.isfinite(yv)
            out.setdefault((c, t["repeat"]), []).extend(zip(yv[ok], m[ok]))
    ref = {c: float(np.nanmean(Tt[c])) for c in ALL_T}
    r2 = {}
    for (c, r), z in out.items():
        yy, pp = np.array([a for a, _ in z]), np.array([b for _, b in z]); r2[(c, r)] = float(1 - np.sum((yy - pp) ** 2) / np.sum((yy - ref[c]) ** 2))
    return r2


def eval_reg(tag="reg", pops=("NEW", "OLD"), repeats=(1, 2)):
    rows = []; res = {}
    for pop in pops:
        Tt = targets(pop); ref = {c: float(np.nanmean(Tt[c])) for c in ALL_T}; R2F = full_r2(pop, repeats)
        U = {}
        for p in (DEV / tag / "units").glob(f"{pop}__*.json.gz"):
            u = RC.read_json_gz(p); U[(u["model"], u["acq"], u["repeat"], u["fold"])] = u
        combos = sorted({(m, a) for (m, a, _, _) in U})
        for (m, a) in combos:
            for c in ALL_T:
                for r in repeats:
                    curve = {}
                    for b in range(0, B1 + 1):
                        yy, pp, lv, ov = [], [], [], []
                        for f in (1, 2, 3, 4, 5):
                            u = U.get((m, a, r, f))
                            if u is None:
                                break
                            e = {x["budget"]: x for x in u["evals"]}.get(b)
                            if e is None or e["pred"].get(c) is None:
                                break
                            yv = Tt.reindex(u["test_ids"])[c].to_numpy(float); ok = np.isfinite(yv); P = e["pred"][c]
                            yy += list(yv[ok]); pp += list(np.asarray(P[0])[ok]); lv += list(np.asarray(P[1])[ok]); ov += list(np.asarray(P[2])[ok])
                        else:
                            yy, pp, ov = map(np.asarray, (yy, pp, ov))
                            r2 = 1 - np.sum((yy - pp) ** 2) / np.sum((yy - ref[c]) ** 2)
                            cov = float(np.mean(np.abs(yy - pp) <= 1.645 * np.sqrt(ov)))
                            nlpd = float(np.mean(0.5 * np.log(2 * np.pi * ov) + 0.5 * (yy - pp) ** 2 / ov))
                            curve[b] = (r2, cov, nlpd)
                    if not curve:
                        continue
                    lev = 0.9 * np.mean([R2F[(c, rr)] for rr in repeats if (c, rr) in R2F]) if any((c, rr) in R2F for rr in repeats) else np.nan
                    bs = sorted(curve); grid = [b for b in range(B0, B1 + 1, 4)]
                    hit = next((g for i, g in enumerate(grid[:-1]) if curve.get(g, (-9,))[0] >= lev and curve.get(grid[i + 1], (-9,))[0] >= lev), 64)
                    aulc = float(np.trapezoid([curve[b][0] for b in range(B0, B1 + 1)], dx=1) / (B1 - B0)) if all(b in curve for b in range(B0, B1 + 1)) else np.nan
                    rows.append({"pop": pop, "model": m, "acq": a, "target": c, "repeat": r, "R2_AULC": aulc, "budget_to_target": hit, "level": lev,
                                 **{f"R2_B{b}": curve[b][0] for b in (0, 4, 8, 12, 16, 24, 40, 60) if b in curve},
                                 **{f"cov90_B{b}": curve[b][1] for b in (8, 24, 60) if b in curve}, **{f"nlpd_B{b}": curve[b][2] for b in (8, 24, 60) if b in curve},
                                 "R2_full_M0": R2F.get((c, r))})
    D = pd.DataFrame(rows); (DEV / tag).mkdir(parents=True, exist_ok=True); D.to_csv(DEV / tag / "eval.csv", index=False, lineterminator="\n")
    return D


if __name__ == "__main__":
    step = sys.argv[1]
    if step == "emulators":
        fit_emulators()
    elif step == "dev-reg":
        dev_reg()
    elif step == "dev-reg2":
        dev_reg(pops=("NEW",), models=("TRX", "TRXS"), tag="reg")
    elif step == "dev-reg3":
        dev_reg(pops=("NEW", "OLD"), models=("M0Q", "SHQ", "TRQ", "TRSQ"), tag="reg")
    elif step == "eval-reg":
        D = eval_reg(); print(D.groupby(["pop", "model", "acq"])[["R2_AULC", "budget_to_target"]].mean().round(3).to_string())
