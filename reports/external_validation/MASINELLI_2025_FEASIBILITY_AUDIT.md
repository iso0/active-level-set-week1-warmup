# Masinelli et al. (2025) external-validation feasibility audit

## Decision

**Overall external-validation value: TIER A.** The public record supports a small, independent experimental transfer study. It does **not** support an exact label replication, a test of the spot-radius exponent, or a bit-exact reproduction of the authors' optical active-learning path without reconstruction work.

| Level | Decision | Why |
|---|---|---|
| A — static experimental validation | **GO WITH CAVEATS** | Per-alloy process inputs and independent metallographic labels are public; effective design is only 38 unique conditions and labels are non-identical to the thesis. |
| B — finite-pool AL replay | **GO WITH CAVEATS** | Four 20-condition experimental pools can be reconstructed exactly for a new metallographic-label replay; the authors' published optical-label path is only partially reconstructable. |
| C1 — within-material bare coordinate | **GO WITH CAVEATS** | `h` is computable, but constant `LS` makes it equivalent in rank to `P/sqrt(VX)` and cannot test the `LS^-3/2` exponent. |
| C2 — material-normalized transfer | **GO WITH CAVEATS** | Gan-type constants exist for Ti64 and SS316, but absorptivity was not measured for these builds and the SS316 constants are not batch-specific 316L constants. Treat this as a high-uncertainty sensitivity. |

The immediate next experiment should be **Level A only**, as specified in `future_experiment_spec.md`. No external model was fitted in this audit.

## 1. Sources and provenance

Primary sources were inspected directly:

