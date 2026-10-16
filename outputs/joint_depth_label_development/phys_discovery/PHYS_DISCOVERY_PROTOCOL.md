# PHYS_DISCOVERY (Study 2) — find an outsider in a physical response, then expand to its family

**Status: REGISTERED BEFORE ANY PHYS_DISCOVERY OUTCOME.** Owner approval of 2026-10-17. Ioan, 2026-10-15: "find some kind of an outsider and then expand to find its whole family". This is DEV work on simulations that were inspected before.
- **Code:** `src/jdl_phys_discovery.py`.
- **Manifest:** `PHYS_DISCOVERY_MANIFEST.json`.

## Why a new study after pilot A

Pilot A defined families by the binary label. In NEW, the rare label regime lies where straddle already searches, so local probes added nothing (real replay: no gain). Here the family is defined on a **continuous physical response**, which is where an "outsider" is meaningful.

## Response and families (evaluator truth only; fixed now)

- **Response:** the velocity spike log-ratio, i.e. brief melt-flow surges. It is LEARNABLE on NEW (R² 0.87, pilot B).
- **Family:** the top decile of the population's observed values.
- **Secondary family:** the bottom decile.
- **Separation:** no membership and no unpaid value enters a selector.

## Rule SD-R (fixed)

- **Surprise:** after paying run c, compute z = (y_c − μ_prev(c)) / sqrt(var_prev(c) + noise) under the GP fitted on the paid runs before c. The run is surprising iff |z| ≥ 2.5 **and** it passes QC.
- **QC:** a finite value, no implausible-velocity rows, no non-finite KE rows, status ok.
  - A QC failure is logged as QC_EVENT and is never a surprise. This separates large errors from corrupted monitor records.
- **Seeds and local probes:** a surprise seeds up to 3 local probes, alternating 1:1 with the base selector. A local probe is the nearest unpaid pool run in fold-standardized log inputs, ties broken by simulation ID. A surprising local probe seeds again.
- **Budget:** every probe is a paid query.

## Arms and design

- **Arms:**
  - MAXVAR (base: argmax of the predictive sd);
  - SD_MAXVAR (candidate);
  - RANDOM;
  - MAXIMIN (frozen feature-only path).
- **Common to all arms:** the same GP as PHYS_AL, the same start (first 8 path points), budgets B8–B60.
- **Populations:** NEW and OLD, separately; DEV repeats 3–4, folds 1–5 (the PHYS_AL tasks).

## Endpoints (fixed)

- **Primary:** the family discovery AUDC, i.e. the area under the fraction of the fold pool's family members paid, over B8–B60 (divided by 52).
- **Also reported:** queries to half of the family (censored at 64), the bottom-decile AUDC, surprises and QC events, and seconds.
- **No-harm check:** the global R²-AULC of the response (PHYS_AL definition).
- **Verdict:** **DISCOVERY GAIN (DEV)** iff all hold:
  1. SD_MAXVAR − MAXVAR family AUDC > 0;
  2. its paired bootstrap interval (10 trajectories, 2000 draws, seed 20261017) is above 0;
  3. SD_MAXVAR's R²-AULC is not lower than MAXVAR's by more than 0.02 (mean of repeats).
  - Otherwise the verdict is **NO DISCOVERY GAIN ESTABLISHED**.
- **Descriptive contrasts:** SD_MAXVAR − RANDOM, MAXVAR − RANDOM, MAXVAR − MAXIMIN.

## Disclosure and limits

- The validation printed one trajectory's event counts (3 surprises, 5 QC events in NEW `r3_f1`) before this freeze.
- The family threshold is computed from all runs (evaluator-side).
- 56 OLD runs have no remote velocity channel at the pinned revision, so they have no response value. They can still be paid, but they never count as family members.
