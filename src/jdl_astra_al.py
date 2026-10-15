"""ASTRA_AL: Astra's real-data sequential acquisition comparison (her previously unexecuted DEV 3-4 policy draft in
outputs/astra_balanced_decision_acquisition/OPUS_DECISION_ACQUISITION_REQUEST.md; owner authorization of 2026-10-15).

EXPLORATORY development on previously inspected simulations, not confirmation.  NEW, DEV repeats 3-4, folds 1-5, the frozen
feature-only B16 starts (stage_a/stage_a_paths_NEW_r3_r4.csv), budgets B16-B24 (eight sequential queries).  Three selectors with
the SAME delivered model, decision and paid outputs:
  model      her joint_model_v2.JointModelV2 (byte-identical snapshot), Stage M priors, rho in {0, .5, 1} with prior 1/3,
             EP with whole-mixture Laplace fallback; inputs log-standardised on the fold pool
  decision   finite-batch BA rule A_m >= B_m with m = 136 (NEW size), uniform reference over the fold pool; decision passes
             at the accepted A1 integration level (src.jdl_v2_decision_audit_a1.decisions_a1: 2^10 -> ... -> 2^16, accept
             when max signed-margin change <= 0.015 and pi change <= 0.003)
  BA_RISK         her paired-output expected reduction in optimised finite-batch BA loss (balanced_method.select_risk,
                  re-expressed with m = 136 and checked against her code at m = 96): ladder (8,9) -> (10,17) -> (12,33);
                  accept when max(order difference, 2 SE) <= 0.002, low-ESS outcome mass <= 0.002, tower discrepancy
                  <= 0.002 and normalisation error <= 1e-8; ties within the error go to the smallest pool index
  V2_VARIANCE     her integrated-probability-variance lookahead (balanced_method.select_variance, unchanged)
  ALIGNED_MARGIN  minimum |A_m - B_m| / (A_m + B_m) over the candidates (balanced_method.select_margin, unchanged)
Future-response availability in both lookaheads: alpha = (paid responses + 1) / (paid simulations + 2) at each budget (a
paid-evidence availability model frozen here; never the synthetic 0.75).  Seeds (her formulas with the real task seed
s = 6000 + 100 r + f): decisions 91000 + s + 101 b, risk 20000 + s + 101 b.
A numerical stop (decision or selector) ends the trajectory and is preserved; no criterion is relaxed, no fallback to another
selector.  The B16 fit and decisions are deterministic and identical for the three arms; they are executed in every unit
(executed fits and component solves are reported separately from the 270 logical requests).  Caps (her draft): 270
top-level requests, 900 component solves including fallback; the solve cap is enforced before every fit (cap_ok: recorded
solves + a worst-case 6-solve fit per active unit <= 900), and a refused fit ends that trajectory with CAP_STOP (preserved).
Per-budget atomic state (temp file in tmp/ + os.replace) makes every trajectory resumable; workers claim units with O_EXCL locks.
Steps: python -m src.jdl_astra_al validate | manifest | work [--arms A,B] [--max-units k] | status   (one BLAS thread per worker)
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

import datetime as dt
import gzip
import hashlib
import json
import sys
import time
import traceback
from dataclasses import asdict
from pathlib import Path

import numpy as np
from scipy.special import logsumexp, ndtr

import src.jdl_model as JM
import src.jdl_stage_m as SMM
import src.jdl_trained_al as TA
import src.jdl_v2_decision_audit as DA
import src.jdl_v2_decision_audit_a1 as A1

STUDY = "ASTRA_AL"
ASTRA_DIR = SMM.ROOT / "outputs" / "astra_balanced_decision_acquisition"
OUT = SMM.OUT / "astra_al"
CACHE = SMM.OUT / "_cache" / "astra_al"
MANIFEST = OUT / "ASTRA_AL_MANIFEST.json"
VALIDATION = OUT / "ASTRA_AL_VALIDATION.json"
ARMS = ("ALIGNED_MARGIN", "V2_VARIANCE", "BA_RISK")          # cheap arms first: their units are claimed first
REPEATS, FOLDS, B_START, B_END = (3, 4), (1, 2, 3, 4, 5), 16, 24
M_BATCH = DA.M_BATCH
CAPS = {"top_level_requests": 270, "component_solves_including_fallback": 900}
CODE = ("src/jdl_astra_al.py", "src/jdl_astra_al_eval.py", "src/jdl_v2_decision_audit_a1.py", "src/jdl_v2_decision_audit.py", "src/jdl_trained_al.py",
        "src/jdl_trained_al_eval.py", "src/jdl_evaluate.py", "src/jdl_stage_m.py", "src/jdl_model.py")
ASTRA_SOURCES = ("balanced_method.py", "joint_model_v2.py", "v1_reference.py")


def astra():
    """Import Astra's delivered modules from the byte-identical snapshot, after checking them against her manifest."""
    man = json.loads((ASTRA_DIR / "MANIFEST.json").read_text(encoding="utf-8"))["source_sha256"]
    for n in ASTRA_SOURCES:
        if hashlib.sha256((ASTRA_DIR / n).read_bytes()).hexdigest() != man[n]:
            raise SystemExit(f"{n} differs from Astra's frozen manifest")
    if str(ASTRA_DIR) not in sys.path:
        sys.path.insert(0, str(ASTRA_DIR))
    import balanced_method as BM
    import joint_model_v2 as AV2
    import v1_reference as V1
    return BM, AV2, V1


