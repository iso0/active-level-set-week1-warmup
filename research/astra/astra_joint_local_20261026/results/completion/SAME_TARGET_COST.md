# Same-target query burden and measured CPU

All startup, discovery and second confirmation queries are charged. Targets require two consecutive evaluations of one learner at B8,10,...24. Nonattainers are censored at24; burden25 is a prespecified penalized score, not an observed success time. Paths are dependent within144 worlds. No new acquisition was run.

|Model|BA .90 reached /288|.93|.95|Burden .90 / .93 / .95|Fit+predict CPU/path (s)|Full dependency CPU/path (s)|
|---|---:|---:|---:|---|---:|---:|
|strong|107|64|24|20.8924 / 23.0764 / 24.4167|1.0127|1.0127|
|fixed_local|108|64|25|20.8819 / 23.1181 / 24.4132|1.0465|1.0465|
|strong_extra|107|64|24|20.8924 / 23.0764 / 24.4167|3.0035|4.9714|
|fixed_extra|108|64|25|20.8819 / 23.1181 / 24.4132|3.0380|5.0059|
|joint|109|65|25|20.8993 / 23.0451 / 24.4132|3.0207|3.0207|
|joint_trace|107|64|24|20.8646 / 23.0764 / 24.4167|3.1520|3.1520|

The extra-null controls receive the joint optimum as a paid-data-only start. Reported arm CPU excludes producing that borrowed start; the last column adds it. They are stronger diagnostic controls, not equally cheap deployable pipelines. Joint costs include its null fit and joint optimization. Path generation is shared and accounted separately, not charged selectively to an arm.

|Joint minus control|Target|Mean restricted-burden difference|Pointwise paired-world 95% interval|
|---|---|---:|---|
|strong_extra|0.90|+0.00694|[-0.03819, +0.05208]|
|strong_extra|0.93|-0.03125|[-0.11458, +0.03819]|
|strong_extra|0.95|-0.00347|[-0.03125, +0.02083]|
|fixed_extra|0.90|+0.01736|[-0.01736, +0.05556]|
|fixed_extra|0.93|-0.07292|[-0.15625, -0.00694]|
|fixed_extra|0.95|+0.00000|[+0.00000, +0.00000]|

Actual TEST execution: 2373.719s combined replay CPU plus 364.953s path-construction CPU; peak 171.81MiB. Summed replay wall 3877.977s is not campaign elapsed time because jobs ran in parallel. DEV replay CPU 480.297s. No physical simulator time was measured.

There is a small descriptive .93 burden improvement versus fixed_extra (-.073 queries), but not a consistent improvement across all targets or versus extra-strong. This does not establish acquisition efficiency or meaningful simulator savings. Attainer-only averages in CSV are selected-subset descriptions and must not replace censored comparisons.
