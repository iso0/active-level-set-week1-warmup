# Sources and prior exposure, 26 October 2026

The entire previous local-correction DEV summary was known before registration.
Its local V2 BA improvement .00173 failed the .005 screen. The null-trained
background limitation was explicitly unresolved. Those32worlds/64paths are
reused here for diagnosis, never relabelled as independent TEST. Original files
are immutable copies indexed by source_snapshot/PREVIOUS_MANIFEST.json.

Public Opus context was retrieved from immutable commit
acf673924b44413a64f55511660baefd9256e9a0, with no local Opus imports/writes.
Selective downloads: FINAL_REPORT_EL, PROTOCOL_EL_OBJECTIVES, src/el_eval.py,
src/el_mix.py; byte hashes in GITHUB_MANIFEST. The first guessed nested src URL
returned404 and was corrected using the public directory listing; no code
execution or outcome-based change followed. el_mix.py combines32 Laplace
classifier evidences and plug-in sigmoid predictions of separately constructed
LEAN/TREND features. It does not implement the joint continuous GP covariance
fit tested here. Its early-BA versus sustained-target distinction motivates
retaining separate endpoints; no real-data refit is authorized.

Primary full texts inspected:

* [Ba–Joseph, Composite Gaussian process models (PENDING_ARCHIVE)](../../../../docs/research/ARCHIVE_MANIFEST.md#pending-7e1c39b7741e88e1):
  §3.2 Theorem1 equates predictor forms at common parameter values, then explains
  why learning parameters together permits interaction between global/local
  parts. §4 Eqs20–25 derive profile likelihood and constrained optimization.
  This is the closest antecedent of the hypothesis, not evidence that our
  particular finite gate mixture will improve classification.
* [Davis–Hans–Santner, Bayesian heteroscedastic composite GP (PENDING_ARCHIVE)](../../../../docs/research/ARCHIVE_MANIFEST.md#pending-d707d717816e19a5):
  §2 gives global/local covariance components and a latent variance process;
  §3 Eq14 and Gibbs/Metropolis updates integrate broader parameter uncertainty.
  Our64 mutually exclusive coherent bases, fixed local amplitude and plug-in
  shared theta deliberately restrict that model class. No full-Bayes claim.
* [GPML Chapter2 (PENDING_ARCHIVE)](../../../../docs/research/ARCHIVE_MANIFEST.md#pending-cf7205116f1c419f) and
  [Chapter5 (PENDING_ARCHIVE)](../../../../docs/research/ARCHIVE_MANIFEST.md#pending-6495ee202797ad5b): standard Gaussian
  conditioning and marginal-likelihood derivatives. Independent dense checks
  validate this implementation, not posterior calibration under misspecification.

Novelty boundary: established additive/local covariance, Bayesian component
averaging, Woodbury updates and empirical Bayes. Potential contribution is an
audited mechanism comparison and, only if observed, early sign-learning benefit
under matched observations and optimization-cost controls. No published-method
superiority follows without matched implementations and appropriate evaluation.