def config():
    _, _, V1 = astra()
    return V1.Config(**asdict(JM.STAGE_M_CONFIG))


def task_seed(r, f):
    return 6000 + 100 * r + f


# ======================================================================================== m-parameterised copies of her risk acquisition
def candidate_table(BM, posts, mixture, j, tau, noise, bits, order, seed, observe_depth, m):
    """balanced_method._candidate_table with an explicit future-batch size m (identical arithmetic; parity-checked at m = 96)."""
    nr = len(posts[0]['h_mean']); M = 2 ** bits
    mf = np.array([p['f_mean'][j] for p in posts])
    vz = np.array([max(p['f_cov'][j, j], 0) + noise ** 2 for p in posts])
    if observe_depth:
        nodes, ww = BM.gh(order)
        z = (mf[:, None] + np.sqrt(vz[:, None]) * nodes).ravel()
        zw = (mixture[:, None] * ww).ravel()
        logw = np.log(mixture)[:, None] - .5 * (np.log(2 * np.pi * vz)[:, None] + (z - mf[:, None]) ** 2 / vz[:, None])
        wk = np.exp(logw - logsumexp(logw, axis=0))
    else:
        z, zw = np.array([0.]), np.array([1.]); wk = mixture[:, None]
    nz = len(z)
    A = np.zeros((nz, 2, nr)); B = A.copy()
    mass = np.zeros((nz, 2)); squares = mass.copy(); maxreg = 0.
    for k, p in enumerate(posts):
        C = p['h_cov'].copy(); mu = np.broadcast_to(p['h_mean'], (nz, nr)).copy()
        if observe_depth:
            cross = p['f_h_cov'][j]
            C -= np.outer(cross, cross) / vz[k]
            mu += (z - mf[k])[:, None] * cross[None, :] / vz[k]
        L, reg = BM.root(C); maxreg = max(maxreg, reg)
        eps = BM.normal_points(bits, nr, seed + 37 * k) @ L.T
        for lo in range(0, nz, 12):
            hi = min(nz, lo + 12)
            h = mu[lo:hi, None, :] + eps[None, :, :]
            a, b, _, eta, _ = BM.batch_coefficients(h, tau, nr, batch_size=m)
            q = eta[:, :, j]
            for y, prob in ((0, ndtr(-h[:, :, j] / tau)), (1, q)):
                weight = wk[k, lo:hi]
                A[lo:hi, y] += weight[:, None] * np.mean(a * prob[:, :, None], axis=1)
                B[lo:hi, y] += weight[:, None] * np.mean(b * prob[:, :, None], axis=1)
                mass[lo:hi, y] += weight * prob.mean(1)
                squares[lo:hi, y] += weight ** 2 * np.mean(prob ** 2, axis=1) / M
    basea = np.einsum('z,zyi->i', zw, A); baseb = np.einsum('z,zyi->i', zw, B)
    base = .5 * np.minimum(basea, baseb).mean()
    after = .5 * np.einsum('z,zyi->', zw, np.minimum(A, B)) / nr
    ess = np.divide(mass ** 2, squares, out=np.zeros_like(mass), where=squares > 0)
    low_mass = float(np.sum(zw[:, None] * mass * (ess < 32)))
    return {'score': float(base - after), 'base_risk': float(base), 'after_risk': float(after), 'a': basea, 'b': baseb, 'ess_min': float(ess.min()),
            'low_ess_outcome_mass': low_mass, 'max_covariance_regularization': maxreg, 'normalization_error': float(abs(zw @ mass.sum(1) - 1))}


