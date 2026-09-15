# results/

Curated thesis evidence copied from the archive by `python experiments/curate_results.py`.
Policy:

- Only primary evidence: decision files, summary tables, preregistration/protocol JSONs,
  the final thesis figures, and one headline figure or table per canonical phase.
- Hard size cap 50 MB. Large caches (checkpoint bundles, per-candidate score dumps,
  prediction histories, parquet time series) stay in the archive and are listed by path
  and sha256 in `MANIFEST.csv` instead of being copied.
- `MANIFEST.csv` (written by the curation script) records source path, destination, bytes
  and sha256 for every copied file.
- Numbers quoted in `docs/claims.md` must be traceable to a file here or to a manifest entry.
