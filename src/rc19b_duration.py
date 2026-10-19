"""RC19B physical-output workstream: the spike-duration bottleneck (zero vs positive) and a two-part (hurdle) model.

Definition (src/jdl_physical_pilot.summarize): D = vmax_spike_us = sum of the row hold times dt over the valid active-window
rows whose maximum melt velocity exceeds twice the active-window median; S = vmax_spike_logratio = log(p99.9 / median) over
the same rows. D is NaN (not 0) when there are <= 50 valid rows or the median is not positive, so a ZERO means "no valid
active row exceeded 2 x median at the monitor's row resolution". Note p99.9 >= 2 x median implies D > 0.

Hurdle model (all parts learned from paid runs only; the run's own paid record quality enters the positive part as in Q):
  q(x) = P(D > 0 | x)                            two candidates:
     QG3  Week 18 G3 GP classifier on the paid indicator 1[D > 0];
     QS   from the arm's own spike log-ratio predictive N(mu_S, v_S) and a threshold c learned from the paid (S, 1[D > 0])
          pairs (E1-style rule: midpoint if separable, else a 1-D logistic boundary): q = Phi((mu_S - c) / sqrt(v_S));
  m(x)  positive part, a QA-aware GP (M0Q) on the paid positive durations, either on D itself (RAW) or on log D (LOG; then
        E[D | D > 0] = exp(m + v / 2) with v the observation variance clipped at 1 to avoid exponential blow-up);
  E[D | x] = q(x) * E[D | D > 0, x]  (point prediction used for R2);  Var[D | x] = q E[D^2 | +] - E[D | x]^2.
Matched-path replay: on existing RC19 final regression paths the duration prediction is recomputed on the SAME paid prefixes
and the joint 8-output endpoint is re-evaluated with every other output's recorded prediction unchanged.
    python -m src.rc19b_duration audit
"""
from __future__ import annotations

import time
import warnings

import numpy as np
import pandas as pd
from scipy.special import ndtr

import src.rc18_campaign as C
import src.rc18_common as RC
import src.rc19_learn as LN
import src.rc19_pool as P

OUT = RC.ROOT / "outputs" / "research_campaign_20261018" / "opus_rc19b"
REPLAY_ARMS = (("SHQ", "RANDOM"), ("M0Q", "MOIVR"), ("SHQ", "MOIVR"))
VARIANTS = ("QG3_RAW", "QG3_LOG", "QS_RAW", "QS_LOG")


# ======================================================================================== audit (descriptive, all runs)
def audit():
    import json
    M = P.manifest(); S = pd.read_csv(RC.CAMP / "data" / "SUMMARIES.csv").set_index("sim_id").reindex(M.index)
    D, Sr = M.vmax_spike_us, M.vmax_spike_logratio; ok = D.notna()
    dt_us = pd.Series(M.index, index=M.index).str.extract(r"_DT-([0-9pe\-]+)_")[0].str.replace("p", ".").astype(float) * 1e6
    zero = ok & (D == 0); pos = ok & (D > 0)
    rows_above = (D / dt_us).where(pos)
    out = {"valid_duration": int(ok.sum()), "zeros": int(zero.sum()), "zero_share": float(zero.sum() / ok.sum()), "missing_NaN": int((~ok).sum()),
           "zero_share_by_batch(provenance only)": {b: float((zero & (M.source_batch == b)).sum() / (ok & (M.source_batch == b)).sum()) for b in ("OLD", "NEW")},
           "zeros_with_logratio_ge_log2": int((zero & (Sr >= np.log(2))).sum()), "positives_with_logratio_lt_log2": int((pos & (Sr < np.log(2))).sum()),
           "logratio_quantiles_zero": np.nanquantile(Sr[zero], [0, .5, .9, 1]).round(3).tolist(), "logratio_quantiles_positive": np.nanquantile(Sr[pos], [0, .1, .5, 1]).round(3).tolist(),
           "output_interval_DT_us_quantiles": np.nanquantile(dt_us[ok], [0, .5, 1]).round(2).tolist(),
           "positive_duration_in_rows_quantiles": np.nanquantile(rows_above[pos], [0, .1, .25, .5, .9]).round(2).tolist(),
           "positives_with_at_most_2_rows": int((rows_above[pos] <= 2.01).sum()),
           "zero_share_short_records": float((zero & M.short_record).sum() / max(1, (ok & M.short_record).sum())), "short_records_valid": int((ok & M.short_record).sum()),
           "zero_share_by_keyhole_label": {int(k): float((zero & (M.y == k)).sum() / (ok & (M.y == k)).sum()) for k in (0, 1)},
           "active_rows_quantiles_zero_vs_positive": [np.nanquantile(S.vmax__n_rows_active[zero], [.1, .5]).tolist(), np.nanquantile(S.vmax__n_rows_active[pos], [.1, .5]).tolist()]}
    OUT.mkdir(parents=True, exist_ok=True); (OUT / "DURATION_ZERO_AUDIT.json").write_text(json.dumps(out, indent=1), encoding="utf-8"); return out


