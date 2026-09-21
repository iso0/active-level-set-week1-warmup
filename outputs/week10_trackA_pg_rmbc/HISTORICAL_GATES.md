# Week 10 Track A — PG-RMBC historical gates

Project name: `week10-pg-rmbc-internal-replication`

Gate status: **PASS**

This gate was completed before any PG-RMBC trajectory implementation or run. It reads the historical artifacts in place and does not alter any historical output directory. The forthcoming Ioan dataset was not opened, read, hashed, or otherwise inspected.

## Evidence checked

- Week 8.5 frozen confirmation: the 405-row population and grouped split generator are the frozen basis; manual `has_keyhole` remains the only ground truth. Its validation artifact reports `PASS_WITH_QUALIFICATIONS`.
- Phase 1.13: M3 is the revealed-prefix-fitted logistic physics mean on the exact existing `log h`, plus a four-input ARD Matérn-3/2 GP discrepancy. The residual inputs are `[P,VX,LS,ST]`, standardized on the outer training pool; `log h` is not added as a fifth discrepancy input. The Phase 1.13 validation reports `PASS`.
- Phase 1.14: the live control is M3 probability margin with the frozen 16-point feature-space maximin initial design. Early q20 accuracy AULC B16–B40 was weak relative to the same-path control (`-0.001556`, 95% interval `[-0.007525,+0.004106]`). Validation reports `PASS`.
- Phase 1.16: generic geometry-relative repulsion changed paths and increased spread, but every primary q20 AULC interval included zero and no scale survived multiplicity control. It did not repair the B40 Keyhole-recall issue. Validation reports `PASS`.
- Phase 1.17A: the extra repulsion distance was a mixed combination of tangent, normal, and ST components. The audit did not isolate evidence sufficient to replace the successful standardized 4D coverage geometry with tangent-only coverage. Validation reports `PASS`.
- Phase 1.19A: the physical partial order is `P` up, `VX` down, `LS` down, with at least one strict inequality; `ST` is explicitly excluded. Validation reports `PASS`.
- Phase 1.19B: monotone inferences never entered M3 fitting, but candidate removal/resolution and hard implication mistakes reduced recovery. The primary P3–P0 balanced-accuracy AULC effect was `-0.0085249553`, 95% interval `[-0.0119076178,-0.0052645627]`. The mean wrong-inference rate among inferred labels was `0.7689%`, but Keyhole-as-Conduction errors averaged `1.8/73 = 2.466%`, versus Conduction-as-Keyhole `0.65/332 = 0.196%`. Decisions were `MONOTONE_POOL_HARM` and `MONOTONE_PROPAGATION_TOO_RISKY`; validation reports `PASS`.
- Phase 1.20 acquisition search/early start: the internally confirmed gain was carried by early boundary-conditioned coverage; the late misfit component did not replicate. This phase also established the early-start mechanism but screened multiple strategies, so its development comparisons are not reused as fresh evidence here.
- Phase 1.21: on untouched internal repeat blocks 61–120, the simplified coverage rule replicated. The final frozen challenger is exactly `early8__coverage_then_margin_B40`; the live control is exactly M3 probability margin with the frozen 16-point seed. The boundary rule uses pad fraction `0.25`, pad floor `0.05`, uncertainty weight `1.0`, standardized `[P,VX,LS,ST]` nearest-query distance, and a fixed B40 switch. Validation and hidden-label invariance gates report `PASS`.

## Independent reproductions

The current 405-row population was loaded through the frozen Week 8.5 loader, and the Phase 1.19A dominance relation was recomputed directly from coordinates:

| Population | N | Keyhole | Conduction | Comparable directed pairs | Violations |
|---|---:|---:|---:|---:|---:|
| full frozen pool | 405 | 73 | 332 | 22,050 | 3 |
| main configuration | 364 | 70 | 294 | 19,491 | 3 |

The full-pool comparable fraction is `22,050 / 81,810 = 0.26952695`; the violation rate is `3 / 22,050 = 0.0001360544` (`0.01360544%`). The retrospective all-label hard-propagation diagnostic contains 6 wrong implication edges and 5 unique wrong target-label assignments.

The exact M3 physics coordinate resolves through the historical source to:

`log h = log(P / sqrt(VX * LS^3)) = log P - 0.5 log VX - 1.5 log LS`.

All five source hashes recorded in `FINAL_POLICY_FREEZE.json` match the current canonical files: Phase 1.20 acquisition search, Phase 1.20 early start, Phase 1.21 runner, Phase 1.13 M3, and Phase 1.11 fixed-mean GP. This verifies that the definitions above were not inferred from report prose alone.

## Binding Week 10 gate

All required historical facts reproduce. PG-RMBC method development may proceed, subject to these prohibitions:

1. monotonicity creates no training labels;
2. monotonicity removes no candidates;
3. monotonicity marks no point resolved;
4. unqueried/test labels and q20/q30 membership are inaccessible to acquisition;
5. the exact frozen M3, `log h`, boundary band, coverage geometry, and deterministic row-index tie-break are reused;
6. the new Ioan dataset remains untouched.

