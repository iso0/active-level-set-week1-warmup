# Week 9 Phase 1.20 — acquisition that beats M3-margin

## Protocol in one paragraph

Predictive model M3 exactly as in Phase 1.14; control M3 probability margin. All design and selection on development repeats 1-10 (50 runs); one finalist per family frozen (`FINALISTS.json`) before any confirmation run; confirmation on repeats 11-60 (250 runs, 50 repeat blocks) with the pre-registered rule: Holm-adjusted p < 0.05 and 95% repeat-block CI > 0 on q20 accuracy AULC 16-80 or 16-40, the other window non-negative, guardrails met (`PREREGISTERED_PROTOCOL.json`, `PROTOCOL_AMENDMENT_1.json` for the confirmation size, `PROTOCOL_AMENDMENT_2.json` for the two families). Policies receive masked label/depth arrays; an invariance audit scrambling every unqueried label and depth in 36 states changed no choice.

## Results on the confirmation set

### Family A: pure acquisition function (frozen 16-point seed, active from B16) — `cov_then_misfit_B40` — **CONFIRMED**

| endpoint (confirmation set) | M3 margin | this rule | difference |
|---|---:|---:|---|
| q20 accuracy AULC 16-80 (thesis primary) | 0.8429 | 0.8451 | +0.0023 [+0.0007, +0.0039]; 31/50 blocks positive; Holm p = 0.0074 |
| q20 accuracy AULC 16-40 (sample-efficiency window) | 0.8244 | 0.8299 | +0.0055 [+0.0022, +0.0088]; 33/50 blocks positive; Holm p = 0.0032 |

Guardrails: B40 q20 Keyhole recall -0.0136 (limit -0.03); B80 full-fold accuracy +0.0000 (limit -0.01).

Repeats 11-20 alone (10 blocks, the originally frozen confirmation set): 16-80 +0.0041 [+0.0000, +0.0084]; 6/10 blocks positive; Holm p = 0.2306; 16-40 +0.0070 [-0.0018, +0.0161]; 6/10 blocks positive; Holm p = 0.2306.

Late window 41-80 on the confirmation set: +0.0003 (development: see leaderboard).

Share of the attainable maximum: **17%** of +0.0137 (16-80), **17%** of +0.0321 (16-40).

Secondary endpoints (difference vs margin, confirmation set): q30 accuracy AULC 16-80 +0.0019; q20 balanced accuracy AULC 16-80 +0.0014; q20 Keyhole recall AULC 16-80 -0.0019; full-fold accuracy AULC 16-80 +0.0005.

| margin's accuracy at budget | value | this rule reaches it at | simulations saved |
|---:|---:|---:|---:|
| 24 | 0.8233 | 22 | 2 |
| 32 | 0.8339 | 30 | 2 |
| 40 | 0.8426 | 37 | 3 |
| 60 | 0.8555 | 55 | 5 |

### Family B: the same rule with an earlier active start (8 maximin points, then CCM; same total budget) — `early8__cov_then_misfit_B40` — **CONFIRMED**

| endpoint (confirmation set) | M3 margin | this rule | difference |
|---|---:|---:|---|
| q20 accuracy AULC 16-80 (thesis primary) | 0.8429 | 0.8470 | +0.0041 [+0.0021, +0.0060]; 41/50 blocks positive; Holm p = 0.0015 |
| q20 accuracy AULC 16-40 (sample-efficiency window) | 0.8244 | 0.8361 | +0.0116 [+0.0072, +0.0157]; 39/50 blocks positive; Holm p = 0.0004 |

Guardrails: B40 q20 Keyhole recall -0.0023 (limit -0.03); B80 full-fold accuracy -0.0002 (limit -0.01).

Repeats 11-20 alone (10 blocks, the originally frozen confirmation set): 16-80 +0.0043 [+0.0016, +0.0073]; 8/10 blocks positive; Holm p = 0.0864; 16-40 +0.0120 [+0.0045, +0.0186]; 8/10 blocks positive; Holm p = 0.0864.

Late window 41-80 on the confirmation set: -0.0006 (development: see leaderboard).

Share of the attainable maximum: **30%** of +0.0137 (16-80), **36%** of +0.0321 (16-40).

