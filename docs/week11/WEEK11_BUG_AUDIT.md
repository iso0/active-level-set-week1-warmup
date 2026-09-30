# Week 11 Bug eligibility blocker

Historical source expects the mixed frame-level schema `name, hash, P, VX, LS, ST, bug_free, correctly_finished, timestep, label_1, label_2, label_final`. Historical per-simulation `frames.csv` has frame index, timestep, a physical label, and image filenames. This establishes how old frame rows and timesteps were mapped; the actual new annotation schema is uninspected and must not be inferred from the historical schema.

Historical project evidence warns that `bug_free` is inconsistent with the categorical `Screenshot Bug` annotation. Prior source rules and warnings do not define a valid new-cohort Bug exclusion rule. No independent Bug/status file exists in the approved new tree metadata.

The new affected-run count, later-only affected count, first affected frame/timestep, reasons, wall-contact distinction, and final eligible count are all **UNRESOLVED**. No technical exclusion was invented. An apparently clean prefix is not automatically a valid whole run.

The minimal custodian question and allowed export fields are recorded in `WEEK11_DECISION_GATE.md`. The export must remain separate from physical-class annotations and signal values.
