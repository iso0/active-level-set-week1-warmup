# Week 11 New-Batch Bug Audit

## NEW-BATCH BUG AUDIT

Source: `ioandanielc/sph_v2@2e1eec9c98fd57609d2815f174586336ab59da07`. Its `labels_new_data_4_prep.csv` contains exactly the 185 new simulation IDs. Mixed annotation bytes were processed solely for Bug/status projection: ID, timestep, `bug_free`, `correctly_finished`, and explicit Bug-word flags from the three categorical columns. Non-Bug physical classes were not exposed, counted, saved or used for eligibility; `has_keyhole` was neither inspected nor computed. The raw CSV was not saved. Verified SHA-256: `b45518a51ea59d97d1e28e3f2ce5ef563af1c049bce83d0d88b3d510b1adf16d`. The source `hash` column is empty throughout; the pinned file identity and simulation IDs establish provenance.

Explicit Bug tokens occur in 49/185 simulations (26.49%); 136 have none. All 9,675 flagged category cells are exactly `Screenshot Bug`, representing 3,225 flagged annotation rows. There is no alternate Bug literal. `bug_free` is constant within every simulation: false in 48 and true in 137. `correctly_finished` is constant true in all 185. One run marked `bug_free=true` contains five Bug rows, so the status field and categorical annotation are kept as separate evidence.

All 49 onsets were mapped exactly through `frames.csv`, `iter.dat`, and `time.dat`. First-Bug annotation ordinal is 232–328 (median 281); onset occupies 57.1%–99.6% of the annotation span (median 82.1%), at 0.001208254–0.002096426 s (median 0.001731321 s). No numerical “near beginning” cutoff was invented. Bug masks form a terminal contiguous suffix in 34 runs, are intermittent through the end in 13, and are nonterminal in 2. Late onset therefore does not show that every remaining row is invalid.

Reason and wall-contact fields are absent: all 49 causes are unknown. Actual wall-contact timing and onset relative to the relevant laser/melt evolution remain unresolved. The optional bounds check stopped after a remote fetch timeout; its 49 files total about 455 MB and were not refetched. Frame/time alignment passed, but numerical and physical prefix integrity remain unresolved. The CSV records the preceding non-Bug annotation; this is not a proven last-valid frame.

The bounded technical decision is:

- **KEEP:** 136 simulations with no explicit Bug token and consistent approved status flags, for this Bug audit only.
- **KEEP WITH TRUNCATION:** 0; no target-safe truncation rule is established.
- **EXCLUDE:** 0; no permanent-exclusion reason is established.
- **UNRESOLVED:** 49 affected simulations, temporarily withheld pending reason and target-safety clarification.

The 136 retained simulations have singleton exact-configuration groups. A deterministic seed-1101 shuffle and round-robin five-fold witness gives held-out sizes 28/27/27/27/27 and training sizes 108/109/109/109/109, so B80 is structurally feasible. This is advisory and does not settle the separate campaign/solver grouping gate or approve the final external-validation freeze.

## MAIN CONCLUSION

This affects 49 simulations, not merely 5–10, but does not prove that 49 entire runs are invalid. The audit identifies 136 candidate whole runs and temporarily withholds the 49 listed in `bug_affected_simulations.csv`. No final eligibility freeze or execution is approved. Keep the 136 as technically cleared candidates; resolve the others using explicit technical criteria, never physical outcomes or apparent model usefulness.

The frozen target asks whether any genuine Keyhole frame occurs in the run. Late instability could contaminate that target; truncation could remove relevant evolution. Late onset alone therefore justifies neither KEEP nor KEEP WITH TRUNCATION. Physical outcomes were not opened to resolve these cases.

Minimal question for Ioan: For each listed run, what technical cause led to Bug, when does physical reliability first fail, and does the trustworthy interval cover all evolution needed for the frozen whole-run target? Please distinguish wall contact from other technical failures without supplying physical class labels.

Reproduce with `python -m src.week11_bug_audit outputs/week11_new_data_arrival_audit/WEEK11_NEW_BATCH_MANIFEST.csv <new-output-dir> --monitor-metadata outputs/week11_new_data_arrival_audit/new_monitor_metadata.json --directory-metadata outputs/week11_new_data_arrival_audit/new_directory_metadata.json`. Without `--mixed-csv`, the projector fetches only the pinned mixed file in memory; it never saves it.