- Masinelli et al., [full open-access paper](https://infoscience.epfl.ch/server/api/core/bitstreams/e512f942-f109-42be-ab53-4cdfab406af5/content), *Additive Manufacturing* 101 (2025) 104677, DOI [`10.1016/j.addma.2025.104677`](https://doi.org/10.1016/j.addma.2025.104677).
- Public code/metadata repository pinned at GitHub commit [`50ccb1bab03c626cb9f83d9c4f44182f58dda439`](https://github.com/GiulioMa/LPBF-SmartAM-Optical-Data/tree/50ccb1bab03c626cb9f83d9c4f44182f58dda439).
- Public raw dataset [Zenodo record 13380755](https://zenodo.org/records/13380755), DOI `10.5281/zenodo.13380755`, one 86,809,466-byte ZIP, MD5 `7c45f40bef66bc2483eb1ef0959058cc`, CC-BY-4.0.
- Physics normalization: Gan et al. (2021), [primary article and Eq. 1](https://www.nature.com/articles/s41467-021-22704-0) and its [Supplementary Information](https://static-content.springer.com/esm/art%3A10.1038%2Fs41467-021-22704-0/MediaObjects/41467_2021_22704_MOESM1_ESM.pdf).

No third-party paper, repository copy, ZIP, raw signal, or spreadsheet is committed here. Counts below were obtained by reading the public workbooks in memory and joining their declared keys.

## 2. Required paper evidence table

| Field | Finding | Status | Primary location |
|---|---|---|---|
| A. Title | *Autonomous exploration of the PBF-LB parameter space: An uncertainty-driven algorithm for automated processing map generation* | VERIFIED | Paper p. 1 |
| B. Authors | Giulio Masinelli; Lucas Schlenger; Kilian Wasmer; Toni Ivas; Jamasp Jhabvala; Chang Rajani; Amirmohammad Jamili; Roland Logé; Patrik Hoffmann; David Atienza | VERIFIED | Paper p. 1 |
| C. Year | 2025 | VERIFIED | Journal citation |
| D. Journal | *Additive Manufacturing* | VERIFIED | Paper p. 1 |
| E. DOI | `10.1016/j.addma.2025.104677` | VERIFIED | Paper p. 1 |
| F. Alloys | Ti–6Al–4V Grade 23; 316L stainless steel | VERIFIED | Sections 2.6; Tables 2–3 |
| G. Machine/setup | Laboratory PBF-LB machine, SPI 500 W fiber laser, AXIALSCAN FIBER-30; dual photodiodes; 200 kS/s | VERIFIED | Section 2.1 |
| H. Laser wavelength | The reflected-laser channel is centered at 1070 nm; a separate explicit laser-output wavelength specification was not found | AMBIGUOUS | Section 2.1 |
| I–L. Spot definition | 50 µm **diameter**, at focal point, measured at `1/e²`, constant | VERIFIED | Section 2.6 |
| M. Power domain | 90–120 W | VERIFIED | Table 4; Tables 15–16 |
| N. Scan-speed domain | 300–1800 mm/s | VERIFIED | Table 4; Tables 15–16 |
| O. Bed/substrate temperature | Room temperature, approximately 25 °C | VERIFIED | Table 4 |
| P. Other fixed parameters | 100 µm hatch; 80 µm deposited layer, described as steady-state-equivalent 40 µm; same-material substrate; Ar 1.5 m/s; O2 ≤0.01% | VERIFIED | Table 4 |
| Q. Regime classes | Raw codes `C`, `T`, `CT`, `TK`, `K`; published binary Conduction vs Transition/Keyhole | VERIFIED | `Microscopy_1.xlsx`; Section 2.3 |
| R. Ground truth | Multiple Aqua-regia-etched cross-sections at 500 µm spacing; final visible track; predominant regime; MAR and boundary curvature | VERIFIED | Sections 2.7 and 3 |
| S. Experiments/tracks | 120 labelled bundles total, 10 lines per bundle, 1,200 analyzed lines | VERIFIED | Sections 2.6–2.7 |
| T. Unique conditions | 38 unique `(P,VX)` pairs per alloy among 60 labelled bundles | VERIFIED | Workbook join |
| U. Repeats | Ten within-bundle lines; 20-condition A/B grid repeated in C/D with changed order; E/F has two overlaps with the grid | VERIFIED | Section 2.6; workbooks |
| V. Public code | GitHub repository above | VERIFIED | Paper Section 6; live repository |
| W. Public data | Zenodo record above | VERIFIED | Paper Section 6; live record |

## 3. Dataset forensics

### 3.1 What is actually public

The GitHub tree contains 47 tracked entries: notebooks for DoE, signal segmentation, feature extraction, ground-truth inspection, clustering and iterative sampling; two process-parameter workbooks; `Microscopy_1.xlsx`; a small `GT` pickle; and figures. It does not contain the raw CSV signals. The `Data` folders contain only `.wmj3` project files.

Zenodo contains one ZIP with 442 entries. Its central directory exposes nine cubes per material, two channels, and ten `File_i.csv` bundle recordings per cube: 360 raw channel CSVs in total. These cover 90 bundle recordings per alloy, more than the 60 labelled bundles per alloy used in the paper. A raw signal file contains the sequential signal cycles for the ten lines of one bundle; labels are not embedded in these CSVs.

There is no single native table containing all variables. The clean reconstruction is:

1. `Microscopy_1.xlsx`: `(Material, Cube, Line, Mode)`.
2. `experiment_parameters_ref.xlsx`: sheet `CubeN`, local `#`/Line 1–10, `Speed (mm/s)`, `Power (W)`.
3. Join on `(material-specific cube, local line)`.
4. If raw optical data are needed later, join `CubeN/channel_k/File_i.csv` by cube and zero-based workbook row `i`.

The ground-truth notebook documents the published cuboid mapping:

- 316L: A/B = cubes 3/4; C/D = 5/6; E/F = 7/8.
- Ti64: A/B = cubes 1/2; C/D = 3/4; E/F = 7/8.

The `GT` pickle already contains a similar join, but a future implementation should reconstruct it from XLSX sources rather than deserialize an untrusted pickle.

### 3.2 Exact labelled counts

| Alloy | Bundle rows | Unique `(P,VX)` | Raw modes | Published binary counts | Pair counts (Keyhole/Conduction) |
|---|---:|---:|---|---|---|
| Ti–6Al–4V | 60 | 38 | C 26; K 22; T 8; CT 4; TK 0 | 34 / 26 | A/B 11/9; C/D 13/7; E/F 10/10 |
| 316L | 60 | 38 | C 37; K 11; T 6; CT 2; TK 4 | 23 / 37 | A/B 8/12; C/D 8/12; E/F 7/13 |

Each alloy has 18 repeated conditions appearing twice and two conditions appearing three times, giving 22 duplicate rows beyond 38 unique conditions. Ti64 has two binary-discordant repeats: `(120 W, 1300 mm/s)` and `(90 W, 1050 mm/s)` are `CT` in one pair and `C` in the other. 316L has no binary-discordant repeat, although four repeated conditions differ in their finer raw mode code. This is physical/label variability that a deterministic `P,VX` model cannot remove.

Class imbalance is moderate, not prohibitive: Ti64 is 56.7% positive; 316L is 38.3% positive. The unit of statistical independence is not 600 lines per alloy. At most there are 38 unique process settings per alloy, with bundle/cuboid structure retained.

## 4. Label compatibility

**Verdict: CLOSE BUT NON-IDENTICAL VALIDATION.**

The thesis positive label is experiment-level `has_keyhole`: at least one valid saved frame is manually Keyhole. Masinelli's ground truth is post-mortem and geometric: multiple etched cross-sections are examined, the predominant regime is assigned from melt-pool aspect ratio and curvature, and the final visible track of each ten-line bundle is used consistently. Their code maps every non-`C` code (`T`, `CT`, `TK`, `K`) to binary Keyhole; the paper explicitly states that transition characteristics are grouped with Keyhole.

The overlap is scientifically meaningful—both describe the Conduction–Keyhole boundary and use physical rather than model-generated labels for evaluation. The difference is material: a transient Keyhole frame in simulation need not leave a predominant keyhole-shaped cross-section, and an external transition code has no exact thesis counterpart. Results must therefore be described as independent, close-but-non-identical experimental validation, never exact replication.

## 5. Can `h` be computed?

Yes, for both alloys. Use SI units and the verified radius:

```text
r0 = 50 µm / 2 = 25e-6 m
h = P / sqrt(VX * r0^3)
```

`P` and `VX` are row-level public inputs; `r0` is constant for the complete study. The bare coordinate remains dimensional, with units `W s^(1/2) m^-2`.

Because `r0` is fixed,

```text
h = r0^(-3/2) * P / sqrt(VX)
log h = constant + log P - 0.5 log VX.
```

Therefore the within-study ordering is exactly the ordering of `P/sqrt(VX)`. A fitted intercept or standardization removes the constant. This dataset can test the fixed power/scan-speed direction on independent experiments. It cannot test the `LS^-3/2` exponent, distinguish radius from diameter by predictive ranking, or validate a universal numerical `h` threshold. The radius conversion still matters for reproducible numerical values and any later material normalization.

## 6. Level A — static validation

**FEASIBLE WITH CAVEATS / GO WITH CAVEATS.**

Analyze each alloy separately. The exact inputs are `P_W`, `VX_m_per_s`, constant `r0_m=25e-6`, and derived `log h`. The target is the authors' published binary mapping `C=0`, all transition/keyhole codes `=1`. The minimum comparison should be a generic two-slope log-process logistic model versus a one-coordinate `log h` logistic model; a frozen 2D GPC may be a secondary standard baseline.

Repeated identical `(P,VX)` settings must never cross train/test. Train-only scaling, thresholds and calibration are mandatory. Report ROC-AUC, PR-AUC, balanced accuracy, Keyhole recall, Conduction recall and Brier score. Use group-level paired uncertainty. A fixed sensitivity may exclude transition codes, but transition handling must not be selected after model results are seen.

The data are adequate for a compact transfer check, not for a large model zoo or precise universal-threshold estimation.

## 7. Level B — finite-pool AL replay

**PARTIALLY RECONSTRUCTABLE / GO WITH CAVEATS.**

The four published full-map pools used for iterative results are exactly identifiable: Ti64 A/B, Ti64 C/D, 316L A/B and 316L C/D, each with 20 bundle conditions. E/F is a one-power sensitivity design and is not a useful 2D AL pool. A clean new retrospective replay using the public metallographic labels is feasible.

The authors' policy is not pointwise thesis margin sampling:

- start with one randomly selected power level; the paper averages all three possible starts;
- conduct all 6 or 7 scan-speed experiments at that power;
- extract twelve optical statistics after averaging the ten tracks;
- use Spectral Clustering to create binary labels, assigning the lowest-speed cluster to Keyhole;
- fit a GPC on `(P,VX)`;
- calculate `1-max(p)` and select the unexplored **power block** with maximum mean uncertainty over speeds;
- continue until all three power levels have been sampled.

The paper states an anisotropic RBF with starting length scales `10.61 W` and `353.55 mm/s`. The notebook uses `ConstantKernel * RBF` in scikit-learn with default optimization still enabled, so the stated values are initial values rather than demonstrably frozen final hyperparameters.

Exact publication-path reproduction is qualified because the notebooks expect generated `*_feat.pkl` files that are excluded by `.gitignore` and absent from Zenodo, no machine-readable query-path log is saved, dependency versions are not locked, and the clustering/GP stack can vary by library version. `Save_feat.ipynb` plus the raw ZIP provides a plausible deterministic reconstruction route, but equality with the published path must be tested rather than assumed.

A future replay of **our** policies can avoid this ambiguity by using the public metallographic labels as hidden finite-pool truth and shared label-free initial blocks. That would test a new experimental finite-pool task, not reproduce the paper's unsupervised optical procedure.

## 8. Level C — cross-material physics

### C1: bare process scaling

**GO WITH CAVEATS.** Evaluate Ti64 and 316L separately. This can show whether the `P^1 VX^-1/2` direction organizes each external boundary. Since the two alloys use the same constant radius and the same process design, bare `h` cannot explain an alloy-specific boundary shift and should not be pooled as if directly material-normalized.

### C2: material-normalized scaling

Gan et al. Eq. 1 is

```text
Ke = eta P / [(Tl-T0) pi rho Cp sqrt(alpha Vs r0^3)].
```

The exact required quantities are absorptivity `eta`, liquidus and initial temperatures, density, heat capacity, thermal diffusivity, scan speed and radius. Gan's supplement provides temperature-dependent Ti64 and SS316 property tables, including liquidus values, liquid-phase `rho`, `Cp`, `k`, and minimum absorptivities. Masinelli supplies `P`, `VX`, approximate `T0`, and `r0`.

This makes a calculation **POSSIBLE BUT HIGH-UNCERTAINTY**, not ready as an exact material-normalized truth. Masinelli did not measure effective absorptivity for these builds; Gan's `eta_m` is a literature minimum/flat-surface quantity and is not automatically the morphology-coupled effective `eta` in Eq. 1. Gan's steel constants are SS316, not a batch-specific characterization of Masinelli's 316L powder, and all thermophysical choices depend on phase and temperature. `material_constant_requirements.csv` records a defensible predeclared sensitivity set. Do not tune constants against labels.

## 9. Domain comparison

| Variable | Thesis simulator | Masinelli Ti64 | Masinelli 316L | Overlap / semantic match |
|---|---|---|---|---|
| P | 52.5446–449.7624 W | 90–120 W | 90–120 W | External range is inside thesis range; same meaning |
| VX | 0.2010–0.9983 m/s | 0.3–1.8 m/s | 0.3–1.8 m/s | Partial overlap; high-speed external tail outside |
| LS | 40.0293–89.7040 µm radius | 25 µm radius, fixed | 25 µm radius, fixed | No overlap; same `1/e²` radius semantics after conversion |
| ST | 300–399.8177 K | approximately 298.15 K | approximately 298.15 K | Near but just outside; external value approximate and fixed |

The Ti64 alloy family matches, while 316L is new. The machine, powder/build history, and track geometry differ: SPH single-track simulation versus a physical powder layer and ten parallel top-track bundles. The canonical four-input thesis audit does not establish a like-for-like powder representation. Label modality also changes. The overall comparison is a **strong domain shift**, not interpolation-like validation.

## 10. What success and failure would mean

### Safe success interpretations

- If `log h` discriminates Ti64: “The process-coordinate organization observed in the SPH benchmark is also present in an independent Ti–6Al–4V experimental process map.”
- If a later physics-informed surrogate improves finite-pool learning: “Physics-aligned inductive bias improves low-data boundary learning on the simulation benchmark and this independent experimental finite pool.”
- A cross-alloy normalized result must be described as conditional on the declared literature constants and their uncertainty.

None of these means the simulator was experimentally proven, that a universal threshold exists, or that physical experiment savings are guaranteed.

### Failure interpretation matrix

| Failure | Implication |
|---|---|
| A. `h` does not discriminate external Ti64 | Challenges transfer of the Phase 1.5 coordinate; does not invalidate its frozen simulator discrimination. |
| B. `h` works in Ti64 but not 316L | Supports same-material external organization but limits cross-alloy transfer; does not challenge Phase 1.7/1.9 internally. |
| C. `h` works statically but the physics-informed GP does not improve AL | Preserves Phase 1.5-like coordinate evidence; limits transfer of the Phase 1.7/1.9 model advantage. |
| D. Label definitions dominate | Reveals dataset/task mismatch; has little effect on current internal thesis results. |
| E. Pool is too small | Limits external AL inference; has little effect on current thesis evidence. |
| F. Material-normalized coordinate fails | Challenges the attempted cross-material normalization, not bare within-material `h` or frozen simulator results. |

## 11. Leakage, fairness and boundary metrics

- Build features only from process inputs available before querying. Optical features are post-process observations and must not enter a process-parameter baseline.
- Fit scalers, logistic priors, thresholds and any calibration on training data only.
- Group repeated `(P,VX)` bundle conditions. Never count ten lines as ten independent labels.
- External material constants are non-label covariates, but their sources and temperature/phase conventions must be frozen before label results are inspected.
- Hidden pool labels cannot enter acquisition or stopping.
- Do not use paper test labels to tune kernels, feature sets, transition mapping or material constants.
- Do not import thesis B1/q20 automatically. With only 38 unique points, q20 would be tiny and unstable. Conventional full-test metrics should be primary. A later boundary diagnostic may use training-standardized process-space nearest-opposite labels, but it must be predeclared and evaluation-only.

## 12. Code reproducibility

**Reproducibility rating: MEDIUM.** The algorithmic intent, data, seeds (`1995` for Spectral Clustering and GPC), process grids and label mapping are public. The raw ZIP is modest and complete enough to reconstruct feature inputs. However:

- no `requirements.txt`, lock file or environment file exists;
- the README itself says the dependency list remains to be completed;
- notebooks use relative local paths and generated pickle intermediates;
- `utils.py` additionally requires scikit-image, not listed in the README;
- generated feature pickles and exact path logs are absent;
- code has no declared license;
- notebook/kernel versions are not pinned;
- GPC hyperparameters are initialized but not frozen because default optimizer behavior remains active.

These issues do not block a clean-room Level A loader. They prevent claiming a bit-exact reproduction of the authors' full optical workflow until a reconstruction is validated against their published tables at every iteration.

## 13. Red-flag disposition

| Red flag | Disposition |
|---|---|
| Radius vs diameter / `1/e²` | Resolved: 50 µm diameter at `1/e²`; thesis radius 25 µm. |
| Constant LS | Confirmed; prevents testing the LS exponent. |
| Units | Sufficient; convert speed to m/s and spot to m. |
| Transition handling | Confirmed: all non-C modes are binary Keyhole. |
| Duplicate tracks/conditions | Quantified; exact-condition grouping required. |
| Ti64 vs 316L designs | Same parameter design, different cuboid mappings and labels; analyze separately. |
| Optical post-process features | Public raw signals exist, but exclude them from pre-process physics baselines. |
| Full map public | Yes for four 20-point maps and all 60 labelled bundles per alloy. |
| Exact published AL order | Not guaranteed; derived feature pickles/path logs absent. |
| Reliable join | Yes via material/cube/local-line; document mapping. |
| Missing conditions | No missing labelled rows in the 12-cuboid paper subset; extra raw cubes lack paper-subset labels. |
| Material constants | Literature values exist but are not build-specific and are temperature/phase dependent. |
| Test-label tuning | Prohibited by the future specification. |

## 14. Final recommendation

Proceed with the small Level A static experiment in `future_experiment_spec.md`. It uses only the 120 public labelled bundles and two small workbooks, analyzes alloys separately, groups repeats, and compares a generic log-process trend with `log h` before any physics-residual GP or AL replay. This is the minimum experiment that can falsify the transfer claim economically.
