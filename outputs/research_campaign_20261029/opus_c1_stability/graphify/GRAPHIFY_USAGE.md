# Graphify usage record (C1 stability task, 2026-10-29)

## Graph and versions

| item | value |
|---|---|
| Graphify | 0.9.96: launcher `C:\Users\ozgur\.local\bin\graphify.exe`; interpreter `C:\Users\ozgur\AppData\Roaming\uv\tools\graphifyy\Scripts\python.exe` |
| graph | `C:\Users\ozgur\Documents\thesis-graphify-sync-2026-10-29\source\graphify-out\graph.json` — 11,025 nodes / 39,080 links, undirected |
| graph hash | SHA-256 5D96E506…8E4F, 14,792,618 bytes |
| graph build | `built_at_commit` 4fc9b5d50308f29013b7844ec39090b257aa713d (main, Research Hub); `baseline_commit` 3caf7c4e49499f30e6c9b642a226454068f08969; AST reuse + 77-file delta; no semantic extraction |
| code base | `git diff 3caf7c4e..4fc9b5d -- src/` changes 0 files, so `src/` in this worktree equals the graph's `src/` |
| research branch | `c1-stability-20261029`, created at 3caf7c4e. No reset; the 49 untracked experiment records are kept. |

## Settings for every call

- `GRAPHIFY_NO_AUTO_REFRESH=1`: the launcher can otherwise refresh stale user-scope skills (`graphify/__main__.py`, `_refresh_stale_skills`). No skill file changed; checked by modification times.
- `GRAPHIFY_QUERY_LOG_DISABLE=1`: the query log is opt-in, and this keeps it off.
- Always pass an explicit `--graph`. Nothing was written into the snapshot or the shared baseline graph.

## Queries

The query outputs are in this folder.

1. `graphify query "C1 depth fitting and margin" --graph <graph> --seed "src/ea_cand.py" --seed "src/ea_fwd.py" --budget 1000`
   - 218 nodes, truncated at 52 (`query1_c1_depth_fitting_margin.txt`).
   - It finds the C1 functions `GPMAP` (L41), `gp_fit()` (L54), `depth_fit_cand()` (L63), `predict()` (L76), `dev_unit()` (L92) in `src/ea_cand.py`, and `unit_L()` (L29), `unit_X()` (L40) in `src/ea_fwd.py`. All are checked in the source.
2. `graphify query "honest cross-fit folds out-of-fold depth" --graph <graph> --seed "src/ea_diag2.py" --seed "src/rc19b_keyhole.py" --context calls --budget 900`
   - It returns only the two file nodes: file nodes carry `contains`, not `calls`, edges (`query2_crossfit_folds.txt`).
   - The function-level edges were then read directly from `graph.json` (read-only; `graph_edges.py` in the scratchpad, output summarised below).

## Missing cross-file call edges

These were checked in the source. A missing edge does not mean there is no dependency. The graph has only same-file `calls` edges for these functions.

| caller | callee | in graph? | source line |
|---|---|---|---|
| `ea_cand.predict` | `ea_diag2.cf_generic` | no | `src/ea_cand.py:83` `D2.cf_generic(...)` |
| `ea_cand.predict` | `ea_diag.lin` | no | `src/ea_cand.py:84` `DG.lin(...)` |
| `ea_fwd.unit_X` | `ea_cand.predict` | no | `src/ea_fwd.py:44` |
| `ea_fwd.unit_L` | `ea_cand.predict` | no | `src/ea_fwd.py:34` |
| `ea_diag2.cf_generic` | `rc19b_keyhole.folds` | no | `src/ea_diag2.py:51` |
| `ea_diag.lin` | `rc22_common.phr_family` | no | `src/ea_diag.py:80` |
| `ea_cand.predict` | `ea_cand.depth_fit_cand` (same file) | yes | `src/ea_cand.py:83` |

## Old-graph pointers

These were found and not changed:
- `C:\Users\ozgur\Documents\thesis\CLAUDE.md` and `AGENTS.md` ("run `graphify query` ... `graphify update .`");
- `C:\Users\ozgur\Documents\thesis\.claude\settings.json` PreToolUse hooks `graphify hook-guard search|read`.

All of them use the relative `graphify-out/`. In the main checkout (week20 branch) that is the old default graph `C:\Users\ozgur\Documents\thesis\graphify-out\graph.json`. This worktree has no `graphify-out/`, so none of them fires here.

The project skill (`thesis\.claude\skills\graphify\SKILL.md`) also defaults to `graphify-out/` relative to the working directory. This task uses only the explicit `--graph` path and never runs `graphify update .`.

## Limits

- The graph is static Python AST connectivity. Runtime dispatch through module aliases (`CA.`, `D2.`, `DG.`, `C22.`) is not resolved.
- PowerShell runners and scientific tables are outside it.
- The graph does not contain this task's new code. A small local map of the changed files is produced at the end, inside this task folder; the shared graph is not rebuilt.
