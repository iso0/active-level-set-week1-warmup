# Round 3 research package

Prepared 5 October 2026. The thesis repository was read-only. This directory is outside it.

Start with [the complete report](C:/Users/ozgur/Documents/thesis-research-outputs/round3-20261005/ROUND3_RESEARCH_REPORT.md).
It contains the Week 16 interpretation, mathematical results, source audit, literature-priority table,
assumptions, counterexamples, open problems, experiment predictions, and
“What this changes in Burak’s thesis.”

- [Standalone LaTeX theorem/proof appendix](C:/Users/ozgur/Documents/thesis-research-outputs/round3-20261005/ROUND3_THEOREM_APPENDIX.tex): 60 theorem, proposition, lemma or counterexample statements, each with a proof.
- [Week 16 cross-audit](C:/Users/ozgur/Documents/thesis-research-outputs/round3-20261005/WEEK16_CROSS_AUDIT.md).
- [Experiment-prediction table](C:/Users/ozgur/Documents/thesis-research-outputs/round3-20261005/EXPERIMENT_PREDICTIONS.md).
- [Literature-priority table](C:/Users/ozgur/Documents/thesis-research-outputs/round3-20261005/LITERATURE_PRIORITY.md).
- [Assumptions](C:/Users/ozgur/Documents/thesis-research-outputs/round3-20261005/ASSUMPTIONS.md), [counterexamples](C:/Users/ozgur/Documents/thesis-research-outputs/round3-20261005/COUNTEREXAMPLE_CATALOGUE.md), [open problems](C:/Users/ozgur/Documents/thesis-research-outputs/round3-20261005/OPEN_PROBLEMS.md).
- ROUNDS1_2_REFERENCE_APPENDIX.tex preserves the earlier reference proof package; the Round 3 source does not require it to compile.

The LaTeX source was sent to the built-in editor. Compilation could not be verified because the
application compiler returned “Unable to find standard directories for platform.”
No PDF is supplied or claimed to have compiled. No TeX installation or plugin was installed.
Structural checks pass; they do not substitute for successful LaTeX compilation.

NUMERICALLY CHECKED: main Week 16 aggregates were recomputed from saved tables.
Checks also covered 1,819 exact binary laws, 2,036 ranked binary sequences, exact negative-score
and geometric-parity constructions, 2,000 moment-transfer law pairs, 2,700 common-noise checks,
200 sequential law pairs with 12 policy maps each, six discovery constructions and nine
shrinkage grids. Gaussian geometric-value quadrature error was below 8.3e-15.
No new SPH acquisition trajectory experiment or bootstrap replication was run.

Reproducibility: verify_round3.py reads the repository's saved tables and writes beside itself;
verify_extensions.py runs independent mathematical checks and writes beside itself.
build_package.py reconstructs the standalone source from the four proof fragments.
The scripts do not import repository modules. Source hashes and the inspected commit are
recorded in PROVENANCE.json. Source files were checked again before packaging.