# ======================================================================================== hurdle components
def _threshold(s, z):
    from sklearn.linear_model import LogisticRegression
    a, b = s[z == 1], s[z == 0]
    if len(a) and len(b) and b.max() < a.min():
        return 0.5 * (b.max() + a.min())
    if len(a) and len(b):
        lr = LogisticRegression(C=1e6, max_iter=5000).fit(s[:, None], z); return float(-lr.intercept_[0] / lr.coef_[0, 0])
    return None


def hurdle_predict(task, rev, Z, test, variant, s_pred=None):
    """E[D|x] and Var[D|x] at the test rows from the paid runs. s_pred = (mean, obs var) of the arm's spike log-ratio at test."""
    import src.week18_engine as E
    paid = rev.paid; Yp = rev.paid_Y(); D = Yp[:, P.TARGETS.index("vmax_spike_us")]; Sv = Yp[:, P.TARGETS.index("vmax_spike_logratio")]
    L = paid[np.isfinite(D[paid])]; ind = (D[L] > 0).astype(int); qkind, pkind = variant.split("_"); info = {}
    if len(L) == 0:
        return np.zeros(len(test)), np.ones(len(test)), {"status": "no_finite_duration"}
    if len(set(ind.tolist())) < 2:
        q = np.full(len(test), float(ind.mean())); info["q"] = "class_rate"
    elif qkind == "QG3":
        y = np.full(len(task["ids"]), -1, int); y[L] = ind
        f = E.fit_learner(("G3", "mlii"), {"X": task["X"], "y": y, "pool": task["pool"], "prior": np.array([], int), "depth": np.full(len(y), np.nan)}, list(L), None, {"kernel": None, "b0": len(L)})
        q = np.asarray(E.proba(f, task["X"][test]), float); info["q"] = "g3"
    else:
        LS = L[np.isfinite(Sv[L])]; c = _threshold(Sv[LS], (D[LS] > 0).astype(int)) if len(LS) else None
        if c is None or s_pred is None:
            q = np.full(len(test), float(ind.mean())); info["q"] = "class_rate"
        else:
            mu, v = s_pred; q = ndtr((np.asarray(mu) - c) / np.sqrt(np.maximum(np.asarray(v), 1e-12))); info["q"] = f"S_threshold {c:.3f}"
    Lp = L[ind == 1]
    if len(Lp) == 0:
        return np.zeros(len(test)), np.zeros(len(test)) + 1e-6, {**info, "pos": "none"}
    yv = D.copy() if pkind == "RAW" else np.where(D > 0, np.log(np.where(D > 0, D, 1.0)), np.nan)
    Ypos = np.full((len(yv), 1), np.nan); Ypos[Lp, 0] = yv[Lp]
    fit = C.fit_model("M0Q", Z, Ypos, Lp, ["pos"], emu=None, short=rev.paid_short()).get("pos") if len(Lp) >= 3 else None
    if fit is None:
        m = np.full(len(test), float(np.mean(yv[Lp]))); vo = np.full(len(test), float(np.var(yv[Lp])) if len(Lp) > 1 else 1.0)
    else:
        m, _, vo = fit.predict(test)
    if pkind == "RAW":
        e1 = np.maximum(m, 0.0); e2 = e1 ** 2 + vo
    else:
        vc = np.minimum(vo, 1.0); e1 = np.exp(m + vc / 2); e2 = np.exp(2 * m + 2 * vc)
    mean = q * e1; var = np.maximum(q * e2 - mean ** 2, 1e-12)
    return mean, var, {**info, "pos_n": int(len(Lp))}


