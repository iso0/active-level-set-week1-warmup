"""RC19 additive pooled-data test of Astra's frozen v2 ask/tell selector (separately registered; PROTOCOL_RC19_ADDENDUM_AX.md).

Source: a verbatim, SHA-256-checked read-only COPY of her frozen v2 files (model.py, policy.py, acquisition.py,
quota_policy.py) in opus_pooled/astra_copy/; her workspace is never written and never imported from directly.
Adapter: an Opus GP posterior (rc18_gp via rc18_campaign.fit_model, the same SHQ / M0 models as the main region study) is
supplied as her `model.Snapshot` for the single primary channel h(x) = spike log-ratio - log 2 (threshold at 0):
  mean = mu - tau; latent_cov = latent variance; noise_cov = observation-noise variance (kept SEPARATE; never added twice);
  probability = Phi((mu - tau) / sqrt(latent)); reference cloud = the public pool inputs (label-free) with its own moments;
  cross_cov[r, n] = posterior latent covariance between reference r and candidate n (rc18_gp.GP.post_cov);
  weights = [1] (one Gaussian component); availability_weights = paid-only share of revealed runs with / without a valid
  primary channel (patterns: none, primary).
Her geometry constants (local radius 0.15-0.45) assume unit-box features, so features = the pool's log inputs scaled to [0, 1].
Every query is paid through rc19_pool.Reveal (startup included); the snapshot is built and hashed BEFORE the reveal.
    python -m src.rc19_astra copy | accept
"""
from __future__ import annotations

import hashlib
import importlib
import json
import shutil
import sys
import time
from pathlib import Path

import numpy as np
from scipy.special import ndtr

import src.rc18_campaign as C
import src.rc18_common as RC
import src.rc19_learn as LN
import src.rc19_pool as P

SRC = Path(r"C:/Users/ozgur/Documents/Codex/2026-10-10/files-pasted-by-the-user-you/outputs/astra_deep_discovery_20261018")
COPY = P.OUT / "astra_copy"
FILES = ("model.py", "policy.py", "acquisition.py", "quota_policy.py")
TAU = LN.TAU
RESP = LN.RESP


