# Thesis project conventions

Sample-efficient active level-set estimation for melt-pool regime boundaries.
Read `docs/overview.md` first, then `docs/architecture.md`.

## Layout
- `alse/` shared library, one module per concern. All science lives here.
- `experiments/` thin runnable scripts (argparse, `--smoke`), no science logic.
- `tests/` unit tests plus reproduction gates against the archive (`@pytest.mark.archive`).
- `data/population.csv` the frozen 405-simulation population (the dataset). Raw downloads go to `data/raw/` (gitignored).
- `results/` curated evidence only, copied by `experiments/curate_results.py`. Hard cap 50 MB.
- `outputs/` regenerable run outputs, gitignored.
- `docs/` the written record: overview, experiments index, claims, data, protocol, decisions, archive map.
- Archive: the original ChatGPT/Codex worktree at `../thesis_work_chatgpt` (read-only; `ALSE_ARCHIVE` overrides).

## Rules that keep this lean
1. Never copy a helper into an experiment; import it from `alse`. If two experiments need the same thing, it belongs in `alse`.
2. An experiment script is under 300 lines and writes at most `summary.json`, a few CSVs and a few PNGs into `outputs/<name>/`. No manifests, hashes of source files, notebook generation, git assertions or validation checklists.
3. Provenance is `summary.json`: settings, `alse.__version__`, data pin, runtime. That is enough.
4. Frozen behaviour (seed strings, kernels, bounds, tie-breaks, normalisation) is marked `# frozen: <archive file>::<symbol>` and covered by a test. Do not "clean up" such a function without running `pytest -m archive`.
5. Name things by what they test (`synthetic_gpc`, `frozen_protocol`), never by week or phase number.
6. When an experiment concludes, add one row to `docs/experiments.md` and one dated entry to `docs/decisions.md`. Update `docs/claims.md` only when a supported or prohibited claim changes.
7. Notebooks are for looking at outputs, never for defining methods. Keep them out of git unless they are short and stripped of outputs.
8. Prefer deleting over archiving inside this tree; the archive already preserves history.

## Commands
```bash
python -m pytest                      # fast unit tests
python -m pytest -m archive           # reproduction gates against the archive
python experiments/<name>.py --smoke  # every experiment has a quick mode
```
