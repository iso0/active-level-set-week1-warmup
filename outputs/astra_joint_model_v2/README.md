**Independent V2 development package**

Start with [the design and findings][design], then [the prepared Opus handoff][handoff]. V2 learns how strongly paid depth should be shared with the canonical classifier while preserving its marginal prior. It remains an experimental candidate: the tests show both benefits and substantial limitations.

| File | Purpose |
|---|---|
| joint_model_v2.py | Standalone EP/mixture reference implementation and paired acquisition. |
| v1_reference.py | Byte-identical V1 implementation, used as baseline and numerical helper dependency. |
| controlled_worlds.py | Frozen four-dimensional generators, feature-only paths and metrics. |
| reference_checks.py | Deterministic correctness runner and independent quadrature references. |
| run_controlled.py | Resumable static/sequential experiment runner with source/manifest hashes and fit ceilings. |
| supplemental_diagnostics.py | Only the separately recorded diagnostic amendment; includes independent ESS reference. |
| CONTROLLED_RESULTS.json | Full generated inputs, outcomes, seeds, paid paths, predictions, intervals, diagnostics, references, source hashes and combined accounting. |
| CONTROLLED_SUMMARY.md / RESULTS_SUMMARY.json | Readable and machine-readable summaries; every arm/world/seed remains available. |
| SELECTION_RECORD_V2.json / ATTEMPT_LEDGER.md | Prospective selection and execution history. |
| AMENDMENT_01_DIAGNOSTICS.md | Prospective bounded supplement after the frozen comparison. |
| evidence/PROVENANCE.json | Pinned evidence hashes and complete V1 artifact hashes. |
| records/ / checkpoints/ | Individual completed fit/query records and trusted local model checkpoints for resumption. |
| V1_SPARSE_REFERENCE_SAMPLES.npz | Four saved numerical-reference chains, not real observations. |
| DELIVERY_VALIDATION.json | Delivery/source consistency and no-fit batch-invariance checks. |

The original V1 directory is unchanged. The included copy avoids dependence on the thesis repository. Runtime dependencies are NumPy 2.4.6 and SciPy 1.17.1; tested Python was 3.14.4. Matplotlib is used only by make_figures.py. No script installs packages, contacts a service, or launches a simulator.

To reproduce in a **new empty output directory**, copy the Python source files, requirements.txt, SELECTION_RECORD_V2.json and AMENDMENT_01_DIAGNOSTICS.md there. Do not copy RUN_STATE.json, records/ or checkpoints/ into a fresh reproduction. Then run:

~~~powershell
python reference_checks.py
python run_controlled.py all
python supplemental_diagnostics.py
python summarize_results.py
~~~

The main runner resumes compatible completed requests rather than fitting them again. It refuses changed source/manifest fingerprints or an unfinished request requiring an explicit recovery decision. In this delivered directory, the completed records already exist; calling the main runner uses its cache. reference_checks.py and supplemental_diagnostics.py deliberately rerun their checks if invoked. finalize_results.py additionally verifies the original sibling V1 directory and pinned evidence snapshot, so it is a delivery tool for this workspace, not required for a standalone reproduction.

Minimal four-input interface, after the caller freezes the feature transform:

~~~python
import numpy as np
from joint_model_v2 import Config, JointModelV2

cfg = Config(f_lengthscale=1.5, discrepancy_lengthscale=1.5)
# Q: transformed feature-only training candidate pool.
# X_paid / Y_paid / A_paid_um contain only simulations already queried.
z = np.full(len(Y_paid), np.nan)
valid = np.isfinite(A_paid_um) & (A_paid_um > 0)
z[valid] = np.log(A_paid_um[valid] / 111.0)
model = JointModelV2(Q, cfg).fit(X_paid, Y_paid, z)
p = model.predict_proba(X_test)            # four inputs only
interval = model.probability_interval(X_test)
scores = model.acquisition(X_unpaid)       # caller excludes paid IDs

binary = JointModelV2(Q, cfg).fit(
    X_paid, Y_paid, np.full(len(Y_paid), np.nan), use_response=False
)
~~~

Use the full posterior mixture; a Gaussian fitted to its mean/variance is not the implemented predictor or acquisition. A fresh paid pair is appended once and all paid likelihood factors are refitted. Kernel/softness priors and the finite coupling support are fixed; only the component posterior masses are learned.

**Türkçe:** V2 derinlik yanıltıcı olduğunda bu bilgiden uzaklaşabiliyor. Ancak testler, tek negatiften çevresindeki negatif bölgeyi güvenilir biçimde öğrenemediğini ve aktif seçimin margin'e düzenli üstünlük sağlamadığını da gösterdi. V1 deneyi korunarak, V2 ayrı bir gerçek-veri model karşılaştırmasına alınmalı.

[design]: <C:/Users/ozgur/Documents/Codex/2026-10-10/files-pasted-by-the-user-you/outputs/astra_joint_model_v2/ASTRA_JOINT_MODEL_V2_DESIGN.md>
[handoff]: <C:/Users/ozgur/Documents/Codex/2026-10-10/files-pasted-by-the-user-you/outputs/astra_joint_model_v2/OPUS_V2_IMPLEMENTATION_REQUEST.md>
