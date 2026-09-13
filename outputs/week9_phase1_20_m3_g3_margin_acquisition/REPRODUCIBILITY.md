# Reproducing Phase 1.20

Use the published `codex/week9-phase1-20-m3-g3-margin-acquisition` branch, which inherits the exact Phase 1.14 source and frozen input artifacts. Install the repository requirements in a Python environment. The tested runtime and package versions are recorded in `input_provenance.json`.

Limit BLAS/OpenMP threads to one per worker; parallelize outer runs only. The tested run used four workers. From the repository root:

```text
python -m unittest tests.test_week9_phase1_20_m3_g3_margin_acquisition -v
python -m src.week9_phase1_20_m3_g3_margin_acquisition preflight
python -m src.week9_phase1_20_analysis provenance
python -m src.week9_phase1_20_m3_g3_margin_acquisition smoke --workers 1
python -m src.week9_phase1_20_m3_g3_margin_acquisition run --workers 4
python -m src.week9_phase1_20_analysis all
```

Do not proceed past any failed gate. The exact imported historical loader reconstructs deterministic split objects; the provenance command compares every membership against the saved Week 8.5 split manifest. It does not select new splits.

The full-run command resumes atomic per-budget checkpoints, whose source fingerprint must match. Keep these local caches for resumption. Published compact tables contain the complete paths, P2 test predictions and every candidate probability used to audit acquisition. Existing P0/P1 predictions and paths are reused from the inherited, hash-pinned artifacts.

`frozen_protocol.json` contains the predeclared endpoint, practical threshold and decision rule. `paired_contrasts.csv` includes the exact bootstrap seed for each contrast. The bootstrap implementation and 10,000-draw convention come from Phase 1.14. The notebook reads the resulting artifacts and does not rerun trajectories.

Historical headline values refer to accuracy AULC. Phase 1.20's primary endpoint is balanced-accuracy AULC B16–B40; these values must not be conflated.
