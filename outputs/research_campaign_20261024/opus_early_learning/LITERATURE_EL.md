# Nearest literature for "one model selects, another predicts" (EL study, 2026-10-25)

How the sources were checked:
- Read in full text, through the arXiv HTML render (ar5iv): Lowell et al. 2019 and Coleman et al. 2020.
- Checked at abstract / proceedings-record level only (ACL Anthology): Tomanek et al. 2007 and Baldridge & Osborne 2004.

The physics-mean GP, universal-kriging, stacking and margin sources are those already verified in RC24 (`outputs/research_campaign_20261021/opus_rc24/post_audit/ORIGINALITY_AND_LITERATURE.md`).

## 1. Selector and predictor as different models

| work | setting | what is selected / predicted | finding (as reported) | relation to this study |
|---|---|---|---|---|
| Lowell, Lipton & Wallace 2019, "Practical Obstacles to Deploying Active Learning", EMNLP-IJCNLP 2019, pp. 21–30 (arXiv 1807.04801) | text classification (SVM, CNN, BiLSTM; 4 datasets) and NER (CRF, BiLSTM-CNN); uncertainty sampling, QBC, BALD; seed 2.5 %, results at 10 % / 20 % of the pool | an *acquisition model* selects; a *successor model* is trained on the acquired set; all pairs tested | in classification only 37.5 % of the transfer points beat i.i.d. sampling, and same-model AL beat i.i.d. in 60.9 % of cases; NER was more favourable | our C and D are acquisition ≠ successor pairs. Unlike their models, ours share everything except one trend basis function, and we measure the effect on target attainment |
| Coleman et al. 2020, "Selection via Proxy: Efficient Data Selection for Deep Learning", ICLR 2020 (arXiv 1906.11829) | image (CIFAR10/100, ImageNet) and text (Amazon reviews) classification; least-confidence AL, k-centers, core-sets | a smaller / shorter-trained *proxy* selects; the larger *target* is trained on the result | final error close to target-model selection (e.g. CIFAR10 at a 50 % budget: 5.4 % vs 5.3 %), with selection speed-ups of 3.8–51×; high rank correlation between proxy and target; failures on Amazon Review Full and on ImageNet core-sets | D is a "proxy-style" pairing in which the selector (HA_LEAN) is NOT cheaper: the point is the selector's query choice, not compute |
| Tomanek, Wermter & Hahn 2007, EMNLP-CoNLL 2007, pp. 486–495 | NER corpus construction by AL | a corpus selected with one classifier / feature set is reused by other classifiers | annotation reduction up to 72 %; reports evidence on the reusability of the AL corpus | the same reuse question in a data-curation setting |
| Baldridge & Osborne 2004, EMNLP 2004, pp. 9–16 | HPSG parse selection | data selected with one model reused by other models | gains from AL can be negligible or negative under reuse; semi-automation helps | a caution that path transfer can fail; in our data the HA_TREND path does not help HA_LEAN early (C − A ≈ 0) |

## 2. Known components of the systems compared (RC24-verified)

- **Universal kriging** (a GP with an explicit basis-function trend whose Gaussian coefficient is integrated out): O'Hagan 1978; Kennedy & O'Hagan 2001; Rasmussen & Williams 2006 §2.7. HA_TREND uses one basis function, the standardised log h.
- **A physics model as a GP mean**: Ziatdinov et al. 2021, for optimisation and regression.
- **A fixed physics prior mean in a GP classifier**: Hardcastle et al. 2025.
- **Stacking / honest out-of-fold combination**: Wolpert 1992; Breiman 1996; van der Laan et al. 2007.
- **Uncertainty / margin sampling**: Lewis & Gale 1994; Scheffer et al. 2001.

## 2b. Known components of the stage-2 system E

| component | source | used in E |
|---|---|---|
| Bayesian model averaging over a discrete model choice, weighted by the posterior model probability | Hoeting, Madigan, Raftery & Volinsky 1999, "Bayesian Model Averaging: A Tutorial", *Statistical Science* 14(4), 382–417 (with discussion), checked at the journal-record / abstract level | the emulator choice (trend / no trend) is averaged, not selected |
| evidence (marginal likelihood) for comparing classifier variants; moderated, posterior-averaged classifier outputs | MacKay 1992, "The Evidence Framework Applied to Classification Networks", *Neural Computation* 4, 720–736, checked at the record / abstract level | the same Laplace evidence that HA_LEAN already uses for its (τ_F, τ_h) grid now also weights the emulator |
| Laplace approximation to the GP / logistic marginal likelihood | Rasmussen & Williams 2006, ch. 3 (RC24-verified) | log Z_{e,g} for every emulator and grid configuration |

E adds no new statistical idea. It is BMA over one more discrete hyperparameter of an existing evidence-weighted classifier. Ours is the measured effect on early learning and target attainment in this active-learning setting.

## 3. What is ours, and its limit

**Ours (measured, DEV, one 541-run pool):**
- A 2×2 selector × predictor decomposition on identical startups, for a stacked h + depth active classifier.
- An answer from it to "where does the early gain come from":
  - the early BA gain of the trend emulator is a prediction effect;
  - the trend model's own query path adds nothing early and hinders reaching BA 0.95;
  - the pairing "HA_LEAN selects, HA_TREND predicts" keeps the early gain.
- The forward test on fresh repeats decides how much of a single-learner simulation saving remains (`final/FINAL_COMPARISON.md`).

**Not ours, or not shown:**
- No new model or selection rule. D recombines two existing systems.
- **No claim of beating the literature.** None of the works above was reimplemented, and their settings differ: text and image classification, large neural models, and a selector cheaper than the predictor (SVP).
- No external physical validation.
- Effects of about one simulation.
