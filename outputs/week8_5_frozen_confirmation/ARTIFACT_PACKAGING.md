# Week 8.5 large-artifact packaging

The full uncompressed outputs remain present in the execution worktree. Four required CSVs exceed GitHub's normal single-blob limit, and the 3200 restart checkpoints contain 0.65 GB of repetitive JSON. They are therefore stored in two portable compressed bundles for Git publication rather than as oversized ordinary blobs.

## Machine-readable CSV bundle

`week8_5_large_machine_readable_artifacts.tar.gz`

SHA-256: `c2e82faf7bb54c6f943a30529ab03950701d5f7037d9ced0dfc26cbd7036ec59`

Contents:

- `learning_curves.csv`
- `trajectory_per_budget.csv`
- `seed_registry.csv`
- `random_seed_manifest.csv`

Extract from this directory with:

```powershell
tar -xzf week8_5_large_machine_readable_artifacts.tar.gz
```

## Restart-checkpoint bundle

`week8_5_checkpoint_bundle.tar.gz`

SHA-256: `1004fc299e00db6f1b2b89e4407f5ac8b2c4815d1169bcaad43dacdebacf72a9`

It contains the complete `checkpoints/` directory used for deterministic resume at H=80, H=120, and H=160.

Extract with:

```powershell
tar -xzf week8_5_checkpoint_bundle.tar.gz
```

The uncompressed-file SHA-256 values remain authoritative in `run_manifest.json`. Compression changes storage only; it does not change any numerical result.
