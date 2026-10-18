"""RC18 D2 — native-time phase model for the maximum melt temperature (tmax) and melt kinetic energy (ke).

Input: the 1-us native bins of src/rc18_data.py (median per 1-us bin of the valid rows), aligned at the melt onset t_on (first
valid melt row). Per run, from a 5-us block-median curve c(tau), tau = t - t_on (native ms), inside the active window:
  t_on_ms       onset time after the laser start (alignment shift)
  plateau       T0 level (duration-weighted median of the T0 rows; the PHYS_AL-type scalar)
  t90_ms        rise time: first tau with c >= 0.9 * plateau (alignment scale)
  peak          native peak amplitude: max of c over the active window (5-us blocks; no 40-bin attenuation)
  peak_ms       time of that peak after onset
  overshoot     peak / plateau
  fluct         T0 fluctuation: (p90 - p10) / median of c over T0
Curve: E = c(tau) on the fixed early native horizon tau in [0, 0.25 ms] (50 blocks of 5 us; every active window is longer),
log scale for ke. No feature uses a test run's curve when predicting that run.
    python -m src.rc18_temporal features      (per-run features + early curves -> temporal/FEATURES.csv, CURVES.npz)
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import src.rc18_common as RC
import src.rc18_data as D

OUT = RC.CAMP / "temporal"
CH = ("tmax", "ke")
BLOCK_US = 5
H_MS = 0.25
NB = int(round(H_MS * 1000 / BLOCK_US))            # 50 blocks


def block_curve(med, t_on_ms, cutoff_ms):
    """5-us block medians of the 1-us bin medians, from onset to the cutoff (native time)."""
    i0 = int(np.floor(t_on_ms * 1000)); i1 = int(np.floor(cutoff_ms * 1000))
    seg = med[i0:i1 + 1]; n = len(seg) // BLOCK_US
    if n == 0:
        return np.array([])
    B = seg[: n * BLOCK_US].reshape(n, BLOCK_US)
    with np.errstate(all="ignore"):
        return np.nanmedian(B, axis=1)


def run_features(name):
    z = np.load(D.BINS / f"{name}.npz"); t_on, cut = float(z["t_on_ms"]), float(z["cutoff_ms"])
    out = {"unit": name, "t_on_ms": t_on, "window_ms": cut - t_on if np.isfinite(t_on) and np.isfinite(cut) else np.nan}
    curves = {}
    for ch in CH:
        if f"{ch}_med" not in z or not np.isfinite(t_on) or not np.isfinite(cut):
            continue
        c = block_curve(z[f"{ch}_med"].astype(float), t_on, cut)
        if len(c) < NB + 4 or np.isnan(c[:NB]).mean() > 0.2:
            continue
        tau = (np.arange(len(c)) + 0.5) * BLOCK_US / 1000.0
        T0 = tau >= 0.8 * (cut - t_on); plateau = float(np.nanmedian(c[T0]))
        v = np.log(c) if ch == "ke" else c
        out[f"{ch}__plateau"] = float(np.log(plateau)) if ch == "ke" else plateau
        hit = np.flatnonzero(c >= 0.9 * plateau); out[f"{ch}__t90_ms"] = float(tau[hit[0]]) if len(hit) else np.nan
        k = int(np.nanargmax(c)); out[f"{ch}__peak"] = float(v[k]); out[f"{ch}__peak_ms"] = float(tau[k])
        out[f"{ch}__overshoot"] = float(c[k] / plateau)
        q10, q90 = np.nanpercentile(c[T0], [10, 90]); out[f"{ch}__fluct"] = float((q90 - q10) / plateau)
        e = v[:NB].copy(); e[np.isnan(e)] = np.nanmean(e)
        curves[ch] = e
        ke_ = int(np.argmax(e)); out[f"{ch}__epeak"] = float(e[ke_]); out[f"{ch}__epeak_ms"] = float(tau[ke_])     # early-horizon peak
    return out, curves


def features():
    rows, C = [], {ch: {} for ch in CH}
    for p, s in D.run_list():
        name = D.unit_name(p, s)
        if not (D.BINS / f"{name}.npz").exists():
            continue
        f, cv = run_features(name); f.update({"population": p, "sim_id": s}); rows.append(f)
        for ch, e in cv.items():
            C[ch][s] = e
    F = pd.DataFrame(rows); OUT.mkdir(parents=True, exist_ok=True); F.to_csv(OUT / "FEATURES.csv", index=False, lineterminator="\n")
    np.savez_compressed(OUT / "CURVES.npz", **{f"{ch}__ids": np.array(list(C[ch].keys())) for ch in CH},
                        **{f"{ch}__E": np.array(list(C[ch].values())) for ch in CH})
    print(F.groupby("population").count().T.to_string())


# ==================================================================================================== D2 models
FEATS = ["t_on_ms"] + [f"{ch}__{k}" for ch in CH for k in ("plateau", "t90_ms", "peak", "peak_ms", "overshoot", "fluct", "epeak", "epeak_ms")]
EMU_T = OUT / "old_feature_emulators.csv"
RICH_T = {"NEW": "TRSQ", "OLD": "SHQ"}


def feature_table(pop):
    F = pd.read_csv(OUT / "FEATURES.csv"); return F[F.population == pop].set_index("sim_id")[FEATS]


def fit_feature_emulators():
    """One GP per phase feature on ALL OLD runs (historical campaign) -> predictions at every NEW run (TR source)."""
    import src.rc18_campaign as C
    import src.rc18_gp as G
    RC.limit_threads(1)
    FO, FN = feature_table("OLD"), feature_table("NEW")
    W = pd.read_csv(D.PP.W19_DEPTH).set_index("sim_id")
    def X(ids):
        w = W.loc[ids]; return np.log(np.c_[w.P, w.VX, w.LS_um_radius * 1e-6, w.ST].astype(float))
    XO, XN = X(FO.index), X(FN.index); mu, sd = XO.mean(0), XO.std(0); ZO, ZN = (XO - mu) / sd, (XN - mu) / sd
    P = pd.DataFrame(index=FN.index)
    for c in FEATS:
        y = FO[c].to_numpy(float); ok = np.isfinite(y)
        g = G.GP().fit(ZO[ok], y[ok]); m, lat, _ = g.predict(ZN); P[f"{c}__mu"] = m; P[f"{c}__lat"] = lat
    P.to_csv(EMU_T, lineterminator="\n"); print("feature emulators:", len(FEATS))


def _emu(ids):
    P = pd.read_csv(EMU_T, index_col=0).reindex(ids); return {k: P[k].to_numpy(float) for k in P.columns}


def run_features_traj(task, pop, model, F):
    """MAXIMIN-design learning curve of every phase feature (as src.rc18_campaign.run_reg, generic targets)."""
    import time
    import src.rc18_campaign as C
    ids = np.asarray(task["ids"]).astype(str); Z = C.zstd(task); pool, test = task["pool"], task["test"]
    Y = F.reindex(ids)[FEATS].to_numpy(float); short = C.qa_short(ids); E = _emu(ids) if model.startswith("TR") else None
    start = 0 if model.startswith("TR") else 3; evals = []; t0 = time.time()
    for b in range(start, C.B1 + 1):
        paid = np.asarray(task["path"][:b], int); fits = C.fit_model(model, Z, Y, paid, FEATS, emu=E, short=short)
        evals.append({"budget": b, "pred": {c: (None if fits.get(c) is None else [v.tolist() for v in fits[c].predict(test)]) for c in FEATS}})
    return {"population": pop, "repeat": task["repeat"], "fold": task["fold"], "model": model, "acq": "MAXIMIN", "test_ids": [ids[i] for i in test],
            "evals": evals, "seconds": time.time() - t0}


def curve_models(task, pop, model, F, CV, budgets=(16, 40, "full")):
    """Native early-horizon curve prediction at fixed budgets of the MAXIMIN path (and the whole pool): MEAN, KRONn (x (x)
    native tau), PHASE (template x plateau, time scaled by the x-predicted t90), PHASE_PCA (PHASE + up to 3 aligned-shape
    scores, one GP each); direct scalar GPs of peak, peak_ms and t90 as the control. Alignment of a test run is predicted
    from x only."""
    import src.rc18_campaign as C
    import src.rc18_gp as G
    from src.jdl_temporal_vel import KronGP
    ids = np.asarray(task["ids"]).astype(str); Z = C.zstd(task); test = task["test"]; short = C.qa_short(ids)
    E = _emu(ids) if model.startswith("TR") else None; Y = F.reindex(ids)[FEATS].to_numpy(float)
    tau = (np.arange(NB) + 0.5) * BLOCK_US / 1000.0; out = []
    for ch in CH:
        idmap = {s: i for i, s in enumerate(CV[f"{ch}__ids"])}; Ecv = CV[f"{ch}__E"]
        have = np.array([s in idmap for s in ids]); curve = np.full((len(ids), NB), np.nan)
        for i, s in enumerate(ids):
            if s in idmap:
                curve[i] = Ecv[idmap[s]]
        te = [i for i in test if have[i]]
        for b in budgets:
            paid = np.asarray(task["pool"] if b == "full" else task["path"][:b], int)
            pc = np.array([i for i in paid if have[i] and short[i] == 0], int)
            if len(pc) < 5 or not te:
                continue
            Yt = curve[te]; pred = {"MEAN": np.broadcast_to(curve[pc].mean(0), Yt.shape)}
            try:
                kg = KronGP(Z[pc], tau).fit(curve[pc]); pred["KRONn"] = kg.predict(Z[te])[0]
            except Exception:
                pass
            fits = C.fit_model(model, Z, Y, paid, FEATS, emu=E, short=short)
            kp, kt = FEATS.index(f"{ch}__plateau"), FEATS.index(f"{ch}__t90_ms")
            if fits.get(f"{ch}__plateau") is not None and fits.get(f"{ch}__t90_ms") is not None:
                pl = fits[f"{ch}__plateau"].predict(np.asarray(te))[0]; t9 = np.maximum(fits[f"{ch}__t90_ms"].predict(np.asarray(te))[0], 1e-3)
                ug = np.linspace(0, 6, 121); G_ = []; pcg = []
                for i in pc:
                    t90i, pli = Y[i, kt], Y[i, kp]
                    if not (np.isfinite(t90i) and np.isfinite(pli) and t90i > 0):
                        continue
                    g = (curve[i] - pli) if ch == "ke" else curve[i] / pli
                    G_.append(np.interp(ug, tau / t90i, g, right=g[-1])); pcg.append(i)
                if len(G_) >= 5:
                    G_ = np.array(G_); tmpl = G_.mean(0)
                    def recon(t9v, plv, shp):
                        g = np.interp(tau / t9v, ug, shp)
                        return g + plv if ch == "ke" else g * plv
                    pred["PHASE"] = np.array([recon(t9[j], pl[j], tmpl) for j in range(len(te))])
                    R = G_ - tmpl; U_, S_, Vt = np.linalg.svd(R, full_matrices=False); ev = S_ ** 2 / max(1e-12, np.sum(S_ ** 2))
                    k = int(min(3, np.searchsorted(np.cumsum(ev), 0.9) + 1)); sc = R @ Vt[:k].T
                    zz = []
                    for j in range(k):
                        gj = G.GP().fit(Z[np.asarray(pcg)], sc[:, j]); zz.append(gj.predict(Z[te])[0])
                    shapes = tmpl[None, :] + np.array(zz).T @ Vt[:k]
                    pred["PHASE_PCA"] = np.array([recon(t9[j], pl[j], shapes[j]) for j in range(len(te))])
            row = {"population": pop, "repeat": task["repeat"], "fold": task["fold"], "model": model, "channel": ch, "budget": str(b), "n_test": len(te)}
            for nm, P_ in pred.items():
                row[f"sse_{nm}"] = float(np.sum((Yt - P_) ** 2)); row[f"peak_err_{nm}"] = float(np.mean(np.abs(Yt.max(1) - P_.max(1))))
                row[f"peakms_err_{nm}"] = float(np.mean(np.abs(tau[Yt.argmax(1)] - tau[P_.argmax(1)])))
            for q in ("epeak", "epeak_ms", "t90_ms"):                         # same quantities as the curve-derived ones
                f = fits.get(f"{ch}__{q}")
                if f is not None:
                    yt = Y[te, FEATS.index(f"{ch}__{q}")]; ok = np.isfinite(yt)
                    row[f"scalar_{q}_abs_err"] = float(np.mean(np.abs(yt[ok] - f.predict(np.asarray(te))[0][ok])))
            out.append(row)
    return out


# ==================================================================================================== D2 driver (final repeats)
D2_REPEATS = (5, 6, 7, 8)
D2_MANIFEST = OUT / "TEMPORAL_PHASE_MANIFEST.json"
D2_CODE = ("src/rc18_temporal.py", "src/rc18_campaign.py", "src/rc18_gp.py", "src/rc18_common.py", "src/rc18_data.py", "src/jdl_temporal_vel.py")
D2_DATA = ("outputs/research_campaign_20261018/opus/temporal/FEATURES.csv", "outputs/research_campaign_20261018/opus/temporal/CURVES.npz",
           "outputs/research_campaign_20261018/opus/temporal/old_feature_emulators.csv", "outputs/research_campaign_20261018/opus/temporal/TEMPORAL_PHASE_PROTOCOL.md")


def _d2_units(kind):
    import src.rc18_campaign as C
    U = {}
    for pop in ("NEW", "OLD"):
        for t in C.tasks(pop, D2_REPEATS):
            for m in ("M0", RICH_T[pop]):
                U[f"{pop}__r{t['repeat']}_f{t['fold']}__{m}__{kind}"] = (pop, t, m)
    return U


def d2_manifest():
    import json
    import src.jdl_stage_m as SMM
    man = {"study": "RC18_TEMPORAL_PHASE", "status": "FROZEN BEFORE ANY FINAL D2 OUTCOME", "written_utc": RC.utc(), "parent_commit": SMM._git("rev-parse", "HEAD"),
           "repeats": list(D2_REPEATS), "features": FEATS, "rich": RICH_T, "units": {k: len(_d2_units(k)) for k in ("features", "curves")},
           "code_sha256": {c: SMM.sha256(SMM.ROOT / c) for c in D2_CODE}, "data_sha256": {c: SMM.sha256(SMM.ROOT / c) for c in D2_DATA}}
    D2_MANIFEST.write_text(json.dumps(man, indent=1), encoding="utf-8"); print(json.dumps(man["units"]))


def d2_check():
    import json
    import src.jdl_stage_m as SMM
    man = json.loads(D2_MANIFEST.read_text(encoding="utf-8"))
    if not SMM._git("log", "--format=%H", "--", str(D2_MANIFEST.relative_to(SMM.ROOT)).replace("\\", "/")):
        raise SystemExit("commit the D2 manifest before any final D2 run")
    for grp in ("code_sha256", "data_sha256"):
        for c, h in man[grp].items():
            if SMM.sha256(SMM.ROOT / c) != h:
                raise SystemExit(f"{c} changed after the D2 freeze")


def d2_work(kind):
    d2_check(); RC.limit_threads(1)
    Fs = {p: feature_table(p) for p in ("NEW", "OLD")}; CV = dict(np.load(OUT / "CURVES.npz")); U = _d2_units(kind)
    def fn(name):
        pop, t, m = U[name]
        if kind == "features":
            return run_features_traj(t, pop, m, Fs[pop])
        return {"rows": curve_models(t, pop, m, Fs[pop], CV), "population": pop, "repeat": t["repeat"], "fold": t["fold"], "model": m}
    d = OUT / "final" / kind
    RC.run_units(list(U), fn, d / "units", d / "locks", d / "failed", log=lambda s: print(s, flush=True))


if __name__ == "__main__":
    step = sys.argv[1]
    if step in ("final-features", "final-curves"):
        d2_work(step.split("-")[1])
    else:
        {"features": features, "emulators": fit_feature_emulators, "manifest": d2_manifest}[step]()