Secondary endpoints (difference vs margin, confirmation set): q30 accuracy AULC 16-80 +0.0037; q20 balanced accuracy AULC 16-80 +0.0026; q20 Keyhole recall AULC 16-80 -0.0021; full-fold accuracy AULC 16-80 +0.0013.

| margin's accuracy at budget | value | this rule reaches it at | simulations saved |
|---:|---:|---:|---:|
| 24 | 0.8233 | 18 | 6 |
| 32 | 0.8339 | 26 | 6 |
| 40 | 0.8426 | 31 | 9 |
| 60 | 0.8555 | 60 | 0 |

Family B changes how the first 16 simulations are chosen (8 frozen maximin points, then active). It is an acquisition-STRATEGY result, not a like-for-like post-B16 acquisition result; both arms have spent exactly the same number of simulations at every budget, and AULC is computed on the same 16-80 grid.

## The rule (CCM — Coverage-then-Consistency Margin)

**Coverage, before 40 queried simulations.** Estimate the log-h band from queried labels only: [lowest queried Keyhole, highest queried Conduction], or the bracket between them while they are still separable, padded by a quarter of its width. Inside the band choose the candidate maximising rank(M3 uncertainty) + rank(standardised distance to the nearest queried point).

**Consistency, from 40 onwards.** M3 margin down-weighted near queried rows the current M3 fit does not reproduce: score = (1 - 2|p - 0.5|) x (1 - 0.8 exp(-d^2 / (2 x 0.5^2))), d = standardised distance to the nearest queried misfit.

## Why it works and why re-scoring never could

1. **Reducible error is false positives only.** On q20 (17 rows per fold, 39% Keyhole) false negatives stay at ~1.6-1.9 per fold from B16 — the persistent late-onset/transient Keyhole exceptions. Learning = removing false positives; margin finishes by ~B60, so late windows cannot move much.
2. **The attainable maximum is small.** Even if M3 jumped to its all-label accuracy right after the seed, AULC 16-80 could rise by only +0.0137 (16-40: +0.0321). The historical bar +0.010 on 16-80 was 73% of that maximum — the reason every earlier phase looked null.
3. **Early, M3 is a hard step in log h** (66% of runs separable at B16; slope ~21 per revealed sd; residual SD 0.05-0.29 until B20). Margin bisects a thin slab and exposes class overlap slowly; coverage inside the label-estimated band exposes it sooner (separable runs at B24: 4% vs 14%), so false positives fall sooner.
4. **Late, conflicting labels hurt M3 — but avoiding them did not replicate.** A leaky diagnostic that queries exactly the rows nearest an opposite label loses -0.0239 on AULC 41-80, and avoiding queried misfits gained +0.0039 on development; on the confirmation set the late-window difference is +0.0003. The late component is therefore not supported: the confirmed gain is carried by the early coverage phase.
5. **Seed corners are costly labels for a physics-mean model.** The first maximin points sit in the corners of the input box, far from the boundary; M3's physics mean already supplies the global structure they were meant to give. Development: early start alone +0.0038, CCM alone +0.0049, both +0.0089 (AULC 16-80). Seed size is not a knife edge: k = 4, 8, 12 give +0.0057, +0.0089, +0.0071.
6. **Why 1.14-1.18B could not find this.** Under M3 every score built from M3's own posterior ranks like margin (Phase 1.18A, rho 0.977-0.999). The confirmed part of CCM does not re-score margin at all: it changes the geometry of the query set in the regime where M3's posterior is least trustworthy (early), and the early-start variant stops spending labels on corner points M3's physics mean does not need.

## Development screening

31 post-B16 rules and 4 early-start variants, plus two LEAKY diagnostics, on development repeats (`development_leaderboard.csv`). Depth-guided rules (straddle on a revealed-depth GP, depth x margin, regula falsi) did not help; asymmetric margins were strongly harmful; on development, coverage helped early and consistency helped late, and their combination ranked first — of those two, only the early coverage effect replicated on confirmation.

## Claim boundary

405-simulation development pool. Confirmation runs are new cross-validation partitions of that same pool, not an independent dataset; the blinded new pool remains the external test. The switch budget (40), pad (0.25), misfit length (0.5) and seed size (8) were chosen on development repeats only. The winner was selected from many screened rules; the confirmation set, untouched during selection, is what the claim rests on.
