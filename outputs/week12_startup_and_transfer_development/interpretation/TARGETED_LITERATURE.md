# Targeted novelty check — 2026-10-03

Question: Is paid class-discovery/startup under imbalance itself new, and what
claim could this finite-pool SPH study still defend? This is a targeted check
of primary sources, not an exhaustive systematic review or proof of novelty.

1. **Barata et al. (ICAIF 2021), Active learning for imbalanced data under cold
   start.** The authors already study cold start with severe imbalance and a
   staged labeling strategy containing a warm-up phase. This rules out claiming
   discovery/warm-up as a new general concept. Their streaming classification
   setting and outlier/discriminative policies differ from a finite 4D SPH
   regime-boundary pool. [Primary paper](https://arxiv.org/abs/2107.07724).

2. **Chandra et al. (PMLR 148, 2021), On Initial Pools for Deep Active Learning.**
   This preregistration study investigates initial-pool design; its results did
   not establish a conclusive long-run advantage of intelligent initialization
   over random initialization. It supports examining downstream learning as
   well as startup statistics, and limits a novelty claim based on initialization
   alone. It concerns deep AL rather than physics-guided binary boundary search.
   [Primary paper](https://proceedings.mlr.press/v148/chandra21a.html).

3. **Zhao et al. (AISTATS 2021), Active Learning under Label Shift.** MALLS already
   studies AL with changed class proportions. Its label-shift formulation
   assumes unchanged class-conditional feature distributions. Our campaign
   also changes the input domain/support; that assumption is not established,
   so its guarantees cannot simply be imported. The paper is related precedent,
   not a method implemented or validated here.
   [Primary paper](https://proceedings.mlr.press/v130/zhao21b.html),
   [definition in paper](https://proceedings.mlr.press/v130/zhao21b/zhao21b.pdf).

4. **Letham et al. (AISTATS 2022), Look-Ahead Acquisition Functions for
   Bernoulli Level Set Estimation.** Direct precedent for binary GP level-set
   acquisition, including analytically derived look-ahead criteria. This
   limits novelty claims about binary boundary acquisition in general; those
   criteria were not newly benchmarked in this task.
   [Primary paper](https://proceedings.mlr.press/v151/letham22a.html).

5. **Chen et al. (MIDL 2024), Making Your First Choice.** Studies cold-start
   bias/outliers and proposes contrastive-feature initial querying in medical
   learning. Further evidence that principled initial-pool selection already
   has substantial prior art.
   [Primary paper](https://proceedings.mlr.press/v227/chen24a.html).

6. **Hattat et al. (June 2026 preprint), Dataset-Aware Cold-Start Active
   Learning for Annotation-Efficient 3D Medical Image Segmentation.** Describes
   curriculum-stratified initialization using label-free typicality and
   reconstruction uncertainty. This is recent related work, not peer-reviewed
   evidence for SPH or the current physics fallback.
   [Primary preprint](https://arxiv.org/abs/2606.20765).

An institutional page for Gotovos et al.'s level-set work returned 403 and was
not used as substantive evidence. Secondary/reddit search results were not
used. No source was quoted verbatim.

Assessment: the plausible contribution is an auditable, application-grounded
analysis that separates frozen operational failure, paid discovery, model
transfer and complete-protocol efficiency under a new campaign. The basic
startup principle is established prior art. Publication strength depends on
independent replication and a precise limited claim, not on declaring a new
acquisition function or universal physics-guidance advantage.
