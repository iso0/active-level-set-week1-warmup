# Exploratory ideas EX1 and EX2: results, mechanism, and what they do not show

## Status
- **Exploratory.** Each idea has its own manifest (mechanism, prediction, controls, bounded plan), committed in `3afad1dc` before any EX fit. The results were committed in `28f9a932`.
- **Data:** DEV repeats 5–8 only. No J model had been fitted on them before; Stage M used repeats 1–2 and Stage A reserves 3–4.
- **Unchanged decisions:** the frozen Stage M decision (screen failed) and the C3 decision (not confirmed) stand. Nothing here is a confirmation.
- **How to read the numbers:**
  - Each is a mean over the four repeats, with a 95 % class-stratified simulation-cluster bootstrap interval (2000 draws).
  - The intervals are conditional on the stored fits and splits.
  - BA is pooled over the five folds within each repeat, so every NEW simulation is scored once per repeat.
- **POST-HOC sections (§3, §4):** these were computed from stored predictions after the results were seen (`src/jdl_ex_descriptive.py`, outputs in `POSTHOC_descriptive/`). They describe where the registered effects come from; they are not tests.

## Errata of 2026-10-14 (claims narrowed; every number, manifest and decision below is unchanged)
- **[E1] The paid-prevalence rule is a heuristic.**
  - The mechanism in §1 holds for probabilities calibrated to the target population and for that population's prevalence.
  - π̂, the paid fraction of a feature-only maximin prefix, is not an unbiased estimate of that prevalence.
  - Under posterior uncertainty, the BA-optimal action is in general not a single plug-in cutoff.
  - p ≥ π̂ is therefore a train-only heuristic, and its EX1 gain is an empirical result, not the confirmation of an optimum.
- **[E2] Small effects do not establish physical identifiability or irrelevance.**
  - "ST is effectively irrelevant" means that paid-data ML-II put its lengthscale at the bound.
  - "θ and δ stay unidentified" means that the fixed-prior ablations changed little.
  - Neither statement is a physical identifiability or relevance result.
- **[E3] No discriminator among those tested does not mean that none exists.**
  - "No model discriminates", "depth cannot resolve it" and "a property of the NEW data, not of a model" go too far.
  - What is supported: none of the tested models and rules (E1, G3, Binary_matched, J, J_trained; at 0.5 and π̂) separated the fast-corner cases on DEV repeats 5–8, and the depths observed there overlap.
- **[E4] The candidate was chosen on global BA, which is not a sufficient selection criterion.**
  - §7 proposed J_trained at π̂ (BA 0.906) as the single candidate. That version buys its global BA by labelling the fast corner "no Keyhole".
  - The cost: short-K sensitivity falls from 0.675 at 0.5 to 0.05 at π̂, and each NEW negative weighs as much in BA as about ten positives.
  - J_trained at 0.5 (BA 0.752, short-K 0.675) is a serious complete-system comparator and is carried forward alongside it; see `EX_METRICS_ADDENDUM.md`.
  - The V2 comparison uses the 0.5 rule as primary and π̂ only as a secondary rule.
- **[E5] The VX > 0.85 rule is an explanatory reference from earlier inspection, not an independently trained competitor.**
  - The V2 comparison adds a stump whose cut and orientation are learned from the paid labels only.

## 1. The two ideas as registered

