# Independent TEST decision and evidence

144 new worlds,12 fixed families,12 realizations/family;288 dependent paths.
Both paths start at the same eight feature-only maximin points. Models receive
identical paid outputs on each path. They do not choose these comparison paths.
All288 completed, no failed path or undefined reference BA world. This is new
synthetic realization evidence, not new physical/Keyhole evidence. DEV32 worlds
were previously inspected and remain exploratory. No TEST family was removed.

## Prespecified decision: FAIL practical model screen

|Local72-world contrast, joint minus|Mean BA-AULC B8–24|Pointwise95%|One-sided98.333% lower|
|---|---:|---|---:|
|strong_extra|+.007365|[.004737,.010347]|.004526|
|fixed_extra|+.004022|[.001876,.006510]|.001738|
|joint_trace|+.007589|[.004814,.010686]|.004551|

Each mean had to be>=.005. fixed_extra fails. Its interval includes .005: this
screen failure does not establish that the true effect is below the practical
threshold. All three adjusted lower bounds
pass>0. Other frozen checks pass: local regional-error change−.005114 with upper
one-sided95%−.001674; control mean+.000875 with lower95%−.000623>−.01;
smooth/outliers/corruption means−.003546/+.000304/+.002382 exceed−.01;
outside-basis48-world means+.008110 versus strong_extra and+.005344 versus
fixed_extra are positive; all12 families have12 defined paired worlds.
The individual smooth interval includes harm below−.01; the protocol required
the individual family mean, not its lower interval, to exceed−.01. Do not silently
strengthen or weaken that criterion after results. Acquisitions remain unrun.

The inference averages two paths inside each world, resamples whole worlds
within fixed families (10,000 bootstrap draws, seed726280), then averages families
equally. Three primary lower bounds use Bonferroni; other intervals are pointwise
descriptions, not simultaneous coverage. Small12-world family samples and a fixed
generator collection limit inference beyond these worlds. We make no sign-flip
randomization claim. Bootstrap intervals do not establish posterior calibration.

## What survived generalization, and what did not

The joint-vs-extra-strong gain was positive in57/72 worlds, negative11 and tied4;
median+.001989, maximum+.080841. Removing the largest gain **post hoc for a
sensitivity description only** gives+.006330. Against fixed_extra:48 positive,
20 negative,4 tied, median+.000346; removing largest gives+.003117. The primary
analysis retains every world. DEV's much larger+.013287 incremental local gain
did not reproduce at that size; no test seed was chosen from DEV winners.

|All144-world aggregate|BA-AULC|Positive recall|Negative recall|Brier|Log loss|
|---|---:|---:|---:|---:|---:|
|strong_extra|.761248|.763245|.759251|.104492|.699320|
|fixed_extra|.763455|.765432|.761478|.102009|.499234|
|joint|.765368|.767042|.763694|.101084|.552253|

Both recalls improve in this aggregate, not in every family. Against fixed_extra,
Brier improves−.000926 (pointwise95%[−.001728,−.000132]) while log loss worsens
+.053020 ([.032184,.077567]). Lower Brier and higher log loss are possible because
the scores penalize confident mistakes differently. Neither is calibration alone.

All-family details, including every arm/recall/proper score, are in
results/analysis_test_v1/ALL_FAMILIES.csv and PER_WORLD_PATH_MODEL.csv. The most
consequential harms are retained: annular-shell regional error .764524→.769103
against fixed_extra despite BA .536912→.539784; plateau regional error
.678530→.680411; radial-island regional error .536490→.540326. Twin-island
regional error improves .536561→.521952, but BA remains .570912 and confirmed
BA.90 is0/24. Shell and plateau also0/24; radial island1/24. Smooth BA falls
.928280→.924307, with both recalls falling. Correlated-corruption aggregate BA
gain does not identify the unbiased physical response; regional error remains
worse than strong_extra. Controls' arbitrary geometric masks are diagnostic
subsets, not actual planted physical anomalies.

## Queries, computation and uncertainty

See results/completion/SAME_TARGET_COST.md and TARGET_ATTAINMENT.csv. Joint
attainment109/65/25 versus strong_extra107/64/24 for .90/.93/.95 is a small change.
All three restricted-burden contrasts against strong_extra have intervals
including zero. Against fixed_extra the .93 contrast is−.072917 queries with
pointwise95%[−.156250,−.006944]; .90 is slightly worse and .95 exactly unchanged
in this endpoint. Do not erase the small descriptive .93 effect, or promote it
to a general sample-saving result. A value25 is the frozen nonattainment penalty;
it is not an observed time of success. Confirmation's second budget is charged.

Joint fit+prediction averages3.0207 CPU seconds/path against original
fixed_local1.0465 and strong1.0127. Extra-optimized controls were given joint's
paid-data optimum as an additional start. Their displayed3.0035/3.0380 seconds
exclude generating it; dependency-accounted costs4.9714/5.0059 seconds include
that1.9679-second assistance. This favors the controls for attribution but cannot
be called a cheap independent pipeline. Path generation CPU364.953 is shared.
Combined TEST replay CPU2373.719; peak171.81MiB. No simulation-time conversion.

## Verification and scope

Independent metric replay maximum error1.776e-14. TEST retains126 non-successful
optimizer starts; none of the selected solutions reports failure. DEV retains18
failed starts. No chosen-solution success flag proves a global optimum. Every
extra-null CPU target was covered. Raw optimization logs and reservations remain.

The post-TEST finishing protocol checks all288 paths/4,608 prequery hashes/2,592
prediction files,192 independent dense prequery reconstructions (all argmaxes
match;50 near ties),12 dense65-component prefixes, and one ask/tell toy fit.
Maximum moment error1.279e-13; dense mixture discrepancy2.713e-11. This validates
conditional calculations, not an exact hyperparameter posterior or calibration.
Original gradient, tau→0 and sequential-update checks are preserved separately.

No new acquisition experiment, optional method continuation, real-data fit or
physical simulation was run. Preserve the small positive model effect without
promoting the practical-screen failure. A richer local family and insufficient
local evidence remain competing explanations; current comparisons do not
separate them causally. The proposed next diagnostic is in ANALYTICAL_LIMITS.md.
