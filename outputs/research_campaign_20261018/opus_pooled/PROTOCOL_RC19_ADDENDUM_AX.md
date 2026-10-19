# RC19 addendum AX — additive pooled-data test of Astra's frozen v2 ask/tell selector (registered before it runs)

**Registered:** 2026-10-19, before any AX trajectory runs.

**Basis:**
- Owner instruction §7 (Astra intake is additive).
- Astra's `OPUS_DISCOVERY_INTEGRATION_REQUEST.md`, "bounded future DEV proposal".
- Her numerical acceptance `results/NUMERICAL_CHECKS.json` = PASS.

**Status of her own evidence:** her synthetic v2 TEST is still running (6,399 of 10,224 units at 12:25 UTC), and she has inspected no v2 scientific endpoint. This test is therefore an integration-and-stability check on inspected simulations, **not** a scientific confirmation of her method and not SPH superiority.

## Source and contract

**Source:** a verbatim, SHA-256-checked read-only copy of her frozen v2 files `model.py`, `policy.py`, `acquisition.py` and `quota_policy.py`.
- The copy is in `opus_pooled/astra_copy/` with `COPY_MANIFEST.json`; each file's source hash is checked against her `FROZEN_MANIFEST_V2.json`.
- Her workspace is never written and never imported from.

**Contract:** the RC19 paid-only contract (`PROTOCOL_RC19.md` §2).
- The same pooled tasks, the same B8 paid maximin startup, and every revealed simulation counted.
- The selector reads only public inputs (scaled to the unit box, which her geometry constants assume), its own paid values and quality, and the pre-query posterior.

**Posterior (the adapter, `src/rc19_astra.py`):** the main-study SHQ model for the primary channel h(x) = spike log-ratio − log 2.
- **Moments:** latent mean and variance, and a separate observation-noise variance. The noise is never added twice.
- **Exceedance:** Φ(mean / latent SD).
- **Reference cloud:** the label-free public pool inputs, with posterior latent cross-covariance to every candidate.
- **Weights:** one Gaussian component, weight 1.
- **Availability:** paid-only availability of a valid primary channel.

**Adapter acceptance (`astra_copy/ADAPTER_ACCEPTANCE.json`; must PASS before any AX unit):**
- finite positive moments;
- her SUR information fraction equal to a dense rank-one conditioning of the same GP at 5 candidates (< 1e-6);
- the pre-query hash unchanged by `ask`;
- unique paid IDs;
- deterministic continuation: two identical runs give identical paths.

## Design (her proposal, adapted to the pooled region)

**Paths:** exactly 8 final pooled tasks, frozen by their split / path SHA-256: repeat 3, folds 1–5, and repeat 4, folds 1–3.

**Arms (identical model, startup, target and paid outputs):**

| Arm | Selector |
|---|---|
| ASTRA_SUR_GLOBAL | `sur_global` |
| ASTRA_BOUNDARY_REGIONAL | `boundary_regional` |
| ASTRA_QUOTA_SURPRISE | `QuotaPolicy("quota_surprise")` |
| ASTRA_QUOTA_NO_SURPRISE | `QuotaPolicy("quota_no_surprise")` |

**Horizon:** B8–B40, readouts at every budget.

**Size:** 32 trajectories × 33 paid-prefix fits = 1,056 top-level fit requests, each an SHQ fit over 8 outputs. Opus's 2-thread share.

**References:** the main final region units STRADDLE and MAXIMIN (SHQ) on the same 8 tasks, from the frozen main study.

## Reported

**Comparisons, separated as she requested:**
- (1) sur_global vs boundary_regional: the incremental local response under the same schedule;
- (2) quota_surprise vs quota_no_surprise: surprise-informed anchors at a fixed half-local allocation;
- (3) the same model with different selectors: sur_global vs the main study's STRADDLE and MAXIMIN.

**For each:**
- every path;
- BA, both recalls and BA-AULC over B8–B40;
- collection (band share);
- trigger, local-query and near-tie counts;
- quality failures;
- compute cost.

**No DEV success threshold** is set from these outcomes. All results are exploratory and DEV.

**Failure handling:** a unit failure (for example no fitted primary posterior, or a numerical error in her selector) is recorded and never retried; the arm is reported with fewer paths.
