"""RC20 sequential stage (Priority 3): paired adaptive trajectories on FRESH DEV repeats with matched starts, information and
budgets, frozen before any of its outcomes. Runs only if the Stage 1 candidate rule (PROTOCOL_RC20_STAGE1.md section 6) passes
its justification gate; the selected candidate is src.rc20_decisions.CAND.
Arms (B8 -> B60, every budget recorded; startup = the 8 label-free maximin points of RC19; one-class rule of RC19):
  CAND_MARGIN       candidate construction + margin |p - 0.5|                         (model change, same selector as ATSCF)
  CAND_ETASTRADDLE  candidate + eta-straddle 1.96 sd(eta) - |eta| (same posterior)    (selector change)
  ATSCF_MARGIN, ATSAPPROX_MARGIN, E1S (E1RAW / E1CAL + straddle), G3_MARGIN          (unchanged RC19B code, K = 10)
    python -m src.rc20_final manifest | check
"""
from __future__ import annotations

import hashlib
import json
import sys
import time

import numpy as np

import src.rc18_common as RC

OUT = RC.ROOT / "outputs" / "research_campaign_20261020" / "opus_rc20"
MANIFEST = OUT / "final" / "RC20_FINAL_MANIFEST.json"
PROTOCOL = "outputs/research_campaign_20261020/opus_rc20/PROTOCOL_RC20_FINAL.md"
REPEATS = (19, 20, 21, 22, 23, 24, 25, 26)                  # never run before (RC19: 1-10, RC19B: 11-18)
CAND_ARMS = ("CAND_MARGIN", "CAND_ETASTRADDLE")
CONTROL_ARMS = ("ATSCF_MARGIN", "ATSAPPROX_MARGIN", "E1S", "G3_MARGIN")
ARMS = CAND_ARMS + CONTROL_ARMS
REC = tuple(range(8, 61, 4))
# ---- pre-declared evaluation (frozen with PROTOCOL_RC20_FINAL.md). Windows: small = budgets 8..24, all = 8..60 (every budget).
# (role, arm, reference, metric, window, direction, margin); verdict: mean beyond the margin AND good direction in >= MIN_GOOD of 8
PRIMARY = ("PRIMARY: model, same selector", "CAND_MARGIN", "ATSCF_MARGIN", "log_loss", "small", "lower", 0.010)
SECONDARY = [("model, same selector", "CAND_MARGIN", "ATSCF_MARGIN", "log_loss", "all", "lower", 0.005),
             ("model, same selector", "CAND_MARGIN", "ATSCF_MARGIN", "BA", "all", "higher", 0.020),
             ("model, same selector", "CAND_MARGIN", "ATSCF_MARGIN", "BA", "small", "higher", 0.020),
             ("model, same selector", "CAND_MARGIN", "ATSCF_MARGIN", "brier", "all", "lower", 0.005),
             ("selector, same posterior", "CAND_ETASTRADDLE", "CAND_MARGIN", "log_loss", "small", "lower", 0.010),
             ("selector, same posterior", "CAND_ETASTRADDLE", "CAND_MARGIN", "BA", "all", "higher", 0.020),
             ("control", "CAND_MARGIN", "ATSAPPROX_MARGIN", "log_loss", "small", "lower", 0.010),
             ("control", "CAND_MARGIN", "ATSAPPROX_MARGIN", "log_loss", "all", "lower", 0.005),
             ("control", "CAND_MARGIN", "E1CAL+straddle", "log_loss", "all", "lower", 0.020),
             ("control", "CAND_MARGIN", "E1RAW+straddle", "BA", "all", "higher", 0.020),
             ("control", "CAND_MARGIN", "G3_MARGIN", "log_loss", "all", "lower", 0.020)]
MIN_GOOD = 7
# paid-query targets (held-out offline benchmarks, not stopping rules); confirmation = level at b AND at the second checkpoint b + 4
TARGETS = (("BA", 0.93, "higher"), ("log_loss", 0.20, "lower"))
SPEND_PAIRS = [("CAND_MARGIN", "ATSCF_MARGIN"), ("CAND_ETASTRADDLE", "CAND_MARGIN"), ("CAND_MARGIN", "ATSAPPROX_MARGIN"),
               ("CAND_MARGIN", "E1RAW+straddle"), ("CAND_MARGIN", "E1CAL+straddle"), ("CAND_MARGIN", "G3_MARGIN")]
