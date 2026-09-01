# Final red-team report — Phase 1.10 closure

Status: **PASS WITH CLAIM BOUNDARIES**

| Attack | Disposition |
|---|---|
| Standardized coefficient ratio used by mistake | Rejected: executable recovery divides each gamma by its own training-fold sigma before beta_VX/beta_P. |
| Unstable beta_P denominator | 0 invalid main fits; explicit near-zero and extreme-alpha guards stored per fit. |
| One hundred folds treated as independent | Rejected: five folds averaged inside repeat; bootstrap uses exactly 20 repeat means. |
| Theory line selected after results | Rejected: constant `THEORY_ALPHA=-0.5` and test lock. |
| Strict C/K mislabeled primary | Rejected: reports call it post-hoc sensitivity and preserve frozen verdict. |
| Regularization cherry-picking | Rejected: only C=1 and C=1e6 run; unpenalized API status recorded; no winner selected. |
| Strict class imbalance hidden | Audit reports Ti64 26/22 and 316L 37/11; every held-out fold contains both classes. |
| Replicate leakage | Exact condition is one fold in every repeat. |
| Alpha called causal/physical proof | Rejected in reports and claim ledger. |
| Frozen verdict changed | Rejected: remains GENERIC_DIRECTION_SUPERIOR. |

Regularization sign check: transition-inclusive H−G is -0.01561 at C=1 and +0.01459 at C=1e6. Frozen Phase 1.10 artifacts remain byte-unchanged relative to `45e2677b7a57ed3aa5ad5154459100a9b5d2d436`.
