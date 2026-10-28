# Finishing audit repair 02: an optimal-action tie

Registered before retry, 20 October 2026 at approximately 04:40 UTC.
The first exact reference failed at 04:35:34 UTC on the assertion that every
optimal first action has the single expected category. Its traceback remains in
results/failures/LOCAL_VALUE_REFERENCE_1792470934215952900.json. No acquisition
audit fit or completion-integrity scan followed that failure. The completed
main and quota trajectories and their numerical settings are unchanged.

The uncertain-coherent case has q=.5, w=.1, eta=.05, g=.06. One local query
reduces the local risk from .05 to .005; a global query removes .03 risk. With
two queries, local then global and global then local both yield .035, because
these two independent observations commute. Thus the one-step greedy preference
is local, while all four IDs tie as optimal first actions for horizon two.
The frozen minimum loss .035 was correct; the uniqueness assertion was wrong.
This is an analytical test-oracle error, not a new favorable experimental case.

The repair requires exact equality of the complete set of first-action categories
for all four unchanged examples. It expects both local and global only in the
uncertain-coherent case and separately checks its greedy first actions (0,1).
The other three expected losses and first-action categories remain unchanged.
The original six source files and manifest are retained byte-for-byte under
history/finishing_v1_1/. FROZEN_FINISHING_AUDITS_V1_2.json points to the repaired
check, its marked documentation erratum, and the observers' new manifest name.
No scientific model, selector, seed, target or success criterion changes.

One explicit retry of the failed zero-GP exact check is authorized by this record;
all failure and start events remain. The six previously registered acquisition
fits (72 components) and the zero-GP full-path audit have not been rerun.
No reservation is refunded. The absolute deadline remains 08:40:14 UTC today.
All 33 active source hashes matched before this repair. The old observer PID
7364 and postprocessor PID 11376 are absent; no numerical worker is registered.
The sole pool record still grants Astra two slots and Opus two on BURAK.
No v2 scientific endpoint was inspected to choose this repair.
