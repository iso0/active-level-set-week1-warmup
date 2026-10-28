# Active level-set estimation for LPBF melt-pool regimes

This is the canonical research repository for the MSc thesis. It contains the historical Week 1-10 work, later depth/label and in-pool studies, and the four independent Astra synthetic campaigns. The current scope extends beyond the early weekly record.

Start with **[Thesis Research Hub](RESEARCH_INDEX.md)** and **[scientific scopes and reading order](docs/research/SCIENTIFIC_NAVIGATION.md)**. These distinguish source-reported findings, editorial synthesis, negative results and incomplete studies.

## Find a result and its evidence

- [Claim ledger](docs/research/CLAIM_LEDGER.csv): 16 scoped claim records with source references and limitations.
- [Experiment registry](docs/research/EXPERIMENT_REGISTRY.csv): 15 experiment/control contexts, protocols, reports and dependence assumptions.
- [Reported findings](docs/research/REPORTED_FINDINGS.csv): existing reported values; no new endpoint calculations.
- [Evidence/archive index](docs/research/ARCHIVE_MANIFEST.md) and [structured manifest](docs/research/ARCHIVE_MANIFEST.csv): included evidence, existing thesis evidence and explicit unavailable/restricted records.
- [Public provenance](docs/research/PROVENANCE_PUBLIC.json), [source allowlist](PUBLICATION_ALLOWLIST.json) and [SHA-256 manifest](docs/research/PUBLICATION_SHA256.csv): original campaign commits, file identities and publication scope.
- [Selection reconciliation](docs/research/SELECTION_SCOPE.md): the historical 511-versus-393 reading-layer selections and retained evidence boundaries.

## Current scientific results and limitations

These are different tasks and evidence scopes, not successive universal winners.

