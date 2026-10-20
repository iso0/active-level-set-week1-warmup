"""RC21B confirmation stage (registered after the RC21 results, before any RC21B outcome; PROTOCOL_RC21B.md): the plug-in version of
the RC21 learned-regularisation classifier, PHR_NRMAP (same posterior weights over (tau_F, tau_h) as PHR_NR, each configuration's
plug-in sigma(m); no residual, no latent integration), chosen from the RC21 decomposition (exploratory by-product on repeats 27-34),
tested on FRESH DEV repeats 35-42 against the previous strongest model with the RC21 endpoints unchanged.
Arms (B8 -> B60, every budget recorded; same startup and one-class rule):
  NEW_MARGIN  PHR_NRMAP + margin          H_MARGIN  SHQ_ATS_H + margin (RC20 CAND / RC21 H computation)
  ATSAPPROX_MARGIN, E1S                    (unchanged RC19B code, K = 10)
Physical arms record every RC21 construction on their own paid prefix at every budget (src.rc21_attr.state, one upstream fit).
    python -m src.rc21b_final manifest | check
"""
from __future__ import annotations

import hashlib
import json
import sys
import time

import numpy as np

import src.rc18_common as RC

OUT = RC.ROOT / "outputs" / "research_campaign_20261020" / "opus_rc21"
MANIFEST = OUT / "rc21b" / "RC21B_MANIFEST.json"
PROTOCOL = "outputs/research_campaign_20261020/opus_rc21/PROTOCOL_RC21B.md"
REPEATS = (35, 36, 37, 38, 39, 40, 41, 42)                  # never run before (RC19 1-10, RC19B 11-18, RC20 19-26, RC21 27-34)
PHYS_ARMS = ("NEW_MARGIN", "H_MARGIN")
CONTROL_ARMS = ("ATSAPPROX_MARGIN", "E1S")
ARMS = PHYS_ARMS + CONTROL_ARMS
NEW = "PHR_NRMAP"
# ---- pre-declared evaluation (frozen with PROTOCOL_RC21B.md); verdict rule and windows as RC21
Q1 = ("Q1 decision accuracy (co-primary)", "NEW_MARGIN", "H_MARGIN", "BA", "small", "higher", 0.020)
Q2 = ("Q2 paid simulations to a confirmed BA >= 0.93 (co-primary)", "NEW_MARGIN", "H_MARGIN", "BA >= 0.93")
SECONDARY = [("decision, NEW vs H", "NEW_MARGIN", "H_MARGIN", "BA", "all", "higher", 0.020),
             ("decision, NEW vs H (descriptive)", "NEW_MARGIN", "H_MARGIN", "sensitivity", "small", "higher", 0.020),
             ("decision, NEW vs H (descriptive)", "NEW_MARGIN", "H_MARGIN", "specificity", "small", "higher", 0.020),
             ("decision, NEW vs H (descriptive)", "NEW_MARGIN", "H_MARGIN", "sensitivity", "all", "higher", 0.020),
             ("decision, NEW vs H (descriptive)", "NEW_MARGIN", "H_MARGIN", "specificity", "all", "higher", 0.020),
             ("probability, NEW vs H (key secondary)", "NEW_MARGIN", "H_MARGIN", "log_loss", "small", "lower", 0.010),
             ("probability, NEW vs H", "NEW_MARGIN", "H_MARGIN", "log_loss", "all", "lower", 0.005),
             ("probability, NEW vs H", "NEW_MARGIN", "H_MARGIN", "brier", "all", "lower", 0.005),
             ("control", "NEW_MARGIN", "ATSAPPROX_MARGIN", "log_loss", "small", "lower", 0.010),
             ("control", "NEW_MARGIN", "ATSAPPROX_MARGIN", "log_loss", "all", "lower", 0.005),
             ("control", "NEW_MARGIN", "ATSAPPROX_MARGIN", "BA", "small", "higher", 0.020),
             ("control", "NEW_MARGIN", "E1CAL+straddle", "log_loss", "all", "lower", 0.020),
             ("control", "NEW_MARGIN", "E1RAW+straddle", "BA", "all", "higher", 0.020)]
MIN_GOOD = 7
TARGETS = (("BA", 0.93, "higher"), ("log_loss", 0.20, "lower"))
SPEND_PAIRS = [("NEW_MARGIN", "H_MARGIN"), ("NEW_MARGIN", "ATSAPPROX_MARGIN"), ("H_MARGIN", "ATSAPPROX_MARGIN"), ("NEW_MARGIN", "E1RAW+straddle"),
               ("NEW_MARGIN", "E1CAL+straddle")]
