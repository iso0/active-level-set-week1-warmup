# Listing failure root cause

## Previous invalid result

The previous audit reported **117 actual folders**,
**116 monitor-complete simulations**,
**124 master-only records**,
`sim_00001 through sim_00117`, a
**117 rows × 154** dataset, and
endpoint counts **80/116**
and **54/116**. These
statements are retained here only as the explicitly labelled invalid result being
repaired; they are not current scientific findings.

## Faulty method

The previous source called:

```python
info = HfApi().repo_info(..., revision="0e859b748fdbc8454f66e58e101e333ac0479d42")
files = sorted(s.rfilename for s in info.siblings)
```

It then inferred simulation folders from prefixes in `info.siblings`. That field is a
single global repository-metadata payload, not a directory enumeration and not an
iterator whose pagination the caller can consume.

The old program did not numerically equate the file count with the folder count.
Instead, it derived a folder set from prefixes in that incomplete file payload, so
the inferred folder count inherited the payload's truncation. No caller-visible
recursive page traversal was performed.

## Observed failure

- `repo_info().siblings` returned 98,552 file paths.
- Its lexicographically final path was
  `final_data_processed/sim_00117/frames/side/frame_00222.png`.
- The largest simulation prefix visible in that truncated payload was
  `sim_00117`.
- Direct path checks and immediate-directory enumeration at the same immutable SHA
  show `sim_00118`, `sim_00224`, `sim_00241`, and `sim_00242`.

Therefore the absence of later prefixes from `siblings` was incorrectly interpreted as
folder absence. The filtering expression itself did not discard later folders; those
paths never reached it. The revision was also not the cause: old pinned revision and
current `main` both resolve to `0e859b748fdbc8454f66e58e101e333ac0479d42` at inspection time.

The exact demonstrated root cause is reliance on an incomplete global sibling payload
as the sole source of folder truth. Its size and stopping position are consistent with
a server-side large-tree cap, but the repair does not depend on guessing the server's
internal limit.

## Corrected method

1. `HfApi.list_repo_tree(path_in_repo="final_data_processed", recursive=False)`
   was fully consumed and `RepoFolder` entries were selected directly.
2. The independent HTTP tree API was called with `limit=50`; all
   5 `Link: rel="next"` pages were consumed.
3. Every discovered simulation folder was recursively enumerated separately.
   Explicit HTTP pagination consumed 318 pages for
   229 folders. After unauthenticated HTTP rate limiting,
   the remaining 12 folders were re-read through fully consumed
   recursive HfApi iterators.
4. Required paths, including `sim_00242`, were queried directly.
5. The folder set was reconciled with `experiments.csv` and per-folder metadata.

Both top-level methods return 241 simulation
folders and the same sorted ID list. The per-simulation traversal found all 34 monitor
types in every folder and equal front/side/top image counts. These independent checks
are the evidence that corrected enumeration is complete.