| Context | Source-reported conclusion and limits | Authoritative entry point |
|---|---|---|
| Historical Track A / M3 | M3 probability margin with feature-only B16 initialization remains the frozen historical control for its manual-label comparisons. Candidate B did not meet the internal replacement threshold; this does not establish external validation. Preserve the q20 accuracy-AULC definition. | [Track A final state](docs/trackA_freeze/TRACK_A_FINAL_STATE.md), [method](docs/trackA_freeze/FROZEN_METHOD_SPEC.md), [validation protocol](docs/trackA_freeze/EXTERNAL_VALIDATION_PROTOCOL.md) |
| Week 17-18 binary labels / G3 | Week 17 reports NO CHANGE JUSTIFIED. G3 + margin is retained for the stated binary-only tasks; this is not a universal replacement claim across data types. | [Week 17 report](outputs/week17_model_and_acquisition/WEEK17_REPORT.md), [Week 18 report and corrections](outputs/week18_independent_research/REPORT.md) |
| Week 18 OLD depth-threshold task | Depth GP + straddle improvement is limited to OLD-type tasks where revealed depth determines the label. It is not extended to NEW/POOLED binary-label tasks. | [Week 18 report](outputs/week18_independent_research/REPORT.md), [scope guide](docs/research/SCIENTIFIC_NAVIGATION.md) |
| Later C1C in-pool study | C1 + margin is recommended for specified early and stop-at-0.95 uses within the existing 541-run pool. HA_LEAN + margin remains the frozen reference and safer extrapolation/sustaining-target reference. Sustainment and alternative-start reliability limits remain; this is not external physical validation. | [C1C decision](outputs/research_campaign_20261026/opus_c1_confirmation/DECISION_C1C.md), [external validation plan](outputs/research_campaign_20261026/opus_c1_confirmation/EXTERNAL_VALIDATION_PLAN_C1C.md) |
| Independent Astra synthetic studies | Representation/model gains are separated from acquisition, query savings, regional harm and computation. Negative screens and incomplete paths remain evidence. Synthetic latent-monitor results do not validate physical Keyhole labels or the 541-run application. | [Four campaign guides](#independent-astra-campaigns), [claim ledger](docs/research/CLAIM_LEDGER.csv) |

The Week 18 block named C1 and the later C1C learner are distinct identifiers. HA_LEAN is not assumed to be an alias of G3. An external-validation plan is not an executed experiment. Historical frozen reports and corrections retain their original interpretations.

## Independent Astra campaigns

| Campaign | What to read and retain |
|---|---|
| [AD18 - Deep Discovery](research/astra/astra_deep_discovery_20261018/README_PUBLIC.md) | [Final report](research/astra/astra_deep_discovery_20261018/FINAL_REPORT.md): scoped representation benefit, unresolved regional discovery, small-island failures and no established general query savings. |
| [RP20 - Representation Planning](research/astra/astra_representation_planning_20261020/README_PUBLIC.md) | [Final report](research/astra/astra_representation_planning_20261020/FINAL_REPORT.md): no general benefit from the proposed local bank/two-step rule; stronger same-paid-data model controls and three incomplete paths remain explicit. |
| [LC24 - Local Correction](research/astra/astra_local_correction_20261024/README_PUBLIC.md) | [Final report](research/astra/astra_local_correction_20261024/FINAL_REPORT.md): both DEV expansion screens failed; the worlds were reused for V2 and no independent TEST was run. |
| [JL26 - Joint Local](research/astra/astra_joint_local_20261026/README_PUBLIC.md) | [Final report](research/astra/astra_joint_local_20261026/FINAL_REPORT.md): an independent synthetic model increment was observed, but the fixed_extra practical screen was missed and no acquisition expansion followed. |

Original independent Astra Git histories remain separate provenance records; this repository does not claim to host those histories as native commits. Their included source files retain original commit/blob identities and hashes.

## Data availability, offline evidence and rights

The complete Astra execution archive remains in local/external preservation. It will not be mirrored wholesale to GitHub Releases, Git LFS or cloud storage. Only a small, scientifically useful selection may be proposed for later publication, following separate integrity and redistribution-rights review. No new curated evidence is added by this navigation update.

Existing PENDING_ARCHIVE entries mean unavailable or unresolved evidence; they are not download links, promises of future upload, or redistribution permission. Restricted originals and raw execution records remain excluded from the Hub import. TUM-owned inputs, simulator internals, external datasets and third-party material require their own established rights. Protected evaluation targets are excluded.

Read [data availability](DATA_AVAILABILITY.md), [rights and attribution](RIGHTS_AND_ATTRIBUTION.md), [publication status](PUBLICATION_STATUS.md) and the [file-level licensing scope](docs/research/LICENSING_SCOPE.md). MIT applies to the explicitly listed original Hub software; CC BY 4.0 applies to the explicitly listed original research/editorial documentation. These grants do not relicense the complete thesis or third-party material; there is no repository-root license.

## Earlier project navigation and implementations

- [Complete week/phase index](docs/PROJECT_INDEX.md), [five-minute historical project map](docs/THESIS_PROJECT_MAP.md) and [authoritative results index](docs/AUTHORITATIVE_RESULTS_INDEX.md).
- [Track B preparation](docs/trackB/TRACK_B_PROBLEM_DEFINITION.md), [repository forensic audit](docs/consolidation/REPOSITORY_FORENSIC_AUDIT.md) and [known legacy issues](outputs/project_consolidation/KNOWN_LEGACY_ISSUES.md).
- [Historical M3 + G3 margin study](docs/phases/week9_phase1_20_m3_g3_margin_acquisition.md) and [acquisition-search/CCM study](docs/phases/week9_phase1_20_acquisition_search.md) are both named Phase 1.20; their endpoints are separate.
- [Prior root README at Research Hub v1](https://github.com/iso0/active-level-set-week1-warmup/blob/86e400887a069ab054da55a76e34082835052e25/README.md) preserves the earlier Week 1-10 framing.

| Path | Role |
|---|---|
| src/ | Current models, acquisitions, experiment drivers and related tests; historical implementations are explicitly under src/_history/ or other archived paths. |
| research/astra/ | Reviewed campaign reading layers, original software, protocols and reports. |
| outputs/ | Preserved thesis reports, scientific outputs, protocols and manifests. |
| docs/research/ | Scientific navigation, claim/experiment registries, provenance, availability and scoped licenses. |
| notebooks/ | Preserved notebooks and variants, which may require their original environments. |
| data/ | Existing repository inputs; presence does not extend redistribution rights to other datasets. |

The existing Graphify graph is an earlier code-connectivity aid, not a complete index of the Hub documents, numerical evidence or later curation. Use the registries and source reports for scientific claims; a graph edge does not establish a scientific conclusion. No graph rebuild or new research execution accompanies this navigation update.
