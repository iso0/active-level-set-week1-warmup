# Deviations from the Week 14 freeze (commit 3278f7dc)

- **D1 (C1 crash fix, no design change).** `heldout_mono_curved` was implemented and listed in the
  freeze but missing from the `FAMILIES` seed-index tuple in `src/week14_discovery.py`, so the first C1
  run crashed before producing any result. The name was appended at the end of the tuple (seed index 10),
  leaving all other seeds unchanged. No result had been observed.
- **D2 (execution only).** After the freeze, the NEW-only and OLD in-domain loops of
  `src/week14_real_checks.py` were wrapped in `joblib.Parallel` for speed. Model definitions, splits,
  seeds (`seed=0` per fit) and outputs are unchanged; each split is fitted independently, so results are
  identical to serial execution.
- **Additional post-freeze analyses (clearly labelled, not part of the frozen predictions):** NSD-oracle
  mechanism (Study 4c), BALD development study (Study 5), and the NEW anomaly sensitivity run
  (`src/week14_anomaly_sensitivity.py`, POST-HOC NEW).
