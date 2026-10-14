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
ARMS = ("V2_EP_mixture", "rho1_EP", "Binary_V2_EP")
SEED = 771


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
    res.update({"hard_checks": hard, "status": "PASS" if all(hard.values()) else "FAIL", "batch_size_m": M_BATCH, "seconds": time.time() - t0,
                "module_sha256": hashlib.sha256((ROOT / "src" / "jdl_v2_decision_audit.py").read_bytes()).hexdigest(),
                "component_solves": 0, "note": "identities and numerical references for the decision computation only; Astra's own INDEPENDENT_CHECKS gate for her acquisition study is separate and is not duplicated here"})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "DECISION_AUDIT_VALIDATION.json").write_text(json.dumps(res, indent=1, default=lambda o: o.tolist() if isinstance(o, np.ndarray) else (o.item() if hasattr(o, "item") else str(o))), encoding="utf-8")
    print(json.dumps({"status": res["status"], "hard_checks": hard}, indent=1))
    return res


# ======================================================================================== manifest / run / evaluate
def _committed(p):
    return bool(SMM._git("log", "--format=%H", "--", str(p.relative_to(ROOT)).replace("\\", "/")))


def write_manifest():
    val = json.loads((OUT / "DECISION_AUDIT_VALIDATION.json").read_text(encoding="utf-8"))
    v2val = json.loads((V2DIR / "validation" / "V2_VALIDATION.json").read_text(encoding="utf-8"))
    if val["status"] != "PASS" or v2val["status"] != "PASS":
        raise SystemExit("decision-rule validation and V2 validation must PASS before the audit is frozen")
    if not (V2DIR / "V2_DECISION.json").exists():
        raise SystemExit("the V2 comparison must be complete (evaluated) first")
    idx = {}
    for f in sorted(EXPORTS.glob("NEW__*.json")):
        side = json.loads(f.read_text(encoding="utf-8")); idx[f.stem] = side["file_sha256"]
    man = {"study": "cached-posterior decision audit of the frozen V2 comparison (decision-only readouts; zero new fits)",
           "status": "FROZEN BEFORE ANY AUDIT DECISION", "written_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "parent_commit": SMM._git("rev-parse", "HEAD"), "source": "outputs/astra_balanced_decision_acquisition/OPUS_DECISION_ACQUISITION_REQUEST.md (first step)",
           "fits": "none; the exported V2 component posteriors of v2_model_comparison (V2_EP_mixture, its rho=1 EP component as rho1_EP, Binary_V2_EP), NEW DEV repeats 1-2, folds 1-5, B16/B40",
           "rules": {r: d for r, d in zip(RULES, ("A_m >= B_m (prospective IID batch, m = 136, fixed fold-pool reference)", "p >= E[pi | D] (same draws)",
                                                  "p >= paid positive fraction", "p >= 0.5"))},
           "target_distribution": "uniform over the fixed fold training-candidate inputs (never the paid subset); a model-based approximation to the eligible feature distribution; may be biased for another deployment population",
           "batch_size_m": M_BATCH, "m_source": "NEW population size from the feature/provenance intake (not its positive count)",
           "numerics": {"QMC": "scrambled Sobol, 4 scrambles, seeds 771 + 1009 s + 37 k, ladder 2^10 -> 2^12 -> 2^14", "accept": f"max signed-margin change <= {ACCEPT_MARGIN_CHANGE} and pi change <= {ACCEPT_PI_CHANGE}",
                        "ambiguous": "|signed margin| <= max(2 SE over scrambles, last margin change); the sign of the estimate is used and the flag reported",
                        "failure": "a checkpoint whose ladder is not accepted is recorded as DECISION_NUMERICAL_STOP for the finite-batch rule; no seed or tolerance change"},
           "protections": ["no held-out label, global label count, short-K or q20 membership, test depth or post-hoc VX cut enters a decision", "probability scores identical across the cutoff readouts (checked against the stored V2 predictions)",
                           "no rule is tuned on these metrics", "not an acquisition or simulation-saving experiment"],
           "metrics": ["pooled-per-repeat BA", "sensitivity", "specificity", "q20 (unchanged)", "short-K sensitivity (10 unique simulations)", "Brier / log loss (rule-independent)", "per-simulation decision changes (full IDs)",
                       "class fractions: model reference prevalence E[pi|D], paid fraction, evaluator-only true fractions (never learner inputs)"],
           "uncertainty": "Stage M class-stratified simulation-cluster bootstrap (2000, seed 20261013), conditional on the stored fits and splits",
           "validation": {"file": "v2_decision_audit/DECISION_AUDIT_VALIDATION.json", "status": val["status"], "sha256": hashlib.sha256((OUT / "DECISION_AUDIT_VALIDATION.json").read_bytes()).hexdigest()},
           "exports_sha256": idx, "code_sha256": {c: SMM.sha256(ROOT / c) for c in ("src/jdl_v2_decision_audit.py", "src/jdl_v2_export.py", "src/jdl_v2_evaluate.py", "src/jdl_evaluate.py", "src/jdl_stage_m.py")},
           "not_authorized": ["acquisition", "Stage A", "C4", "new fits"]}
    (OUT / "DECISION_AUDIT_MANIFEST.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    print(json.dumps({k: man[k] for k in ("status", "written_utc", "batch_size_m")}, indent=1))


def run():
    import src.jdl_v2_export as VX
    man_p = OUT / "DECISION_AUDIT_MANIFEST.json"
    if not man_p.exists() or not _committed(man_p):
        raise SystemExit("commit the decision-audit manifest first")
    man = json.loads(man_p.read_text(encoding="utf-8"))
    for c, h in man["code_sha256"].items():
        if SMM.sha256(ROOT / c) != h:
            raise SystemExit(f"{c} changed after the audit freeze")
    v2pred = pd.read_csv(V2DIR / "predictions_all.csv.gz")
    fits = {}
    for f in (SMM.OUT / "_cache" / "v2").glob("NEW__*.json.gz"):
        r = json.loads(gzip.decompress(f.read_bytes()))["fit"]; fits[(r["repeat"], r["fold"], r["budget"], r["arm"])] = r
    CACHE.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    for rep in (1, 2):
        for fold in range(1, 6):
            for b in (16, 40):
                for arm in ARMS:
                    cf = CACHE / f"NEW__r{rep}_f{fold}__B{b}__{arm}.json.gz"
                    if cf.exists():
                        continue
                    src_arm = "V2_EP_mixture" if arm == "rho1_EP" and not fits[(rep, fold, b, "rho1_EP")].get("export") else arm
                    stem = f"NEW__r{rep}_f{fold}__B{b}__{src_arm}"
                    if man["exports_sha256"].get(stem) is None:
                        raise SystemExit(f"export {stem} missing from the frozen index")
                    arrays, side = VX.load_export(EXPORTS / f"{stem}.npz")
                    if side["file_sha256"] != man["exports_sha256"][stem]:
                        raise SystemExit(f"export {stem} differs from the frozen index")
                    posts, w = VX.components(arrays), arrays["weights"]
                    if arm == "rho1_EP" and src_arm == "V2_EP_mixture":
                        k = int(np.flatnonzero(arrays["rho"] == 1.0)[0]); posts, w = [posts[k]], np.array([1.0])
                    nref = len(arrays["x_ref"])
                    dec = decisions(posts, w, nref)
                    p = sum(wk * ndtr(q["h_mean"] / np.sqrt(TAU ** 2 + np.maximum(np.diag(q["h_cov"]), 0))) for wk, q in zip(w, posts))
                    pt = p[nref:]
                    stored = v2pred[(v2pred.arm == arm) & (v2pred.repeat == rep) & (v2pred.fold == fold) & (v2pred.budget == b)].set_index("sim_id").p
                    test_ids = side["test_ids"]
                    p_diff = float(np.max(np.abs(stored.loc[test_ids].to_numpy() - pt)))
                    pi_hat = fits[(rep, fold, b, arm)]["pi_hat"]
                    rules = {"finite_batch": dec["decision"][nref:], "posterior_mean_pi": pt >= dec["pi_mean"], "paid_fraction": pt >= pi_hat, "cutoff_0.5": pt >= 0.5}
                    rec = {"repeat": rep, "fold": fold, "budget": b, "arm": arm, "export": stem, "m": M_BATCH, "nref": nref, "pi_mean": dec["pi_mean"], "pi_2se": dec["pi_2se"],
                           "paid_fraction": pi_hat, "numerically_accepted": bool(dec["numerically_accepted"]), "history": dec["history"], "bits": dec["bits"],
                           "max_abs_p_minus_stored_prediction": p_diff, "n_ambiguous_test": int(dec["ambiguous"][nref:].sum()),
                           "status": "ok" if dec["numerically_accepted"] else "DECISION_NUMERICAL_STOP"}
                    preds = [{"repeat": rep, "fold": fold, "budget": b, "arm": arm, "sim_id": s, "p": float(pt[j]), "A": float(dec["A"][nref + j]), "B": float(dec["B"][nref + j]),
                              "signed_margin": float(dec["signed_margin"][nref + j]), "margin_2se": float(dec["margin_2se"][nref + j]), "ambiguous": bool(dec["ambiguous"][nref + j]),
                              **{f"d_{r}": bool(v[j]) for r, v in rules.items()}} for j, s in enumerate(test_ids)]
                    cf.write_bytes(gzip.compress(json.dumps({"fit": rec, "predictions": preds}, default=float).encode()))
                    print(rep, fold, b, arm, rec["status"], f"pi_mean {dec['pi_mean']:.3f} paid {pi_hat:.3f} |p-stored| {p_diff:.1e}", flush=True)
    print(f"decision audit: {time.time() - t0:.1f}s, zero fits")


def evaluate():
    from src.jdl_evaluate import boot_weights, population_frame
    recs, preds = [], []
    for f in sorted(CACHE.glob("NEW__*.json.gz")):
        r = json.loads(gzip.decompress(f.read_bytes())); recs.append(r["fit"]); preds += r["predictions"]
    pr, fl = pd.DataFrame(preds), pd.DataFrame(recs)
    tasks = [t for t in SMM.build_tasks() if t["population"] == "NEW"]
    F = population_frame("NEW", tasks); ids, y, sk, VX_ = F["ids"], F["y"], F["shortk"], F["VX"]
    fast = VX_ > SMM.FAST_VX
    W = boot_weights(y); pos = {s: i for i, s in enumerate(ids)}

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

    rows, crow, flips = [], [], []
    for arm in ARMS:
        for b in (16, 40):
            store = {}
            for rep in (1, 2):
                g = pr[(pr.arm == arm) & (pr.budget == b) & (pr.repeat == rep)]
                ii = g.sim_id.map(pos).to_numpy(int)
                p = np.full(len(ids), np.nan); p[ii] = g.p.to_numpy(float)
                for rule in RULES:
                    d = np.zeros(len(ids), bool); d[ii] = g[f"d_{rule}"].to_numpy(bool)
                    store[(rule, rep)] = (p, d)
                    m = metrics(p, d, np.isfinite(p), rep, W[:1])
                    cnt = {"TP": int((d & (y == 1)).sum()), "FN": int((~d & (y == 1)).sum()), "TN": int((~d & (y == 0)).sum()), "FP": int((d & (y == 0)).sum()),
                           "shortK_detected": int((d & sk).sum()), "fast_negatives_rejected": int((~d & (y == 0) & fast).sum()), "fast_positives_detected": int((d & (y == 1) & fast).sum())}
                    rows.append({"arm": arm, "budget": b, "repeat": rep, "rule": rule, **{k: float(v[0]) for k, v in m.items()}, **cnt})
            for rule in RULES[:3]:
                per = []
                for rep in (1, 2):
                    p1, d1 = store[(rule, rep)]; p0, d0 = store[("cutoff_0.5", rep)]
                    av = np.isfinite(p1)
                    m1, m0 = metrics(p1, d1, av, rep, W), metrics(p0, d0, av, rep, W)
                    per.append({k: m1[k] - m0[k] for k in m1})
                    for i in np.flatnonzero(av & (d1 != d0)):
                        flips.append({"arm": arm, "budget": b, "repeat": rep, "rule": rule, "sim_id": ids[i], "label": int(y[i]), "from_cutoff_0.5": bool(d0[i]),
                                      "to_rule": bool(d1[i]), "fast_scan_EVALUATOR_ONLY": bool(fast[i]), "shortK_EVALUATOR_ONLY": bool(sk[i])})
                for k in per[0]:
                    dd = np.nanmean(np.vstack([r[k] for r in per]), axis=0); lo, hi = np.nanpercentile(dd[1:], [2.5, 97.5])
                    crow.append({"arm": arm, "budget": b, "contrast": f"{rule} - cutoff_0.5", "metric": k, "estimate": float(dd[0]),
                                 "per_repeat": json.dumps([float(r[k][0]) for r in per]), "cluster_bootstrap_lo": float(lo), "cluster_bootstrap_hi": float(hi)})
    mt, ct, fp = pd.DataFrame(rows), pd.DataFrame(crow), pd.DataFrame(flips)
    true_frac = {}
    for t in tasks:
        true_frac[(t["repeat"], t["fold"])] = {"EVALUATOR_pool_positive_fraction": float(t["y"][t["pool"]].mean()), "EVALUATOR_test_positive_fraction": float(t["y"][t["test"]].mean())}
    fl["EVALUATOR_pool_positive_fraction"] = [true_frac[(r, f_)]["EVALUATOR_pool_positive_fraction"] for r, f_ in zip(fl.repeat, fl.fold)]
    fl["EVALUATOR_test_positive_fraction"] = [true_frac[(r, f_)]["EVALUATOR_test_positive_fraction"] for r, f_ in zip(fl.repeat, fl.fold)]
    OUT.mkdir(parents=True, exist_ok=True)
    mt.to_csv(OUT / "metrics_per_repeat.csv", index=False, lineterminator="\n"); ct.to_csv(OUT / "rule_contrasts.csv", index=False, lineterminator="\n")
    fp.to_csv(OUT / "decision_changes_by_simulation.csv", index=False, lineterminator="\n"); fl.drop(columns=["history"]).to_csv(OUT / "class_fractions_and_numerics.csv", index=False, lineterminator="\n")
    pr.to_csv(OUT / "decisions_all.csv.gz", index=False, lineterminator="\n", compression={"method": "gzip", "mtime": 0})
    summary = {"checkpoints": len(fl), "numerical_stops": int((fl.status != "ok").sum()), "max_abs_p_minus_stored": float(fl.max_abs_p_minus_stored_prediction.max()),
               "ambiguous_test_decisions": int(fl.n_ambiguous_test.sum()), "probabilities_identical_across_cutoff_rules": True}
    (OUT / "DECISION_AUDIT_SUMMARY.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(mt.groupby(["arm", "budget", "rule"])[["BA", "sensitivity", "specificity", "q20", "shortK_sensitivity", "brier", "log_loss", "TP", "FN", "TN", "FP", "shortK_detected"]].mean().round(3).to_string())
    print(ct[ct.metric.isin(["BA", "sensitivity", "specificity", "shortK_sensitivity", "q20"])].round(4).to_string())
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "validate"
    {"validate": validate, "manifest": write_manifest, "run": run, "evaluate": evaluate}[step]()
