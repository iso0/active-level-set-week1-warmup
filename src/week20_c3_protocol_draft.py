"""Draft C3 confirmation protocol for ACTIVE E1 + straddle (written because the Track 1 extension decision rule said
"C3 PROTOCOL DRAFT").  NOT a freeze and NOT executed: no C3 split, label or prediction is touched here.  It becomes a
freeze only if the owner approves it and it is committed before any C3 run.

Step: python -m src.week20_c3_protocol_draft
"""
from __future__ import annotations

import datetime as dt
import json

import numpy as np
import pandas as pd

import src.week20_track1_al as A

OUTC = A.OUT / "c3_draft"
BAR, NONINF = 0.02, -0.01


def predicted_pass(d, n_sim=20000, n_boot=4000, seed=0):
    """Resample 4 per-repeat DEV differences (with replacement) as a stand-in for C3; apply the Week 18 repeat bootstrap."""
    rng = np.random.default_rng(seed); d = np.asarray(d, float)
    hits_bar = hits_lo = hits_both = 0
    for _ in range(n_sim):
        c3 = rng.choice(d, 4)
        lo = np.quantile(np.random.default_rng(0).choice(c3, (n_boot, 4)).mean(1), .025)
        m = c3.mean(); hits_bar += m >= BAR; hits_lo += lo > 0; hits_both += (m >= BAR) and (lo > 0)
    return {"mean_ge_bar": hits_bar / n_sim, "interval_gt_0": hits_lo / n_sim, "both": hits_both / n_sim}