def replay_unit(task, unit, M):
    """Recompute the duration prediction with every hurdle variant on the arm's own paid prefixes (recorded budgets)."""
    Z = P.zstd(task); pos = {s: i for i, s in enumerate(task["ids"])}; paid = [pos[s] for s in unit["paid_ids"]]; test = task["test"]; t0 = time.time(); evals = []
    for e in unit["evals"]:
        b = e["budget"]; rev = P.Reveal(task, M)
        for i in paid[:b]:
            rev.reveal(int(i))
        sp = e["pred"].get("vmax_spike_logratio"); s_pred = None if sp is None else (np.asarray([np.nan if v is None else v for v in sp[0]], float), np.asarray([np.nan if v is None else v for v in sp[1]], float))
        out = {}
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for v in VARIANTS:
                mean, var, info = hurdle_predict(task, rev, Z, test, v, s_pred)
                out[v] = [LN._f32(mean), LN._f32(var)]
        evals.append({"budget": b, "pred": out})
    return {"repeat": task["repeat"], "fold": task["fold"], "model": unit["model"], "acq": unit["acq"], "test_ids": unit["test_ids"], "paid_ids": unit["paid_ids"],
            "evals": evals, "seconds": time.time() - t0}


def loo_r2(f, y):
    """Paid-data self-assessment of one fitted output: closed-form leave-one-out R2 on its own training rows (paid only)."""
    m, _ = LN._loo(f.g, y); return float(1 - np.sum((y - m) ** 2) / max(np.sum((y - y.mean()) ** 2), 1e-12))


def run_reg_b(task, model, acq, bmax, M=None, variant=None, record=None):
    """8-output regression trajectory (RC19 models) that also records the hurdle duration prediction (variant) at every recorded
    budget. acq: RANDOM, MOIVR (RC19) or MOIVRB = MOIVR with output weights w_t = max(0.05, 1 - LOO-R2_t) from the paid data
    (the outputs the learner itself predicts worst get more weight; no evaluation residual is used)."""
    import src.rc19b_final as F
    variant = variant or F.DURATION_VARIANT
    M = P.manifest() if M is None else M; rev = P.Reveal(task, M); Z = LN.design_inputs(task, model); pool, test = task["pool"], task["test"]; ids = task["ids"]
    record = sorted(set(record or range(P.B0, bmax + 1, 4)) | {bmax}); rng = np.random.default_rng([P.SPLIT_SEED, 7, task["repeat"], task["fold"]])
    LN.startup(task, rev); evals = []; t0 = time.time(); wlog = []
    while True:
        b = rev.queries; need = acq != "RANDOM" or b in record
        if need:
            fits = C.fit_model(LN.base(model), Z, rev.paid_Y(), rev.paid, list(P.TARGETS), emu=None, short=rev.paid_short())
        if b in record:
            pr = {}
            for c in P.TARGETS:
                f = fits.get(c); pr[c] = None if f is None else [LN._f32(x) for x in (f.predict(test)[0], f.predict(test)[2])]
            sp = pr.get("vmax_spike_logratio"); s_pred = None if sp is None else (np.asarray(sp[0], float), np.asarray(sp[1], float))
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                hm, hv, hinfo = hurdle_predict(task, rev, Z, test, variant, s_pred)
            pr["vmax_spike_us__hurdle"] = [LN._f32(hm), LN._f32(hv)]
            evals.append({"budget": b, "pred": pr, "hurdle": hinfo})
        if b >= bmax:
            break
        unpaid = np.setdiff1d(pool, rev.paid)
        if acq == "RANDOM":
            nxt = int(rng.choice(unpaid))
        else:
            sub = [c for c in P.TARGETS if fits.get(c) is not None and isinstance(fits[c], C.Fitted)]
            Yp = rev.paid_Y()
            if acq == "MOIVRB":
                w = []
                for c in sub:
                    k = P.TARGETS.index(c); L = rev.paid[np.isfinite(Yp[rev.paid, k])]
                    try:
                        w.append(max(0.05, 1.0 - loo_r2(fits[c], Yp[L, k])))
                    except Exception:
                        w.append(1.0)
                w = np.asarray(w); wlog.append(dict(zip(sub, np.round(w, 3).tolist())))
            else:
                w = np.ones(len(sub))
            sc = np.zeros(len(unpaid))
            for wk, c in zip(w, sub):
                f = fits[c]; s1 = C.mo_ivr({c: f}, [c], Z, rev.paid, unpaid, pool, Yp[:, [P.TARGETS.index(c)]]); sc += wk * s1
            nxt = int(unpaid[int(np.argmax(sc))]) if sub else LN.next_on_path(task, rev)
        rev.reveal(nxt)
    return {"repeat": task["repeat"], "fold": task["fold"], "model": model, "acq": acq, "variant": variant, "paid": rev.order, "paid_ids": [ids[i] for i in rev.order],
            "test_ids": [ids[i] for i in test], "evals": evals, "weights_log": wlog[::4], "seconds": time.time() - t0, "queries": rev.queries}


if __name__ == "__main__":
    import json
    import sys
    if sys.argv[1] == "audit":
        print(json.dumps(audit(), indent=1))
