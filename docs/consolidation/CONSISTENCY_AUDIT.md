# Scientific and repository consistency audit

## Verdict: PASS with documented legacy exceptions

## Scientific naming and claim checks

- `ST` is consistently defined as substrate temperature in the Track A and Track B authoritative documents.
- `has_keyhole` is the manual ground-truth target. It is not described as an experimentally observed online signal.
- M3 is consistently defined as a physics-informed trend in `log h` plus a 4D ARD Matérn-3/2 GP discrepancy over `[P, VX, LS, ST]`.
- The live control is M3 probability margin with frozen B16 initialization.
- The frozen external challenger is `early8__coverage_then_margin_B40`.
- The same-B16 attribution control is `coverage_then_margin_B40`.
- `historical_binary_A0_live` remains explicitly historical and is not collapsed into the live control.
- Candidate B's internal q20 **accuracy** AULC effect over M3 margin is approximately `+0.006708`; it is below the `+0.01` replacement threshold and is not labelled externally validated.
- The M3+G3 study's balanced-accuracy endpoint is not mixed with the Candidate B accuracy endpoint.
- Boundary-displacement M1 gained approximately `+0.000004` over M0 and did not beat generic M2. The large alternate-start covariance instability is assigned to M2, not M1. Gate 2 was not run.
- Width-change evidence is described as modest internal predictive-ranking information, not as a successful acquisition variable or proven sensor.

## Repository-integrity checks

| Check | Result |
|---|---|
| No authoritative source exists only on a deletion-candidate remote branch | PASS: all 38 initial remote tips are reachable; PG-RMBC files are in the candidate tree |
| No final report exists only locally | PASS: all 2,361 local scientific files have verified canonical destinations |
| Provenance links resolve | PASS for canonical navigation/freeze/Track B documents |
| No duplicate authoritative implementation is unnamed | PASS: current implementations are indexed; content-distinct historical variants remain explicitly historical |
| Freeze-document paths exist | PASS |
| Pinned SHA-256 references resolve | PASS |
| Current model imports/tests execute | PASS: 16 selected M3/control tests and 30 Week 10 tests |
| Unexpected deletions relative to old main | none |
| New Git object ≥100 MiB | none |
| High-confidence credential/private-key pattern in added text | none |
| Open PR head among deletion candidates | none; GitHub API reported both repository PRs closed/merged |

## Scope statements

- The consolidation reran validation code and tests, not scientific experiments or acquisition searches.
- No genuinely new Ioan simulation batch was accessed.
- Track B preparation is an inventory and analysis plan only.
- The two frozen Phase 2 manifest mismatches are inherited, documented exceptions, not silently corrected data.
- Historical test assumptions and missing untracked checkpoints are recorded in `TEST_VALIDATION_LOG.md`; current-method acceptance is green.
