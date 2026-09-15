# Week 8 Phase 1 headline results

These statements describe empirical held-out boundary-region classification or saved GPC model confidence. They do **not** state certainty about the continuous physical boundary.

- **H01.** At 40 simulator queries, Binary reaches 81.2% mean B1-q20 empirical near-boundary accuracy, versus 76.8% for Random (+4.4 percentage points).
- **H02.** At 40 queries, Binary reaches 86.2% mean B1-q30 accuracy, versus 83.2% for Random (+3.0 percentage points).
- **H03.** For B1-q20 accuracy >=80%, Binary succeeds in 18/20 runs with median first crossing 16 queries; Random succeeds in 14/20 with median 30 among successful runs.
- **H04.** Binary's mean 79.7% B1-q20 accuracy at budget 30 is first matched by the observed Random mean curve at about 70 queries: approximately 40 saved simulator calls (2.33x query equivalent).
- **H05.** Binary's mean 81.2% B1-q20 accuracy at budget 40 is not matched by Random by budget 80, implying >40 saved calls and a >2.00x lower-query equivalent within the observed horizon.
- **H06.** At budget 30, Binary has discovered 12.20 Keyhole simulations on average, versus 5.45 for Random; discovery is a secondary diagnostic, not a boundary-localization metric.
- **H07.** At budget 40, 48.2% of held-out B1-q20 predictions carry at least 80% saved GPC confidence, and 93.3% of that high-confidence band is correct.
- **H08.** Binary's B1-q20 accuracy AULC is 0.8138, compared with 0.7711 for Random over the common 16-80 budget grid.
- **H09.** The Binary advantage over Random is robust in direction under B2 and B3 q20 error AULC (reductions 0.0549 and 0.0492, respectively).
- **H10.** All sample-efficiency results are offline/retrospective: held-out saved simulations were hidden until queried, but no new simulator campaign or prospective closed loop was run.
