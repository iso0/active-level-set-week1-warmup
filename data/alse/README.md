# data/

- `population.csv` is the frozen thesis dataset: 405 simulations (73 `has_keyhole`), one row per
  simulation, features `P` [W], `VX` [m/s], `LS` [m, Gaussian spot radius], `ST` [K], plus the
  extracted physical responses (`value__max_depth`, `value__G3`, ...) and the grouping key
  `input_tuple_sha256`. It is a byte-identical copy of the archive's
  `outputs/week7_06_real_data_boundary_active_level_set/primary_common_population.csv`
  (sha256 of raw bytes `c15658cac87a8616a1984185ec1afc8126a1db811f0d5819e62cfb621a7486c7`).
- How it was built (Hugging Face `ioandanielc/sph_v2` at revision `b6dc254a…`, label ledgers,
  target extraction, exclusion rules) is documented in `docs/data.md`. Raw downloads go to
  `data/raw/` (gitignored); `alse.data` has the pinned download helpers.
- Never edit this file. Derived tables belong in `outputs/` or `results/`.
