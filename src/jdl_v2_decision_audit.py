"""Cached-posterior decision audit of the frozen V2 comparison fits (Astra's first follow-up; zero new fits).

The four decision-only readouts on the SAME exported V2 posteriors and paths:
  finite_batch       Astra's prospective IID-batch BA rule: positive iff A_m(x) >= B_m(x), with
                       A_m = E[w_m(pi) eta(x) / pi], B_m = E[w_m(pi) (1 - eta(x)) / (1 - pi)], w_m = 1 - pi^m - (1 - pi)^m,
                       eta = Phi(h / tau) and pi = the mean of eta over the fixed fold reference pool, evaluated in the
                       SAME joint posterior draw (component weights, full within-component covariance over
                       [reference pool; test inputs]).  m = 136, the NEW population size known from the feature intake.
  posterior_mean_pi  p >= E[pi | D] (same draws)
  paid_fraction      p >= share of positives among the paid labels
  cutoff_0.5         p >= 0.5
p is the closed-form mixture probability, identical for the three cutoff rules and checked against the stored V2
predictions.  The target is a prospective IID batch under a fixed training-feature reference; it is neither the exact
expected BA of the recorded test panel nor a guarantee for transient (short-K) positives.  No held-out label, global
label count, short-K or q20 membership, test depth or post-hoc VX cut enters any decision.

Integration with a public batch size m (Astra's frozen reference fixes m = 96): src/jdl_v2_decision_audit.py is hashed
separately and must pass the m = 2 / 4 / 96 (and 136) identities in `validate` before any audit.

Version decision-audit-1.1 (correction of 2026-10-14, before the audit was validated, frozen or run; the previous
version is commit a0e3dd67, sha256 4199768b...): checkpoint acceptance safeguards.
  * Every checkpoint is classified before scoring, in this order: INVALID_EXPORT (failed or missing comparison fit,
    export missing from / differing with the frozen index, altered file, inconsistent sidecar, nonfinite or misshaped
    arrays, weights not a probability vector, missing/duplicated/misaligned simulation IDs), PROBABILITY_PARITY_FAILURE
    (the closed-form probability reconstructed from the export differs from the stored V2 prediction by more than
    P_PARITY_TOL = 1e-10 in maximum absolute value, or is nonfinite; declared here before any audit outcome),
    DECISION_NONFINITE (nonfinite QMC coefficients, margins or ladder changes), DECISION_NUMERICAL_STOP (Astra's
    ladder not accepted, or the QMC pass failed, e.g. a non-PSD covariance) or ok.
  * Rule validity: finite_batch and posterior_mean_pi need status ok; paid_fraction and cutoff_0.5 need a valid
    export and probability parity only.  Attempted decisions of every checkpoint are kept with their validity; invalid
    ones are written as failed numerical output and never enter a metric.  Records are written atomically.
  * A pooled-per-repeat readout exists only if all five folds of that repeat are valid for that rule and their test
    sets partition the population; otherwise it is UNAVAILABLE (no surviving-subset metric is reported as the complete
    experiment).  The primary audit (finite_batch on all 20 V2_EP_mixture checkpoints) is COMPLETE only if all 20 are
    ok; otherwise PRIMARY_UNAVAILABLE: `evaluate` writes every output but DECISION_AUDIT_UNAVAILABLE.json in place of
    DECISION_AUDIT_SUMMARY.json (the queue's completion marker) and exits with code 3, so the queue records the step
    as failed.  Unreadable records have the same effect.
  * Summary flags are derived from the checks; ambiguity flags of accepted decisions are kept and are distinct from
    numerical failure.  `validate` runs the safeguard self-tests (synthetic export) as part of its gate.
  * Unchanged: model, exports, decision equations, m, tau, ladder, acceptance thresholds, seeds, metrics, labels,
    bootstrap and success criteria; nothing is retried and no tolerance is relaxed after a failure.
Version decision-audit-1.1.1 (2026-10-14, after queue task T05 failed): the 1.1 `validate` run wrote
DECISION_AUDIT_VALIDATION.json (status PASS, 45 of 45 hard checks) and then crashed with exit code 1 in its console
echo, which passed numpy bools to json.dumps (a line inherited from 1.0).  Only that echo changed (values cast to
bool); no check, tolerance or output field changed.  The 1.1 validation file no longer matches this module's hash, so
`manifest` refuses it and the validation must be re-run before any freeze.

Steps: python -m src.jdl_v2_decision_audit validate | manifest | run | evaluate        (one BLAS thread)
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

import datetime as dt
import gzip
import hashlib
import importlib
import itertools
import json
import sys
import time
import traceback
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from numpy.polynomial.hermite import hermgauss
from scipy.special import log_ndtr, logsumexp, ndtr, ndtri
from scipy.stats import qmc

import src.jdl_stage_m as SMM

ROOT = SMM.ROOT
OUT = SMM.OUT / "v2_decision_audit"
CACHE = SMM.OUT / "_cache" / "decision_audit"
EXPORTS = SMM.OUT / "_cache" / "v2_exports"
V2DIR = SMM.OUT / "v2_model_comparison"
ASTRA_DEC = ROOT / "outputs" / "astra_balanced_decision_acquisition"
M_BATCH = 136                                                        # NEW population size (feature intake), fixed before results
TAU = 0.15
LADDER = ((10,), (12,), (14,))
ACCEPT_MARGIN_CHANGE, ACCEPT_PI_CHANGE = 0.015, 0.003                # Astra's frozen decision ladder
RULES = ("finite_batch", "posterior_mean_pi", "paid_fraction", "cutoff_0.5")
QMC_RULES, CUTOFF_RULES = ("finite_batch", "posterior_mean_pi"), ("paid_fraction", "cutoff_0.5")
ARMS = ("V2_EP_mixture", "rho1_EP", "Binary_V2_EP")
PRIMARY_ARM, PRIMARY_RULE = "V2_EP_mixture", "finite_batch"
DESIGN = {"repeats": (1, 2), "folds": (1, 2, 3, 4, 5), "budgets": (16, 40)}
SEED = 771
AUDIT_VERSION = "decision-audit-1.1.1"                               # 1.1.1: validate's console echo only (see docstring)
P_PARITY_TOL = 1e-10                                                 # declared 2026-10-14 before any audit outcome
EXIT_PRIMARY_UNAVAILABLE = 3


# ======================================================================================== numerics
def batch_coefficients(h, tau, nref, m):
    """a = w_m(pi) eta / pi and b = w_m(pi) (1 - eta) / (1 - pi) per latent draw (last axis = inputs; the first nref
    inputs are the reference).  Log-domain throughout; the larger class probability is recovered from the smaller."""
    if m < 2:
        raise ValueError("a BA batch needs at least two slots")
    lp, ln = log_ndtr(h / tau), log_ndtr(-h / tau)
    lpi = logsumexp(lp[..., :nref], axis=-1) - np.log(nref)
    lpn = logsumexp(ln[..., :nref], axis=-1) - np.log(nref)
    small = np.minimum(lpi, lpn); large = np.log1p(-np.exp(small))
    logp = np.where(lpi <= lpn, small, large); logn = np.where(lpi <= lpn, large, small)
    w = -np.expm1(m * large) - np.exp(m * small)                         # 1 - pi^m - (1 - pi)^m, accurate in both tails
    logw = np.where(w > np.finfo(float).tiny, np.log(np.maximum(w, np.finfo(float).tiny)), np.log(m) + small)
    a = np.exp(lp + logw[..., None] - logp[..., None]); b = np.exp(ln + logw[..., None] - logn[..., None])
    return a, b, np.exp(logp), np.exp(lp)


def geometric_reference(h, tau, nref, m):
    """Independent finite geometric sums w_m(p)/p = sum_{k<m} q^k - p^(m-1) (and class-reversed)."""
    eta, neg = ndtr(h / tau), ndtr(-h / tau)
    p, q = eta[..., :nref].mean(-1), neg[..., :nref].mean(-1)
    gp, gq = np.ones_like(p), np.ones_like(q)
    for _ in range(m - 1):
        gp, gq = 1 + p * gp, 1 + q * gq
    return eta * np.maximum(gq - p ** (m - 1), 0.0)[..., None], neg * np.maximum(gp - q ** (m - 1), 0.0)[..., None]


def _root(C):
    C = (np.asarray(C) + np.asarray(C).T) / 2
    ev = np.linalg.eigvalsh(C)
    if ev.min() < -1e-7:
        raise FloatingPointError(f"covariance not PSD: {ev.min()}")
    reg = max(1e-12, 1e-12 - ev.min())
    return np.linalg.cholesky(C + reg * np.eye(len(C))), float(reg)


def _normals(bits, dim, seed):
    u = qmc.Sobol(dim, scramble=True, seed=int(seed)).random_base2(bits)
    return ndtri(np.clip(u, np.finfo(float).eps, 1 - np.finfo(float).eps))


def decision_pass(posts, weights, nref, m, bits, seed=SEED, scrambles=4, tau=TAU):
    aa, bb, pp, prev, regs = [], [], [], [], []
    roots = [_root(q["h_cov"]) for q in posts]
    n = len(posts[0]["h_mean"])
    for s in range(scrambles):
        A = np.zeros(n); B = np.zeros(n); P = np.zeros(n); pi = 0.0
        for k, (w, q) in enumerate(zip(weights, posts)):
            L, reg = roots[k]; regs.append(reg)
            h = q["h_mean"] + _normals(bits, n, seed + 1009 * s + 37 * k) @ L.T
            a, b, pr, p = batch_coefficients(h, tau, nref, m)
            A += w * a.mean(0); B += w * b.mean(0); P += w * p.mean(0); pi += w * pr.mean()
        aa.append(A); bb.append(B); pp.append(P); prev.append(pi)
    A, B = np.mean(aa, 0), np.mean(bb, 0)
    ss = (np.asarray(aa) - np.asarray(bb)) / (np.asarray(aa) + np.asarray(bb))
    return {"A": A, "B": B, "signed_margin": (A - B) / (A + B), "decision": A >= B, "p_qmc": np.mean(pp, 0), "pi_mean": float(np.mean(prev)),
            "margin_2se": 2 * np.std(ss, axis=0, ddof=1) / np.sqrt(scrambles), "pi_2se": float(2 * np.std(prev, ddof=1) / np.sqrt(scrambles)),
            "bits": bits, "max_covariance_regularization": max(regs)}


def decisions(posts, weights, nref, m=M_BATCH, seed=SEED):
    prev = decision_pass(posts, weights, nref, m, 10, seed)
    hist, cur, dm = [], prev, np.inf
    for (bits,) in LADDER[1:]:
        cur = decision_pass(posts, weights, nref, m, bits, seed)
        dm = float(np.max(np.abs(cur["signed_margin"] - prev["signed_margin"]))); dp = abs(cur["pi_mean"] - prev["pi_mean"])
        hist.append({"bits": bits, "max_margin_change": dm, "pi_change": dp})
        if dm <= ACCEPT_MARGIN_CHANGE and dp <= ACCEPT_PI_CHANGE:
            cur["numerically_accepted"] = True
            break
        prev = cur
    else:
        cur["numerically_accepted"] = False
    cur["history"] = hist
    cur["ambiguous"] = np.abs(cur["signed_margin"]) <= np.maximum(cur["margin_2se"], dm if np.isfinite(dm) else 0.0)
    return cur


# ======================================================================================== validation
def _tensor(order, dim):
    n, w = hermgauss(order); n = n * np.sqrt(2); w = w / np.sqrt(np.pi)
    ids = np.array(list(itertools.product(range(order), repeat=dim)))
    return n[ids], np.prod(w[ids], axis=1)


def _finite_loss(d, y):
    n1 = int(sum(y)); n0 = len(y) - n1
    if min(n1, n0) == 0:
        return 0.5
    return 0.5 * (sum((1 - d[i]) * y[i] for i in range(len(y))) / n1 + sum(d[i] * (1 - y[i]) for i in range(len(y))) / n0)


def validate():
    t0 = time.time()
    res, hard = {}, {}
    g = np.random.default_rng(11)
    # (1) m = 2 closed form
    h = g.normal(0, 2, (50, 12)); a, b, pi, eta = batch_coefficients(h, 1.0, 8, 2)
    res["m2_max_error"] = float(max(np.max(np.abs(a - 2 * (1 - pi)[:, None] * eta)), np.max(np.abs(b - 2 * pi[:, None] * (1 - eta)))))
    hard["m2_identity"] = res["m2_max_error"] <= 1e-12
    # (2) m = 4 exact IID-batch enumeration (Astra's fixture, re-implemented)
    m = 4; v = np.array([.5, .5]); etas = np.array([[.2, .9], [.7, .3]]); post = np.array([.6, .4])
    actions = np.array(list(itertools.product((0, 1), repeat=2))); loss = np.zeros(4)
    for seq in itertools.product(list(itertools.product((0, 1), (0, 1))), repeat=m):
        xx = np.array([s[0] for s in seq]); yy = np.array([s[1] for s in seq])
        prob = sum(w * np.prod(v[xx] * np.where(yy, e[xx], 1 - e[xx])) for w, e in zip(post, etas))
        loss += prob * np.array([_finite_loss(d[xx], yy) for d in actions])
    A4, B4, pi4, _ = batch_coefficients(ndtri(etas), 1.0, 2, m)
    both = 1 - pi4 ** m - (1 - pi4) ** m
    form = np.array([.5 * (1 - post @ both) + .5 * v @ ((post @ A4) * (1 - d) + (post @ B4) * d) for d in actions])
    res["m4_enumeration_max_error"] = float(np.max(np.abs(loss - form)))
    hard["m4_enumeration"] = res["m4_enumeration_max_error"] <= 1e-12
    # (3) m = 96 and 136 against the independent geometric sums, including extreme tails
    errs = {}
    for mm in (96, M_BATCH):
        hh = np.r_[g.normal(0, 1.5, (40, 10)), np.array([[1000.] * 10, [-1000.] * 10, [1000.] * 5 + [-1000.] * 5])]
        a, b, _, _ = batch_coefficients(hh, 1.0, 6, mm); ra, rb = geometric_reference(hh, 1.0, 6, mm)
        errs[mm] = float(max(np.max(np.abs(a - ra)), np.max(np.abs(b - rb)))); hard[f"m{mm}_geometric_identity"] = errs[mm] <= 1e-10 and np.isfinite(a).all() and np.isfinite(b).all()
        hard[f"m{mm}_bounded_by_m"] = bool(max(a.max(), b.max()) <= mm + 1e-9)
    res["geometric_max_error"] = errs
    # (4) parity with Astra's frozen batch_coefficients (repository snapshot; read only), m = 96 and m = 136
    sys.path.insert(0, str(ASTRA_DEC))
    try:
        for name in ("balanced_method", "joint_model_v2", "v1_reference"):
            sys.modules.pop(name, None)
        BM = importlib.import_module("balanced_method")
        hh = g.normal(0, 2, (30, 14)); par = {}
        for mm in (96, M_BATCH):
            a, b, pi, eta = batch_coefficients(hh, TAU, 9, mm); ra, rb, rpi, reta, _ = BM.batch_coefficients(hh, TAU, 9, batch_size=mm)
            par[mm] = float(max(np.max(np.abs(a - ra) / np.maximum(1, np.abs(ra))), np.max(np.abs(b - rb) / np.maximum(1, np.abs(rb))), np.max(np.abs(pi - rpi))))
            hard[f"parity_with_astra_m{mm}"] = par[mm] <= 1e-12
        res["astra_parity_max_rel_error"] = par
        res["astra_balanced_method_sha256"] = hashlib.sha256((ASTRA_DEC / "balanced_method.py").read_bytes()).hexdigest()
    finally:
        sys.path.remove(str(ASTRA_DEC))
        for name in ("balanced_method", "joint_model_v2", "v1_reference"):
            sys.modules.pop(name, None)
    # (5) Gaussian-mixture fixture: QMC decision coefficients against independent tensor quadrature (Astra's tolerance 0.002)
    posts = []
    for mean, scale in (([-.15, .3], 1.0), ([.2, -.1], .7)):
        posts.append({"h_mean": np.asarray(mean), "h_cov": np.array([[.25, .12], [.12, .3]]) * scale})
    wts = np.array([.65, .35]); tau = .6
    fx = {}
    for mm in (96, M_BATCH):
        nodes, ww = _tensor(64, 2)
        A = np.zeros(2); B = np.zeros(2)
        for w, q in zip(wts, posts):
            hq = q["h_mean"] + nodes @ np.linalg.cholesky(q["h_cov"]).T
            ra, rb = geometric_reference(hq, tau, 2, mm)
            A += w * (ww @ ra); B += w * (ww @ rb)
        qd = decision_pass(posts, wts, 2, mm, 14, seed=8201, tau=tau)
        fx[mm] = {"max_A_error": float(np.max(np.abs(qd["A"] - A))), "max_B_error": float(np.max(np.abs(qd["B"] - B))), "decision_agrees": bool(np.array_equal(qd["decision"], A >= B))}
        hard[f"fixture_qmc_accuracy_m{mm}"] = max(fx[mm]["max_A_error"], fx[mm]["max_B_error"]) <= 0.002 and fx[mm]["decision_agrees"]
    res["gaussian_fixture"] = fx
    # (6) known-eta limit: cutoff pi (degenerate posterior = one draw repeated)
    hk = g.normal(0, 1, (1, 10)); a, b, pi, eta = batch_coefficients(hk, 1.0, 7, M_BATCH)
    res["known_eta_cutoff_is_pi"] = bool(np.array_equal(a[0] >= b[0], eta[0] >= pi[0]))
    hard["known_eta_cutoff_is_pi"] = res["known_eta_cutoff_is_pi"]
    # (7) checkpoint acceptance safeguards of decision-audit-1.1 on a synthetic export; an error inside the self-test is
    #     recorded and fails the gate (it never passes silently)
    try:
        sg = safeguard_selftest()
    except Exception as ex:
        sg = {"checks": {"selftest_completed": False}, "error": f"{type(ex).__name__}: {ex}"[:500], "traceback": traceback.format_exc()[-3000:]}
    res["safeguards"] = sg
    hard.update({f"safeguard_{k}": bool(v) for k, v in sg["checks"].items()})
    res.update({"hard_checks": hard, "status": "PASS" if all(hard.values()) else "FAIL", "batch_size_m": M_BATCH, "seconds": time.time() - t0,
                "module_sha256": hashlib.sha256((ROOT / "src" / "jdl_v2_decision_audit.py").read_bytes()).hexdigest(),
                "audit_version": AUDIT_VERSION, "p_parity_tolerance": P_PARITY_TOL, "weight_sum_tolerance": WEIGHT_SUM_TOL,
                "component_solves": 0, "note": "identities and numerical references for the decision computation only; Astra's own INDEPENDENT_CHECKS gate for her acquisition study is separate and is not duplicated here"})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "DECISION_AUDIT_VALIDATION.json").write_text(json.dumps(res, indent=1, default=lambda o: o.tolist() if isinstance(o, np.ndarray) else (o.item() if hasattr(o, "item") else str(o))), encoding="utf-8")
    print(json.dumps({"status": res["status"], "hard_checks": {k: bool(v) for k, v in hard.items()}}, indent=1))   # numpy bools (1.1.1 fix)
    return res


# ======================================================================================== checkpoint acceptance (1.1)
ST_OK, ST_INVALID, ST_PARITY = "ok", "INVALID_EXPORT", "PROBABILITY_PARITY_FAILURE"
ST_NONFINITE, ST_STOP, ST_MISSING, ST_DUPLICATE = "DECISION_NONFINITE", "DECISION_NUMERICAL_STOP", "MISSING_RECORD", "DUPLICATE_RECORD"
WEIGHT_SUM_TOL = 1e-9                                                # export consistency; declared with P_PARITY_TOL
SUMMARY_FILE, UNAVAILABLE_FILE = "DECISION_AUDIT_SUMMARY.json", "DECISION_AUDIT_UNAVAILABLE.json"   # SUMMARY_FILE = queue T08 marker


def checkpoint_name(rep, fold, b, arm):
    return f"NEW__r{rep}_f{fold}__B{b}__{arm}"


def readout_key(arm, b, rep, rule):
    return f"{arm}|B{b}|r{rep}|{rule}"


def rule_validity(status):
    """Readouts a checkpoint may enter: the QMC rules need status ok; the cutoff rules need a valid export and
    probability parity only (their probability is closed form)."""
    return {r: (status == ST_OK) if r in QMC_RULES else (status in (ST_OK, ST_NONFINITE, ST_STOP)) for r in RULES}


def mixture_probability(posts, weights, tau=TAU):
    """Closed-form mixture probability sum_k w_k Phi(mu_k / sqrt(tau^2 + V_k)), the V2 predict_proba formula."""
    return sum(wk * ndtr(q["h_mean"] / np.sqrt(tau ** 2 + np.maximum(np.diag(q["h_cov"]), 0))) for wk, q in zip(weights, posts))


def _json_default(o):
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, np.generic):
        return o.item()
    raise TypeError(f"{type(o).__name__} is not JSON serializable")


def load_checkpoint(rep, fold, b, arm, fits, index, exports=None):
    """Locate and verify the export behind one checkpoint without raising.  Returns the export stem, arrays and sidecar,
    the sidecar metadata the checkpoint requires and, for rho1_EP reused from the mixture, the component to keep; a
    non-empty 'reason' means INVALID_EXPORT."""
    import src.jdl_v2_export as VX
    out = {"stem": None, "arrays": None, "side": None, "expect": None, "component_rho": None, "reason": None}
    rec = fits.get((rep, fold, b, arm))
    if rec is None or rec.get("status") != "ok":
        out["reason"] = "no V2 comparison record" if rec is None else f"V2 comparison record status {rec.get('status')!r}"
        return out
    src_arm = arm
    if arm == "rho1_EP" and not rec.get("export"):
        if not str(rec.get("reused_from") or "").startswith("V2_EP_mixture"):
            out["reason"] = "rho1_EP record has neither its own export nor an exact reuse of the mixture component"
            return out
        src_arm, out["component_rho"] = "V2_EP_mixture", 1.0
    out["stem"] = stem = checkpoint_name(rep, fold, b, src_arm)
    out["expect"] = {"arm": src_arm, "repeat": rep, "fold": fold, "budget": b, "prefix_sha256": rec.get("prefix_sha256")}
    path = Path(EXPORTS if exports is None else exports) / f"{stem}.npz"
    if index.get(stem) is None:
        out["reason"] = "export missing from the frozen index"
    elif not path.exists() or not path.with_suffix(".json").exists():
        out["reason"] = "export file or sidecar missing"
    else:
        try:
            arrays, side = VX.load_export(path)
        except Exception as ex:                                      # recorded SHA-256 or input fingerprint mismatch, unreadable file
            out["reason"] = f"export unreadable or altered: {type(ex).__name__}: {ex}"[:300]
        else:
            if side.get("file_sha256") != index[stem]:
                out["reason"] = "export differs from the frozen index"
            else:
                out["arrays"], out["side"] = arrays, side
    return out


def audit_checkpoint(arrays, side, stored, pi_hat, expect=None, component_rho=None, decide=None, reason=None):
    """Classify and score one checkpoint (no file access).  stored: the stored V2 test predictions of this arm and
    checkpoint, a pd.Series indexed by full simulation ID.  Order: export validity -> probability parity (P_PARITY_TOL)
    -> QMC decisions -> finiteness -> ladder acceptance.  Returns (record, per-test rows); the rows keep every attempted
    decision with its rule validity, so an invalid decision is reported as failed output and never scored."""
    import src.jdl_v2_export as VX
    decide = decide or decisions
    rec = {"status": None, "reason": None, "audit_version": AUDIT_VERSION, "m": M_BATCH, "paid_fraction": pi_hat, "p_parity_tolerance": P_PARITY_TOL,
           "max_abs_p_minus_stored_prediction": None, "parity_pass": False, "numerically_accepted": False, "history": [], "bits": None,
           "pi_mean": None, "pi_2se": None, "nref": None, "n_test": None, "n_ambiguous_test": None, "max_covariance_regularization": None}

    def done(status, why, rows=()):
        rec.update({"status": status, "reason": why, "valid": rule_validity(status)})
        return rec, [{**r, "checkpoint_status": status, **{f"valid_{k}": v for k, v in rec["valid"].items()}} for r in rows]

    if reason is not None or arrays is None or side is None:
        return done(ST_INVALID, reason or "no export")
    try:
        meta_bad = sorted(k for k, v in (expect or {}).items() if side.get(k) != v)
        test_ids = [str(s) for s in side["test_ids"]]
        nref, ntest = len(arrays["x_ref"]), len(arrays["x_eval"])
        posts, w, rho = VX.components(arrays), np.asarray(arrays["weights"], float), np.asarray(arrays["rho"], float)
    except Exception as ex:
        return done(ST_INVALID, f"export arrays or sidecar incomplete: {type(ex).__name__}: {ex}"[:300])
    n, problems = nref + ntest, []
    if meta_bad:
        problems.append(f"sidecar metadata differs from the checkpoint: {meta_bad}")
    if ntest == 0 or len(test_ids) != ntest or len(set(test_ids)) != ntest:
        problems.append("test IDs missing, duplicated or not aligned with the exported inputs")
    if not (len(w) == len(posts) == len(rho) and len(w) > 0):
        problems.append("component arrays inconsistent")
    elif not (np.isfinite(w).all() and (w >= 0).all() and abs(w.sum() - 1) <= WEIGHT_SUM_TOL):
        problems.append("component weights are not a finite probability vector")
    for k, q in enumerate(posts):
        if np.shape(q["h_mean"]) != (n,) or np.shape(q["h_cov"]) != (n, n):
            problems.append(f"component {k}: h mean or covariance has the wrong shape")
        elif not (np.isfinite(q["h_mean"]).all() and np.isfinite(q["h_cov"]).all()):
            problems.append(f"component {k}: nonfinite h mean or covariance")
    if not (isinstance(pi_hat, (int, float)) and np.isfinite(pi_hat) and 0 <= pi_hat <= 1):
        problems.append("paid fraction not in [0, 1]")
    sidx = pd.Index([str(s) for s in stored.index])
    if not sidx.is_unique or set(sidx) != set(test_ids):
        problems.append("test IDs differ from the stored V2 predictions of this checkpoint")
    try:
        spv = np.asarray(stored, float)
    except (TypeError, ValueError):
        spv = None; problems.append("stored V2 predictions are not numeric")
    if component_rho is not None and not problems:
        ks = np.flatnonzero(rho == component_rho)
        if len(ks) != 1:
            problems.append(f"exactly one rho = {component_rho} component expected")
        elif side.get("fallback"):
            problems.append("the reused rho = 1 component comes from a fallback fit")
        else:
            posts, w = [posts[int(ks[0])]], np.array([1.0])
    if problems:
        return done(ST_INVALID, "; ".join(problems))
    # probability parity: the closed-form probability from the export must reproduce the stored V2 prediction
    pt = mixture_probability(posts, w)[nref:]
    sp = pd.Series(spv, index=sidx).loc[test_ids].to_numpy(float)
    diff = np.abs(sp - pt)
    rec.update({"nref": nref, "n_test": ntest, "max_abs_p_minus_stored_prediction": float(np.max(diff))})
    rec["parity_pass"] = bool(np.isfinite(diff).all() and np.max(diff) <= P_PARITY_TOL)
    base = [{"sim_id": s, "p": float(pt[j]), "p_stored": float(sp[j])} for j, s in enumerate(test_ids)]
    if not rec["parity_pass"]:
        return done(ST_PARITY, f"max |p - stored V2 prediction| = {rec['max_abs_p_minus_stored_prediction']:.3e} exceeds {P_PARITY_TOL:g} or is nonfinite", base)
    try:
        dec = decide(posts, w, nref)
    except (FloatingPointError, np.linalg.LinAlgError, ValueError) as ex:
        rows = [{**r, "d_paid_fraction": bool(r["p"] >= pi_hat), "d_cutoff_0.5": bool(r["p"] >= 0.5)} for r in base]
        return done(ST_STOP, f"QMC decision pass failed: {type(ex).__name__}: {ex}"[:300], rows)
    rec.update({"pi_mean": float(dec["pi_mean"]), "pi_2se": float(dec["pi_2se"]), "bits": int(dec["bits"]), "history": dec["history"],
                "numerically_accepted": bool(dec["numerically_accepted"]), "max_covariance_regularization": float(dec["max_covariance_regularization"])})
    amb = np.asarray(dec["ambiguous"])[nref:]
    rec["n_ambiguous_test"] = int(amb.sum())
    rules = {"finite_batch": np.asarray(dec["decision"])[nref:], "posterior_mean_pi": pt >= dec["pi_mean"], "paid_fraction": pt >= pi_hat, "cutoff_0.5": pt >= 0.5}
    rows = [{**r, "A": float(dec["A"][nref + j]), "B": float(dec["B"][nref + j]), "signed_margin": float(dec["signed_margin"][nref + j]),
             "margin_2se": float(dec["margin_2se"][nref + j]), "ambiguous": bool(amb[j]), **{f"d_{k}": bool(v[j]) for k, v in rules.items()}}
            for j, r in enumerate(base)]
    checked = [dec["A"][nref:], dec["B"][nref:], dec["signed_margin"][nref:], dec["margin_2se"][nref:], [dec["pi_mean"], dec["pi_2se"]]]
    checked += [[hh["max_margin_change"], hh["pi_change"]] for hh in dec["history"]]
    if not all(np.isfinite(np.asarray(v, float)).all() for v in checked):
        return done(ST_NONFINITE, "nonfinite QMC coefficients, margins or ladder changes", rows)
    if not rec["numerically_accepted"]:
        return done(ST_STOP, f"ladder not accepted up to 2^{rec['bits']} (needs max margin change <= {ACCEPT_MARGIN_CHANGE} and pi change <= {ACCEPT_PI_CHANGE})", rows)
    return done(ST_OK, None, rows)


def summarize(recs, partition=None):
    """Checkpoint, readout and primary status derived from the checkpoint records (no file access).  A pooled-per-repeat
    readout is AVAILABLE only if all five folds of that repeat are valid for the rule and (when given) the five test sets
    partition the population; the primary is COMPLETE only if all 20 V2_EP_mixture checkpoints are ok."""
    keys = [(r["repeat"], r["fold"], r["budget"], r["arm"]) for r in recs]
    dup = {k for k, c in Counter(keys).items() if c > 1}
    by = dict(zip(keys, recs))
    status = {}
    for arm in ARMS:
        for b in DESIGN["budgets"]:
            for rep in DESIGN["repeats"]:
                for fold in DESIGN["folds"]:
                    k = (rep, fold, b, arm)
                    status[k] = ST_DUPLICATE if k in dup else (by[k]["status"] if k in by else ST_MISSING)
    readouts = {}
    for arm in ARMS:
        for b in DESIGN["budgets"]:
            for rep in DESIGN["repeats"]:
                part = True if partition is None else bool(partition.get((arm, b, rep), False))
                for rule in RULES:
                    bad = [checkpoint_name(rep, f, b, arm) for f in DESIGN["folds"] if not rule_validity(status[(rep, f, b, arm)])[rule]]
                    readouts[readout_key(arm, b, rep, rule)] = {"available": not bad and part, "valid_folds": len(DESIGN["folds"]) - len(bad),
                                                                "invalid_checkpoints": bad, "test_partition_complete": part}
    prim = sorted(k for k in status if k[3] == PRIMARY_ARM)
    prim_bad = [checkpoint_name(*k) for k in prim if status[k] != ST_OK]
    prim_part = all(readouts[readout_key(PRIMARY_ARM, b, rep, PRIMARY_RULE)]["test_partition_complete"] for b in DESIGN["budgets"] for rep in DESIGN["repeats"])
    primary_ok = not prim_bad and prim_part
    all_ok = all(s == ST_OK for s in status.values()) and all(ro["available"] for ro in readouts.values())
    return {"audit_version": AUDIT_VERSION, "audit_status": "COMPLETE" if all_ok else ("PRIMARY_COMPLETE_SECONDARY_UNAVAILABLE" if primary_ok else "PRIMARY_UNAVAILABLE"),
            "exit_code": 0 if primary_ok else EXIT_PRIMARY_UNAVAILABLE,
            "primary": {"arm": PRIMARY_ARM, "rule": PRIMARY_RULE, "checkpoints_expected": len(prim), "checkpoints_ok": len(prim) - len(prim_bad),
                        "invalid_checkpoints": prim_bad, "test_partitions_complete": prim_part, "status": "COMPLETE" if primary_ok else "PRIMARY_UNAVAILABLE"},
            "checkpoints_expected": len(status), "checkpoints_recorded": sum(k in by for k in status),
            "unexpected_records": sorted(checkpoint_name(*k) for k in by if k not in status),
            "status_counts": dict(Counter(status.values())), "numerical_stops": sum(s == ST_STOP for s in status.values()),
            "invalid_checkpoints": {checkpoint_name(*k): s for k, s in sorted(status.items()) if s != ST_OK},
            "p_parity_tolerance": P_PARITY_TOL, "readouts": readouts}


def finalize(summary, out_dir):
    """Write the summary under the queue's completion marker only if the primary audit is complete; otherwise write
    DECISION_AUDIT_UNAVAILABLE.json instead.  Returns the exit code (EXIT_PRIMARY_UNAVAILABLE when unavailable)."""
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    name = SUMMARY_FILE if summary["exit_code"] == 0 else UNAVAILABLE_FILE
    tmp = out_dir / (name + ".tmp")
    tmp.write_text(json.dumps(summary, indent=1, default=_json_default), encoding="utf-8")
    os.replace(tmp, out_dir / name)
    return int(summary["exit_code"])


def _toy_checkpoint(seed=5):
    """Synthetic two-component export (6 reference + 4 test inputs, means far from the decision boundary) and stored
    predictions from the V2 closed form; used only by the safeguard self-tests."""
    import src.jdl_v2_export as VX
    g = np.random.default_rng(seed); nref, ntest = 6, 4; n = nref + ntest
    arrays = {"x_ref": g.uniform(-1, 1, (nref, 2)), "x_eval": g.uniform(-1, 1, (ntest, 2)), "weights": np.array([.7, .3]),
              "log_evidence": np.log([.7, .3]), "rho": np.array([0.0, 1.0])}
    mean = np.r_[[.6, -.6] * 3, [.45, -.45, .3, -.35]]
    for k in range(2):
        L = g.normal(0, .03, (n, n))
        arrays[f"h_mean_{k}"] = mean + g.normal(0, .02, n); arrays[f"h_cov_{k}"] = L @ L.T + .004 * np.eye(n)
        arrays[f"f_mean_{k}"] = np.zeros(n); arrays[f"f_cov_{k}"] = np.eye(n); arrays[f"f_h_cov_{k}"] = np.zeros((n, n)); arrays[f"theta_{k}"] = np.array([0.0, .01])
    ids = [f"TOY-SIM-{j}_H-{seed:02d}{j:08d}" for j in range(ntest)]
    side = {"arm": "V2_EP_mixture", "repeat": 1, "fold": 1, "budget": 16, "prefix_sha256": "toy-prefix", "test_ids": ids, "fallback": False}
    stored = pd.Series(mixture_probability(VX.components(arrays), arrays["weights"])[nref:], index=ids)
    return arrays, side, stored, {k: side[k] for k in ("arm", "repeat", "fold", "budget", "prefix_sha256")}


def _toy_records(change):
    """One status record per design checkpoint (ok unless changed; None = missing)."""
    out = []
    for arm in ARMS:
        for b in DESIGN["budgets"]:
            for rep in DESIGN["repeats"]:
                for fold in DESIGN["folds"]:
                    st = change.get((rep, fold, b, arm), ST_OK)
                    if st is not None:
                        out.append({"repeat": rep, "fold": fold, "budget": b, "arm": arm, "status": st})
    return out


def safeguard_selftest():
    """decision-audit-1.1 safeguards on a synthetic export (no study data, no fit): the valid unchanged case, forced
    ladder failure, non-PSD covariance, nonfinite coefficients, probability mismatch, invalid exports and export files,
    readout and primary availability, and the queue completion marker.  Returns {"checks": {name: bool}, "info": ...}."""
    import tempfile
    import src.jdl_v2_export as VX
    c, info = {}, {}
    arrays, side, stored, expect = _toy_checkpoint()
    nref = len(arrays["x_ref"]); posts, w = VX.components(arrays), arrays["weights"]

    def audit(a=None, s=None, st=None, **kw):
        return audit_checkpoint(arrays if a is None else a, side if s is None else s, stored if st is None else st, 0.5, expect=expect, **kw)

    def copy_arrays():
        return {k: v.copy() for k, v in arrays.items()}

    # valid and unchanged: the same decisions, coefficients and pi as the decision-audit-1.0 computation
    rec, rows = audit()
    dec = decisions(posts, w, nref); pt = mixture_probability(posts, w)[nref:]
    want = {"finite_batch": dec["decision"][nref:], "posterior_mean_pi": pt >= dec["pi_mean"], "paid_fraction": pt >= 0.5, "cutoff_0.5": pt >= 0.5}
    c["valid_case_accepted"] = rec["status"] == ST_OK and all(rec["valid"].values()) and rec["parity_pass"]
    c["valid_case_unchanged"] = (c["valid_case_accepted"] and all(np.array_equal([r[f"d_{k}"] for r in rows], v) for k, v in want.items())
                                 and np.array_equal([r["A"] for r in rows], dec["A"][nref:]) and np.array_equal([r["B"] for r in rows], dec["B"][nref:])
                                 and rec["pi_mean"] == dec["pi_mean"] and rec["n_ambiguous_test"] == int(dec["ambiguous"][nref:].sum()))
    info["valid_case"] = {"status": rec["status"], "bits": rec["bits"], "max_abs_p_minus_stored": rec["max_abs_p_minus_stored_prediction"],
                          "decisions": {k: [bool(x) for x in v] for k, v in want.items()}}

    # forced numerical failure: the ladder is declared not accepted
    def forced_stop(p_, w_, n_):
        d = decisions(p_, w_, n_); d["numerically_accepted"] = False
        return d
    rec, rows = audit(decide=forced_stop)
    c["forced_ladder_failure_is_numerical_stop"] = rec["status"] == ST_STOP
    c["forced_ladder_failure_excludes_only_qmc_rules"] = rec["valid"] == {"finite_batch": False, "posterior_mean_pi": False, "paid_fraction": True, "cutoff_0.5": True}
    c["forced_ladder_failure_keeps_attempted_decisions"] = len(rows) == len(pt) and all(r.get("d_finite_batch") is not None and r["valid_finite_batch"] is False for r in rows)
    # a real numerical failure: indefinite joint covariance with an unchanged diagonal (parity still holds)
    bad = copy_arrays(); cov = bad["h_cov_0"]; cov[0, 1] = cov[1, 0] = 1.5 * np.sqrt(cov[0, 0] * cov[1, 1])
    rec, _ = audit(a=bad)
    c["non_psd_covariance_is_numerical_stop"] = (rec["status"] == ST_STOP and "FloatingPointError" in str(rec["reason"])
                                                 and not rec["valid"]["finite_batch"] and rec["valid"]["cutoff_0.5"])

    def forced_nan(p_, w_, n_):
        d = decisions(p_, w_, n_); d["A"] = np.array(d["A"], float); d["A"][-1] = np.nan
        return d
    rec, _ = audit(decide=forced_nan)
    c["nonfinite_coefficients_flagged"] = rec["status"] == ST_NONFINITE and not rec["valid"]["finite_batch"] and rec["valid"]["cutoff_0.5"]

    # probability parity
    s2 = stored.copy(); s2.iloc[1] += 1e-8
    rec, _ = audit(st=s2)
    c["probability_mismatch_fails_parity"] = rec["status"] == ST_PARITY and not any(rec["valid"].values()) and rec["max_abs_p_minus_stored_prediction"] > P_PARITY_TOL
    s3 = stored.copy(); s3.iloc[1] += 0.5 * P_PARITY_TOL
    c["difference_within_tolerance_accepted"] = audit(st=s3)[0]["status"] == ST_OK
    s4 = stored.copy(); s4.iloc[2] = np.nan
    c["nonfinite_stored_prediction_fails_parity"] = audit(st=s4)[0]["status"] == ST_PARITY

    # invalid exports
    inv = {}
    a = copy_arrays(); a["h_mean_1"][3] = np.nan; inv["nonfinite_h_mean"] = audit(a=a)[0]
    a = copy_arrays(); a["weights"] = np.array([.6, .3]); inv["weights_not_a_probability_vector"] = audit(a=a)[0]
    a = copy_arrays(); a["x_eval"] = a["x_eval"][:3]; inv["inputs_not_aligned_with_test_ids"] = audit(a=a)[0]
    inv["duplicated_test_id"] = audit(s=dict(side, test_ids=[side["test_ids"][0]] * 2 + side["test_ids"][2:]))[0]
    st = stored.copy(); st.index = list(stored.index[:3]) + ["OTHER-SIM_H-0000000000"]; inv["stored_ids_differ"] = audit(st=st)[0]
    inv["sidecar_metadata_differs"] = audit(s=dict(side, fold=2))[0]
    inv["loader_reason"] = audit_checkpoint(None, None, stored, 0.5, expect=expect, reason="export missing from the frozen index")[0]
    for k, r in inv.items():
        c[f"invalid_export_{k}"] = r["status"] == ST_INVALID and not any(r["valid"].values())

    # export files: frozen index, missing or altered files, failed fits and the exact rho = 1 reuse
    with tempfile.TemporaryDirectory() as d:
        d = Path(d); stem = checkpoint_name(1, 1, 16, PRIMARY_ARM)
        sw = VX.save_export(d / f"{stem}.npz", arrays, side)
        pref = {"status": "ok", "prefix_sha256": side["prefix_sha256"], "pi_hat": 0.5}
        fits = {(1, 1, 16, PRIMARY_ARM): dict(pref, export=sw), (1, 1, 16, "rho1_EP"): dict(pref, reused_from="V2_EP_mixture rho=1 EP component (exact; same fit)"),
                (1, 1, 16, "Binary_V2_EP"): {"status": "failed", "error": "synthetic"}}
        index = {stem: sw["file_sha256"]}
        ld = load_checkpoint(1, 1, 16, PRIMARY_ARM, fits, index, d)
        c["file_valid_export_accepted"] = ld["reason"] is None and audit_checkpoint(ld["arrays"], ld["side"], stored, .5, expect=ld["expect"])[0]["status"] == ST_OK
        ld1 = load_checkpoint(1, 1, 16, "rho1_EP", fits, index, d)
        s1 = pd.Series(mixture_probability([posts[1]], [1.0])[nref:], index=side["test_ids"])
        c["file_rho1_reuse_uses_the_rho1_component"] = (ld1["reason"] is None and ld1["stem"] == stem and ld1["component_rho"] == 1.0
                                                       and audit_checkpoint(ld1["arrays"], ld1["side"], s1, .5, expect=ld1["expect"], component_rho=ld1["component_rho"])[0]["status"] == ST_OK)
        c["file_failed_fit_invalid"] = load_checkpoint(1, 1, 16, "Binary_V2_EP", fits, index, d)["reason"] is not None
        c["file_missing_record_invalid"] = load_checkpoint(2, 1, 16, PRIMARY_ARM, fits, index, d)["reason"] is not None
        c["file_not_in_frozen_index_invalid"] = load_checkpoint(1, 1, 16, PRIMARY_ARM, fits, {}, d)["reason"] is not None
        c["file_frozen_hash_mismatch_invalid"] = load_checkpoint(1, 1, 16, PRIMARY_ARM, fits, {stem: "0" * 64}, d)["reason"] is not None
        c["file_missing_export_invalid"] = load_checkpoint(1, 1, 16, PRIMARY_ARM, fits, index, d / "absent")["reason"] is not None
        f = d / f"{stem}.npz"; f.write_bytes(f.read_bytes() + b"\0")
        c["file_altered_export_invalid"] = load_checkpoint(1, 1, 16, PRIMARY_ARM, fits, index, d)["reason"] is not None

    # readout and primary availability
    s_all = summarize(_toy_records({}))
    c["summary_all_ok_complete"] = s_all["audit_status"] == "COMPLETE" and s_all["exit_code"] == 0 and s_all["checkpoints_recorded"] == 60
    s_stop = summarize(_toy_records({(1, 3, 40, PRIMARY_ARM): ST_STOP})); ro = s_stop["readouts"]
    c["summary_primary_stop_unavailable"] = (s_stop["audit_status"] == "PRIMARY_UNAVAILABLE" and s_stop["exit_code"] == EXIT_PRIMARY_UNAVAILABLE
                                             and s_stop["primary"]["invalid_checkpoints"] == [checkpoint_name(1, 3, 40, PRIMARY_ARM)]
                                             and not ro[readout_key(PRIMARY_ARM, 40, 1, "finite_batch")]["available"]
                                             and not ro[readout_key(PRIMARY_ARM, 40, 1, "posterior_mean_pi")]["available"]
                                             and ro[readout_key(PRIMARY_ARM, 40, 1, "cutoff_0.5")]["available"]
                                             and ro[readout_key(PRIMARY_ARM, 40, 2, "finite_batch")]["available"])
    s_sec = summarize(_toy_records({(2, 5, 16, "rho1_EP"): ST_PARITY}))
    c["summary_secondary_failure_keeps_primary"] = (s_sec["audit_status"] == "PRIMARY_COMPLETE_SECONDARY_UNAVAILABLE" and s_sec["exit_code"] == 0
                                                    and not s_sec["readouts"][readout_key("rho1_EP", 16, 2, "cutoff_0.5")]["available"])
    c["summary_missing_primary_record_unavailable"] = summarize(_toy_records({(2, 2, 16, PRIMARY_ARM): None}))["exit_code"] == EXIT_PRIMARY_UNAVAILABLE
    c["summary_duplicate_primary_record_unavailable"] = summarize(_toy_records({}) + _toy_records({})[:1])["exit_code"] == EXIT_PRIMARY_UNAVAILABLE
    part = {(a_, b_, r_): not (a_ == PRIMARY_ARM and b_ == 16 and r_ == 2) for a_ in ARMS for b_ in DESIGN["budgets"] for r_ in DESIGN["repeats"]}
    c["summary_incomplete_test_partition_unavailable"] = summarize(_toy_records({}), part)["exit_code"] == EXIT_PRIMARY_UNAVAILABLE

    # the queue's T08 completion marker is written only for a complete primary audit
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        c["marker_absent_when_primary_unavailable"] = finalize(s_stop, d) == EXIT_PRIMARY_UNAVAILABLE and (d / UNAVAILABLE_FILE).exists() and not (d / SUMMARY_FILE).exists()
        c["marker_written_when_primary_complete"] = finalize(s_all, d / "ok") == 0 and (d / "ok" / SUMMARY_FILE).exists() and not (d / "ok" / UNAVAILABLE_FILE).exists()
    qf = SMM.OUT / "queue" / "QUEUE.json"
    if qf.exists():
        t08 = [t for t in json.loads(qf.read_text(encoding="utf-8"))["tasks"] if t["id"] == "T08_DECISION_EVALUATE"]
        c["queue_T08_marker_is_the_summary_file"] = len(t08) == 1 and Path(t08[0]["done"]["path"]).name == SUMMARY_FILE
    return {"checks": {k: bool(v) for k, v in c.items()}, "info": info, "audit_version": AUDIT_VERSION, "p_parity_tolerance": P_PARITY_TOL}


# ======================================================================================== manifest / run / evaluate
def _committed(p):
    return bool(SMM._git("log", "--format=%H", "--", str(p.relative_to(ROOT)).replace("\\", "/")))


def write_manifest():
    val = json.loads((OUT / "DECISION_AUDIT_VALIDATION.json").read_text(encoding="utf-8"))
    v2val = json.loads((V2DIR / "validation" / "V2_VALIDATION.json").read_text(encoding="utf-8"))
    if val["status"] != "PASS" or v2val["status"] != "PASS":
        raise SystemExit("decision-rule validation and V2 validation must PASS before the audit is frozen")
    if val.get("audit_version") != AUDIT_VERSION or val.get("module_sha256") != SMM.sha256(ROOT / "src" / "jdl_v2_decision_audit.py").lower():
        raise SystemExit("the decision-rule validation was not produced by this module version")
    if not (V2DIR / "V2_DECISION.json").exists():
        raise SystemExit("the V2 comparison must be complete (evaluated) first")
    idx = {}
    for f in sorted(EXPORTS.glob("NEW__*.json")):
        side = json.loads(f.read_text(encoding="utf-8")); idx[f.stem] = side["file_sha256"]
    man = {"study": "cached-posterior decision audit of the frozen V2 comparison (decision-only readouts; zero new fits)",
           "status": "FROZEN BEFORE ANY AUDIT DECISION", "written_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "audit_version": AUDIT_VERSION,
           "parent_commit": SMM._git("rev-parse", "HEAD"), "source": "outputs/astra_balanced_decision_acquisition/OPUS_DECISION_ACQUISITION_REQUEST.md (first step)",
           "fits": "none; the exported V2 component posteriors of v2_model_comparison (V2_EP_mixture, its rho=1 EP component as rho1_EP, Binary_V2_EP), NEW DEV repeats 1-2, folds 1-5, B16/B40",
           "rules": {r: d for r, d in zip(RULES, ("A_m >= B_m (prospective IID batch, m = 136, fixed fold-pool reference)", "p >= E[pi | D] (same draws)",
                                                  "p >= paid positive fraction", "p >= 0.5"))},
           "target_distribution": "uniform over the fixed fold training-candidate inputs (never the paid subset); a model-based approximation to the eligible feature distribution; may be biased for another deployment population",
           "batch_size_m": M_BATCH, "m_source": "NEW population size from the feature/provenance intake (not its positive count)",
           "numerics": {"QMC": "scrambled Sobol, 4 scrambles, seeds 771 + 1009 s + 37 k, ladder 2^10 -> 2^12 -> 2^14", "accept": f"max signed-margin change <= {ACCEPT_MARGIN_CHANGE} and pi change <= {ACCEPT_PI_CHANGE}",
                        "ambiguous": "|signed margin| <= max(2 SE over scrambles, last margin change); the sign of the estimate is used and the flag reported (distinct from numerical failure)",
                        "failure": "a checkpoint whose ladder is not accepted or whose QMC decision pass fails is DECISION_NUMERICAL_STOP; nonfinite coefficients, margins or ladder changes are DECISION_NONFINITE; their finite_batch and posterior_mean_pi decisions are kept as failed output and never scored; no seed, ladder or tolerance change and no retry"},
           "acceptance": {"order": "export validity -> probability parity -> QMC decisions -> finiteness -> ladder acceptance",
                          "p_parity_tolerance": P_PARITY_TOL, "p_parity_definition": "max over test inputs of |closed-form mixture probability from the export - stored V2 prediction|; all values finite",
                          "weight_sum_tolerance": WEIGHT_SUM_TOL,
                          "statuses": {ST_OK: "valid for all four rules", ST_INVALID: "missing, altered or inconsistent export, failed fit, or missing/duplicated/misaligned simulation IDs: no rule",
                                       ST_PARITY: "export probabilities differ from the stored V2 predictions: no rule", ST_NONFINITE: "cutoff rules only", ST_STOP: "cutoff rules only"},
                          "readout": "a pooled-per-repeat readout is AVAILABLE only if all five folds are valid for that rule and the five test sets partition the NEW population; otherwise UNAVAILABLE (no surviving-subset metric)",
                          "contrast": "a rule - cutoff_0.5 contrast needs both readouts available in both repeats",
                          "primary": f"{PRIMARY_RULE} on all 20 {PRIMARY_ARM} checkpoints (2 repeats x 5 folds x B16/B40); COMPLETE only if all 20 are ok, otherwise PRIMARY_UNAVAILABLE",
                          "unavailable_primary": f"evaluate writes {UNAVAILABLE_FILE} instead of {SUMMARY_FILE} (the queue's T08 completion marker) and exits with code {EXIT_PRIMARY_UNAVAILABLE}",
                          "correction_record": "v2_decision_audit/SAFEGUARD_CORRECTION.md"},
           "protections": ["no held-out label, global label count, short-K or q20 membership, test depth or post-hoc VX cut enters a decision",
                           f"probability parity enforced per checkpoint (max absolute difference <= {P_PARITY_TOL:g}); the three cutoff rules use that single probability vector",
                           "no rule is tuned on these metrics", "not an acquisition or simulation-saving experiment"],
           "metrics": ["pooled-per-repeat BA", "sensitivity", "specificity", "q20 (unchanged)", "short-K sensitivity (10 unique simulations)", "Brier / log loss (rule-independent)", "per-simulation decision changes (full IDs)",
                       "class fractions: model reference prevalence E[pi|D], paid fraction, evaluator-only true fractions (never learner inputs)"],
           "uncertainty": "Stage M class-stratified simulation-cluster bootstrap (2000, seed 20261013), conditional on the stored fits and splits",
           "validation": {"file": "v2_decision_audit/DECISION_AUDIT_VALIDATION.json", "status": val["status"], "sha256": hashlib.sha256((OUT / "DECISION_AUDIT_VALIDATION.json").read_bytes()).hexdigest()},
           "exports_sha256": idx, "code_sha256": {c: SMM.sha256(ROOT / c) for c in ("src/jdl_v2_decision_audit.py", "src/jdl_v2_export.py", "src/jdl_v2_evaluate.py", "src/jdl_evaluate.py", "src/jdl_stage_m.py")},
           "not_authorized": ["acquisition", "Stage A", "C4", "new fits"]}
    (OUT / "DECISION_AUDIT_MANIFEST.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    print(json.dumps({k: man[k] for k in ("status", "written_utc", "audit_version", "batch_size_m")}, indent=1))


def run():
    man_p = OUT / "DECISION_AUDIT_MANIFEST.json"
    if not man_p.exists() or not _committed(man_p):
        raise SystemExit("commit the decision-audit manifest first")
    man = json.loads(man_p.read_text(encoding="utf-8"))
    for c, h in man["code_sha256"].items():
        if SMM.sha256(ROOT / c) != h:
            raise SystemExit(f"{c} changed after the audit freeze")
    if man.get("audit_version") != AUDIT_VERSION or man.get("acceptance", {}).get("p_parity_tolerance") != P_PARITY_TOL:
        raise SystemExit("the frozen manifest does not declare this audit version and parity tolerance")
    v2pred = pd.read_csv(V2DIR / "predictions_all.csv.gz", dtype={"sim_id": str})
    fits = {}
    for f in (SMM.OUT / "_cache" / "v2").glob("NEW__*.json.gz"):
        r = json.loads(gzip.decompress(f.read_bytes()))["fit"]; fits[(r["repeat"], r["fold"], r["budget"], r["arm"])] = r
    partial = CACHE / "_partial"                                     # records are written here and moved atomically
    partial.mkdir(parents=True, exist_ok=True)
    t0, counts = time.time(), Counter()
    for rep in DESIGN["repeats"]:
        for fold in DESIGN["folds"]:
            for b in DESIGN["budgets"]:
                for arm in ARMS:
                    name = checkpoint_name(rep, fold, b, arm); cf = CACHE / f"{name}.json.gz"
                    if cf.exists():
                        continue
                    ld = load_checkpoint(rep, fold, b, arm, fits, man["exports_sha256"])
                    stored = v2pred[(v2pred.arm == arm) & (v2pred.repeat == rep) & (v2pred.fold == fold) & (v2pred.budget == b)].set_index("sim_id").p
                    pi_hat = (fits.get((rep, fold, b, arm)) or {}).get("pi_hat")
                    rec, preds = audit_checkpoint(ld["arrays"], ld["side"], stored, pi_hat, expect=ld["expect"], component_rho=ld["component_rho"], reason=ld["reason"])
                    rec.update({"repeat": rep, "fold": fold, "budget": b, "arm": arm, "checkpoint": name, "export": ld["stem"]})
                    preds = [{"repeat": rep, "fold": fold, "budget": b, "arm": arm, **r} for r in preds]
                    tmp = partial / cf.name
                    tmp.write_bytes(gzip.compress(json.dumps({"fit": rec, "predictions": preds}, default=_json_default).encode()))
                    os.replace(tmp, cf)
                    counts[rec["status"]] += 1
                    msg = f"{name} {rec['status']}"
                    if rec["max_abs_p_minus_stored_prediction"] is not None:
                        msg += f" |p-stored| {rec['max_abs_p_minus_stored_prediction']:.1e}"
                    if rec["pi_mean"] is not None:
                        msg += f" pi_mean {rec['pi_mean']:.3f} paid {pi_hat:.3f}"
                    if rec["reason"]:
                        msg += f" ({rec['reason']})"
                    print(msg, flush=True)
    print(f"decision audit: {time.time() - t0:.1f}s, zero fits; checkpoint statuses written in this session: {dict(counts)}")


def evaluate():
    from src.jdl_evaluate import boot_weights, population_frame
    recs, preds, unreadable = [], [], []
    for f in sorted(CACHE.glob("NEW__*.json.gz")):
        try:
            r = json.loads(gzip.decompress(f.read_bytes()))
            if r["fit"].get("audit_version") != AUDIT_VERSION or r["fit"].get("checkpoint") != f.name[:-len(".json.gz")]:
                raise ValueError("record version or checkpoint name does not match")
        except Exception as ex:
            unreadable.append(f"{f.name}: {type(ex).__name__}: {ex}"[:200]); continue
        recs.append(r["fit"]); preds += r["predictions"]
    pr = pd.DataFrame(preds) if preds else pd.DataFrame(columns=["repeat", "fold", "budget", "arm", "sim_id", "p"])
    tasks = [t for t in SMM.build_tasks() if t["population"] == "NEW"]
    F = population_frame("NEW", tasks); ids, y, sk, VX_ = F["ids"], F["y"], F["shortk"], F["VX"]
    fast = VX_ > SMM.FAST_VX
    W = boot_weights(y); pos = {s: i for i, s in enumerate(ids)}
    # the five fold test sets of every (arm, budget, repeat) must cover the NEW population exactly once
    partition = {}
    for arm in ARMS:
        for b in DESIGN["budgets"]:
            for rep in DESIGN["repeats"]:
                s_ = pr[(pr.arm == arm) & (pr.budget == b) & (pr.repeat == rep)].sim_id.tolist()
                partition[(arm, b, rep)] = len(s_) == len(ids) and set(s_) == set(ids)
    S = summarize(recs, partition)

    def metrics(p, d, avail, rep, Wm):
        av = avail.astype(float); dd = np.where(avail, d, 0).astype(float)
        P, N = av * (y == 1), av * (y == 0)
        sens = (Wm @ (P * dd)) / (Wm @ P); spec = (Wm @ (N * (1 - dd))) / (Wm @ N)
        skm = av * sk; correct = (dd == y).astype(float); accs = []
        for f_ in range(1, 6):
            mm = av * F["q20"][rep] * (F["fold"][rep] == f_)
            if mm.sum():
                accs.append((Wm @ (mm * correct)) / (Wm @ mm))
        pe = np.where(avail, p, 0.5); pc = np.clip(pe, 1e-12, 1 - 1e-12)
        return {"BA": 0.5 * (sens + spec), "sensitivity": sens, "specificity": spec, "shortK_sensitivity": (Wm @ (skm * dd)) / (Wm @ skm),
                "q20": np.nanmean(np.vstack(accs), axis=0), "brier": (Wm @ (av * (pe - y) ** 2)) / (Wm @ av),
                "log_loss": (Wm @ (av * -(y * np.log(pc) + (1 - y) * np.log(1 - pc)))) / (Wm @ av)}

    names = ("BA", "sensitivity", "specificity", "shortK_sensitivity", "q20", "brier", "log_loss")
    rows, crow, flips, store = [], [], [], {}
    for arm in ARMS:
        for b in DESIGN["budgets"]:
            for rep in DESIGN["repeats"]:
                g = pr[(pr.arm == arm) & (pr.budget == b) & (pr.repeat == rep)]
                for rule in RULES:
                    ro = S["readouts"][readout_key(arm, b, rep, rule)]
                    head = {"arm": arm, "budget": b, "repeat": rep, "rule": rule, "availability": "AVAILABLE" if ro["available"] else "UNAVAILABLE",
                            "valid_folds": ro["valid_folds"], "invalid_checkpoints": ";".join(ro["invalid_checkpoints"])}
                    if not ro["available"]:
                        rows.append({**head, **{k: np.nan for k in names}}); continue
                    if not (g[f"valid_{rule}"] == True).all():           # noqa: E712 (object column)
                        raise SystemExit(f"internal inconsistency: {readout_key(arm, b, rep, rule)} available with an invalid decision")
                    ii = g.sim_id.map(pos).to_numpy(int)
                    p = np.full(len(ids), np.nan); p[ii] = g.p.to_numpy(float)
                    d = np.zeros(len(ids), bool); d[ii] = (g[f"d_{rule}"] == True).to_numpy(bool)   # noqa: E712
                    store[(arm, b, rule, rep)] = (p, d)
                    m = metrics(p, d, np.isfinite(p), rep, W[:1])
                    cnt = {"TP": int((d & (y == 1)).sum()), "FN": int((~d & (y == 1)).sum()), "TN": int((~d & (y == 0)).sum()), "FP": int((d & (y == 0)).sum()),
                           "shortK_detected": int((d & sk).sum()), "fast_negatives_rejected": int((~d & (y == 0) & fast).sum()), "fast_positives_detected": int((d & (y == 1) & fast).sum())}
                    rows.append({**head, **{k: float(v[0]) for k, v in m.items()}, **cnt})
            for rule in RULES[:3]:
                con = f"{rule} - cutoff_0.5"
                if not all((arm, b, r_, rep) in store for r_ in (rule, "cutoff_0.5") for rep in DESIGN["repeats"]):
                    crow += [{"arm": arm, "budget": b, "contrast": con, "metric": k, "availability": "UNAVAILABLE", "estimate": np.nan} for k in names]
                    continue
                per = []
                for rep in DESIGN["repeats"]:
                    p1, d1 = store[(arm, b, rule, rep)]; p0, d0 = store[(arm, b, "cutoff_0.5", rep)]
                    av = np.isfinite(p1)
                    m1, m0 = metrics(p1, d1, av, rep, W), metrics(p0, d0, av, rep, W)
                    per.append({k: m1[k] - m0[k] for k in m1})
                    for i in np.flatnonzero(av & (d1 != d0)):
                        flips.append({"arm": arm, "budget": b, "repeat": rep, "rule": rule, "sim_id": ids[i], "label": int(y[i]), "from_cutoff_0.5": bool(d0[i]),
                                      "to_rule": bool(d1[i]), "fast_scan_EVALUATOR_ONLY": bool(fast[i]), "shortK_EVALUATOR_ONLY": bool(sk[i])})
                for k in per[0]:
                    dd = np.nanmean(np.vstack([r[k] for r in per]), axis=0); lo, hi = np.nanpercentile(dd[1:], [2.5, 97.5])
                    crow.append({"arm": arm, "budget": b, "contrast": con, "metric": k, "availability": "AVAILABLE", "estimate": float(dd[0]),
                                 "per_repeat": json.dumps([float(r[k][0]) for r in per]), "cluster_bootstrap_lo": float(lo), "cluster_bootstrap_hi": float(hi)})
    mt, ct, fp, fl = pd.DataFrame(rows), pd.DataFrame(crow), pd.DataFrame(flips), pd.DataFrame(recs)
    if len(fl):
        true_frac = {(t["repeat"], t["fold"]): (float(t["y"][t["pool"]].mean()), float(t["y"][t["test"]].mean())) for t in tasks}
        fl["EVALUATOR_pool_positive_fraction"] = [true_frac[(r, f_)][0] for r, f_ in zip(fl.repeat, fl.fold)]
        fl["EVALUATOR_test_positive_fraction"] = [true_frac[(r, f_)][1] for r, f_ in zip(fl.repeat, fl.fold)]
        for col in ("history", "valid"):
            fl[col] = fl[col].map(json.dumps)
    # derived flags: parity on every design checkpoint, and the cutoff decisions recomputed from the single p column
    by = {(r["repeat"], r["fold"], r["budget"], r["arm"]): r for r in recs}
    recomputed = True
    if len(pr) and "checkpoint_status" in pr.columns:
        for key, g in pr.groupby(["repeat", "fold", "budget", "arm"]):
            r = by.get(tuple(key))
            if r is None:
                recomputed = False; continue
            p = g.p.to_numpy(float)
            if r["valid"]["cutoff_0.5"]:
                recomputed &= bool(np.array_equal((g["d_cutoff_0.5"] == True).to_numpy(bool), p >= 0.5)            # noqa: E712
                                   and np.array_equal((g["d_paid_fraction"] == True).to_numpy(bool), p >= r["paid_fraction"]))   # noqa: E712
            if r["valid"]["posterior_mean_pi"]:
                recomputed &= bool(np.array_equal((g["d_posterior_mean_pi"] == True).to_numpy(bool), p >= r["pi_mean"]))   # noqa: E712
    diffs = [r["max_abs_p_minus_stored_prediction"] for r in recs if r["max_abs_p_minus_stored_prediction"] is not None]
    parity_all = S["checkpoints_recorded"] == S["checkpoints_expected"] and not unreadable and all(r["parity_pass"] for r in recs)
    S.update({"unreadable_records": unreadable, "max_abs_p_minus_stored": float(np.max(diffs)) if diffs else None,
              "probability_parity_pass_all_checkpoints": bool(parity_all), "cutoff_decisions_recomputed_from_p": bool(recomputed),
              "probabilities_identical_across_cutoff_rules": bool(parity_all and recomputed),
              "ambiguous_test_decisions_accepted": int(sum(r["n_ambiguous_test"] or 0 for r in recs if r["status"] == ST_OK)),
              "ambiguous_test_decisions_all_attempted": int(sum(r["n_ambiguous_test"] or 0 for r in recs))})
    if unreadable:                                                   # an unreadable record is never ignored
        S.update({"audit_status": "UNREADABLE_RECORDS", "exit_code": EXIT_PRIMARY_UNAVAILABLE})
    OUT.mkdir(parents=True, exist_ok=True)
    mt.to_csv(OUT / "metrics_per_repeat.csv", index=False, lineterminator="\n"); ct.to_csv(OUT / "rule_contrasts.csv", index=False, lineterminator="\n")
    fp.to_csv(OUT / "decision_changes_by_simulation.csv", index=False, lineterminator="\n"); fl.to_csv(OUT / "class_fractions_and_numerics.csv", index=False, lineterminator="\n")
    pr.to_csv(OUT / "decisions_all.csv.gz", index=False, lineterminator="\n", compression={"method": "gzip", "mtime": 0})
    code = finalize(S, OUT)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    cols = ["BA", "sensitivity", "specificity", "q20", "shortK_sensitivity", "brier", "log_loss", "TP", "FN", "TN", "FP", "shortK_detected"]
    print(mt.groupby(["arm", "budget", "rule"])[[c_ for c_ in cols if c_ in mt.columns]].agg(lambda s: s.mean(skipna=False)).round(3).to_string())
    print(ct[ct.metric.isin(["BA", "sensitivity", "specificity", "shortK_sensitivity", "q20"])].round(4).to_string())
    print(json.dumps({k: v for k, v in S.items() if k != "readouts"}, indent=1, default=_json_default))
    if code:
        print(f"{S['audit_status']}: {UNAVAILABLE_FILE} written instead of {SUMMARY_FILE}; exit code {code}", flush=True)
        raise SystemExit(code)


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "validate"
    {"validate": validate, "manifest": write_manifest, "run": run, "evaluate": evaluate}[step]()