| | **EX1: decision rule aligned with BA** | **EX2: response prior trained on paid depths** |
|---|---|---|
| **Mechanism** [E1] | BA weights the two classes equally. For a calibrated probability p, the BA-optimal decision is p ≥ π (the class prior), not p ≥ 0.5. On NEW, π is about 0.88–0.91. | The frozen response prior is isotropic: amplitude 0.60 and lengthscale 1.5 on all four standardized log inputs. It smooths slow-scan depths into the fast-scan corner. For the fast-scan NEW negatives, J predicted f = 0.10–0.42 where the observed z ran from −0.33 to +0.17 (Stage M mechanism report). |
| **What changes** | π̂ = share of positives among the paid labels at the checkpoint (train-only). Decisions at p ≥ π̂ are compared with decisions at p ≥ 0.5 on the same stored probabilities. | At every checkpoint, the response amplitude and the four lengthscales are set by ML-II on the paid responses only (noise fixed at 0.03, zero mean). The θ, δ and τ priors are unchanged. |
| **Fits** | 320: NEW arms J, Binary_matched, ACTIVE_E1 and G3; OLD/POOLED arms J and Binary_matched; budgets B16 and B40 | 120: J_trained in every population, same paths |
| **Registered** | P1–P4 directional; P5 (OLD/POOLED) reported only | P1–P2 directional; P3 (OLD/POOLED) reported only |

## 2. Results against the registered predictions (NEW, B40, DEV repeats 5–8)

| Prediction | Registered expectation | Result | Verdict |
|---|---|---|---|
| EX1-P1 | J: BA(p ≥ π̂) − BA(p ≥ 0.5) > 0 | 0.543 → 0.878: **+0.335 [+0.241, +0.419]**; repeats +0.344, +0.310, +0.340, +0.344 | supported |
| EX1-P2 | the gain comes from specificity at a sensitivity cost | specificity +0.813 (0.104 → 0.917); sensitivity −0.143 (0.982 → 0.839) | supported |
| EX1-P3 | Binary_matched: same rule gives ≤ 0 | 0.568 → 0.501: **−0.067 [−0.133, −0.012]**. At π̂ it predicts almost nothing positive (sensitivity 0.002), because its depth-free probabilities stay below the paid prevalence. | supported |
| EX1-P4 | J at π̂ beats ACTIVE_E1 at its own frozen 0.5 rule | 0.878 vs 0.682: **+0.196 [+0.074, +0.318]** | supported |
| EX2-P1 | J_trained has lower held-out response RMSE than J (all runs, and fast scans separately) | all runs: 0.175 → 0.084, **−0.091 [−0.113, −0.070]**. Fast scans: 0.236 → 0.117. | supported |
| EX2-P2 | at π̂, BA(J_trained) ≥ BA(J) and log loss not worse | BA 0.878 → 0.906: **+0.028 [+0.012, +0.047]**; repeats +0.032, +0.024, +0.024, +0.032. Log loss 0.214 → 0.166 (−0.048 [−0.073, −0.020]). | supported |

**Also reported by the frozen EX evaluations (not registered predictions):**
- **B16:**
  - EX1-P1 analogue: +0.292 [+0.198, +0.371].
  - EX2 BA at π̂: +0.097 [+0.066, +0.134].
- **J at π̂ against the frozen systems given the same rule:**
  - ACTIVE_E1: +0.149 [+0.042, +0.267].
  - G3 at 0.5: +0.234 [+0.137, +0.334].
  - Binary_matched: +0.377 [+0.282, +0.441].
- **ACTIVE_E1 and G3 at π̂ instead of 0.5:** +0.047 [+0.006, +0.097] and +0.044 [−0.038, +0.126].
- **EX2 at the 0.5 rule:** BA +0.209 [+0.110, +0.310] (0.543 → 0.752).

**Secondary populations (no directional expectation was registered):**

| Population (B40) | EX1: J, π̂ − 0.5 | EX1: Binary_matched, π̂ − 0.5 | EX2: J_trained − J, BA at π̂ | EX2: log loss | EX2: response RMSE |
|---|---|---|---|---|---|
| OLD (paid prevalence ≈ 0.27) | +0.024 [−0.001, +0.050] | −0.048 [−0.087, −0.007] | +0.010 [−0.002, +0.021] | −0.035 [−0.044, −0.025] | −0.033 [−0.044, −0.022] |
| POOLED (≈ 0.37) | −0.004 [−0.013, +0.005] | −0.007 [−0.021, +0.007] | +0.007 [+0.001, +0.014] | −0.018 [−0.026, −0.010] | −0.031 [−0.039, −0.023] |

