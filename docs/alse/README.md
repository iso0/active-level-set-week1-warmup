# alse: sample-efficient active level-set estimation

Code and written record for the thesis "Sample-Efficient Active Level-Set Estimation, with an Application to Melt-Pool Regime Boundaries" (supervisor: Ioan).

The problem: SPH simulations of laser powder-bed fusion have four inputs, P [W], VX [m/s], LS [m, Gaussian spot radius], ST [K, substrate temperature], and a manual binary label `has_keyhole`. The method chooses which simulations to label so that the keyhole/conduction boundary is learned with the fewest simulator calls. The frozen population is 405 simulations, 73 Keyhole (`data/population.csv`).

This tree is a lean rewrite of a much larger ChatGPT/Codex-generated repository (the archive). Every frozen number, seed and kernel is ported exactly from the archive and gated by tests against it. Read `docs/overview.md` first.

## Layout

```
alse/            shared library, one module per concern (all science lives here)
experiments/     thin runnable scripts, each with --smoke
tests/           unit tests plus reproduction gates against the archive (@pytest.mark.archive)
data/            population.csv (frozen dataset); data/raw/ for downloads (gitignored)
results/         curated evidence copied from the archive; hard cap 50 MB
outputs/         regenerable run outputs (gitignored)
docs/            overview, architecture, experiments, claims, data, protocol, decisions, archive map
```

Conventions and rules are in `CLAUDE.md`; the module-by-module porting contract is in `docs/architecture.md`.
Status on 2026-09-03: `alse` has `config`, `io`, `benchmarks`, `physics`, `acquisition`, `metrics`, `stats`, `data`; `surrogates`, `hybrid_gpc`, `sur`, `protocol` and the experiment scripts are still to be written.

## Install

Python 3.12 or newer (`pyproject.toml`). The frozen numbers were produced with Python 3.14.4, numpy 2.5.1, pandas 2.3.3, scipy 1.18.0 and scikit-learn 1.9.0 (archive `outputs/week6_03_model_target_robustness/phase3_runtime_provenance.json`); other versions may change float-exact results.

```bash
python -m pip install -e ".[dev]"
```

## Tests

```bash
python -m pytest                 # fast unit tests
python -m pytest -m archive      # reproduction gates; skipped if the archive is absent
```

The archive gates compare `alse` functions and outputs with the archived code and artifacts (for example B1-q20 accuracy AULC 0.8135202205882353 for the frozen margin arm, `outputs/week8_5_frozen_confirmation/repeat_level_metrics.csv`).

## Experiments

Every script writes `summary.json` plus a few CSVs and PNGs into `outputs/<name>/`. Run any of them with `--smoke` first.

| Script | What it reproduces | Notes |
|---|---|---|
| `experiments/synthetic_gpr.py` | Branin and Ackley4 with five GPR pool rules and boundary metrics | `--benchmark --seeds --budget` |
| `experiments/synthetic_gpc.py` | fixed-kernel GPC rules and Bernoulli SUR on Branin, Ackley4, Hartmann4 | |
| `experiments/real_benchmark.py` | Phase 6/7 exploratory benchmark on `data/population.csv` (20 runs) | `--workers`; optional hybrids |
| `experiments/frozen_protocol.py` | Week 8.5 frozen confirmation protocol (100 runs, 30 random continuations) | full run took 9336 s in the archive and is not required; `--horizon`, `--workers` |
| `experiments/physics_surrogates.py` | h coordinate and the M0, H, M2W, M3 surrogates replayed on the frozen margin path; M3-margin sequential run | `--limit-specs` |
| `experiments/curate_results.py` | copies the curated evidence shortlist from the archive into `results/` with a manifest | |
| `experiments/summarize_results.py` | regenerates the headline tables from `results/` | |

```bash
python experiments/<name>.py --smoke
```

Scripts are written after the library; `docs/experiments.md` is the index with the status and decision of each.

## The archive

The original repository lives beside this tree at `../thesis_work_chatgpt` (override with the `ALSE_ARCHIVE` environment variable; see `alse/config.py`). It is read-only: sources in `src/`, results in `outputs/`, old documents in `docs/` and `reports/`. Nothing in this tree writes to it. Archive tests skip when it is absent. `docs/archive.md` maps every archived phase to its script and artifacts.

One caveat: the archive working tree is a snapshot, and its git HEAD (`2552078`) holds a completed Phase 1.18B result whose files are not present on disk. `docs/overview.md` section 3.3 explains what to restore before curating results.

## Documentation

- `docs/overview.md`: research question, final method, evidence chain, current state, open decisions
- `docs/architecture.md`: layout and porting contract for `alse`
- `docs/experiments.md`: one row per experiment with its decision
- `docs/claims.md`: supported and prohibited claims with artifact paths
- `docs/data.md`: dataset pins, population construction, target definitions
- `docs/protocol.md`: the frozen Week 8.5 protocol and the Phase 6/7 protocol
- `docs/decisions.md`: dated decision log
- `docs/archive.md`: map of the archived repository