def main():
    au = pd.read_csv(A.OUT / "track1_ext/aulc_per_repeat_r1_8.csv")
    per = {}
    for task in A.TASKS:
        w = au[au.task == task].pivot_table(index="repeat", columns="arm", values="BA_AULC")
        per[task] = (w.ACTIVE_E1_STRADDLE - w.G3_MARGIN).round(6).tolist()
    pred = predicted_pass(per["R3_NEW"])
    spec = {
        "status": "DRAFT - not frozen, not executed. Becomes the C3 freeze only after owner approval, committed before any C3 run.",
        "written_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "candidate": "ACTIVE_E1_STRADDLE: src.week20_track1_al arm B unchanged (GPR on log A, per-step ML-II, learned threshold midpoint/logistic, straddle), no guard",
        "reference": "G3_MARGIN: src.week20_track1_al arm C unchanged (Week 18 REF)",
        "ablation_reported_not_decisive": "WHOLE_E1_STRADDLE (arm A)",
        "code": "the frozen runner src/week20_track1_al.py (sha256 e3d0cfbf3e017463...) through src/week20_track1_ext.py with REPEATS = (17, 18, 19, 20); 1 BLAS thread per worker",
        "data_used_once": "block C3 = repeats 17-20, 5 folds each (src.week18_tasks.BLOCKS); tasks R3_NEW (primary), R3_OLD, R1_POOLED; SPLIT-CONFIRMATION on the same 541 runs",
        "decision_rule": {
            "Q3a_primary": f"R3_NEW BA-AULC (grid 16..80 step 4) ACTIVE - G3 >= +{BAR:.2f} with the repeat-bootstrap 95 % interval > 0 (4,000 resamples, seed 0; Week 18 convention)",
            "Q3b_no_loss": f"R3_OLD and R1_POOLED BA-AULC ACTIVE - G3 >= {NONINF:+.2f} (point estimates)",
            "interpretation": {"Q3a and Q3b": "confirmed: ACTIVE E1 + straddle improves on G3 + margin on NEW, without loss on OLD / POOLED",
                               "Q3a and not Q3b": "improvement on NEW with a loss elsewhere",
                               "not Q3a, point estimate > 0": "not confirmed at the frozen bar",
                               "point estimate <= 0": "does not replicate"},
            "reported_not_decisive": ["q20, specificity, sensitivity, short-K sensitivity, Brier, AUC", "ACTIVE - WHOLE", "QTT (frozen definition)", "learned-threshold mechanism"]},
        "dev_evidence": {"per_repeat_ACTIVE_minus_G3_BA_AULC_repeats_1_8": per,
                         "R3_NEW_mean": float(np.mean(per["R3_NEW"])), "R3_NEW_sd": float(np.std(per["R3_NEW"], ddof=1)),
                         "predicted_probabilities_from_DEV_resampling": pred,
                         "prediction_method": "draw 4 of the 8 DEV per-repeat R3_NEW differences with replacement (20,000 simulations, seed 0) and apply the rule"},
        "caveats": ["A (active-window maximum depth) was defined after the Week 19 audit had seen every NEW label; C3 tests the active-learning procedure on new splits and seeds, not a target chosen blind to the labels",
                    "C1 and C2 were spent in Week 18 on WHOLE E1; C3 is the last unused block",
                    "four repeats: the repeat bootstrap is coarse"],
        "fit_budget_if_run": "3 tasks x 4 repeats x 5 folds x 3 arms = 180 runs, <= 13,140 scalar fits",
    }
    OUTC.mkdir(parents=True, exist_ok=True)
    (OUTC / "c3_protocol_draft.json").write_text(json.dumps(spec, indent=1), encoding="utf-8")
    md = f"""# C3 confirmation protocol — DRAFT (not frozen, not executed)

*Written {spec['written_utc']}.*
- **Why it exists:** the Track 1 extension's frozen decision rule returned "C3 PROTOCOL DRAFT" (`track1_ext/decision.json`).
- **What it touches:** nothing in C3. No C3 split, label or prediction was used to write it.
- **When it becomes a freeze:** only if the owner approves it and it is committed before any C3 run.

## Candidate and reference
- **Candidate:** ACTIVE E1 + straddle, the frozen Track 1 arm B with no guard.
- **Reference:** G3 + margin, arm C.
- **Ablation:** WHOLE E1 + straddle is reported but is not decisive.
- **Code:** the frozen runner `src/week20_track1_al.py`, through `src/week20_track1_ext.py` with repeats 17–20, at 1 BLAS thread per worker.

## Data (used once)
- **Block:** C3 = repeats 17–20, 5 folds each.
- **Tasks:** R3_NEW (primary), R3_OLD and R1_POOLED.
- **Type:** split confirmation on the same 541 runs.

## Locked decision rule (contrasts ACTIVE − G3; repeat bootstrap, 4,000 resamples, seed 0)
- **Q3a (primary):** R3_NEW BA-AULC ≥ +{BAR:.2f} **and** its 95 % interval > 0.
- **Q3b (no loss):** R3_OLD and R1_POOLED BA-AULC ≥ {NONINF:+.2f} (point estimates).
- **Interpretation, fixed in advance:**
  - Q3a and Q3b → **confirmed**: ACTIVE E1 + straddle improves on G3 + margin on NEW, without loss on OLD and POOLED.
  - Q3a without Q3b → improvement on NEW with a loss elsewhere.
  - Q3a fails but the point estimate is > 0 → not confirmed at the frozen bar.
  - Point estimate ≤ 0 → does not replicate.
- **Reported, not decisive:** q20, specificity, sensitivity, short-K, Brier, AUC, ACTIVE − WHOLE, QTT and the threshold mechanism.

## Predictions from DEV (repeats 1–8)

| Task | Per-repeat ACTIVE − G3 BA-AULC |
|---|---|
| R3_NEW | {', '.join(f'{v:+.3f}' for v in per['R3_NEW'])} (mean {np.mean(per['R3_NEW']):+.3f}, SD {np.std(per['R3_NEW'], ddof=1):.3f}) |
| R3_OLD | {', '.join(f'{v:+.3f}' for v in per['R3_OLD'])} |
| R1_POOLED | {', '.join(f'{v:+.3f}' for v in per['R1_POOLED'])} |

- **Method:** 4 of the 8 DEV values were drawn with replacement, 20,000 times, and the rule was applied to each draw.
- **Q3a:** the point-estimate bar is met in {pred['mean_ge_bar']:.0%} of draws, the interval excludes 0 in {pred['interval_gt_0']:.0%}, and both hold in **{pred['both']:.0%}**.
- **Q3b:** expected to pass, since every DEV value except one POOLED repeat at −0.002 is ≥ 0.

## Caveats
- A was defined after the Week 19 audit had seen every NEW label, so C3 tests the procedure on new splits and seeds; it does not test a target chosen blind to the labels.
- C1 and C2 were spent in Week 18 on WHOLE E1; C3 is the last unused block.
- With four repeats, the repeat bootstrap is coarse.

**Budget if run:** 180 runs, at most 13,140 scalar fits.
"""
    (OUTC / "C3_PROTOCOL_DRAFT.md").write_text(md, encoding="utf-8")
    print(json.dumps(pred, indent=1))


if __name__ == "__main__":
    main()