SPEND_RULE = (2.0, 6)          # FEWER iff mean paired spend difference <= -2 simulations, fewer in >= 6/8 repeats, no extra censoring
FROZEN = ["src/rc20_attr.py", "src/rc20_gp.py", "src/rc20_final.py", "src/rc20_jobs.py", "src/rc20_decisions.py", "src/rc20_report.py", "src/rc20_eval.py",
          "src/rc19b_keyhole.py", "src/rc19b_keyhole_eval.py", "src/rc19_pool.py", "src/rc19_learn.py", "src/rc19_eval.py", "src/rc19_report.py",
          "src/rc18_campaign.py", "src/rc18_gp.py", "src/rc18_common.py", "src/week18_engine.py", "src/week17_models.py", "src/week17_audit_impact.py",
          "src/week13_synthetic_al.py", "src/external_validation/analysis.py", "outputs/research_campaign_20261018/opus_pooled/data/POOLED_MANIFEST.csv", PROTOCOL]


def units(job):
    if job == "c-final":
        return [(f"r{r}_f{f}__{a}", ("final", a, r, f)) for r in REPEATS for f in range(1, 6) for a in ARMS]
    if job == "c-smoke":
        return [(f"r1_f{f}__{a}", ("final", a, 1, f)) for f in (1, 2) for a in ARMS]
    raise ValueError(job)


def run_cand(task, arm, bmax, M):
    """One adaptive trajectory of the candidate construction with its selector."""
    import src.rc19_learn as LN
    import src.rc19_pool as P
    import src.rc19b_keyhole as K
    import src.rc20_attr as A
    import src.rc20_decisions as DEC
    rev = K._rev_with(task, M, []); Z = P.zstd(task); LN.startup(task, rev); evals = []; t0 = time.time(); sel = "straddle" if arm == "CAND_ETASTRADDLE" else "margin"
    while True:
        b = rev.queries; cands = np.setdiff1d(task["pool"], rev.paid); t1 = time.time()
        st = A.cand_state(task, rev, Z, DEC.CAND, cands)
        e = {"budget": b, "p": {DEC.CAND: LN._f32(st["p_test"])}, "cpu_s": None}
        if b in REC and st.get("extra"):
            e["p_all"] = {k: LN._f32(v) for k, v in st["extra"].items()}
        if b >= bmax:
            e["cpu_s"] = time.time() - t1; evals.append(e); break
        if st["one_class"]:
            nxt = LN.next_on_path(task, rev); how = "path"
        else:
            score = (1.96 * np.sqrt(np.maximum(st["var_cand"], 0.0)) - np.abs(st["eta_cand"])) if sel == "straddle" else -np.abs(st["p_cand"] - 0.5)
            nxt = int(cands[int(np.argmax(score))]); how = sel
        e["cpu_s"] = time.time() - t1; e["how"] = how; evals.append(e); rev.reveal(nxt)
    return {"repeat": task["repeat"], "fold": task["fold"], "arm": arm, "cand": DEC.CAND, "paid": rev.order, "paid_ids": [task["ids"][i] for i in rev.order],
            "test_ids": [task["ids"][i] for i in task["test"]], "evals": evals, "seconds": time.time() - t0, "queries": rev.queries}


def run_unit(kind, arm, task, M):
    if arm in CAND_ARMS:
        return run_cand(task, arm, 60, M)
    import src.rc19b_keyhole as K
    t0 = time.time(); u = K.run_adaptive(task, arm, 60, M=M, K=10, record_all=False); u["seconds"] = time.time() - t0; return u


def _sha(p):
    return hashlib.sha256((RC.ROOT / p).read_bytes()).hexdigest()


def write_manifest():
    import src.rc20_decisions as DEC
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    m = {"utc": RC.utc(), "repeats": list(REPEATS), "arms": list(ARMS), "cand": DEC.CAND, "files": {f: _sha(f) for f in FROZEN},
         "units": {j: len(units(j)) for j in ("c-final",)}}
    MANIFEST.write_text(json.dumps(m, indent=1), encoding="utf-8"); return m


def check():
    m = json.loads(MANIFEST.read_text(encoding="utf-8")); bad = [f for f, h in m["files"].items() if _sha(f) != h]
    if bad:
        raise SystemExit(f"RC20 frozen files changed since the manifest: {bad}")
    return True


if __name__ == "__main__":
    if sys.argv[1] == "manifest":
        print(json.dumps(write_manifest(), indent=1)[:3000])
    elif sys.argv[1] == "check":
        print("RC20 manifest check:", check())
