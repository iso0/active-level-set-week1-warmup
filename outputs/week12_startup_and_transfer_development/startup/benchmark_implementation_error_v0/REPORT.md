# Week 12 startup benchmark

Post-hoc developmental benchmark of four fixed, label-blind startup protocols over the original 100 NEW-136 training pools. Every query is paid. The benchmark does not establish external confirmation.

The four protocols are maximin, physics-stratified geometry, adaptive physics, and deterministic uniform random. Configuration was written and hashed before path execution. Discovery costs, budget CDFs, standardized 4D coverage, and rare-class capture are reported separately.

The adaptive rule uses observed labels only during its one-class phase. Once both classes are observed, its continuation is geometry-only. No rule or parameter was tuned against outcomes.
