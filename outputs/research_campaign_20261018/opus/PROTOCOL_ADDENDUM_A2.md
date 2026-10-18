# RC18 protocol addendum A2 — which first NEW simulations to buy once transfer exists (registered before it runs; exploratory)

**Registered:** 2026-10-18 ~11:00 UTC. At registration the final primary result was known: TRSQ reaches the 0.9 level at B0 for 5 of 6 NEW targets. None of the A2 designs had been run.

**Motivation.** A descriptive diagnostic: the transfer error |y − μ_OLD|/SD is 15–40 % larger for the 63 NEW runs with ST > 400 K, outside the OLD range, than for those inside it, with small negative biases for log A and laser power. A design that buys the first NEW runs where the transfer is least supported could correct it faster.

**Designs.** All use model TRSQ, NEW final tasks (repeats 5–8, 20 tasks), budgets B0–B24, and the same evaluator as the final programme.
- **MAXIMIN0:** the final MAXIMIN units, reused and not rerun.
- **RANDOM0:** seeded random choice from B0.
- **MOIVR0:** MOIVR from B0.
- **GAP0** (new acquisition): the argmax over unpaid pool runs of Σ_t [latent variance of the residual GP_t(x) + latent variance of the OLD emulator_t(x)] / Var_t.
  - The sum runs over the 6 NEW primary targets.
  - Var_t is the variance of the OLD-emulator predictions over the pool. It is label-free and uses no unpaid NEW output.
- **Small samples:** with fewer than 5 usable paid rows, only the OLD-emulator variance is used (GAP0); MOIVR0 continues the MAXIMIN path.

**Endpoints (exploratory, no superiority claim):**
- R²-AULC over B0–B24, mean over the 6 primary targets, with all 4 per-repeat values;
- R² at B4, B8, B16 and B24;
- sustained budget-to-target at a stricter level, 0.95 × R²_full(M0), because the 0.9 level is reached at B0;
- the share of paid runs with ST > 400 K.

**Code:** `src/rc18_transfer_design.py` imports the frozen modules unchanged and checks the final manifest.
