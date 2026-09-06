# Follow-up closure package — 2026-09-06

Continues `claude_rnd_2026_09_05/` (unchanged). Development data only; no new-pool label or input accessed.

Read in this order: PREVIOUS_CONCLUSIONS_RED_TEAM.md → MATHEMATICAL_SEMANTICS_AUDIT.md → ORACLE_MECHANISM_AUDIT.md → ORACLE_ENDPOINT_SENSITIVITY.md → EXCEPTION_CLUSTERING_AUDIT.md → ROBUST_LOCAL_MODEL_RND.md → NESTED_SUBSET_LABEL_HARM_AUDIT.md → ACQUISITION_CLOSURE.md → UPDATED_SATURATION_PREDICTIONS.md → EXTERNAL_PROTOCOL_REVIEW.md → FINAL_CLOSURE_DECISION.md.

Machine-readable: key_tests.json, updated_predictions.json, followup_protocol_addendum.json, results/*.csv(.gz).
Code: code/ (oracle_values.py, oracle_analysis.py, clustering_test.py, m3r_tests.py, nested_subsets.py, nested_analysis.py, xsur.py with S1/S2/S3 semantics, m3r.py). Requires the previous package's rnd harness (core.py, tmodel.py, acq_replay.py) on the path and the repository at bf4782881bc27fe1ec5256dc3ba0516478a1ed13.
Bottom line: no attainable oracle signal; XSUR negative survives corrected semantics; exceptions campaign/configuration-structured, not locally clustered; M3R killed; no local model justified; label-blind "more labels hurt" exists but is small and far-row driven; M3+TV retained as the weak frozen external challenger (Case C); predictions P1 reworded, P1b added, P9 rewritten.