## 3. Where the NEW effect comes from (POST-HOC, by full simulation ID)

### 3.1 The twelve NEW negatives
Each count is the number of the four repeats (B40) in which the negative was predicted Keyhole, i.e. a false positive.

| Simulation (full ID) | VX (m/s) | A (µm) | fast scan | recording ended early | E1 0.5 | G3 0.5 | Binary 0.5 | J 0.5 | J π̂ | J_trained 0.5 | J_trained π̂ |
|---|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| `P-423p267621988_VX-0p332154005524_LS-4p22725332613e-05_ST-473p308549274_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-1p45237465838e-05_H-e7dbd8e5ce` | 0.332 | missing | no | yes | 4 | 4 | 4 | 4 | 4 | 4 | 4 |
| `P-376p749294588_VX-0p89878118514_LS-4p48900537333e-05_ST-301p683894272_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p36740274805e-06_H-2e066980ca` | 0.899 | 115.1 | yes | no | 4 | 4 | 3 | 4 | 0 | 2 | 0 |
| `P-372p400266258_VX-0p904171786761_LS-4p46899874615e-05_ST-344p55726366_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p3354027118e-06_H-1d4ea0f649` | 0.904 | 111.6 | yes | no | 4 | 1 | 1 | 1 | 0 | 0 | 0 |
| `P-369p593326825_VX-0p912334588191_LS-4p43771409089e-05_ST-483p802696386_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p28766602238e-06_H-29cf03a279` | 0.912 | 131.2 | yes | no | 4 | 4 | 4 | 4 | 0 | 4 | 0 |
| `P-360p512213414_VX-0p918600295589_LS-4p99465552486e-05_ST-350p063552758_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p25159922785e-06_H-be08daa72c` | 0.919 | 107.3 | yes | no | 1 | 3 | 3 | 4 | 0 | 0 | 0 |
| `P-353p784791664_VX-0p953661701626_LS-4p00659722232e-05_ST-310p795032219_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p05852399734e-06_H-f4fc937e86` | 0.954 | 110.8 | yes | no | 3 | 1 | 4 | 4 | 0 | 1 | 0 |
| `P-387p361336282_VX-0p960187357846_LS-4p72484046084e-05_ST-390p52586458_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p02414509376e-06_H-b302fc6cbd` | 0.960 | 115.6 | yes | no | 2 | 2 | 3 | 3 | 0 | 2 | 0 |
| `P-361p800115091_VX-0p960992922817_LS-4p74221265218e-05_ST-336p90191265_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p01993353798e-06_H-6f28bdc6c9` | 0.961 | 79.4 | yes | no | 0 | 3 | 3 | 3 | 0 | 1 | 0 |
| `P-382p345911972_VX-0p96482137946_LS-4p36339294138e-05_ST-407p155631275_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p00001420544e-06_H-ce04be44b1` | 0.965 | 87.3 | yes | yes | 3 | 3 | 4 | 4 | 0 | 3 | 0 |
| `P-426p768553369_VX-0p970152058637_LS-4p12602194162e-05_ST-379p997827854_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-4p97254070645e-06_H-b2eec677b1` | 0.970 | 118.8 | yes | no | 4 | 4 | 4 | 4 | 0 | 4 | 0 |
| `P-380p582137919_VX-0p978166332261_LS-4p83858659008e-05_ST-415p110382592_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-4p93179988302e-06_H-210d3fce7d` | 0.978 | 98.7 | yes | no | 0 | 1 | 4 | 4 | 0 | 1 | 0 |
| `P-353p345541692_VX-0p9799872487_LS-4p48105452089e-05_ST-375p566167213_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-4p92263609492e-06_H-3172b413b1` | 0.980 | 90.8 | yes | no | 0 | 2 | 3 | 4 | 0 | 0 | 0 |

