# Astra Week 19 R&D package — receipt note (written by the repository, not part of the package)

The owner attached these three files on 2026-10-10 from
`C:/Users/ozgur/Documents/Codex/2026-10-10/files-pasted-by-the-user-you/outputs/week19_temporal_regime_audit/`.
They are copied verbatim (byte-identical, `cmp`), and nothing here was edited or executed. The sibling `work/` folder
was not opened.

| File | SHA-256 |
|---|---|
| `ASTRA_RND_MEMO.md` | `f7a5fa9ac54a4f202b13f8f556efb951c7baab93c957c76f40a25122670d2551` |
| `OPUS_IMPLEMENTATION_REQUEST.md` | `58d00ab6b5f19c4189506ffa3e3ef369d83b09a47c5571ef3471db91a2ae3ba4` |
| `ASTRA_REVIEW_CHECKS.json` | `f4fc435150cc8c27d51ff1e9140cb9179ffbc460653ec84415b27038bc2771dc` |

How they are used:

- **What was implemented.** P0–P2 of the request, with the owner's changes of 2026-10-10, in `outputs/week19_temporal_regime_dev_pilot/`:
  - the primary endpoint is BA at B40, with specificity and short-K sensitivity as gate conditions;
  - q20 is reported as a co-endpoint;
  - a falsifiable prediction was written before any fit.
- **What was not started.** P3 and the morphology fallback machinery.
- **How Astra's statements are treated.** They are hypotheses or specifications, never evidence. Astra's arithmetic is re-derived independently (pilot `tables/P0_CHECKS.csv`).
