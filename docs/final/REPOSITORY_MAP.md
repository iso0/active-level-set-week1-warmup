# Repository, branch and folder map

Written on 2026-11-02 during the finalization. It records the state of GitHub and of the local computer, says which copy is canonical, and explains how to reproduce, test and restore. It answers "where is what" for the whole thesis.

## 1. GitHub

Repository: `https://github.com/iso0/active-level-set-week1-warmup` (public; default branch `main`; no GitHub Pages).

**`main` is the single complete branch.** The finalization merged the last study branch into `main`, so `main` now holds:
- every study, Week 1 to GT;
- the finalization layer `docs/final/`;
- the Research Hub of 2026-10-28.

Every other branch is an ancestor of `main`: nothing exists only on a side branch. The side branches are kept because the records cite them by name.

| Branch | Tip | What it holds | Status |
|---|---|---|---|
| `main` | tag `thesis-final-2026-11-02` | everything | **canonical** |
| `thesis-finalization-20261102` | = `main` at the finalization | the finalization commits | merged; kept |
| `geometry-temperature-20261102` | 7ffaa7d9 | GT (and every earlier study) | merged; frozen |
| `ioan-requests-20261031` | 0a57d644 | IR | merged; frozen |
| `final-robustness-20261029` | b0e9569f | FR | merged; frozen |
| `c1-stability-20261029` | c8437907 | C1S | merged; frozen |
| `joint-depth-label-dev` | 3caf7c4e | joint study, RC18–RC24, EL, EA, C1C | merged; frozen |
| `research-hub-public-2026-10-28` | 86e40088 | Research Hub v1 publication | merged; frozen |
| `week20-active-temporal-dev` | e2bcf97a | Weeks 20 and C3 | merged; frozen |
| `week19-temporal-audit` | 7707d7f4 | Week 19 | merged; frozen |
| local only: `research-hub-integration-2026-10-28` | 3caf7c4e | Hub review workspace branch (same commit as C1C) | kept |

**Linear history.** week19 → week20 → joint-depth-label-dev → C1S → FR → IR → GT is one chain. The three Research Hub commits sat on `main` beside it, on top of 3caf7c4e, until the finalization merge joined them.

**Tags** (annotated, pushed) give each frozen study state a permanent name:

| Tag | Commit | Meaning |
|---|---|---|
| `study/week19-review` | 7707d7f4 | Week 19 pilot review and Ioan package |
| `study/week20-c3` | e2bcf97a | Week 20 and the C3 confirmation |
| `study/c1c-close` | 3caf7c4e | C1C close (end of `joint-depth-label-dev`) |
| `hub/v1` | 86e40088 | Research Hub v1 |
| `hub/curated-evidence` | 4fc9b5d5 | Research Hub curated Astra evidence |
| `study/c1s-close` | c8437907 | C1S close |
| `study/fr-close` | b0e9569f | FR close |
| `study/ir-close` | 0a57d644 | IR close |
| `study/gt-close` | 7ffaa7d9 | GT close (with its test note) |
| `thesis-final-2026-11-02` | final `main` | the finalized repository for thesis writing |

**Earlier cleanups** had already removed obsolete branches, each with its tip SHA logged:
- 2026-09-21: 38 branches (`docs/consolidation/BRANCH_DELETION_LOG.md`);
- 2026-10-02: 52 local and 2 remote branches (progress log 2026-10-02). The two git stashes "thesis consolidation 20260914 original main safety snapshot" and "phase1-20 preserve original main user work" are old safety snapshots. They were left untouched.

**The Research Hub layer.** Its files on `main` are hash-locked by its own publication manifest (`docs/research/PUBLICATION_SHA256.csv`): `RESEARCH_INDEX.md`, `docs/research/*`, `research/astra/*`, `PUBLICATION_*`, `DATA_AVAILABILITY.md`, `RIGHTS_AND_ATTRIBUTION.md`. The finalization therefore did not edit them. They are a dated layer that covers results up to C1C. The root `README.md` is not hash-locked; it was updated to point to `docs/final/` and to list the later studies.

## 2. The canonical local folder

**`C:\Users\ozgur\Documents\thesis`** is the repository's main checkout. Write the thesis from here. On 2026-11-02 it was still on the old branch `week20-active-temporal-dev`. This session ran in an isolated worktree and could not switch it, so one command does that, safely and logged:

```
powershell -NoProfile -ExecutionPolicy Bypass -File tools\finalize_local_workspace_20261102.ps1
```