- **At π̂, J and J_trained reject all 11 fast-scan negatives in every repeat.**
- **One false positive remains under every model and rule** (except Binary_matched at π̂, which predicts almost nothing positive). It is `P-423p267621988_VX-0p332154005524_LS-4p22725332613e-05_ST-473p308549274_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-1p45237465838e-05_H-e7dbd8e5ce`:
  - the only NEW negative outside the fast-scan corner;
  - its recording ended early, and it has no active-window depth A;
  - it alone sets the specificity ceiling of 11/12 = 0.917 that J reaches at π̂ in every repeat.
  - Its label, exclusion status and missing A are preserved. Whether "no Keyhole" describes the physics or the truncated record is a data-support question that this study cannot settle.
- **ACTIVE_E1 at 0.5** (which never sees a test depth) rejects, in every repeat, three of the four fast negatives with A below 100 µm. The exception is the early-ended `P-382p345911972_VX-0p96482137946_LS-4p36339294138e-05_ST-407p155631275_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p00001420544e-06_H-ce04be44b1`. It is wrong in 21 of 24 cases for the six fast negatives with A ≥ 110 µm, where depth says Keyhole.

### 3.2 The positives the π̂ rule gives up
False negatives per repeat (mean over the four repeats, B40; NEW has 124 positives, 12 of them fast scans and 10 short-K):

| Arm and rule | all | fast scan | rest | short-K |
|---|---:|---:|---:|---:|
| ACTIVE_E1, 0.5 | 4.00 | 4.00 | 0.00 | 3.00 |
| G3, 0.5 | 5.75 | 5.50 | 0.25 | 4.50 |
| Binary_matched, 0.5 | 3.75 | 2.25 | 1.50 | 2.25 |
| J, 0.5 | 2.25 | 2.25 | 0.00 | 1.50 |
| **J, π̂** | **20.00** | 11.75 | **8.25** | 9.75 |
| J_trained, 0.5 | 4.75 | 4.75 | 0.00 | 3.25 |
| **J_trained, π̂** | **13.00** | 11.50 | **1.50** | 9.50 |

- **The π̂ rule gives up almost every fast-scan positive,** and with them almost all short-K (brief-keyhole) positives.
- **EX2's +0.028 at π̂ comes from slow, deep positives.** The frozen prior had left them below π̂; there were 8.25 such misses per repeat. Examples, missed by J in 2–4 of 4 repeats: VX 0.21–0.78 m/s with A = 225–303 µm. The trained prior keeps 1.5 such misses per repeat, mainly `P-351p157464561_VX-0p813888376043_LS-4p78494456981e-05_ST-349p508071973_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p92725089215e-06_H-bba3700d20` at VX 0.814 and A 142 µm.
- **The table below lists the positives J_trained misses at π̂ in at least 2 of 4 repeats.** All of them are fast scans except the VX 0.814 run just named.