def _sha(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def make_copy():
    COPY.mkdir(parents=True, exist_ok=True)
    man = json.loads((SRC / "FROZEN_MANIFEST_V2.json").read_text(encoding="utf-8"))
    rows = {}
    for f in FILES:
        shutil.copyfile(SRC / f, COPY / f)
        rows[f] = {"source_sha256": _sha(SRC / f), "copy_sha256": _sha(COPY / f)}
    flat = json.dumps(man)
    for f, r in rows.items():
        r["listed_in_her_frozen_manifest_v2"] = r["source_sha256"] in flat
    (COPY / "COPY_MANIFEST.json").write_text(json.dumps({"utc": RC.utc(), "source_dir": str(SRC), "her_manifest": "FROZEN_MANIFEST_V2.json",
                                                         "her_manifest_sha256": _sha(SRC / "FROZEN_MANIFEST_V2.json"), "files": rows}, indent=1), encoding="utf-8")
    return rows


def load():
    rec = json.loads((COPY / "COPY_MANIFEST.json").read_text(encoding="utf-8"))
    for f, r in rec["files"].items():
        if _sha(COPY / f) != r["copy_sha256"]:
            raise SystemExit(f"astra copy {f} changed")
    if str(COPY) not in sys.path:
        sys.path.insert(0, str(COPY))
    return importlib.import_module("model"), importlib.import_module("policy"), importlib.import_module("quota_policy")


def unit_features(task):
    lx = np.log(task["X"])[task["pool"]]; lo, hi = lx.min(0), lx.max(0)
    return (lx - lo) / np.where(hi > lo, hi - lo, 1.0)


def snapshot(AM, f, Z, pool, paid_pool_pos, avail):
    mu, lat, obs = f.predict(pool); noise = np.maximum(obs - lat, 1e-12); lat = np.maximum(lat, 1e-12)
    cross = f.g.post_cov(Z[pool], None, Z[pool], None)                     # (ref = pool) x (candidate = pool), latent
    h = hashlib.sha256(np.asarray(f.g.theta, float).tobytes() + np.asarray(sorted(paid_pool_pos), np.int64).tobytes()).hexdigest()
    prob = ndtr((mu - TAU) / np.sqrt(lat))
    return AM.Snapshot(model_hash=h, paid_count=len(paid_pool_pos), mean=(mu - TAU)[:, None], latent_cov=lat[:, None, None], noise_cov=noise[:, None, None],
                       probability=prob, ref_mean=mu - TAU, ref_variance=lat, ref_probability=prob, cross_cov=cross[:, :, None],
                       weights=np.array([1.0]), availability_weights=np.array([1.0 - avail, avail]))


def run_region_astra(task, model, mode, bmax, M=None):
    AM, AP, AQ = load()
    rev = P.Reveal(task, M); Z = LN.design_inputs(task, model); pool, test = task["pool"], task["test"]; ids = task["ids"]
    pos = {int(i): k for k, i in enumerate(pool)}; LN.startup(task, rev); U = unit_features(task)
    startup = [pos[int(i)] for i in rev.order]; seed = int(P.SPLIT_SEED * 1000 + 100 * task["repeat"] + task["fold"])
    pol = AQ.QuotaPolicy(U, startup, mode, seed) if mode.startswith("quota") else AP.Policy(U, startup, mode, seed)
    shared = LN.base(model).startswith("SH"); cols = list(P.TARGETS) if shared else [RESP]; evals, events = [], []; t0 = time.time()
    while True:
        b = rev.queries; Yp = rev.paid_Y() if shared else rev.paid_Y()[:, [LN.TI[RESP]]]
        fits = C.fit_model(LN.base(model), Z, Yp, rev.paid, cols, emu=None, short=rev.paid_short()); f = fits.get(RESP)
        if f is None or not isinstance(f, C.Fitted):
            raise RuntimeError("no fitted primary-channel posterior")          # recorded as a unit failure (never retried)
        m, lat, _ = f.predict(test); evals.append({"budget": b, "mean": LN._f32(m), "lat": LN._f32(lat)})
        if b >= bmax:
            break
        yv = rev.paid_Y()[rev.paid, LN.TI[RESP]]; avail = float(np.mean(np.isfinite(yv)))
        snap = snapshot(AM, f, Z, pool, [pos[int(i)] for i in rev.order], avail); digest0 = snap.digest()
        ch = pol.ask(snap); k = int(ch["paid_id"]); row = int(pool[k])
        if snap.digest() != digest0:
            raise RuntimeError("pre-query snapshot changed during ask")
        out = rev.reveal(row); v = float(out["Y"][LN.TI[RESP]]); ok = bool(np.isfinite(v))
        ev = pol.tell(AP.PaidObservation(paid_id=k, values=(v if ok else None,), quality=(ok,), cost=1.0, canonical_label=None))
        events.append({"budget": b + 1, "reason": ch["reason"], "triggered": bool(ev.get("triggered")), "confirmed_now": bool(ev.get("confirmed_now")),
                       "ended": ev.get("ended"), "prequery_hash": ch["prequery_hash"], "near_tie": bool(ch.get("near_tie"))})
    return {"repeat": task["repeat"], "fold": task["fold"], "model": model, "acq": "ASTRA_" + mode.upper(), "paid": rev.order, "paid_ids": [ids[i] for i in rev.order],
            "test_ids": [ids[i] for i in test], "evals": evals, "astra_events": events, "seconds": time.time() - t0, "queries": rev.queries}


def accept():
    """Numerical acceptance of the adapter (her integration request): finite PSD moments, separate noise, the information
    fraction of her SUR equals a dense rank-one conditioning of the same GP, pre-query hash immutability, unique paid IDs,
    deterministic continuation (two identical runs give identical paths)."""
    RC.limit_threads(1); AM, AP, AQ = load(); Mf = P.manifest(); t = P.tasks((1,))[0]; acq = importlib.import_module("acquisition")
    rev = P.Reveal(t, Mf); Z = LN.design_inputs(t, "SHQ"); pool = t["pool"]; LN.startup(t, rev)
    for i in t["path"][P.B0:P.B0 + 8]:
        rev.reveal(int(i))
    fits = C.fit_model("SHQ", Z, rev.paid_Y(), rev.paid, list(P.TARGETS), emu=None, short=rev.paid_short()); f = fits[RESP]
    pos = {int(i): k for k, i in enumerate(pool)}; snap = snapshot(AM, f, Z, pool, [pos[int(i)] for i in rev.order], 1.0)
    out = {"psd_finite": bool(np.all(np.isfinite(snap.latent_cov)) and np.all(snap.latent_cov > 0) and np.all(snap.noise_cov > 0))}
    frac = acq.information_fraction(snap, 1)                                  # (ref, cand)
    worst = 0.0; rng = np.random.default_rng(0)
    for j in rng.choice(len(pool), 5, replace=False):                         # dense check: condition the same GP on one more noisy point at x_j
        g = f.g; xj = Z[pool][j:j + 1]; d = g.Z.shape[1]
        sf2, sn2 = np.exp(g.theta[0]), np.exp(g.theta[1 + d])
        Za = np.vstack([g.Z, xj]); wa = np.r_[g.w, 1.0]; K = g._K(g.theta, Za, None, wa)[0]
        from src.rc18_gp import matern32
        kr = sf2 * matern32(Z[pool], Za, np.exp(g.theta[1:1 + d]))                   # (ref, n+1)
        Kinv = np.linalg.inv(K + 1e-10 * np.eye(len(K)))
        var_after = g.sd ** 2 * (sf2 - np.einsum("ij,jk,ik->i", kr, Kinv, kr))
        var_before = snap.ref_variance
        dense_frac = (var_before - var_after) / np.maximum(var_before, 1e-12)
        worst = max(worst, float(np.max(np.abs(dense_frac - frac[:, j]))))
    out["info_fraction_vs_dense_max_abs_diff"] = worst
    out["info_fraction_ok"] = worst < 1e-6
    r1 = run_region_astra(t, "SHQ", "boundary_regional", P.B0 + 10, M=Mf); r2 = run_region_astra(t, "SHQ", "boundary_regional", P.B0 + 10, M=Mf)
    out["deterministic_continuation"] = r1["paid_ids"] == r2["paid_ids"]
    out["paid_ids_unique"] = len(set(r1["paid_ids"])) == len(r1["paid_ids"])
    out["status"] = "PASS" if all(v for k, v in out.items() if isinstance(v, bool)) else "FAIL"
    (COPY / "ADAPTER_ACCEPTANCE.json").write_text(json.dumps(out, indent=1), encoding="utf-8"); print(json.dumps(out, indent=1))


if __name__ == "__main__":
    {"copy": lambda: print(json.dumps(make_copy(), indent=1)), "accept": accept}[sys.argv[1]]()
