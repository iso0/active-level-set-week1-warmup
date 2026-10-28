# Explicit retry of the interrupted zero-fit integrity scan

20 October 2026, approximately 04:44 UTC. Exact rational reference PASS and all
six finite-mixture acquisition references accepted. Acquisition budget is exactly
six fits / 72 component solves; these saved results will be skipped, not rerun.
The subsequent integrity scan exited at 04:41:41 UTC when the unchanged resource
guard reported global total exceeded. No integrity result exists and it performs
zero GP fits. The observer state and stderr are archived under
history/finishing_integrity_resource_yield_20261020/.

This turn used short read-only Python JSON-inspection processes without a
--threads argument. The conservative guard counts such a leaf as four threads,
so overlap with the one-slot scan can produce this yield without numerical BLAS
oversubscription. The exact triggering process snapshot was not saved: this is
a plausible operational explanation, not a reconstructed proof or an attribution
to Opus. Subsequent inspections use PowerShell or explicitly accounted processes.
No resource limit, grant, live identity or scientific source is changed.

The failed observer has exited. One explicit idempotent observer retry is now
registered. It skips the two existing completed results and reruns only the
interrupted read-only integrity traversal, followed by the existing ledger export.
All fit reservations and earlier failures remain. The deadline stays 08:40:14 UTC.