SPEND_RULE = (2.0, 6)


def construction(arm):
    return {"NEW_MARGIN": NEW, "H_MARGIN": "SHQ_ATS_H"}[arm]


def units(job):
    if job == "e-final":
        return [(f"r{r}_f{f}__{a}", ("final", a, r, f)) for r in REPEATS for f in range(1, 6) for a in ARMS]
    if job == "e-smoke":
        return [(f"r1_f{f}__{a}", ("final", a, 1, f)) for f in (1, 2) for a in ARMS]
    raise ValueError(job)


def run_phys(task, arm, bmax, M):
    """Identical loop to src.rc21_final.run_phys; only the construction map differs (NEW = PHR_NRMAP)."""
    import src.rc19_learn as LN
    import src.rc19_pool as P
    import src.rc19b_keyhole as K
    import src.rc21_attr as RA
    own = construction(arm); rev = K._rev_with(task, M, []); Z = P.zstd(task); LN.startup(task, rev); nt = len(task["test"]); evals = []; t0 = time.time(); c0 = time.process_time()
    while True:
        b = rev.queries; cands = np.setdiff1d(task["pool"], rev.paid); t1 = time.process_time()
        out, info = RA.state(task, rev, Z, np.r_[task["test"], cands])
        e = {"budget": b, "p": {own: LN._f32(out[own][:nt])}, "p_all": {k: LN._f32(v[:nt]) for k, v in out.items()},
             "info": {k: v for k, v in info.items() if k in ("one_class", "K", "fallbacks", "phr", "coef_H")}}
        if b >= bmax:
            e["cpu_s"] = time.process_time() - t1; evals.append(e); break
        if info["one_class"]:
            nxt = LN.next_on_path(task, rev); how = "path"
        else:
            nxt = int(cands[int(np.argmax(-np.abs(out[own][nt:] - 0.5)))]); how = "margin"
        e["cpu_s"] = time.process_time() - t1; e["how"] = how; evals.append(e); rev.reveal(nxt)
    return {"repeat": task["repeat"], "fold": task["fold"], "arm": arm, "construction": own, "paid": rev.order, "paid_ids": [task["ids"][i] for i in rev.order],
            "test_ids": [task["ids"][i] for i in task["test"]], "evals": evals, "seconds": time.time() - t0, "cpu_s": time.process_time() - c0, "queries": rev.queries}


def run_unit(arm, task, M):
    if arm in PHYS_ARMS:
        return run_phys(task, arm, 60, M)
    import src.rc19b_keyhole as K
    t0 = time.time(); c0 = time.process_time(); u = K.run_adaptive(task, arm, 60, M=M, K=10, record_all=False)
    u["seconds"] = time.time() - t0; u["cpu_s"] = time.process_time() - c0; return u


FROZEN = ["src/rc21b_final.py", "src/rc21b_jobs.py", "src/rc21b_report.py", "src/rc21_report.py", "src/rc21_phr.py", "src/rc21_attr.py",
          "src/rc20_attr.py", "src/rc20_gp.py", "src/rc19b_keyhole.py", "src/rc19b_keyhole_eval.py", "src/rc19_pool.py", "src/rc19_learn.py", "src/rc19_eval.py",
          "src/rc19_report.py", "src/rc18_campaign.py", "src/rc18_gp.py", "src/rc18_common.py", "src/week18_engine.py", "src/week17_models.py",
          "src/week17_audit_impact.py", "src/week13_synthetic_al.py", "src/external_validation/analysis.py",
          "outputs/research_campaign_20261018/opus_pooled/data/POOLED_MANIFEST.csv", PROTOCOL]


def _sha(p):
    return hashlib.sha256((RC.ROOT / p).read_bytes()).hexdigest()


def write_manifest():
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    m = {"utc": RC.utc(), "repeats": list(REPEATS), "arms": list(ARMS), "new": NEW, "files": {f: _sha(f) for f in FROZEN}, "units": {"e-final": len(units("e-final"))}}
    MANIFEST.write_text(json.dumps(m, indent=1), encoding="utf-8"); return m


def check():
    m = json.loads(MANIFEST.read_text(encoding="utf-8")); bad = [f for f, h in m["files"].items() if _sha(f) != h]
    if bad:
        raise SystemExit(f"RC21B frozen files changed since the manifest: {bad}")
    return True


if __name__ == "__main__":
    if sys.argv[1] == "manifest":
        print(json.dumps(write_manifest(), indent=1)[:3000])
    elif sys.argv[1] == "check":
        print("RC21B manifest check:", check())