| Arm | Simulation (full ID) | repeats missed (of 4) | VX (m/s) | A (µm) | fast scan | short-K | mean p |
|---|---|---:|---:|---:|---|---|---:|
| J_trained | `P-351p157464561_VX-0p813888376043_LS-4p78494456981e-05_ST-349p508071973_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p92725089215e-06_H-bba3700d20` | 4 | 0.814 | 142.2 | no | no | 0.800 |
| J_trained | `P-351p92267109_VX-0p98107853237_LS-4p98248594664e-05_ST-477p481832276_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-4p91716049617e-06_H-349225d53c` | 4 | 0.981 | 79.0 | yes | no | 0.304 |
| J_trained | `P-356p512304128_VX-0p915902400152_LS-4p25307438822e-05_ST-398p167342825_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p26706841495e-06_H-5a876064ac` | 4 | 0.916 | 123.3 | yes | yes | 0.568 |
| J_trained | `P-366p200299346_VX-0p894349968262_LS-4p89176892953e-05_ST-476p393782659_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p39399650496e-06_H-6ca7f366ce` | 2 | 0.894 | 111.3 | yes | yes | 0.924 |
| J_trained | `P-380p041479483_VX-0p952843483906_LS-4p56527036263e-05_ST-376p177191048_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p0628678104e-06_H-b7e3ed2e12` | 4 | 0.953 | 112.3 | yes | yes | 0.240 |
| J_trained | `P-380p999402419_VX-0p875337770389_LS-4p81159771741e-05_ST-321p053866736_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p51115325558e-06_H-35aba40198` | 4 | 0.875 | 124.9 | yes | yes | 0.531 |
| J_trained | `P-391p205274968_VX-0p925842355033_LS-4p23814583284e-05_ST-496p182210661_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p21052053494e-06_H-3af0d97597` | 4 | 0.926 | 144.4 | yes | yes | 0.616 |
| J_trained | `P-391p835745622_VX-0p97812625082_LS-4p53819703986e-05_ST-409p919098726_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-4p93200197722e-06_H-24e1882408` | 4 | 0.978 | 111.8 | yes | yes | 0.479 |
| J_trained | `P-395p034741205_VX-0p948017796542_LS-4p62627342543e-05_ST-456p720388169_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p08863928569e-06_H-6dae2a1270` | 4 | 0.948 | 119.3 | yes | yes | 0.658 |
| J_trained | `P-403p038889513_VX-0p985529827275_LS-4p01644776726e-05_ST-436p069675401_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-4p89495139518e-06_H-8827d7eb9a` | 4 | 0.986 | 119.4 | yes | yes | 0.566 |
| J_trained | `P-406p355211464_VX-0p957561000575_LS-4p64266873864e-05_ST-388p32623861_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p03792510359e-06_H-85317ef64f` | 4 | 0.958 | 119.2 | yes | yes | 0.624 |
| J_trained | `P-406p380830901_VX-0p951683507815_LS-4p66758065298e-05_ST-424p48123111_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p06903877539e-06_H-f557a9383e` | 4 | 0.952 | 120.4 | yes | yes | 0.782 |
| J_trained | `P-421p195263483_VX-0p917377630556_LS-4p41837964853e-05_ST-310p141031825_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p25859846843e-06_H-a35fd4b93e` | 4 | 0.917 | 147.8 | yes | no | 0.542 |

The corresponding list for J is in `POSTHOC_descriptive/NEW_missed_positive_ids.csv`.

### 3.3 Inside the fast-scan corner, no model discriminates [E3: none of the tested models did]
- **The corner:** 23 NEW runs with VX > 0.85 m/s, of which 12 are positive and 11 negative. Their depths overlap: fast positives have A = 79–148 µm and fast negatives A = 79–131 µm.
- **Week 19 already saw this:** its matched fast-scan pair had the same startup depth peak and opposite recorded labels.
- **Balanced accuracy inside the corner** (B40, mean over repeats; `POSTHOC_descriptive/NEW_BA_inside_vs_outside_fast_corner.csv`):

| | E1 0.5 | G3 0.5 | Binary 0.5 | J 0.5 | J π̂ | J_trained 0.5 | J_trained π̂ |
|---|---:|---:|---:|---:|---:|---:|---:|
| BA inside the corner (12 positives, 11 negatives) | 0.549 | 0.453 | 0.497 | 0.463 | 0.510 | 0.598 | 0.521 |

- Every value is close to chance on 23 runs.
- At π̂, the joint model treats the corner as "no Keyhole" as a whole: specificity 1.0 and sensitivity about 0.02–0.04 inside it.
- **A reference point, not a learner:** "predict no Keyhole iff VX > 0.85 m/s" gives NEW BA **0.910** (sensitivity 112/124 = 0.903, specificity 11/12 = 0.917).
  - J_trained at π̂ reaches 0.906, and J at π̂ reaches 0.878.
  - The 0.85 cut was set in Week 19 after inspecting these NEW data, so this rule is not a fair competitor. It shows what the NEW BA gain at π̂ consists of: a fast-corner split learned from the paid data, not a resolution of the corner.

