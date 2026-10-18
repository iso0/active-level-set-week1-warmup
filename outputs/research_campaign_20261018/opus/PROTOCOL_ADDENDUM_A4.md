# RC18 protocol addendum A4 — hybrid label model: PHYS_TR prior + NEW-label residual GPC (registered before it runs; exploratory)

**Registered:** 2026-10-18 ~11:35 UTC, before any A4 run.

**What was known at registration (final repeats):**

| Arm | Budget | BA | Specificity | log loss |
|---|---|---|---|---|
| PHYS_TR | B0 | 0.69 | — | 0.19 |
| PHYS_TR | B40 | 0.71 | 0.44 | 0.19 |
| E1 + straddle | B8 | 0.64 | — | — |
| E1 + straddle | B40 | 0.74 | — | 0.57 |

PHYS_TR is flat from B0 to B40. E1 + straddle starts lower but keeps improving.

**Question:** can a classifier keep PHYS_TR's zero-simulation start and calibration while learning NEW's boundary shift (the fast-scan corner) from paid NEW labels?

**Model** (`src/rc18_physgpc.py`):
- **Prior mean:** at every budget, the PHYS_TR probability P_phys(x), recomputed exactly as in A3. The latent prior mean is m(x) = logit(clip(P_phys, 0.01, 0.99)).
- **Residual classifier:** a fixed-mean Laplace GP classifier (the Week 17/18 safeguarded Newton implementation, residual kernel M3 = C × Matérn-3/2 ARD, ML-II), fitted on the paid NEW labels with mean m.
- **Output:** P(K | x) is the classifier's predictive probability. With no paid labels, P_phys is used.

**Arms:**
- **PHYS_GPC_MARGIN:** the common 8-point start, then argmin |P − 0.5|.
- **PHYS_GPC_MAXIMIN:** the label-free path from B0.

Both run to B40 on the NEW final tasks (repeats 5–8).

**Endpoints:** as in A3 — BA, both recalls, q20, short-K captured/total, Brier, log loss, AUC — reported next to A3 and the final label arm. GPC fit failures are counted and fall back to P_phys at that budget. Exploratory; no superiority claim.
