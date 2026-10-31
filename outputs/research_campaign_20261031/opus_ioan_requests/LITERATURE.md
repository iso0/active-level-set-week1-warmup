# IR part G: literature check

Label: LITERATURE. Nothing here changes a registered rule.

Two of the sources below were read in full during this study:
- Sheikh et al. 2023, read on ar5iv;
- Bonilla et al. 2007, the abstract and the excerpt on cancellation of inter-task transfer.

The other sources were checked only through their abstracts or through secondary citations, as marked. Before any of them is quoted in the thesis, check the original.

## 1. Melt-pool geometry criteria for Keyhole vs conduction

**Johnson, Mahmoudi, Zhang, Seede, Huang, Maier, Maier, Karaman, Elwany, Arróyave (2019)**
- "Assessing printability maps in additive manufacturing of metal alloys." *Acta Materialia* 176, 199–210.
- A keyholing criterion based on the melt-pool width-to-depth ratio, with a threshold of 1.5.
- Later printability-map work applies it as W/D ≤ 1.5 → Keyhole.
- Taken from the summary in Sheikh et al. 2023. The direction of the inequality must be checked in the original.

**Zhang, Seede, Xue, Atli, Zhang, Whitt, Karaman, Arróyave, Elwany (2021)**
- "An efficient framework for printability assessment in laser powder bed fusion metal additive manufacturing." *Additive Manufacturing* 46, 102018.
- Revised the threshold to 2 from NiTi measurements: W/D ≤ 2.0.

**Sheikh et al. (2023)**
- "An automated fully-computational framework to construct printability maps for additively manufactured metal alloys." arXiv:2304.04113.
- Eq. (8): W/D ≤ 2.75 for general AM alloys. Their Table 1 gives 2.5 instead.
- Eq. (9): W/D ≤ 2.0 for NiTi.
- The authors state that better keyholing criteria are needed.

**Gan et al. (2021)**
- "Universal scaling laws of keyhole stability and porosity in 3D printing of metals." *Nature Communications* 12.
- Keyhole number Ke > 6. This criterion does not use W or D.

**How this study uses them** (part A3): the registered thresholds c ∈ {1.5, 2.0, 2.5} correspond to Johnson 2019, Zhang 2021 and Sheikh 2023 Table 1. The value 2.75 (Sheikh 2023, Eq. 8) is reported as an extra. It was added after registration, from this literature check.

## 2. Where z_h comes from

**King et al. (2014)**
- "Observation of keyhole-mode laser melting in laser powder-bed fusion additive manufacturing." *J. Mater. Process. Technol.* 214(12), 2915–2925.
- Normalised enthalpy ΔH/h_s ∝ A·P / (h_s √(D·v·σ³)) correlates with melt depth. The conduction → Keyhole transition sits near ΔH/h_s ≈ 30 ± 4 (as quoted by later work).
- The thesis's h = P / √(VX · LS³) is the material-independent core of this quantity (RC24 literature matrix).

**Rubenchik, King, Wu (2018)**
- "Scaling laws for the additive manufacturing." *J. Mater. Process. Technol.* 257, 234–243.

## 3. Multi-output GP transfer theory

**Bonilla, Chai, Williams (2007)**
- "Multi-task Gaussian process prediction." *Advances in Neural Information Processing Systems* 20, 153–160.
- Setting: a shared input kernel times a free-form task covariance, i.e. the intrinsic coregionalisation model.
- Result: with noise-free observations and a block design (every task observed at the same inputs), the predictions for one task depend only on that task's own targets. Inter-task transfer cancels.

**Rakitsch, Lippert, Borgwardt, Stegle (2013)**
- "It is all in the noise: efficient multi-task Gaussian process inference with structured residuals." *NeurIPS* 26.
- In the limit of noise-free training observations, the coupling between tasks is lost for prediction.

**Wackernagel (1994 / 2003)**
- "Cokriging versus kriging in regionalized multivariate data analysis." *Geoderma* 62, 83–92.
- *Multivariate Geostatistics*, 3rd ed., Springer 2003, chapter "Isotopic cokriging".
- **Autokrigeability:** if the variables are intrinsically correlated and every variable is measured at every sample location (isotopy), cokriging of each variable equals its kriging.

**Álvarez, Rosasco, Lawrence (2012)**
- "Kernels for vector-valued functions: a review." *Foundations and Trends in Machine Learning* 4(3), 195–266.
- The LMC / ICM framework used for LMC_q and ICM_W.

**Why it matters here:** every physical output comes from the same simulation as the depth, so the data are isotopic. Depth noise is small after the Q rule. A co-output can therefore improve the depth prediction at unopened inputs only through three routes:
1. a cross-covariance that is not proportional (an LMC with different lengthscales, tested as LMC_q);
2. missing or short records;
3. better hyperparameter estimation, the route of RC19's shared lengthscales, where RC23 found no material gain.

Our ICM_W control and the synthetic V3 check reproduce the cancellation.