### 3.4 What the response prior learned
Median ML-II estimates over all fits (`POSTHOC_descriptive/EX2_learned_response_hyperparameters.csv`). The frozen prior is lengthscale 1.5 on all inputs, amplitude 0.60; the bounds are [0.05, 20].

| Population, budget | P | VX | LS | ST | amplitude | ST at the upper bound |
|---|---:|---:|---:|---:|---:|---:|
| NEW, B16 | 13.9 | 1.60 | 17.7 | 20.0 | 0.65 | 20/20 |
| NEW, B40 | 9.8 | 1.52 | 9.6 | 20.0 | 0.60 | 15/20 |
| OLD, B16 | 3.9 | 4.05 | 6.6 | 20.0 | 0.93 | 18/20 |
| OLD, B40 | 2.8 | 2.53 | 3.7 | 20.0 | 0.86 | 15/20 |
| POOLED, B16 | 3.3 | 3.83 | 5.5 | 20.0 | 0.98 | 14/20 |
| POOLED, B40 | 2.2 | 2.44 | 3.8 | 20.0 | 0.76 | 17/20 |

- **On NEW, depth varies mainly with scan speed;** VX has the only short lengthscale.
- **ST is effectively irrelevant everywhere:** it sits at the upper bound in 99 of 120 fits. [E2: a property of these ML-II fits, not a physical irrelevance result]
- **Warnings:** sklearn raised a bound warning in 102 of the 120 fits. These are recorded and were not acted on.
- **Defect:** the field `learned_lengthscales_median_NEW_B40` in `EX2_RESULTS.json` lists the first three NEW B40 fits, not medians. The values above replace it; the results file is left as written.

## 4. The EX2 candidate next to the frozen systems (POST-HOC, same estimator)
`POSTHOC_descriptive/complete_system_contrasts.csv`

| NEW, B40 | J_trained at π̂ minus … |
|---|---|
| ACTIVE_E1 at its frozen 0.5 rule | **+0.224 [+0.104, +0.346]** |
| ACTIVE_E1 at π̂ | +0.177 [+0.069, +0.294] |
| G3 at 0.5 / at π̂ | +0.262 [+0.168, +0.360] / +0.219 [+0.148, +0.267] |
| Binary_matched at 0.5 / at π̂ | +0.338 [+0.249, +0.420] / +0.405 [+0.313, +0.466] |

**Under the frozen 0.5 rule, J_trained − Binary_matched BA at B40:**
- NEW +0.184 [+0.100, +0.268];
- OLD +0.063 [+0.037, +0.091];
- POOLED +0.011 [−0.001, +0.023].

For comparison, the frozen Stage M J − Binary_matched values on repeats 1–2 were +0.006 (NEW), +0.067 (OLD) and +0.016 (POOLED).

## 5. What EX1 and EX2 show, and what they do not

**They show** (exploratory, on fresh DEV repeats, in the registered directions):
1. **The Stage M failure on NEW is not evidence that paid depth carries no label information.** At about 90 % paid prevalence, the 0.5 rule hides J's better ranking. The BA-aligned rule recovers +0.335, while the depth-free matched model loses with the same rule (−0.067).
2. **The frozen response prior is a second, separate defect.** Training its amplitude and lengthscales on the paid depths:
   - halves the held-out depth error (fast scans 0.236 → 0.117);
   - adds +0.028 BA at π̂ and +0.209 at 0.5;
   - improves log loss in all three populations.
3. **On OLD, paid depth adds label information at either rule:** J_trained − Binary_matched at 0.5 is +0.063, consistent with Stage M's +0.067 for J. On POOLED the gain is small (+0.011).

