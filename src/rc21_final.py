"""RC21 sequential stage: paired adaptive trajectories on FRESH DEV repeats 27-34 with matched starts, information and budgets,
frozen (PROTOCOL_RC21_FINAL.md + manifest) before any of its outcomes. NEW = src.rc21_decisions.NEW.
Arms (B8 -> B60, every budget recorded; startup = the 8 label-free maximin points of RC19, paid and counted; one-class rule):
  NEW_MARGIN   NEW construction + margin |p - 0.5|
  H_MARGIN     SHQ_ATS_H + margin (identical computation to RC20 CAND_MARGIN; validated against src.rc20_attr.cand_state)
  X_MARGIN     SHQ_ATS_X + margin (generic exact inputs on their own queries)
  ATSAPPROX_MARGIN, E1S (E1RAW / E1CAL + straddle), G3_MARGIN    (unchanged RC19B code, K = 10)
The three physical arms evaluate every RC21 construction on their own paid prefix at every budget from ONE shared upstream fit
("p_all"; matched-path by-products); the arm's own choice uses only its own construction.
    python -m src.rc21_final manifest | check
"""
from __future__ import annotations

import hashlib
import json
import sys
import time

import numpy as np

import src.rc18_common as RC

OUT = RC.ROOT / "outputs" / "research_campaign_20261020" / "opus_rc21"
MANIFEST = OUT / "final" / "RC21_FINAL_MANIFEST.json"
PROTOCOL = "outputs/research_campaign_20261020/opus_rc21/PROTOCOL_RC21_FINAL.md"
REPEATS = (27, 28, 29, 30, 31, 32, 33, 34)                  # never run before (RC19 1-10, RC19B 11-18, RC20 19-26)
PHYS_ARMS = ("NEW_MARGIN", "H_MARGIN", "X_MARGIN")
CONTROL_ARMS = ("ATSAPPROX_MARGIN", "E1S", "G3_MARGIN")
ARMS = PHYS_ARMS + CONTROL_ARMS
# ---- pre-declared evaluation (frozen with PROTOCOL_RC21_FINAL.md). Windows: small = budgets 8..24, all = 8..60 (every budget).
# (role, arm, reference, metric, window, direction, margin); verdict: mean beyond the margin AND good direction in >= MIN_GOOD of 8
Q1 = ("Q1 decision accuracy (co-primary)", "NEW_MARGIN", "H_MARGIN", "BA", "small", "higher", 0.020)
Q2 = ("Q2 paid simulations to a confirmed BA >= 0.93 (co-primary)", "NEW_MARGIN", "H_MARGIN", "BA >= 0.93")
SECONDARY = [("decision, NEW vs H", "NEW_MARGIN", "H_MARGIN", "BA", "all", "higher", 0.020),
             ("decision, NEW vs H (descriptive)", "NEW_MARGIN", "H_MARGIN", "sensitivity", "small", "higher", 0.020),
             ("decision, NEW vs H (descriptive)", "NEW_MARGIN", "H_MARGIN", "specificity", "small", "higher", 0.020),
             ("decision, NEW vs H (descriptive)", "NEW_MARGIN", "H_MARGIN", "sensitivity", "all", "higher", 0.020),
             ("decision, NEW vs H (descriptive)", "NEW_MARGIN", "H_MARGIN", "specificity", "all", "higher", 0.020),
             ("probability, NEW vs H", "NEW_MARGIN", "H_MARGIN", "log_loss", "small", "lower", 0.010),
             ("probability, NEW vs H", "NEW_MARGIN", "H_MARGIN", "log_loss", "all", "lower", 0.005),
             ("probability, NEW vs H", "NEW_MARGIN", "H_MARGIN", "brier", "all", "lower", 0.005),
             ("generic inputs on own queries, X vs H", "X_MARGIN", "H_MARGIN", "BA", "small", "higher", 0.020),
             ("generic inputs on own queries, X vs H", "X_MARGIN", "H_MARGIN", "BA", "all", "higher", 0.020),
             ("generic inputs on own queries, X vs H", "X_MARGIN", "H_MARGIN", "log_loss", "small", "lower", 0.010),
             ("generic inputs on own queries, X vs H", "X_MARGIN", "H_MARGIN", "log_loss", "all", "lower", 0.005),
             ("control", "NEW_MARGIN", "ATSAPPROX_MARGIN", "log_loss", "small", "lower", 0.010),
             ("control", "NEW_MARGIN", "ATSAPPROX_MARGIN", "BA", "small", "higher", 0.020),
             ("control", "NEW_MARGIN", "E1CAL+straddle", "log_loss", "all", "lower", 0.020),
             ("control", "NEW_MARGIN", "E1RAW+straddle", "BA", "all", "higher", 0.020),
             ("control", "NEW_MARGIN", "G3_MARGIN", "log_loss", "all", "lower", 0.020)]