def risk_pass(BM, model, candidate_ids, bits, order, seed, response_availability, m):
    posts = model.component_posteriors(model.x_ref)
    candidates = np.asarray(candidate_ids, int)
    score = np.zeros((4, len(candidates))); bases = score.copy(); low = score.copy(); norm = score.copy(); ess = score.copy()
    for s in range(4):
        for jj, j in enumerate(candidates):
            pieces = []
            if response_availability > 0:
                pieces.append((response_availability, candidate_table(BM, posts, model.weights, j, model.c.probit_scale, model.c.response_noise_sd, bits, order, seed + 1009 * s, True, m)))
            if response_availability < 1:
                pieces.append((1 - response_availability, candidate_table(BM, posts, model.weights, j, model.c.probit_scale, model.c.response_noise_sd, bits, order, seed + 1009 * s, False, m)))
            score[s, jj] = sum(w * q['score'] for w, q in pieces); bases[s, jj] = sum(w * q['base_risk'] for w, q in pieces)
            low[s, jj] = sum(w * q['low_ess_outcome_mass'] for w, q in pieces); norm[s, jj] = max(q['normalization_error'] for _, q in pieces)
            ess[s, jj] = min(q['ess_min'] for _, q in pieces)
    return {'scores': score.mean(0), 'score_2se': 2 * score.std(0, ddof=1) / 2, 'replicate_scores': score, 'base_risks': bases.mean(0), 'ess_min': float(ess.min()),
            'low_ess_outcome_mass': float(low.max()), 'normalization_error': float(norm.max()), 'bits': bits, 'gh_order': order}


