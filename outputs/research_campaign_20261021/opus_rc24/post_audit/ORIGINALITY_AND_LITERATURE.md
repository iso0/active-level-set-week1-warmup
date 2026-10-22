# What is known, what we changed, what was measured (dated 2026-10-22; corrects the RC24 literature summary)

**Sources.** `literature/LITERATURE_MATRIX.md` (RC24). The method sections of the nearest works were checked from full text:
- Ziatdinov et al. 2021 (arXiv 2108.10280), PDF text;
- Hardcastle et al. 2025 (arXiv 2502.11369 HTML);
- Bryan & Schneider 2008 (ICML), PDF;
- Gotovos et al. 2013 (IJCAI), PDF.

## 1. Known components

| component | known from | note |
|---|---|---|
| GP with explicit basis functions / a linear trend with Gaussian-prior coefficients integrated out (universal kriging) | O'Hagan 1978; Kennedy & O'Hagan 2001; Rasmussen & Williams 2006 §2.7 | TR_PHYS is exactly this with ONE basis function (standardised log h) |
| physics model as the GP mean | Ziatdinov et al. 2021: parametric physical mean m(x; φ), with φ and the kernel hyperparameters sampled jointly by HMC; Thompson / UCB / variance acquisition; scalar regression / optimisation | our anchor is a linear-Gaussian, analytically integrated instance, placed on the AUXILIARY output |
| physics prior mean in a GP classifier | Hardcastle et al. 2025: designer-set FIXED prior class probabilities, logit as the latent prior mean; latent GP fitted with a Gaussian likelihood on ±5 targets; maximum-entropy acquisition; one label per query; no learned physics parameter, no learned-trend baseline | closest within-setting analogues tested here: historical M3 (saturated fixed h mean + residual GPC) and M3_C1 (regularised) |
| stacking / honest out-of-fold combination | Wolpert 1992; Breiman 1996; van der Laan et al. 2007 | HA_LEAN = stacking of a depth emulator into a learned-regularisation classifier (RC20–RC23) |
| uncertainty / margin sampling, level-set estimation, straddle, SUR | Lewis & Gale 1994; Bryan et al. 2005; Gotovos et al. 2013; Bect et al. 2012 | margin is the selector throughout; straddle and SUR variants lost (RC22, RC24) |
| normalised enthalpy as a keyhole / depth scaling variable | Hann et al. 2011; King et al. 2014 | z_h equals the standardised log normalised enthalpy only if the material constants are constant (PROPOSITIONS_v2 §0) |

## 2. Our actual change

The only change in HA_TREND relative to the RC23 system is a one-basis-function GP trend, along standardised log h, in the emulator of the auxiliary output (depth). That emulator feeds an honest out-of-fold stacked active classifier.
- This is an **implementation-level combination** of known parts (universal kriging + stacking + margin).
- It is not a new statistical method.
- Exact identities: TR_NONE ≡ HA_LEAN and TR_PHYS ≡ HA_TREND, so the change is isolated.

## 3. Measured benefit (DEV, one 541-run pool)

**In distribution (random splits):**
- no shown BA benefit (Stage C: +0.0034 / +0.0007, non-inferior);
- a generic log-input trend does as well (clean control: physics − generic ≤ +0.003);
- log loss slightly worse (+0.004 to +0.007);
- spend to BA ≥ 0.95 non-inferiority NOT SHOWN.

**Extrapolation to unseen regions of the same pool:**
- the pooled class-balanced BA improves (+0.011 vs no trend; +0.007 / +0.010 vs a generic trend);
- per-region BA falls (−0.047 vs no trend), and minority-class detection falls in three of the four two-class regions;
- the gain is a structural constraint toward the h-only extrapolation, not better within-region discrimination.

**Against the closest within-setting analogues of the physics-prior-mean GPC idea**, on identical paths (Stage A, B8–B60):
- M3: −0.007 BA, 0/8;
- M3_C1: −0.011, 0/8, log loss 0.249 vs 0.143.

## 4. Not shown

- Superiority over any published method. Ziatdinov's HMC physics-mean GP and Hardcastle's fixed-prior GPC were not reimplemented as published. Their setting differs: optimisation and regression in one case, alloy phase constraints with one output per query in the other. So we cannot say "we beat the literature".
- A physics-specific benefit in distribution.
- Within-region superiority under extrapolation.
- Any external (physical or other-simulator) validation.
- **The synthetic benchmark does not cover the real heavy-minority situation.** Its supported and unsupported hypotheses stay as recorded:
  - S2 and S3 supported;
  - S1 and S4 not supported as registered;
  - S5 not observed.
  - Its block test sets were CHOSEN to have at least 15 runs of each class, so they do not represent the real blocks, whose minorities are 1, 4, 11 and 17 runs, plus a one-class block.

## 5. Originality verdict (choosing among the owner's four options)

**A useful, measured combination of known components, plus an application / diagnostic contribution.** Not a new and supported methodological contribution.

The diagnostic contribution has three parts:
1. a demonstration, on a real active-learning pool, that pooled and per-region evaluation of geometric extrapolation can rank the same models in opposite orders, with a decomposition showing why;
2. a correction of spend "non-inferiority" read from the absence of a "MORE" verdict;
3. the clean control showing that the anchor's in-distribution effect is reproduced by a generic trend.
