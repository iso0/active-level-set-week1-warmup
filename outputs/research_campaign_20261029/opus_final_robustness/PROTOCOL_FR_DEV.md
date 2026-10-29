# FR step 2: the one candidate (GATE), its control and the DEV rule. Registered before any DEV gate result

Written 2026-10-29 around 14:20 UTC. The gain-area gate passed (`gain/GAIN_AREA.json`):
- **G1:** oracle room 0.049.
- **G2:** META +0.021 [LCB +0.012] on geometric blocks; STD early +0.0005.

The DEV gain area also shows a constraint:
- K5 (A better) and K4 (C1 better) point in opposite directions.
- The fixed average AVG loses early on STD (−0.0014) and on K4 (−0.014).

So the only lawful signal is each model's honest performance away from the data, measured on the paid runs themselves.

## Candidate GATE (`src/fr_gate.py`; the only candidate)

p_GATE(x) = w(x) · p_C1(x) + [1 − w(x)] · p_A(x), where:
- w(x) = σ(a + c · u(x));
- u(x) = clip(log(d(x, L) / s_L), −2, 2).

**Terms:**
- p_C1 and p_A: the unchanged C1 pipeline (`src/ea_cand.py` SYSTEMS["C1"]) and HA_LEAN pipeline (`src/rc23_common.state`), fitted on the full paid set L.
- d(x, L): the distance from x to its nearest paid run, in the public standardised log inputs (`src.rc19_pool.zstd`).
- s_L: the median nearest-neighbour spacing of the paid runs.

**(a, c)** are a MAP estimate.
- **Prior:** a ~ N(0, 1.5²), c ~ N(0, 1).
- **Likelihood:** Bernoulli on the paid labels under q_i = w_i · p1_i + (1 − w_i) · p2_i.
- **Nested out-of-fold predictions p1_i, p2_i:**
  - The paid runs are split into G = 4 spatial groups: k-means on their public inputs, n_init 4, seed 0.
  - For each group, both FULL pipelines are refitted on the other groups only, their own inner K = 10 cross-fits included.
  - So neither the label nor the depth nor any output of a held-out run enters its own prediction.
  - u_i is measured to those training runs.
- **Refit schedule:** at b = 16, 20, …, 60. A fit is reused until the next refit; u(x) always comes from the current paid set.

**Defined behaviour:**

| situation | behaviour |
|---|---|
| data insufficient: b < 16, or fewer than 4 depth-usable paid runs of either class at a refit | w = 1, i.e. C1 unchanged (C1's early behaviour is kept by construction for b < 16) |
| one class among the paid labels | both pipelines return the paid mean, so GATE does too; margin follows the label-free path, as C1 does |
| missing depth | handled inside the unchanged pipelines in every refit |
| reduction | w ≡ 1 must give C1 + margin exactly (same path, same probabilities); w ≡ 0 must give HA_LEAN + margin exactly |
| shadow test | flipping the labels and permuting the outputs of all never-opened runs must leave the path, the probabilities and the gate parameters identical |

**Inputs never read:** test labels, unopened outputs, campaign id, short-Keyhole or hard-group membership, OLD/NEW. There is no region rule; the corner and the blocks are not inputs.

**Selector:** margin −|p_GATE − 0.5|, first index on ties (the C1 convention).

**Control AVG:** a fixed w = 0.5 at the same paid data. It shows whether the local, learned rule is needed.

## How GATE differs from what was already tested

| earlier attempt | how it differs from GATE |
|---|---|
| EL-2 E | global Laplace-evidence weights between two ML-II emulators (HA_LEAN, HA_TREND). GATE instead uses nested, spatial out-of-fold predictive likelihood of the two FULL pipelines (C1 with its MAP prior, and HA_LEAN); its weight depends on x through geometric support; it has a fixed C1 fallback |
| a generic C1 / HA_TREND mixture | GATE mixes C1 with HA_LEAN, not with HA_TREND |
| RC21 residual GP | GATE adds no new emulator; it only reweights two fixed pipelines |
| AVG4 / hysteresis | those smooth over time; GATE does not |
| BA_RISK, JEER, coverage | those change acquisition; GATE keeps plain margin on its own probability |

## DEV data: limited replay of recorded paths, no new simulation

The gate weights are computed along recorded paid paths, then combined with the recorded p_C1 and p_A at the same prefixes (model effect):
- **STD:** 163–182, both paths (EA validation), 200 learner-paths.
- **K5:** 33–40 on A's path (EA cand-DEV) and 41–48 on both paths, test regions with both classes only.
- **K4:** 17–24 on A's path and 25–32 on both paths.

**Smoke:** reduction w ≡ 1 / w ≡ 0 against the recorded EA units STD r163 f1; the shadow test; own-path cost for STD r163 f1 and K5 s41 b2.

## DEV rule to carry GATE to a fresh test (fixed now)

All three must hold. Contrasts are GATE − C1 at identical paid data; cluster means; one-sided 95 % t-bounds.

| rule | condition |
|---|---|
| C-GEO | geometric per-region BA-AULC B8–B60 (K5 and K4 startup clusters): mean ≥ +0.010 and LCB > 0 |
| C-EARLY | STD BA-AULC B8–B24: LCB ≥ −0.003 |
| C-LATE | STD BA-AULC B25–B60: LCB ≥ −0.003 |

**Reported, not in the rule:**
- GATE − AVG and GATE − A;
- K5 and K4 separately;
- the hard-group recall and specificity;
- the out-of-fold diagnostics (do the paid runs prefer A where A is better?).

**Outcomes:**
- C-GEO fails: the task closes. A paid-only gate does not capture the gain area, so no fresh test is run.
- C-GEO holds but C-EARLY or C-LATE fails: the task closes on harm.
- The development limit stays 75 min of wall time.
