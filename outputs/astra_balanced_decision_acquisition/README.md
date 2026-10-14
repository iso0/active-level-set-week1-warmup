**Decision-and-acquisition research package — status is in PIPELINE_STATE.json**

Start with [DECISION_ACQUISITION_DESIGN.md](DECISION_ACQUISITION_DESIGN.md) and [OPUS_DECISION_ACQUISITION_REQUEST.md](OPUS_DECISION_ACQUISITION_REQUEST.md).

The selected method uses the unchanged V2 mixture and minimizes expected finite-batch BA loss. Its target is a prospective IID batch approximated using a fixed training-feature reference. It is not exact optimization of the fixed recorded test panel; the latter has separate enumeration checks. Scientific outcomes must be read from CONTROLLED_RESULTS.json once present. A queued job, successful import or completed implementation is not a passed experiment.

Files: balanced_method.py (decisions/lookahead/fixed-panel reference API), joint_model_v2.py and v1_reference.py (byte-identical model dependencies), worlds.py, independent_checks.py, run_controlled.py, runtime.py. Requirements: NumPy 2.4.6, SciPy 1.17.1, tested interpreter for this workspace is Python 3.14.4; final numerical acceptance is pending until the reference gate runs. No repo imports or external services are required.

Reproduce in this directory with a suitable Python interpreter:

```text
python run_controlled.py freeze
python run_controlled.py checks
python run_controlled.py run
python summarize_results.py
```

Those commands resume this attempt and retain its existing checks/stops. For a **fresh Windows reproduction**, the self-contained `reproduce_standalone.py` creates a new directory, copies only frozen sources/provenance plus the small historical V2 identity bundle, and initializes a separate ledger. Example preparation without calculations:

```text
python reproduce_standalone.py --destination path_to_new_reproduction --prepare-only
```

Omitting `--prepare-only` executes the checks and comparisons under the same host queue. It is a reproducibility entry point, not authorization to launch a second experiment during this bounded study; doing so here would need a prospective budget amendment. The helper refuses existing destinations. The historical V2 results in `preserved_v2_identity/` are integrity evidence only and never enter any learner. No Opus checkout, repository installation or external service is required. The host-aware runner requires Windows/PowerShell; the mathematical model/decision modules use NumPy/SciPy only.

An existing manifest is checked rather than replaced. The initial mathematical target revision is preserved in MANIFEST_00_SUPERSEDED.json, evidence/pre_batch_correction/ and AMENDMENT_00_BEFORE_RESULTS.md. It preceded every reference and model fit. The final manifest controls all comparisons. V1/V2 historical experiments are preserved; the V2 design has only the explicitly requested marked plus-sign erratum.

The Windows runner sets BLAS/OpenMP to one thread and waits while four foreign numerical slots are occupied. It never modifies Opus's processes, locks, priority or files. HOST_QUEUE.json records detected workers. fit_records/ and checkpoints/ support resumption; ledger.jsonl records requests before fits and all component solves. Local pickle files are trusted only if created by this runner and matching their saved hashes; never load an untrusted checkpoint.

Do not automatically rerun a crashed independent-reference pass: inspect its already charged REFERENCE events and remaining total budget first. No reference/group result may be discarded. A failed reference gate prevents comparisons. Interrupted model fits are flagged as pending and require an explicit audit before resumption; completed checkpoints are not refitted. Scientific failures/stops never trigger a new seed or changed tolerance.

The optional finish_queue.ps1 starts one sequential pipeline: independent checks (waiting for a free numerical slot), the frozen comparisons after the reference gate passes, and postprocessing. It holds only a duplicate-prevention handle inside this package. It performs no scheduling change to other jobs. Its final state is COMPUTATION_FINISHED_REVIEW_REQUIRED, not automatic scientific approval. PIPELINE_STATE.json and the append-only stdout logs show progress; completed reference subsections are saved separately. An interrupted subsection requires audit, never an automatic retry. No C4, real-data Stage A, SPH fits, simulators, label changes, remote pushes or messages are performed.

AMENDMENT_01_NUMERICAL_AUDIT.md preserves the pre-computation static audit: independent tail arithmetic, durable reference accounting, separate production-validation QMC budget, stricter tower/normalization acceptance and always-defined zero-class loss reporting. Previous frozen sources are retained under evidence/pre_numerical_audit/. These corrections preceded all numerical results.

Numerical and scientific results, when complete, are in INDEPENDENT_CHECKS.json, CONTROLLED_RESULTS.json, RESULTS_SUMMARY.json and CONTROLLED_SUMMARY.md. Every seed, path, divergence, loss, numerical near tie and stop is retained. Reported uncertainty across four seeds is descriptive and has no SPH population interpretation. No query-saving endpoint is registered.
