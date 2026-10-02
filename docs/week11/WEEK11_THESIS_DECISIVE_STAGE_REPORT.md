# A. Repository consolidation

`main` is now the sole local and remote development branch. The four Week 11 commits were incorporated by fast-forward without rewriting their SHAs. All former branch tips remain reachable; 52 redundant local and two remote branches were removed after publication and preservation checks. Sixteen unique historical stash artifacts and a safety note were archived; five historical worktrees were detached at their original commits without deleting files, and both stashes remain. User-owned `.codex/` is untouched. [Complete checkpoint](WEEK11_REPOSITORY_CONSOLIDATION.md).

The original freeze commit `e0adbc28b6368ee6366c6dcd7d500632c7b5f8f1` and freeze SHA-256 `856219763ec41ba22eb13ebb5c23e2137fb3d6eb884de71a44f96d80debe1eee` are unchanged. The repository was published and verified at `ed491faa08782bcb9db42ac4bbc031bd2e32457f` before any execution. The confirmatory attempt was subsequently closed at commit `f83b0c17a24339ed8c09d507473de0f4e5394a5a` before exploratory work began. The final publication record and response identify the final main commit containing this report.

# B. Frozen external validation

**INCOMPLETE — FROZEN STOP.** Of 185 new simulations, 136 were included and 49 remain Bug-withheld. Included balance is 124 Keyhole/12 non-Keyhole. The locked execution passed the freeze, source, environment, manifest, fold and oracle-identity gates. It stopped at repeat 3/fold 4 because its feature-only B16 contained only one class. This is the specified stop rule, not an implementation bug to repair.

Thirteen paired folds / 39 arm paths reached B80; 87 folds / 261 paths remain incomplete. All 69,030 predictions, 2,638 fit diagnostics, 103 prescribed empty-band margin fallbacks and the fatal event are retained. Exact IDs, splits, every completed frozen initialization, training-only queries and held-out prediction coverage passed independent structural QC. The stronger unqueried-label access claim additionally relies on the accepted frozen-source information-barrier audit. [Full confirmatory report](../../outputs/week11_external_execution_record/CONFIRMATORY_STOP_REPORT.md); [QC](../../outputs/week11_external_execution_record/QC_VALIDATION.json).

Candidate B primary mean ΔAULC, interval, positive-repeat count, B40 recall guardrail and B80 accuracy guardrail are **not estimable/evaluated**. External confirmation, incumbent replacement and pure acquisition attribution are **not established**. No partial subset, secondary endpoint, crossing statistic or method ranking was computed. OLD-405's +0.006708 Candidate-B effect remains an internal result; there is no complete external estimate to compare or pool with it. [Null-estimate claim ledger](../../outputs/week11_external_execution_record/CONFIRMATORY_STOP_LEDGER.json).

The cohort is the 136 Bug-cleared cases, whose VX distribution differs from the withheld 49. The 20 repeated partitions are not 20 independent external campaigns. All arms use M3; the design does not establish a new model-versus-model advantage.

# C. What the result means

The experiment did not establish which acquisition policy is better on the new campaign. It exposed a distinction between having enough simulations for B80 and observing both classes in the first 16 queries. The prior M3 incumbent remains in place because no replacement evidence was obtained, not because it won a completed external comparison. Neither a positive nor a negative performance story can be inferred from the completed subset.

# D. Post-hoc research observations

**POST-HOC EXPLORATORY — NOT PRE-REGISTERED CONFIRMATORY EVIDENCE**

All 100 fixed training pools contain both classes, but 3 of the originally frozen B16 starts contain only Keyhole; 97 contain both. No seed was changed. The same-start contract makes this a shared startup limitation across the three arms, although execution reached the incumbent first. The exact uniform 16 analytic reference gives 20.805 expected one-class starts across these pools; this is descriptive, with no independence claim or significance test. It does not justify abandoning maximin or favoring another acquisition policy.

The included class medians follow the expected `log h` direction, but their scalar ranges overlap. A perfect increasing scalar threshold cannot reproduce these labels; the relevance of the M3 discrepancy component remains a hypothesis without a new model contrast. [Evidence, interpretation, alternatives and confidence](../../outputs/week11_posthoc_initialization/RESEARCH_INTERPRETATION_AND_NOVELTY.md); [100-start audit](../../outputs/week11_posthoc_initialization/FROZEN_B16_SPLIT_AUDIT.csv).

# E. Novelty / publication opportunities

**POST-HOC EXPLORATORY — NOT PRE-REGISTERED CONFIRMATORY EVIDENCE**

The targeted primary literature already recognizes geometric coverage and one-class warm-up problems; no novelty claim is made. The strongest opportunity is a systematic study of entire-protocol feasibility under external shift, including fully charged class discovery. This is a useful thesis result now; a workshop paper would need stronger mechanistic replication. A physics-trend/discrepancy transfer study is a secondary hypothesis requiring matched comparisons. Neither opportunity currently supports a stronger publication claim. Required evidence and the smallest next studies are detailed in the [research assessment](../../outputs/week11_posthoc_initialization/RESEARCH_INTERPRETATION_AND_NOVELTY.md).

# F. Recommended next step

Keep this confirmatory attempt closed. Agree and preregister a future one-class startup/discovery rule with explicit query costs before the next independent campaign. These 136 outcomes are now open and can support clearly marked development only. Do not rescue this experiment with alternative seeds or reinterpret incomplete folds as confirmation.
