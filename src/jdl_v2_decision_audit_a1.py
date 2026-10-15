"""Decision-audit amendment A1: extended QMC ladder (owner decision of 2026-10-15; registered before it runs).

A NEW ATTEMPT on the same exported V2 posteriors.  It does not replace the frozen decision-audit-1.1.1 outcome
(PRIMARY_UNAVAILABLE, commit 3e990a8d), which stays the audit's frozen result; A1 outputs are labelled AMENDED.

The only change: Astra's ladder 2^10 -> 2^12 -> 2^14 gets one further level, 2^16.  A checkpoint is accepted at the
first level whose change against the previous level meets the UNCHANGED criterion (max signed-margin change <= 0.015
over the reference pool and test inputs, and pi change <= 0.003).  Unchanged: model and exports, m = 136, tau, QMC seeds
(771 + 1009 s + 37 k) and scrambles, the four rules, probability parity at 1e-10, checkpoint classification, rule
validity, readout availability, the primary definition (all 20 V2_EP_mixture checkpoints ok), metrics and bootstrap.
The frozen module src/jdl_v2_decision_audit.py is imported, not modified.  Up to 2^14 the draws and comparisons are
identical, so every checkpoint accepted by 1.1.1 must give bitwise the same record here (checked in `run`).  If A1 still
leaves the primary unavailable, that is reported; no further extension without a new owner decision.  The attempted
finite-batch decisions of 1.1.1 were never scored or inspected before this registration.

Steps: python -m src.jdl_v2_decision_audit_a1 validate | manifest | run | evaluate        (one BLAS thread)
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
from collections import Counter

import numpy as np
import pandas as pd

import src.jdl_stage_m as SMM
import src.jdl_v2_decision_audit as DA

AMENDMENT = "A1_extended_ladder_2^16"
A1_VERSION = "decision-audit-1.1.1+A1"
LADDER_A1 = (10, 12, 14, 16)
ROOT = DA.ROOT
OUT_A1 = DA.OUT / "A1_extended_ladder"
CACHE_A1 = SMM.OUT / "_cache" / "decision_audit_A1"
MANIFEST_A1 = OUT_A1 / "DECISION_AUDIT_A1_MANIFEST.json"
VALIDATION_A1 = OUT_A1 / "DECISION_AUDIT_A1_VALIDATION.json"
OUTCOME_A1 = OUT_A1 / "A1_OUTCOME.json"
FROZEN_MANIFEST = DA.OUT / "DECISION_AUDIT_MANIFEST.json"
FROZEN_RESULT = DA.OUT / DA.UNAVAILABLE_FILE
CODE = ("src/jdl_v2_decision_audit_a1.py", "src/jdl_v2_decision_audit.py", "src/jdl_v2_export.py", "src/jdl_v2_evaluate.py", "src/jdl_evaluate.py", "src/jdl_stage_m.py")
PER_TEST_FIELDS = ("sim_id", "p", "p_stored", "A", "B", "signed_margin", "margin_2se", "ambiguous", "d_finite_batch", "d_posterior_mean_pi", "d_paid_fraction", "d_cutoff_0.5")
RECORD_FIELDS = ("status", "pi_mean", "pi_2se", "bits", "history", "numerically_accepted", "n_ambiguous_test", "max_abs_p_minus_stored_prediction")


def decisions_a1(posts, weights, nref, m=DA.M_BATCH, seed=DA.SEED):
    """DA.decisions with one further ladder level; identical draws, comparisons and criterion up to 2^14."""
    prev = DA.decision_pass(posts, weights, nref, m, LADDER_A1[0], seed)
    hist, cur, dm = [], prev, np.inf
    for bits in LADDER_A1[1:]:
        cur = DA.decision_pass(posts, weights, nref, m, bits, seed)
        dm = float(np.max(np.abs(cur["signed_margin"] - prev["signed_margin"]))); dp = abs(cur["pi_mean"] - prev["pi_mean"])
        hist.append({"bits": bits, "max_margin_change": dm, "pi_change": dp})
        if dm <= DA.ACCEPT_MARGIN_CHANGE and dp <= DA.ACCEPT_PI_CHANGE:
            cur["numerically_accepted"] = True
            break
        prev = cur
    else:
        cur["numerically_accepted"] = False
    cur["history"] = hist
    cur["ambiguous"] = np.abs(cur["signed_margin"]) <= np.maximum(cur["margin_2se"], dm if np.isfinite(dm) else 0.0)
    return cur


def _same(a, b):
    """Bitwise equality of JSON-roundtripped values (NaN equal to NaN)."""
    return json.dumps(a, sort_keys=True, default=DA._json_default) == json.dumps(b, sort_keys=True, default=DA._json_default)


def validate():
    t0 = time.time(); checks, info = {}, {}
    try:
        sg = DA.safeguard_selftest()                                  # the frozen gate, unchanged
        checks["frozen_safeguard_selftest"] = all(sg["checks"].values()) and len(sg["checks"]) == 34
        arrays, side, stored, expect = DA._toy_checkpoint()
        import src.jdl_v2_export as VX
        posts, w, nref = VX.components(arrays), arrays["weights"], len(arrays["x_ref"])
        d0, d1 = DA.decisions(posts, w, nref), decisions_a1(posts, w, nref)
        checks["identical_to_frozen_when_accepted_by_2^14"] = (d0["numerically_accepted"] and d1["numerically_accepted"] and d0["bits"] == d1["bits"]
                                                               and all(np.array_equal(d0[k], d1[k]) for k in ("A", "B", "signed_margin", "decision", "margin_2se", "ambiguous"))
                                                               and d0["pi_mean"] == d1["pi_mean"] and _same(d0["history"], d1["history"]))
        # the extra level is reached exactly when 2^14 is not accepted (control flow, checked by a temporarily tightened
        # criterion that is restored immediately; no study decision uses it)
        saved = DA.ACCEPT_MARGIN_CHANGE
        try:
            DA.ACCEPT_MARGIN_CHANGE = -1.0
            dz, dx = DA.decisions(posts, w, nref), decisions_a1(posts, w, nref)
        finally:
            DA.ACCEPT_MARGIN_CHANGE = saved
        checks["criterion_restored"] = DA.ACCEPT_MARGIN_CHANGE == 0.015
        checks["frozen_ladder_stops_at_2^14"] = (not dz["numerically_accepted"]) and dz["bits"] == 14 and [h["bits"] for h in dz["history"]] == [12, 14]
        checks["extended_ladder_adds_only_2^16"] = (not dx["numerically_accepted"]) and dx["bits"] == 16 and [h["bits"] for h in dx["history"]] == [12, 14, 16]
        checks["levels_up_to_2^14_identical"] = _same(dz["history"], dx["history"][:2])
        rec, rows = DA.audit_checkpoint(arrays, side, stored, 0.5, expect=expect, decide=decisions_a1)
        checks["audit_checkpoint_accepts_toy_with_A1"] = rec["status"] == DA.ST_OK and rec["parity_pass"]
        info["toy_bits"] = int(d1["bits"])
        checks["frozen_module_hash_matches_frozen_manifest"] = (SMM.sha256(ROOT / "src" / "jdl_v2_decision_audit.py")
                                                                == json.loads(FROZEN_MANIFEST.read_text(encoding="utf-8"))["code_sha256"]["src/jdl_v2_decision_audit.py"])
    except Exception as ex:
        checks["selftest_completed"] = False
        info["error"] = f"{type(ex).__name__}: {ex}"[:500]; info["traceback"] = traceback.format_exc()[-2000:]
    res = {"status": "PASS" if checks and all(checks.values()) else "FAIL", "checks": {k: bool(v) for k, v in checks.items()}, "info": info,
           "amendment": AMENDMENT, "a1_version": A1_VERSION, "ladder": list(LADDER_A1), "seconds": time.time() - t0,
           "module_sha256": SMM.sha256(ROOT / "src" / "jdl_v2_decision_audit_a1.py"), "frozen_module_sha256": SMM.sha256(ROOT / "src" / "jdl_v2_decision_audit.py")}
    OUT_A1.mkdir(parents=True, exist_ok=True)
    VALIDATION_A1.write_text(json.dumps(res, indent=1, default=DA._json_default), encoding="utf-8")
    print(json.dumps({"status": res["status"], "checks": res["checks"]}, indent=1))
    if res["status"] != "PASS":
        raise SystemExit(1)


def write_manifest():
    val = json.loads(VALIDATION_A1.read_text(encoding="utf-8"))
    if val["status"] != "PASS" or val["module_sha256"] != SMM.sha256(ROOT / "src" / "jdl_v2_decision_audit_a1.py"):
        raise SystemExit("the A1 validation must PASS with this module before the amendment is frozen")
    fm = json.loads(FROZEN_MANIFEST.read_text(encoding="utf-8"))
    fr = json.loads(FROZEN_RESULT.read_text(encoding="utf-8"))
    man = {"study": "decision-audit amendment A1 (extended QMC ladder) - a new attempt on the frozen V2 exports; zero fits",
           "status": "REGISTERED BEFORE ANY A1 DECISION", "written_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "amendment": AMENDMENT, "a1_version": A1_VERSION, "parent_commit": SMM._git("rev-parse", "HEAD"),
           "authorization": "owner decision of 2026-10-15 (choice 'Karar denetimi DA-A1')",
           "rationale": {"frozen_outcome": fr["audit_status"], "frozen_primary_checkpoints_ok": fr["primary"]["checkpoints_ok"],
                         "frozen_status_counts": fr["status_counts"], "frozen_result_sha256": hashlib.sha256(FROZEN_RESULT.read_bytes()).hexdigest(),
                         "frozen_result_commit": "3e990a8d",
                         "observation": "every one of the 21 stops failed the margin criterion at 2^14 (max change 0.0151-0.0331 > 0.015) with pi changes <= 6.6e-5; Astra's synthetic controlled study recorded the same DECISION_NUMERICAL_STOP at B6, mostly in its rare-negatives world"},
           "change": "one further ladder level 2^16 (ladder 2^10 -> 2^12 -> 2^14 -> 2^16); acceptance at the first level whose change against the previous level meets the unchanged criterion",
           "unchanged": ["acceptance criterion: max signed-margin change <= 0.015 over reference and test inputs and pi change <= 0.003",
                         "model, exports and their frozen index", "m = 136, tau = 0.15", "QMC seeds 771 + 1009 s + 37 k, 4 scrambles", "the four rules",
                         "probability parity <= 1e-10", "checkpoint classification and rule validity", "readout availability (all five folds; partition)",
                         "primary: finite_batch on all 20 V2_EP_mixture checkpoints ok", "metrics, cluster bootstrap (2000, seed 20261013)"],
           "label": "AMENDED (extended ladder); the frozen decision-audit-1.1.1 result PRIMARY_UNAVAILABLE remains the frozen outcome",
           "blindness": "no finite_batch or posterior_mean_pi metric of 1.1.1 was computed (readouts UNAVAILABLE) and the attempted decisions were not inspected before this registration",
           "reproducibility_gate": "every checkpoint accepted by 1.1.1 must give a bitwise identical record under A1, otherwise run() stops",
           "no_further_extension": "if A1 leaves the primary unavailable, that is the reported result; any further change needs a new owner decision",
           "validation": {"file": str(VALIDATION_A1.relative_to(ROOT)).replace("\\", "/"), "status": val["status"], "sha256": hashlib.sha256(VALIDATION_A1.read_bytes()).hexdigest()},
           "exports_sha256": fm["exports_sha256"], "code_sha256": {c: SMM.sha256(ROOT / c) for c in CODE},
           "not_authorized": ["acquisition", "Stage A", "C4", "new fits", "a change of the acceptance thresholds"]}
    MANIFEST_A1.write_text(json.dumps(man, indent=1), encoding="utf-8")
    print(json.dumps({k: man[k] for k in ("status", "written_utc", "amendment")}, indent=1))


def run():
    if not MANIFEST_A1.exists() or not DA._committed(MANIFEST_A1):
        raise SystemExit("commit the A1 manifest first")
    man = json.loads(MANIFEST_A1.read_text(encoding="utf-8"))
    for c, h in man["code_sha256"].items():
        if SMM.sha256(ROOT / c) != h:
            raise SystemExit(f"{c} changed after the A1 registration")
    v2pred = pd.read_csv(DA.V2DIR / "predictions_all.csv.gz", dtype={"sim_id": str})
    fits = {}
    for f in (SMM.OUT / "_cache" / "v2").glob("NEW__*.json.gz"):
        r = json.loads(gzip.decompress(f.read_bytes()))["fit"]; fits[(r["repeat"], r["fold"], r["budget"], r["arm"])] = r
    partial = CACHE_A1 / "_partial"; partial.mkdir(parents=True, exist_ok=True)
    t0, counts, reproduced = time.time(), Counter(), 0
    for rep in DA.DESIGN["repeats"]:
        for fold in DA.DESIGN["folds"]:
            for b in DA.DESIGN["budgets"]:
                for arm in DA.ARMS:
                    name = DA.checkpoint_name(rep, fold, b, arm); cf = CACHE_A1 / f"{name}.json.gz"
                    if cf.exists():
                        continue
                    ld = DA.load_checkpoint(rep, fold, b, arm, fits, man["exports_sha256"])
                    stored = v2pred[(v2pred.arm == arm) & (v2pred.repeat == rep) & (v2pred.fold == fold) & (v2pred.budget == b)].set_index("sim_id").p
                    pi_hat = (fits.get((rep, fold, b, arm)) or {}).get("pi_hat")
                    rec, preds = DA.audit_checkpoint(ld["arrays"], ld["side"], stored, pi_hat, expect=ld["expect"], component_rho=ld["component_rho"],
                                                     reason=ld["reason"], decide=decisions_a1)
                    rec.update({"repeat": rep, "fold": fold, "budget": b, "arm": arm, "checkpoint": name, "export": ld["stem"], "amendment": AMENDMENT})
                    preds = [{"repeat": rep, "fold": fold, "budget": b, "arm": arm, **r} for r in preds]
                    frozen = json.loads(gzip.decompress((DA.CACHE / f"{name}.json.gz").read_bytes()))
                    if frozen["fit"]["status"] == DA.ST_OK:               # reproducibility gate
                        ok = all(_same(rec.get(k), frozen["fit"].get(k)) for k in RECORD_FIELDS) and len(preds) == len(frozen["predictions"]) \
                            and all(_same({k: p.get(k) for k in PER_TEST_FIELDS}, {k: q.get(k) for k in PER_TEST_FIELDS}) for p, q in zip(preds, frozen["predictions"]))
                        if not ok:
                            raise SystemExit(f"A1 does not reproduce the accepted 1.1.1 checkpoint {name}")
                        reproduced += 1
                    rec["frozen_status"] = frozen["fit"]["status"]
                    tmp = partial / cf.name
                    tmp.write_bytes(gzip.compress(json.dumps({"fit": rec, "predictions": preds}, default=DA._json_default).encode()))
                    os.replace(tmp, cf)
                    counts[(frozen["fit"]["status"], rec["status"])] += 1
                    print(f"{name} frozen={frozen['fit']['status']} A1={rec['status']} bits={rec['bits']} "
                          f"last_change={rec['history'][-1]['max_margin_change'] if rec['history'] else None}", flush=True)
    print(f"A1 run: {time.time() - t0:.1f}s, zero fits; accepted-by-1.1.1 checkpoints reproduced bitwise: {reproduced}; (frozen, A1) status counts: {dict(counts)}")


def evaluate():
    """The frozen evaluation (DA.evaluate, unchanged definitions) pointed at the A1 records and output directory."""
    saved = DA.CACHE, DA.OUT
    DA.CACHE, DA.OUT = CACHE_A1, OUT_A1
    code = 0
    try:
        DA.evaluate()
    except SystemExit as ex:
        code = int(ex.code) if isinstance(ex.code, int) else 1
    finally:
        DA.CACHE, DA.OUT = saved
    name = DA.SUMMARY_FILE if code == 0 else DA.UNAVAILABLE_FILE
    res = OUT_A1 / name
    summary = json.loads(res.read_text(encoding="utf-8")) if res.exists() else None
    out = {"amendment": AMENDMENT, "a1_version": A1_VERSION, "label": "AMENDED (extended ladder); not the frozen primary", "exit_code": code,
           "result_file": name if res.exists() else None, "result_sha256": hashlib.sha256(res.read_bytes()).hexdigest() if res.exists() else None,
           "audit_status": summary["audit_status"] if summary else None, "primary": summary["primary"] if summary else None,
           "status_counts": summary["status_counts"] if summary else None,
           "frozen_outcome": {"file": "v2_decision_audit/" + DA.UNAVAILABLE_FILE, "sha256": hashlib.sha256(FROZEN_RESULT.read_bytes()).hexdigest(), "audit_status": "PRIMARY_UNAVAILABLE"}}
    OUTCOME_A1.write_text(json.dumps(out, indent=1, default=DA._json_default), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("audit_status", "exit_code", "status_counts")}, indent=1, default=DA._json_default))
    if code:
        raise SystemExit(code)


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "validate"
    {"validate": validate, "manifest": write_manifest, "run": run, "evaluate": evaluate}[step]()