MIN_GOOD = 7
# paid-query targets (held-out offline benchmarks, not stopping rules); confirmation = level at b AND at the second checkpoint b + 4
TARGETS = (("BA", 0.93, "higher"), ("log_loss", 0.20, "lower"))
SPEND_PAIRS = [("NEW_MARGIN", "H_MARGIN"), ("X_MARGIN", "H_MARGIN"), ("NEW_MARGIN", "X_MARGIN"), ("NEW_MARGIN", "ATSAPPROX_MARGIN"),
               ("NEW_MARGIN", "E1RAW+straddle"), ("NEW_MARGIN", "E1CAL+straddle"), ("NEW_MARGIN", "G3_MARGIN")]
SPEND_RULE = (2.0, 6)          # FEWER iff mean paired spend difference <= -2 simulations, fewer in >= 6/8 repeats, no extra censoring


def construction(arm):
    import src.rc21_decisions as DEC
    return {"NEW_MARGIN": DEC.NEW, "H_MARGIN": "SHQ_ATS_H", "X_MARGIN": "SHQ_ATS_X"}[arm]


def units(job):
    if job == "d-final":
        return [(f"r{r}_f{f}__{a}", ("final", a, r, f)) for r in REPEATS for f in range(1, 6) for a in ARMS]
    if job == "d-smoke":
        return [(f"r1_f{f}__{a}", ("final", a, 1, f)) for f in (1, 2) for a in ARMS]
    raise ValueError(job)


def run_phys(task, arm, bmax, M):
    """One adaptive trajectory of a physical arm: margin on its own construction; all RC21 constructions recorded."""
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


FROZEN = ["src/rc21_phr.py", "src/rc21_attr.py", "src/rc21_final.py", "src/rc21_jobs.py", "src/rc21_decisions.py", "src/rc21_report.py",
          "src/rc20_attr.py", "src/rc20_gp.py", "src/rc19b_keyhole.py", "src/rc19b_keyhole_eval.py", "src/rc19_pool.py", "src/rc19_learn.py", "src/rc19_eval.py",
          "src/rc19_report.py", "src/rc18_campaign.py", "src/rc18_gp.py", "src/rc18_common.py", "src/week18_engine.py", "src/week17_models.py",
          "src/week17_audit_impact.py", "src/week13_synthetic_al.py", "src/external_validation/analysis.py",
          "outputs/research_campaign_20261018/opus_pooled/data/POOLED_MANIFEST.csv", PROTOCOL]


def _sha(p):
    return hashlib.sha256((RC.ROOT / p).read_bytes()).hexdigest()


def write_manifest():
    import src.rc21_decisions as DEC
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    m = {"utc": RC.utc(), "repeats": list(REPEATS), "arms": list(ARMS), "new": DEC.NEW, "files": {f: _sha(f) for f in FROZEN}, "units": {"d-final": len(units("d-final"))}}
    MANIFEST.write_text(json.dumps(m, indent=1), encoding="utf-8"); return m


def check():
    m = json.loads(MANIFEST.read_text(encoding="utf-8")); bad = [f for f, h in m["files"].items() if _sha(f) != h]
    if bad:
        raise SystemExit(f"RC21 frozen files changed since the manifest: {bad}")
    return True


if __name__ == "__main__":
    if sys.argv[1] == "manifest":
        print(json.dumps(write_manifest(), indent=1)[:3000])
    elif sys.argv[1] == "check":
        print("RC21 manifest check:", check())