Run it from the canonical folder; on its current branch the script is in this worktree's `tools\` folder. It:
1. detaches the Research Hub worktree that still holds `main`, with its files unchanged;
2. switches the canonical folder to `main` and fast-forwards it to `origin/main`;
3. keeps every untracked and ignored file. That includes `data\raw\sph_v2\` (the raw monitors), caches, the Week 10–18 advisor deck (`outputs\week10_18_presentation\`), the meeting pages (`29-10-2026html`, `30-10-2026_ioan_meeting.html`) and the agent settings (`.claude\`, `.codex\`, `CLAUDE.md`, `AGENTS.md`).

`-DryRun` prints the plan without changing anything; a dry run on 2026-11-02 passed every check. `-Archive` additionally moves the folders listed as "archive candidate" in §3 into `Documents\thesis_archive\` and writes an old → new map; this step is optional.

Before the script runs:
- the canonical folder on its old branch does not contain C1S, FR, IR, GT or `docs/final/`;
- the complete state is on GitHub `main` and in this worktree.

## 3. Every thesis-related folder on this computer (2026-11-02)

Sizes are approximate and exclude `.git`. The column "unique content" says what exists nowhere else: everything tracked is also in git and on GitHub.

| Folder (`Documents\…`) | What it is | Unique content | Recommendation |
|---|---|---|---|
| `thesis` | **canonical checkout** (main worktree of the repository) | raw data `data\raw\sph_v2\` (3 revisions, git-ignored); `.venv`; Week 18–20 caches; advisor deck; meeting pages; agent settings | keep; switch to `main` (§2) |
| `thesis\.claude\worktrees\joint-depth-label-dev` | this session's worktree (branch `thesis-finalization-20261102`) | about 3 GB of raw unit outputs, now **copied** to `thesis_archive` (§4) | keep until you no longer need the session; the archive copy protects the raw outputs if the app removes the worktree |
| `thesis_archive` | created by the finalization: raw-output copy, logs, optional moved folders | the copy of §4 | keep |
| `thesis_shared_runtime` | campaign coordination state (`opus_state.json`, `astra_state.json`); all CLOSED | — | keep (read by campaign code) |
| `thesis_external_quarantine` | sealed oracle of the Week 11 NEW batch (`NEW185_SEALED_ORACLE.csv`) | the sealed oracle | keep in place (read by `src/week11_external_oracle_deriver.py`; never open it for learning) |
| `thesis-preservation-staging` | `astra-git-bundles` (2.4 GB): Astra's original git histories | Astra histories (the Hub's "offline preservation") | keep |
| `Codex` | the Codex application's own workspace, including Astra's delivered packages under `2026-10-10\…\outputs\` | Astra packages | do not touch (another application's area) |
| `thesis-week4-chronology-restructure`, `thesis-week5-first-conduction-gp`, `thesis-week9-phase1-18b-…`, `thesis-week9-phase1-19a-…` | old detached worktrees (Weeks 4, 5, 9) | 18b: 70 ignored checkpoint files; 19a: `00_AKTIF_PROJE_YOLU.md` and ignored Phase 2 CSVs (110 MB); week5: its `.venv` (1.4 GB) | **keep in place**: `src/week9_phase1_21_repeat_audit_driver.py` and the Phase 1.10 scripts read them by absolute path |
| `thesis-research-outputs` | Astra Round 3 package as delivered | — (copied into `outputs/astra_round3/`) | keep (named in `outputs/astra_round3/PROVENANCE.json`) |
| `hf-sph-v2-old-data-monitor-restoration` | August restoration of old-data monitors on Hugging Face | its PR scripts and payload | keep (named in the Phase 1.22 audit) |
| `thesis-complete-consolidation` | detached worktree of the 2026-09-21 consolidation | none (pycache only) | archive candidate |
| `thesis-research-hub-main-2026-10-28`, `thesis-research-hub-publish`, `thesis-research-hub-review` | Research Hub worktrees of 2026-10-28 | hub-review: its build workspace (438 untracked files, 75 MB: `_build/`, `provenance/`, drafts) | archive candidate (moved intact with `git worktree move`) |
| `thesis-curated-evidence-staging-2026-10-28`, `thesis-research-hub-staging`, `thesis-research-hub-public-draft`, `thesis-graphify-audit`, `thesis-graphify-sync-2026-10-29`, `codex-temp-week8-figure-audit` | staging copies of the Hub publication, graphify audits, two figure montages | staging files (all published content is on `main`) | archive candidate |

## 4. Raw outputs that are not in git

**Where they are.** The study folders keep per-unit checkpoints (`*/units/`, resumable caches) out of git on purpose: they are large and reproducible from the frozen code. Their committed exports, tables and decisions are the evidence of record. Until 2026-11-02 the raw units of RC18–GT existed only in this worktree.

**The copy.**
- Location: `C:\Users\ozgur\Documents\thesis_archive\worktree_raw_outputs_20261102\`.
- Size: 18,972 files, 2,993,011,746 bytes, 0 conflicts.
- Verification: every file was checked by SHA-256 after copying. The per-file manifest is `FILE_MANIFEST_SHA256.csv` (its own SHA-256 is b7e5cd384aaadd7eba1591bab26ee1beea93112fad9a7bbf75c78db368604c94). The per-directory summary is committed as [RAW_OUTPUTS_ARCHIVE_SUMMARY.csv](RAW_OUTPUTS_ARCHIVE_SUMMARY.csv).

**Which studies need them.**
- IR and GT read the 272 recorded EA C1 paths from `outputs/research_campaign_20261026/opus_error_attribution/ea-fwd/units/`.
- To re-run IR or GT elsewhere, restore that directory first:

```
robocopy "%USERPROFILE%\Documents\thesis_archive\worktree_raw_outputs_20261102\outputs" "%USERPROFILE%\Documents\thesis\outputs" /E /XC /XN /XO
```

**Ignore rules.** The finalization added ignore patterns for the RC24, EL, EA, C1C, C1S and FR unit folders, which had none, so `git status` is clean.

## 5. Inside the repository

| Path | Content |
|---|---|
| `docs/final/` | **start here**: synthesis, study index, claims for the thesis, open items, glossary, this map, Turkish summary, final figures |
| `docs/alse/` | central records: `claims.md` (C01–C158), `decisions.md`, `experiments.md`, `data.md`, `protocol.md`, `overview.md` |
| `docs/thesis_progress_log.md` | chronological log (Turkish from 2026-09-14) |
| `outputs/joint_depth_label_development/` | central attempt ledger (`ATTEMPT_LEDGER.md`), `CLAIMS_MATRIX.md`, joint-study reports, pool coordination |
| `outputs/research_campaign_2026MMDD/opus_*/` | one folder per study from RC18 on: `PROTOCOL*`, `FINAL_REPORT*`, `DECISION*`, exports, ledgers; `STATE.json` says CLOSED. `runner/STATUS.md` files are snapshots at closure (their "remaining … h" is not live) |
| `outputs/weekNN_*`, `docs/phases/`, `docs/trackA_freeze/`, `docs/week11/` | Weeks 1–20 |
| `outputs/astra_*` | Astra packages copied verbatim (hypotheses; never executed) |
| `research/astra/`, `docs/research/`, `RESEARCH_INDEX.md` | the Research Hub layer (§1) |
| `src/` | all code: weekly modules `weekNN_*`, joint study `jdl_*`, campaigns `rc18_*` … `rc24*`, `el_*`, `ea_*`, `c1c_*`, `c1s_*`, `fr_*`, `ir_*`, `gt_*`, finalization `fin_figures.py`; tests in `src/tests/` |
| `tools/` | `run_regression_gate.py`, `finalize_local_workspace_20261102.ps1` and older helpers |

## 6. Environment, tests and reproduction

**Environment.**
- Python 3.14.4, NumPy 2.5.1, SciPy 1.18.0, scikit-learn 1.9.0, OpenBLAS 0.3.33 (8 threads by default).
- The campaign runners used single-thread workers (BLAS = 1). The Week 18 T_TOBIT twin truth needs 8 BLAS threads to reproduce; its test now sets this itself.

**Regression gate.**
- Command: `python tools/run_regression_gate.py`. It runs the Weeks 12+ suite: `src/tests` without `test_week1`–`test_week11`, 27 files.
- On the final tree: 219 passed, 2 skipped, 0 failed, with the default threads and with `--threads 1`.
- Before the finalization: 217 / 2 / 2. The two failures are explained and fixed in the central ledger rows FIN-TOBIT and FIN-IDS.

**Legacy suite.** The Week 8.5–11 tests (40 failures in the full suite of 59 files) check historical layouts. The 38 Week 8.5–9 failures are pre-existing and identical on 0a57d644. Running them rewrites three tracked Week 9 outputs (restore them with `git restore`) and downloads three public Masinelli files into `.cache/`. Run them only in a scratch worktree (`opus_geometry_temperature/regression/FULL_SUITE_NOTE.md`).

**Raw data.**
- Hugging Face `ioandanielc/sph_v2`, pinned revisions: `b6dc254a` (OLD), `2e1eec9c` (NEW), `d69dac5b` (first `sph_v2` audit).
- Local copy: `thesis\data\raw\sph_v2\<revision>\` (git-ignored).
- Run folder names exceed Windows' 260-character limit. Python needs the `\\?\` prefix or long-path support to open their monitor files.

**Final figures.** `python -m src.fin_figures` rebuilds `docs/final/figures/` from the frozen C1C exports and checks them against the reported numbers (`FIGURE_CHECKS.json`).

**Integrity conventions.** These held for every study and should be described in the thesis appendix:
- register before results;
- fresh repeat IDs used once;
- paid-only learners;
- every opened run counted;
- append-only ledgers with dated errata;
- evidence labels.