**They do not show:**
1. **That depth resolves the NEW fast-scan boundary.** Inside the corner every model is near chance, and at π̂ the joint model labels the whole corner "no Keyhole". [E3]
2. **That the candidate beats a one-feature split on NEW.** Its BA (0.906) equals that of the Week 19 VX cut (0.910). [E5: an explanatory reference, not a trained competitor; the paid-trained stump is in the V2 comparison]
3. **Anything about acquisition.** All paths are feature-only maximin.
4. **A magnitude that should be expected elsewhere.** DEV repeats 1–8 and the C1–C3 blocks have all been inspected, and the 0.85 cut itself came from inspecting NEW.

## 6. Defects and omissions (all in `ATTEMPT_LEDGER.md`)
- **Mislabelled field:** the EX2 lengthscale field (§3.4).
- **AUC not computed:** the EX2 manifest lists AUC among its outcomes, but its evaluate step did not compute it. It is completed post hoc from the stored probabilities in `POSTHOC_descriptive/AUC_per_repeat.csv` (row EX-D2).
- **No re-runs:** the EX runs were not re-run, and no rule, prior or split was chosen on the EX results.

## 7. Independently discovered, and the most efficient next test

**Discovered in this study** (not given by the brief or by Astra's package):
1. **The frozen Stage M screen failed because of its decision rule and its response prior, not because depth lacks label information.** Both repairs were predicted before they were run, and both held on fresh DEV repeats with their controls:
   - the depth-free model gets worse under the same rule;
   - the trained prior lowers depth error first, and BA second.
2. **After both repairs, NEW balanced accuracy is a fast-corner split.**
   - The joint model rejects all 11 fast-scan negatives and gives up nearly all 12 fast-scan (mostly short-K) positives.
   - Inside the corner, no model in the study is better than chance, because depth at the 111 µm reference does not separate the labels there. [E3]
   - The one persistent NEW false positive is a slow scan whose recording ended early and which has no A.
   - This ceiling is a property of the NEW data, not of a model. [E3: overstated. It is a ceiling of the tested models on these data]
3. **At B16–B40 the threshold θ and the discrepancy δ stay unidentified.** [E2]
   - In Stage M, the fixed-θ and no-δ ablations perform like J: NEW B40 BA 0.552 / 0.552 / 0.575 and AUC 0.873 / 0.878 / 0.876.
   - The posterior SD of θ stays between 0.14 and 0.27, against a prior SD of 0.35.
   - The label information passes through f, so the joint model's value lies in its response model and decision rule, not in its threshold or discrepancy terms.

**The most efficient next test:**
- **[E4: superseded. Do not select the π̂ version on global BA. J_trained at 0.5 is carried as a serious comparator, and the V2 comparison is the next frozen model study.]**
- **What:** freeze one candidate, J_trained (paid-only ML-II response prior) with the π̂ rule, and run it once as the C4 stability check that is already drafted (new seed namespace, NEW/OLD/POOLED, four repeats, feature-only paths, B16/B40).
- **Arms:** the candidate, plus four frozen comparators:
  - ACTIVE_E1 and G3 at 0.5;
  - Binary_matched at both rules;
  - a **train-only** one-feature stump on VX (cut chosen on the paid labels only).
- **Primary endpoint:** NEW B40 BA, candidate minus ACTIVE_E1.
- **Required secondary endpoints:**
  - candidate minus stump;
  - BA inside the fast corner;
  - OLD and POOLED not worse than −0.01.
- **Cost:** about 600 fits, under one CPU-minute. The only scarce resource is the unused partitions, which is why it should be a single frozen run.
- **What it answers:** whether the repaired model generalises beyond the DEV partitions, and whether it adds anything beyond the speed split.
- **Outside this request:** if the corner is the scientific target, depth cannot resolve it [E3: the tested depth models did not]. That needs new simulations placed inside the corner, which would require simulator time.
- **Authorisation:** C4 and any simulator work need an owner decision; this study runs neither.
