# RC18 protocol addendum A1 — robustness on DEV repeats 3–4 (registered before it runs; exploratory)

**Registered:** 2026-10-18, while the final programme (repeats 5–8) was running and before any final result was read.

**What runs:** the MAXIMIN regression comparison of PROTOCOL_20261018 §5, on DEV repeats 3–4 (10 tasks per population).
- NEW models: M0, M0Q, SHQ, TRQ, TRSQ.
- OLD models: M0, SHQ.
- The code is `src/rc18_robust.py`, which imports the frozen modules unchanged and checks the final manifest.

**Status:** exploratory only. It is **not** part of the primary verdict.
- Repeats 3–4 are further partitions of the same simulations; Studies 1–3 (PHYS_AL etc.) used them for other questions.
- They are reported next to the final repeats, so that the size of the transfer effect can be seen across 6 partitions rather than 4.
- The same endpoints and levels are used, with level = 0.9 × R²_full(M0) over repeats 3–4.
