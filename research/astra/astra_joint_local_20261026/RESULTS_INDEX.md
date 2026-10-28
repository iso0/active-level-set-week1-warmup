# Astra joint general/local learning — evidence index

Start with [one-page Turkish explanation](FINAL_REPORT.md),
[independent TEST review](docs/TEST_V1_REVIEW.md) and
[same-target query/cost table](results/completion/SAME_TARGET_COST.md).
Decision: small positive same-data model effect; frozen practical TEST gate
failed against fixed_extra. No acquisition expansion or physical-data validation.

|Question|Evidence|
|---|---|
|What changed and why?|[Model equations/inference](docs/DESIGN_V1.md), [limits and competing explanations](docs/ANALYTICAL_LIMITS.md)|
|What was fixed before outcomes?|FROZEN_DEV_V1.json, FROZEN_TEST_V1.json; docs/DEV_PROTOCOL_V1.md, TEST_PROTOCOL_V1.md|
|What was exploratory?|[DEV review](docs/DEV_V1_REVIEW.md); finishing diagnostics were registered after TEST and labelled as audits|
|All six models and every family?|[All-family table](results/analysis_test_v1/ALL_FAMILIES.md), ALL_FAMILIES.csv|
|Every world/path/recall/score?|results/analysis_test_v1/PER_WORLD_PATH_MODEL.csv and PER_BUDGET_METRICS.csv|
|Whole-world paired uncertainty?|results/analysis_test_v1/ANALYSIS.json: screen and comparisons, including per_world arrays|
|Raw predictions and paid observations?|results/test_v1/*/B*.npz; results/unit__test_v1_*.json; data/test_v1/*/parent.json and prequery_B*.json|
|Failures and resource accounting?|OPTIMIZATION.csv; evidence/QUEUE_LEDGER_LATEST.json; raw per-start logs in unit results|
|Numerical validity?|evidence/NUMERICAL_REFERENCES_V1.json; results/finishing/AUDIT.json; evidence/PORTABLE_CHECK.json|
|Hit versus information limits?|results/finishing/HIT_DIAGNOSTICS.csv, MODEL_DIAGNOSTICS.csv and results/completion/FAMILY_DIAGNOSTICS_B24.csv|
|Readable plots?|results/completion/LEARNING_CURVES_REVIEWED.png/pdf and PREQUERY_REPLAY_REVIEWED.png/pdf; evidence/VISUAL_REVIEW.json|
|Portable integration?|[Handoff (RESTRICTED)](../../../docs/research/ARCHIVE_MANIFEST.md#rec-pkg-0335), handoff_api.py, portable_check.py, requirements.txt|
|Source provenance?|source_snapshot/PREVIOUS_MANIFEST.json, GITHUB_MANIFEST.json and [source review](docs/SOURCE_REVIEW.md)|
|Actual continuation/closure?|AUTO_RESUME_RECEIPT.json, runtime/HEARTBEAT_PROBES.json, evidence/CLOSURE_RECEIPT.json; no real quota-reset takeover claim|
|Copyable thesis-log entry?|[Thesis paragraph](THESIS_LOG_INSERT.md)|
|Complete portable package?|review_bundle/ASTRA_JOINT_LOCAL_REVIEW/ and .zip; BUNDLE_RECEIPT.json; verify_bundle.py|

The machine-readable RESULTS_INDEX.json links and hashes the principal records.
The portable BUNDLE_MANIFEST hashes every exported source/result file. The ZIP
receipt remains outside its own archive to avoid a self-hash cycle. Existing
V1/V2/old campaign files and Opus work were not modified. All Git commits are local.