def select_risk(BM, model, candidate_ids, seed, response_availability, decision_risk, m, ladder=((8, 9), (10, 17), (12, 33)), timer=None):
    """balanced_method.select_risk with an explicit m (same ladder, acceptance and tie rule)."""
    previous = risk_pass(BM, model, candidate_ids, *ladder[0], seed, response_availability, m)
    if timer is not None:
        timer.append({"level": ladder[0], "utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
    history = []; accepted = False
    for bits, order in ladder[1:]:
        current = risk_pass(BM, model, candidate_ids, bits, order, seed, response_availability, m)
        if timer is not None:
            timer.append({"level": (bits, order), "utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
        delta = np.abs(current['scores'] - previous['scores']); error = np.maximum(delta, current['score_2se'])
        tower = 0. if decision_risk is None else float(np.max(abs(current['base_risks'] - decision_risk)))
        history.append({'bits': bits, 'gh_order': order, 'max_order_difference': float(delta.max()), 'max_2se': float(current['score_2se'].max()),
                        'low_ess_mass': current['low_ess_outcome_mass'], 'tower_risk_difference': tower, 'normalization_error': current['normalization_error']})
        accepted = bool(error.max() <= .002 and current['low_ess_outcome_mass'] <= .002 and tower <= .002 and current['normalization_error'] <= 1e-8)
        if accepted:
            break
        previous = current
    if not accepted:
        return {**current, 'status': 'NUMERICAL_STOP', 'history': history, 'selected': None}
    top = int(np.argmax(current['scores']))
    tie = np.flatnonzero(current['scores'][top] - current['scores'] <= .002 + error[top] + error)
    chosen = int(min(np.asarray(candidate_ids)[tie]))
    current.update(status='accepted', selected=chosen, history=history, errors=error, near_tie_ids=np.asarray(candidate_ids)[tie],
                   estimated_argmax=int(np.asarray(candidate_ids)[top]), ranking_resolved=bool(len(tie) == 1), candidate_ids=np.asarray(candidate_ids),
                   max_tower_risk_difference=None if decision_risk is None else float(np.max(abs(current['base_risks'] - decision_risk))))
    return current


# ======================================================================================== decisions at m = 136, A1 level
def decide(model, x_ref, x_pred, seed):
    """Finite-batch decision over [x_ref; x_pred] at the A1 level; adds her 'risk' (reference-pool optimised loss)."""
    X = np.vstack([x_ref, x_pred]) if len(x_pred) else x_ref
    posts = model.component_posteriors(X, full=False)
    d = A1.decisions_a1(posts, np.asarray(model.weights, float), len(x_ref), m=M_BATCH, seed=seed)
    nr = len(x_ref)
    d["risk"] = float(.5 * np.mean(np.minimum(d["A"][:nr], d["B"][:nr])))
    return d


def _compact(d):
    return {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in d.items() if k in
            ("decision", "signed_margin", "margin_2se", "pi_mean", "pi_2se", "bits", "history", "numerically_accepted", "risk", "max_covariance_regularization", "ambiguous")}


# ======================================================================================== one trajectory
def run_traj(task, arm, b_start=B_START, b_end=B_END, ckpt=None, std_fn=None, shared_start=None, ladder=((8, 9), (10, 17), (12, 33)), stop_after=None,
             cap_check=None):
    BM, AV2, _ = astra()
    from src.jdl_stage_m import Oracle, standardizer
    oracle = Oracle(task); std = std_fn or standardizer(task)[0]
    x_ref = std(task["X"][task["pool"]]); x_test = std(task["X"][task["test"]])
    pool = list(task["pool"]); pos = {int(i): k for k, i in enumerate(pool)}
    s = task.get("seed_override", task_seed(task["repeat"], task["fold"]))
    st = TA._read(ckpt) if (ckpt is not None and ckpt.exists()) else {"arm": arm, "paid": [int(i) for i in task["path"][:b_start]], "b": b_start, "steps": [], "evals": [],
                                                                      "status": "ok", "resumed_at": [], "component_solves": 0, "fits_executed": 0}
    if st["b"] != b_start:
        st["resumed_at"].append(st["b"])
    while st["b"] <= b_end and st["status"] == "ok":
        b = st["b"]; paid = st["paid"]; t0 = time.time()
        reused = shared_start is not None and b == b_start
        if reused:
            model, dec, test, rec_fit = shared_start
        else:
            if cap_check is not None and not cap_check():
                st["status"] = f"CAP_STOP at B{b}"
                if ckpt is not None:
                    TA._atomic_write(ckpt, st)
                break
            pt = oracle.reveal(paid)
            model = AV2.JointModelV2(x_ref, config()).fit(std(pt.X), pt.y.astype(float), pt.z)
            st["fits_executed"] += 1; st["component_solves"] += int(getattr(model, "solve_count", 3))
            dec = decide(model, x_ref, np.empty((0, x_ref.shape[1])), 91000 + s + 101 * b)
            test = decide(model, x_ref, x_test, 91000 + s + 101 * b)
            rec_fit = {"weights": np.asarray(model.weights).tolist(), "fallback": bool(model.diagnostics.get("fallback", False)) if isinstance(model.diagnostics, dict) else None}
        pt = oracle.reveal(paid)
        p = model.predict_proba(x_test)
        nr = len(x_ref)
        st["evals"].append({"budget": b, "p": np.asarray(p).tolist(), "finite_batch": np.asarray(test["decision"][nr:]).astype(int).tolist(),
                            "pi_mean": test["pi_mean"], "test_decision_accepted": bool(test["numerically_accepted"])})
        state = {"budget": b, "n_paid": len(paid), "n_pos": int(pt.y.sum()), "n_neg": int((pt.y == 0).sum()), "n_response": int(np.isfinite(pt.z).sum()),
                 "start_reused": reused, **rec_fit, "decision_ref": _compact(dec) | {"signed_margin": None, "margin_2se": None, "decision": None},
                 "decision_test_history": test["history"], "decision_test_bits": test["bits"]}
        if not dec["numerically_accepted"] or not test["numerically_accepted"]:
            state["status"] = "DECISION_NUMERICAL_STOP"; st["steps"].append(state); st["status"] = f"DECISION_NUMERICAL_STOP at B{b}"; st["b"] = b + 1
            if ckpt is not None:
                TA._atomic_write(ckpt, st)
            break
        if b == b_end:
            state["seconds"] = time.time() - t0; st["steps"].append(state); st["b"] = b + 1
            if ckpt is not None:
                TA._atomic_write(ckpt, st)
            break
        cand = [k for k in range(nr) if pool[k] not in set(paid)]
        alpha = (int(np.isfinite(pt.z).sum()) + 1) / (len(paid) + 2)
        ts = time.time(); timer = []
        if arm == "BA_RISK":
            q = select_risk(BM, model, cand, 20000 + s + 101 * b, alpha, dec["risk"], M_BATCH, ladder=ladder, timer=timer)
        elif arm == "V2_VARIANCE":
            q = BM.select_variance(model, cand, alpha)
        else:
            q = BM.select_margin(dec, cand)
        state.update({"selector_status": q["status"], "selected_pool_index": q.get("selected"), "response_availability": alpha, "score_seconds": time.time() - ts,
                      "score_evaluations": len(cand) * ((4 * (1 + (alpha < 1)) * (1 + len(q.get("history") or []))) if arm == "BA_RISK" else
                                                        ((1 + (alpha < 1)) * (1 + len(q.get("history") or [])) if arm == "V2_VARIANCE" else 1)),
                      "ranking_resolved": bool(q.get("ranking_resolved", False)),
                      "near_tie_ids": [int(v) for v in q.get("near_tie_ids", [])], "history": q.get("history"), "level_times": timer,
                      "low_ess_outcome_mass": q.get("low_ess_outcome_mass"), "normalization_error": q.get("normalization_error"),
                      "max_tower_risk_difference": q.get("max_tower_risk_difference"), "seconds": time.time() - t0})
        st["steps"].append(state)
        if q["status"] != "accepted" or q.get("selected") is None:
            st["status"] = f"{q['status']} at B{b}"; st["b"] = b + 1
        else:
            paid.append(int(pool[int(q["selected"])])); st["b"] = b + 1
        if ckpt is not None:
            TA._atomic_write(ckpt, st)
        if stop_after is not None and b == stop_after:
            return None
    st["paid_ids"] = [str(task["ids"][i]) for i in st["paid"]]
    return st


def shared_b16(task, std):
    """The B16 fit and decisions shared by the three arms (identical paid set and seeds)."""
    _, AV2, _ = astra()
    from src.jdl_stage_m import Oracle
    x_ref = std(task["X"][task["pool"]]); x_test = std(task["X"][task["test"]])
    pt = Oracle(task).reveal(task["path"][:B_START])
    model = AV2.JointModelV2(x_ref, config()).fit(std(pt.X), pt.y.astype(float), pt.z)
    s = task_seed(task["repeat"], task["fold"])
    dec = decide(model, x_ref, np.empty((0, x_ref.shape[1])), 91000 + s + 101 * B_START)
    test = decide(model, x_ref, x_test, 91000 + s + 101 * B_START)
    rec = {"weights": np.asarray(model.weights).tolist(), "fallback": bool(model.diagnostics.get("fallback", False)) if isinstance(model.diagnostics, dict) else None}
    return model, dec, test, rec, int(getattr(model, "solve_count", 3))


# ======================================================================================== units and workers
def units():
    return [(r, f, a) for a in ARMS for r in REPEATS for f in FOLDS]      # cheap arms' units first


def unit_name(r, f, a):
    return f"NEW__r{r}_f{f}__{a}"


def work(argv=()):
    """Claim and run units.  --arms A,B restricts the arms; --max-units k exits after k finished units (so that the pool
    runner re-allocates capacity at unit boundaries).  Lock files live in locks/<arm>/ (one directory per arm)."""
    argv = list(argv); arms, max_units = ARMS, None
    if "--arms" in argv:
        arms = tuple(argv[argv.index("--arms") + 1].split(","))
        if not set(arms) <= set(ARMS):
            raise SystemExit(f"unknown arm in {arms}")
    if "--max-units" in argv:
        max_units = int(argv[argv.index("--max-units") + 1])
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if not SMM._git("log", "--format=%H", "--", str(MANIFEST.relative_to(SMM.ROOT)).replace("\\", "/")):
        raise SystemExit("commit the ASTRA_AL manifest before any run")
    for c, h in man["code_sha256"].items():
        if SMM.sha256(SMM.ROOT / c) != h:
            raise SystemExit(f"{c} changed after the ASTRA_AL freeze")
    astra()
    tasks = {(t["repeat"], t["fold"]): t for t in TA.build_tasks()}
    CACHE.mkdir(parents=True, exist_ok=True)
    from src.jdl_stage_m import standardizer
    finished = 0
    for r, f, a in units():
        if a not in arms:
            continue
        if max_units is not None and finished >= max_units:
            break
        name = unit_name(r, f, a); out = CACHE / f"{name}.json.gz"
        if out.exists():
            continue
        locks = CACHE / "locks" / a; locks.mkdir(parents=True, exist_ok=True)
        lock = locks / f"{name}.lock"
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            continue
        os.write(fd, str(os.getpid()).encode()); os.close(fd)
        try:
            if out.exists():
                continue
            t = tasks[(r, f)]; std = standardizer(t)[0]; t0 = time.time()
            ck = CACHE / "partial" / f"{name}.json.gz"
            res = run_traj(t, a, ckpt=ck, std_fn=std, cap_check=cap_ok)
            res.update({"study": STUDY, "repeat": r, "fold": f, "arm": a, "test_ids": [str(t["ids"][i]) for i in t["test"]], "unit_seconds": time.time() - t0,
                        "logical_requests": B_END - B_START + 1, "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
            TA._atomic_write(out, res); finished += 1
            print(json.dumps({"unit": name, "status": res["status"], "seconds": round(res["unit_seconds"], 1), "fits_executed": res["fits_executed"]}), flush=True)
        finally:
            lock.unlink(missing_ok=True)


def solves_used():
    """Component solves recorded so far over all units (finished file, else the unit's last atomic checkpoint)."""
    used = 0
    for r, f, a in units():
        nm = unit_name(r, f, a); p = CACHE / f"{nm}.json.gz"
        if not p.exists():
            p = CACHE / "partial" / f"{nm}.json.gz"
        if p.exists():
            try:
                used += int(json.loads(gzip.decompress(p.read_bytes())).get("component_solves", 0))
            except Exception:
                pass
    return used


def cap_ok():
    """A fit may start only if recorded solves plus a worst-case fit (3 components x EP + Laplace fallback) for every
    active unit stay within the 900-solve cap; a refused fit ends that trajectory with CAP_STOP (preserved)."""
    active = max(1, sum(1 for _ in (CACHE / "locks").rglob("*.lock")))
    return solves_used() + 6 * active <= CAPS["component_solves_including_fallback"]


def status():
    done = {p.name[:-len(".json.gz")] for p in CACHE.glob("NEW__*.json.gz")}
    print(json.dumps({"done": len(done), "of": len(units())}))


# ======================================================================================== validation
def validate():
    t0 = time.time(); checks, info = {}, {}
    try:
        BM, AV2, V1 = astra()
        checks["astra_sources_match_her_manifest"] = True
        live_ic = Path(r"C:\Users\ozgur\Documents\Codex\2026-10-10\files-pasted-by-the-user-you\outputs\astra_balanced_decision_acquisition\INDEPENDENT_CHECKS.json")
        ic = json.loads(live_ic.read_text(encoding="utf-8")) if live_ic.exists() else {}                 # read only
        checks["her_independent_reference_checks_accepted"] = bool(ic.get("acceptance_pass"))
        info["her_independent_checks"] = {k: bool(v) for k, v in (ic.get("checks") or {}).items()}
        intake = json.loads((SMM.OUT / "v2_decision_audit" / "intake" / "ASTRA_RESULTS_INTAKE.json").read_text(encoding="utf-8"))
        checks["her_frozen_sources_unchanged"] = bool(intake["frozen_sources_unchanged_since_intake"])
        dv = json.loads((SMM.OUT / "v2_decision_audit" / "DECISION_AUDIT_VALIDATION.json").read_text(encoding="utf-8"))
        checks["m_identities_and_parity_with_astra_m96_m136"] = dv["status"] == "PASS" and all(dv["hard_checks"][k] for k in dv["hard_checks"] if k.startswith(("m2", "m4", "m96", "m136", "parity_with_astra")))
        # synthetic V2 model: the m-parameterised risk table equals her _candidate_table at m = 96 (bitwise)
        g = np.random.default_rng(31)
        Xs = g.normal(0, 1, (14, 4)); xr = Xs[:10]; paid = [0, 3, 5, 7, 9]
        ys = np.array([1, 0, 1, 1, 0.]); zs = np.array([.2, -.4, .3, np.nan, -.1])
        mdl = AV2.JointModelV2(xr, config()).fit(xr[paid], ys, zs)
        posts = mdl.component_posteriors(mdl.x_ref)
        mine = candidate_table(BM, posts, mdl.weights, 2, mdl.c.probit_scale, mdl.c.response_noise_sd, 8, 9, 1171, True, 96)
        hers = BM._candidate_table(posts, mdl.weights, 2, mdl.c.probit_scale, mdl.c.response_noise_sd, 8, 9, 1171, True)
        checks["risk_table_equals_hers_at_m96"] = all(np.array_equal(np.asarray(mine[k]), np.asarray(hers[k])) for k in ("score", "base_risk", "after_risk", "a", "b", "ess_min", "low_ess_outcome_mass", "normalization_error"))
        m136 = candidate_table(BM, posts, mdl.weights, 2, mdl.c.probit_scale, mdl.c.response_noise_sd, 8, 9, 1171, True, 136)
        checks["outcome_normalization_m136"] = m136["normalization_error"] <= 1e-8
        q = select_risk(BM, mdl, [1, 2, 4, 6, 8], 1171, 0.75, None, 136, ladder=((6, 5), (7, 9)))
        checks["risk_selector_runs_m136"] = q["status"] in ("accepted", "NUMERICAL_STOP")
        dm = decide(mdl, xr, Xs[10:], 91000)
        checks["decision_A1_m136_runs"] = dm["bits"] in (12, 14, 16) and "risk" in dm
        # covariance identity of the delivered model on the synthetic case (joint covariance reproduces h covariance)
        qf = mdl.component_posteriors(Xs, full=True)[1]
        checks["joint_covariance_identity"] = float(np.max(np.abs(qf["H"] @ qf["joint_cov"] @ qf["H"].T - qf["h_cov"]))) <= 1e-8
        # real tasks: plumbing, start sharing, and corruption invariance of the first selection (cheap settings)
        tasks = TA.build_tasks(); t = [x for x in tasks if (x["repeat"], x["fold"]) == (3, 1)][0]
        from src.jdl_stage_m import standardizer
        std = standardizer(t)[0]
        cs = run_traj(t, "ALIGNED_MARGIN", 16, 17, std_fn=std, cap_check=lambda: False)
        checks["cap_stop_preserved_before_fit"] = cs["status"] == "CAP_STOP at B16" and cs["fits_executed"] == 0 and cs["evals"] == []
        a1 = run_traj(t, "ALIGNED_MARGIN", 16, 17, std_fn=std)
        y2, A2 = t["y"].copy(), t["A"].copy(); hidden = np.setdiff1d(np.arange(len(y2)), t["path"][:16]); y2[hidden] = 1 - y2[hidden]; A2[hidden] = 4000.0
        a2 = run_traj({**t, "y": y2, "A": A2}, "ALIGNED_MARGIN", 16, 17, std_fn=std)
        checks["hidden_outcomes_do_not_change_first_selection_margin"] = a1["paid"][16] == a2["paid"][16] and a1["evals"][0]["p"] == a2["evals"][0]["p"]
        v1 = run_traj(t, "V2_VARIANCE", 16, 17, std_fn=std); v2 = run_traj({**t, "y": y2, "A": A2}, "V2_VARIANCE", 16, 17, std_fn=std)
        checks["hidden_outcomes_do_not_change_first_selection_variance"] = v1["paid"][16] == v2["paid"][16]
        info["first_unit_timing_seconds"] = {"ALIGNED_MARGIN_one_step": a1["steps"][0].get("seconds"), "V2_VARIANCE_one_step": v1["steps"][0].get("seconds")}
        # BA_RISK corruption invariance on the first two ladder levels only (structural; the full ladder is the benchmark)
        BMm, AV2m, _ = astra()
        from src.jdl_stage_m import Oracle
        x_ref = std(t["X"][t["pool"]])
        def first_scores(task):
            pt = Oracle(task).reveal(task["path"][:16])
            mdl_ = AV2m.JointModelV2(x_ref, config()).fit(std(pt.X), pt.y.astype(float), pt.z)
            cand = [k for k in range(len(x_ref)) if t["pool"][k] not in set(task["path"][:16].tolist())][:6]
            return risk_pass(BMm, mdl_, cand, 6, 5, 20000 + task_seed(3, 1) + 101 * 16, 0.9, M_BATCH)["scores"]
        checks["hidden_outcomes_do_not_change_risk_scores"] = np.array_equal(first_scores(t), first_scores({**t, "y": y2, "A": A2}))
        checks["ten_task_folds_with_frozen_paths"] = len(tasks) == 10
    except Exception as ex:
        checks["selftest_completed"] = False; info["error"] = f"{type(ex).__name__}: {ex}"[:400]; info["traceback"] = traceback.format_exc()[-2500:]
    res = {"study": STUDY, "status": "PASS" if checks and all(checks.values()) else "FAIL", "checks": {k: bool(v) for k, v in checks.items()}, "info": info,
           "seconds": time.time() - t0, "module_sha256": SMM.sha256(SMM.ROOT / "src" / "jdl_astra_al.py")}
    OUT.mkdir(parents=True, exist_ok=True)
    VALIDATION.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps({"status": res["status"], "checks": res["checks"], "info": {k: v for k, v in info.items() if k != "traceback"}}, indent=1, default=str))
    if res["status"] != "PASS":
        raise SystemExit(1)


def write_manifest():
    val = json.loads(VALIDATION.read_text(encoding="utf-8"))
    if val["status"] != "PASS" or val["module_sha256"] != SMM.sha256(SMM.ROOT / "src" / "jdl_astra_al.py"):
        raise SystemExit("ASTRA_AL validation must PASS with this module before the freeze")
    tm = json.loads(TA.MANIFEST.read_text(encoding="utf-8"))
    man = {"study": STUDY, "status": "FROZEN BEFORE ANY ASTRA_AL OUTCOME", "written_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "parent_commit": SMM._git("rev-parse", "HEAD"), "authorization": "owner execution request of 2026-10-15 (Astra's real-data acquisition policy draft)",
           "design_source": "outputs/astra_balanced_decision_acquisition/OPUS_DECISION_ACQUISITION_REQUEST.md (bounded future DEV policy draft)",
           "population": "NEW-136, DEV repeats 3-4, folds 1-5", "start": "frozen feature-only B16 (stage_a paths)", "budgets": [B_START, B_END], "arms": list(ARMS),
           "path_sha256": tm["path_sha256"], "m": M_BATCH, "decision_level": "A1 extended ladder 2^10..2^16 (criterion unchanged)",
           "risk_ladder": [[8, 9], [10, 17], [12, 33]], "risk_acceptance": "max(order difference, 2 SE) <= 0.002, low-ESS mass <= 0.002, tower <= 0.002, normalisation <= 1e-8",
           "precision_extension": "none registered for the risk selector; an unresolved risk ranking is a NUMERICAL_STOP",
           "availability_model": "alpha = (paid responses + 1) / (paid simulations + 2) at each budget",
           "seeds": "task seed s = 6000 + 100 r + f; decisions 91000 + s + 101 b; risk 20000 + s + 101 b",
           "primary_contrasts": ["BA_RISK - ALIGNED_MARGIN", "BA_RISK - V2_VARIANCE"], "endpoint": "pooled-per-repeat finite-batch BA-AULC over B16-B24 (trapezoid / 8), mean of repeats 3-4",
           "reported": "terminal (B24) BA, both class recalls, q20, short-K recall (evaluation guardrail only), AUC/Brier/log loss of the mixture probability, decisions per simulation",
           "guardrail": "short-K recall is never a selector input; a BA gain with short-K loss beyond 2 of 20 events relative to ALIGNED_MARGIN is a trade-off, not success",
           "savings": "no savings endpoint is registered for this study (her draft)", "caps": CAPS,
           "cap_enforcement": "before every fit: recorded solves + 6 per active unit <= 900, else CAP_STOP (preserved); executed fits reported beside the 270 logical requests",
           "runtime_plan": ("pool runner src/jdl_pool_runner.ps1, one BLAS thread per worker, each worker exits after one unit (--max-units 1); cheap arms "
                            "(ALIGNED_MARGIN, V2_VARIANCE) up to 2 workers; BA_RISK: the predeclared first unit NEW__r3_f1__BA_RISK runs alone until its first "
                            "acquisition step is recorded, then BA_RISK gets up to 2 workers while any other registered study has claimable units, else up to 3; "
                            "unfinished units are reported as unfinished"),
           "validation": {"status": val["status"], "sha256": SMM.sha256(VALIDATION)}, "code_sha256": {c: SMM.sha256(SMM.ROOT / c) for c in CODE},
           "astra_source_sha256": {n: hashlib.sha256((ASTRA_DIR / n).read_bytes()).hexdigest() for n in ASTRA_SOURCES}}
    MANIFEST.write_text(json.dumps(man, indent=1), encoding="utf-8")
    print(json.dumps({k: man[k] for k in ("status", "written_utc", "arms")}, indent=1))


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "status"
    {"validate": validate, "manifest": write_manifest, "work": lambda: work(sys.argv[2:]), "status": status}[step]()
