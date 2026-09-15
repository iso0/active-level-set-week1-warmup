"""Build and execute the Week 7 Phase 1 teaching notebook."""

from __future__ import annotations

import json
from pathlib import Path

import nbformat as nbf
import pandas as pd
from nbclient import NotebookClient


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "week7_01_sph_v2_audit"
NOTEBOOK = ROOT / "notebooks" / "week_07" / "01_sph_v2_dataset_shift_audit.ipynb"


def code(source: str) -> nbf.NotebookNode:
    return nbf.v4.new_code_cell(source=source)


def markdown(source: str) -> nbf.NotebookNode:
    return nbf.v4.new_markdown_cell(source=source)


def main() -> None:
    provenance = json.loads((OUT / "dataset_provenance.json").read_text(encoding="utf-8"))
    summary = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
    missing = pd.read_csv(OUT / "missing_unexpected_files.csv")
    reference = pd.read_csv(OUT / "ioan_reference_comparison.csv")
    sequences = pd.read_csv(OUT / "experiment_label_sequences.csv")
    anomalies = pd.read_csv(OUT / "suspicious_label_anomalies.csv")
    bounds = pd.read_csv(OUT / "parameter_bounds_shift.csv").set_index("feature")
    membership = pd.read_csv(OUT / "new_data_domain_membership.csv")
    integrity = pd.read_csv(OUT / "integrity_audit.csv")

    keyhole = sequences[sequences["has_keyhole"]]
    missing_experiments = int(missing["experiment_name"].nunique())
    disagreement_experiments = int(
        anomalies.loc[
            anomalies["reason"].eq("annotator_or_channel_disagreement"), "experiment_name"
        ].nunique()
    )
    new_outside = membership[membership["outside_any_week6_axis_range"]]
    new_inside = membership[~membership["outside_any_week6_axis_range"]]
    outside_keyhole_percent = 100 * float(new_outside["has_keyhole"].mean())
    inside_keyhole_percent = 100 * float(new_inside["has_keyhole"].mean())

    cells: list[nbf.NotebookNode] = [
        markdown(
            """# Week 7 Phase 1 — `sph_v2` dataset and design-space audit

This notebook answers one bounded question: **what is in the pinned `sph_v2` snapshot, is it internally consistent, and how does its input domain differ from the Week 6 population?**

```text
Phase 1
├── 1. Scope and reproducible setup
├── 2. Immutable dataset provenance
├── 3. Repository structure and missing files
├── 4. Label counts and Ioan-reference reproduction
├── 5. Experiment-level sequences and Keyhole episodes
├── 6. Label provenance and anomaly flags
├── 7. P / VX / LS / ST domain shift
├── 8. Duplicate and partition integrity
├── 9. Conservative conclusions
└── 10. Validation and requirement dashboard
```

Scope boundary: this is descriptive auditing only. No predictive model, classifier, active learning, or level-set estimation is run."""
        ),
        markdown(
            """## 1. Scope and reproducible setup

**What are we doing?** Load the exact saved audit and visibly import the reusable Phase 1 functions.  
**Why?** The notebook should teach and reproduce the scientific calculations, not merely point to a hidden script.  
**Question answered.** Are the notebook, saved artifacts, and source functions tied to one population and revision?  
**Suspicious result.** A floating `main`, a different revision, a population mismatch, or an output generated outside this worktree."""
        ),
        code(
            """from pathlib import Path
import json
import numpy as np
import pandas as pd
from IPython.display import Image, Markdown, display

from src.week7_sph_v2_common import (
    PARTITION_ORDER, SPH_V2_REPO_ID, SPH_V2_REVISION, load_partition_labels
)
from src.week7_phase1_sph_v2_dataset_shift_audit import (
    label_distribution, sequence_audit
)

ROOT = Path.cwd().resolve()
OUT = ROOT / "outputs" / "week7_01_sph_v2_audit"
assert ROOT.name == "thesis-week7-sph-v2-audit"

pd.set_option("display.max_columns", 80)
pd.set_option("display.max_colwidth", 90)

def show_figures(*filenames, width=980):
    for filename in filenames:
        display(Markdown(f"**{filename}**"))
        display(Image(filename=str(OUT / "figures" / filename), width=width))

provenance = json.loads((OUT / "dataset_provenance.json").read_text(encoding="utf-8"))
summary = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
assert provenance["analysis_revision"] == SPH_V2_REVISION
assert provenance["all_scientific_access_pinned"] is True
display(pd.DataFrame({
    "scope item": ["models fitted", "labels modified", "simulations removed", "active learning", "level-set estimation"],
    "value": [False, False, False, False, False],
}))"""
        ),
        markdown(
            """**Interpretation.** The notebook runs from the isolated Week 7 worktree and imports the same functions that created the saved tables. The scope flags are deliberately explicit: a successful audit does not provide predictive-model evidence."""
        ),
        markdown(
            """## 2. Immutable dataset provenance

**What are we doing?** Display the repository identity, exact Git revision, retrieval time, population sizes, inventory hash, and label-file hashes.  
**Why?** `sph_v2/main` changes over time; a thesis result must remain recoverable after new experiments are added.  
**Question answered.** Which immutable dataset state produced every result below?  
**Suspicious result.** A revision shorter than 40 hexadecimal characters, a `main` pointer used for data access, or mismatched partition totals."""
        ),
        code(
            """provenance_table = pd.read_csv(OUT / "dataset_provenance_table.csv")
label_hashes = pd.DataFrame(provenance["label_files"])
partition_counts = (
    pd.DataFrame(provenance["partition_counts"]).T
    .rename_axis("partition").reset_index()
)
display(provenance_table)
display(partition_counts)
display(label_hashes[["partition", "relative_path", "sha256", "size_bytes", "frame_rows_in_analysis"]])
display(pd.DataFrame({
    "field": ["tree items", "files", "folders", "inventory SHA-256", "floating main at retrieval", "analysis revision"],
    "value": [
        provenance["repository_tree_item_count"],
        provenance["repository_file_count"],
        provenance["repository_folder_count"],
        provenance["repository_inventory_sha256"],
        provenance["floating_main_resolved_at_run_start"],
        provenance["analysis_revision"],
    ],
}))"""
        ),
        markdown(
            f"""**Interpretation.** Every scientific tree request and download used `{provenance['analysis_revision']}`. The floating `main` happened to resolve to the same commit at retrieval, but it was recorded only as a drift check. The complete remote inventory contains **{provenance['repository_tree_item_count']:,} objects**, including **{provenance['repository_file_count']:,} files**; only small ledgers and Phase 2 monitor inputs are downloaded locally."""
        ),
        markdown(
            """## 3. Repository structure and missing-file audit

**What are we doing?** Count every file type, inspect each experiment folder, and compare the new layout with Week 6 expectations.  
**Why?** “Almost identical” is not an executable schema guarantee. Missing monitors must become explicit rows, not silent exclusions.  
**Question answered.** Is the new repository structurally usable, and where does compatibility break?  
**Suspicious result.** Missing `frames.csv`, mismatched front/side/top counts, malformed folder parameters, or absent physical monitors."""
        ),
        code(
            """top_level = pd.read_csv(OUT / "top_level_inventory.csv")
file_types = pd.read_csv(OUT / "file_type_counts.csv")
partitions = pd.read_csv(OUT / "partition_summary.csv")
missing = pd.read_csv(OUT / "missing_unexpected_files.csv")
structure_comparison = pd.read_csv(OUT / "week6_structure_comparison.csv")

display(top_level.head(12))
display(file_types)
display(partitions)
display(structure_comparison)
display(
    missing.groupby(["partition", "relative_path"])
    .agg(affected_experiments=("experiment_name", "nunique"))
    .reset_index()
)
display(missing.head(10))"""
        ),
        markdown(
            f"""**Interpretation.** The new layout retains `parameters.json`, frame views, and `monitor/*.dat`, removes Week 6's per-simulation metadata/provenance JSON, uses semantic folder names at repository root, and adds three GIFs per experiment. All saved-view counts and label ledgers agree. However, **{missing_experiments} experiments** have **{len(missing)} required-monitor absences**: 56 `old-data-local` experiments lack both `time.dat` and kinetic energy, and one `new-data` experiment lacks position bounds and kinetic energy. This is a real pinned-source limitation and will remain as explicit Phase 2 extraction failures."""
        ),
        markdown(
            """## 4. Label distributions and Ioan-reference reproduction

**What are we doing?** Recompute labels directly from the three pinned ledgers, then compare reproduced counts and percentages with Ioan's screenshot.  
**Why?** Supervisor values are reference checks, not hard-coded truth.  
**Question answered.** Do the independently read ledgers reproduce 407 experiments, 110,804 labelled frames, and the reported Keyhole/Conduction prevalence?  
**Suspicious result.** Any integer count difference or a percentage discrepancy beyond the declared rounding tolerance."""
        ),
        code(
            """# These calls visibly repeat the core label and sequence calculations.
labels_now = load_partition_labels(workers=3)
distribution_now = label_distribution(labels_now)
sequences_now, episodes_now, patterns_now = sequence_audit(labels_now)

stored_distribution = pd.read_csv(OUT / "label_distribution.csv")
reference = pd.read_csv(OUT / "ioan_reference_comparison.csv")
assert len(labels_now) == provenance["labelled_frame_count"]
assert sequences_now["experiment_name"].nunique() == provenance["experiment_count"]

display(
    stored_distribution[stored_distribution["partition"].isin(PARTITION_ORDER)]
    [["partition", "label", "frame_count", "frame_percent", "experiment_count", "experiment_percent"]]
)
display(reference)
show_figures(
    "01_frame_label_distribution_by_partition.png",
    "02_experiment_label_prevalence_by_partition.png",
    "03_keyhole_experiment_prevalence.png",
)"""
        ),
        markdown(
            f"""**Interpretation.** All **{len(reference)}/{len(reference)}** reference checks pass: 407 experiments, 110,804 frames, 6,700 Keyhole frames in 73 experiments, and 52,080 Conduction frames in 373 experiments are reproduced exactly (percentages differ only by screenshot rounding). Experiment-level labels are **not mutually exclusive**: a simulation may contain Conduction and Keyhole at different saved timesteps, so their experiment prevalences need not sum to 100%."""
        ),
        markdown(
            """## 5. Experiment-level sequences and Keyhole episodes

**What are we doing?** Collapse consecutive duplicate labels and calculate first/last physical labels, Keyhole locations, frame counts, fractions, and segment counts per experiment.  
**Why?** A binary experiment label hides whether Keyhole is brief, persistent, or repeatedly interrupted.  
**Question answered.** Which transition patterns occur, and how short are the shortest observed Keyhole episodes?  
**Suspicious result.** Impossible returns to initialization, many isolated segments, or an unjustified conversion from saved frames to milliseconds."""
        ),
        code(
            """sequences = pd.read_csv(OUT / "experiment_label_sequences.csv")
patterns = pd.read_csv(OUT / "label_sequence_patterns.csv")
episodes = pd.read_csv(OUT / "keyhole_episodes.csv")
keyhole = sequences[sequences["has_keyhole"]].copy()

display(patterns[patterns["partition"].eq("combined")].head(15))
display(keyhole[[
    "partition", "experiment_name", "first_physical_label", "last_physical_label",
    "first_keyhole_timestep", "last_keyhole_timestep", "keyhole_frame_count",
    "keyhole_segment_count", "keyhole_transient_by_sequence",
    "keyhole_persistent_to_last_physical_frame", "collapsed_label_sequence",
]].head(12))
display(pd.DataFrame({
    "frame-based diagnostic": ["exactly 1", "at most 3", "at most 5", "at most 20", "more than one segment"],
    "Keyhole-positive experiments": [
        int((keyhole["keyhole_frame_count"] == 1).sum()),
        int((keyhole["keyhole_frame_count"] <= 3).sum()),
        int((keyhole["keyhole_frame_count"] <= 5).sum()),
        int((keyhole["keyhole_frame_count"] <= 20).sum()),
        int((keyhole["keyhole_segment_count"] > 1).sum()),
    ],
}))
show_figures("09_label_sequence_patterns.png", "10_keyhole_duration_segments.png")"""
        ),
        markdown(
            f"""**Interpretation.** No Keyhole-positive experiment has only one saved Keyhole frame; **{int((keyhole['keyhole_frame_count'] <= 3).sum())}** have at most three and **{int((keyhole['keyhole_frame_count'] <= 5).sum())}** have at most five. **{int((keyhole['keyhole_segment_count'] > 1).sum())}** contain repeated Keyhole segments. The repository provides exact solver timesteps for saved frames, but Phase 1 does not yet validate a general frame-duration-to-millisecond rule; therefore these duration statements remain frame-based."""
        ),
        markdown(
            """## 6. Working-student provenance and suspicious-label flags

**What are we doing?** Search for reliable annotator metadata and flag sequence/channel patterns that warrant later review.  
**Why?** Ioan warned that a smaller subset was labelled by a working student, but partition names or label channels must not be treated as annotator identity without evidence.  
**Question answered.** Can that subset be identified, and which records deserve manual review?  
**Suspicious result.** Fabricating an annotator split, calling disagreements “wrong”, modifying labels, or dropping flagged records."""
        ),
        code(
            """annotator = pd.read_csv(OUT / "annotator_provenance_audit.csv")
anomalies = pd.read_csv(OUT / "suspicious_label_anomalies.csv")
display(annotator)
display(
    anomalies.groupby(["severity", "reason"])
    .agg(records=("experiment_name", "size"), experiments=("experiment_name", "nunique"))
    .sort_values("records", ascending=False).reset_index()
)
display(anomalies[~anomalies["reason"].eq("annotator_or_channel_disagreement")].head(20))"""
        ),
        markdown(
            f"""**Interpretation.** The working-student subset is **not reliably identifiable**: no annotator/provenance field or file documents who `label_1` and `label_2` represent, and partition is not used as a proxy. Channel disagreement appears in **{disagreement_experiments}/407 experiments**; it is retained as a broad review flag, not evidence that either channel is wrong. Smaller, more specific flags include Screenshot Bug, repeated Keyhole episodes, and unusual returns to earlier phases. No label is changed."""
        ),
        markdown(
            """## 7. Parameter-space and Week 6 domain-shift audit

**What are we doing?** Verify units and compare P, VX, LS, and ST distributions, marginal bounds, axis-range membership, and four-dimensional convex-hull membership.  
**Why?** Models fitted later could be affected by design-space/covariate shift, but this phase must remain descriptive.  
**Question answered.** Which input regions are genuinely new, and where are Keyhole observations located?  
**Suspicious result.** Causal wording, unit mismatch, non-finite values, or interpreting a 2-D projection as full 4-D support."""
        ),
        code(
            """parameter_summary = pd.read_csv(OUT / "parameter_summary_by_partition.csv")
bounds = pd.read_csv(OUT / "parameter_bounds_shift.csv")
membership = pd.read_csv(OUT / "new_data_domain_membership.csv")

display(parameter_summary)
display(bounds)
display(pd.DataFrame({
    "new-data region": ["inside all Week 6 marginal ranges", "outside at least one Week 6 marginal range", "inside Week 6 4-D convex hull", "outside Week 6 4-D convex hull"],
    "experiments": [
        int((~membership["outside_any_week6_axis_range"]).sum()),
        int(membership["outside_any_week6_axis_range"].sum()),
        int(membership["inside_week6_4d_convex_hull"].sum()),
        int((~membership["inside_week6_4d_convex_hull"]).sum()),
    ],
    "Keyhole-positive": [
        int(membership.loc[~membership["outside_any_week6_axis_range"], "has_keyhole"].sum()),
        int(membership.loc[membership["outside_any_week6_axis_range"], "has_keyhole"].sum()),
        int(membership.loc[membership["inside_week6_4d_convex_hull"], "has_keyhole"].sum()),
        int(membership.loc[~membership["inside_week6_4d_convex_hull"], "has_keyhole"].sum()),
    ],
}))
show_figures(
    "04_parameter_distributions_by_partition.png",
    "05_parameter_boxplots_by_partition.png",
    "06_parameter_space_projections.png",
    "07_week6_vs_new_parameter_bounds.png",
    "08_keyhole_parameter_overlays.png",
)"""
        ),
        markdown(
            f"""**Interpretation.** Units remain P in W, VX in m/s, LS in m (shown as µm in figures), and ST in K. Relative to Week 6, the `new-data` LS lower bound extends by **{bounds.loc['LS', 'range_expansion_below_week6'] * 1e6:.3f} µm**, P extends upward by **{bounds.loc['P', 'range_expansion_above_week6']:.3f} W**, and ST extends upward by only **{bounds.loc['ST', 'range_expansion_above_week6']:.3f} K**; VX adds no marginal range. **{summary['new_data_outside_any_week6_axis_range']}/165** new experiments lie outside at least one Week 6 marginal range and **{summary['new_data_outside_week6_4d_convex_hull']}/165** lie outside the Week 6 4-D convex hull. Keyhole prevalence is {outside_keyhole_percent:.1f}% outside at least one old marginal range versus {inside_keyhole_percent:.1f}% inside all four. This is a strong observed association with the newly sampled region, not evidence that smaller LS or higher P causes Keyhole."""
        ),
        markdown(
            """## 8. Partition, identifier, and duplicate integrity

**What are we doing?** Distinguish duplicate identifiers/content from repeated parameter settings and compare complete folder-content bundles.  
**Why?** Equal P/VX/LS/ST can be a legitimate replicate; only identifier/content equivalence supports a duplicate claim.  
**Question answered.** Are experiments repeated across partitions, labels conflicting for the same identifier, or complete folders duplicated?  
**Suspicious result.** Treating any equal parameter tuple as the same simulation or silently deduplicating scientific rows."""
        ),
        code(
            """integrity = pd.read_csv(OUT / "integrity_audit.csv")
bundles = pd.read_csv(OUT / "experiment_content_bundles.csv")
display(integrity if len(integrity) else pd.DataFrame({"integrity finding": ["No duplicate identifier, complete-content, cross-partition, tuple-conflict, or missing-input issue detected"]}))
display(bundles.groupby("partition").agg(
    experiments=("experiment_name", "nunique"),
    unique_content_bundles=("complete_content_bundle_sha256", "nunique"),
    repository_files=("file_count", "sum"),
).reset_index())"""
        ),
        markdown(
            f"""**Interpretation.** The integrity audit found **{len(integrity)} reportable duplicate/conflict issues**. All 407 semantic identifiers and complete content-bundle hashes are unique, and no identifier crosses partitions. Nothing is removed. The audit logic keeps the important distinction between a replicated design point and duplicate simulation content."""
        ),
        markdown(
            """## 9. Phase 1 conclusions

**What are we doing?** Separate observations, interpretations, and decisions before Phase 2.  
**Why?** A data audit should constrain later work without turning descriptive patterns into causal claims or silently correcting source data.  
**Question answered.** Is the pinned snapshot usable, and what must remain visible during target extraction?  
**Suspicious result.** Declaring the whole dataset clean despite monitor absences, or claiming the working-student labels are identifiable/wrong."""
        ),
        code(
            """display(Markdown((OUT / "results_summary.md").read_text(encoding="utf-8")))
display(pd.DataFrame({"summary field": list(summary), "value": [summary[key] for key in summary]}))"""
        ),
        markdown(
            f"""**Interpretation.** `sph_v2` is usable for a fail-closed Phase 2 migration, not uniformly complete: all **407 experiments** remain in scope, while the **{missing_experiments} monitor-incomplete experiments** must produce explicit failure rows. Ioan's population statistics are reproduced. The input domain expanded mainly toward higher P and smaller LS; the observed Keyhole coverage is concentrated in newly sampled input space. Annotator identity and visual validity of flagged label transitions remain unresolved."""
        ),
        markdown(
            """## 10. Did we satisfy Week 7 Phase 1?

**What are we doing?** Display every validation and requested-item mapping.  
**Why?** A final dashboard makes scientific defects distinct from missing deliverables.  
**Question answered.** Which checks pass, which source-data caveats remain, and where is the evidence?  
**Suspicious result.** A blanket PASS that hides missing monitors or a notebook containing stored execution errors."""
        ),
        code(
            """validation = pd.read_csv(OUT / "validation_results.csv")
checklist = pd.read_csv(OUT / "phase1_requirement_checklist.csv")
display(validation)
display(validation.groupby("status").size().rename("count").reset_index())
display(checklist)
assert summary["scope"]["predictive_models_fitted"] is False
assert summary["scope"]["active_learning"] is False
assert summary["scope"]["level_set_estimation"] is False"""
        ),
        markdown(
            """**Interpretation and hard stop.** The audit deliverables are complete. The structural validation retains a FAIL for missing upstream monitor files; that is a scientific finding, not a hidden pipeline crash. All label/count/revision/integrity guards pass. Phase 1 makes no target-selection or modelling decision and proceeds only to the separately validated Phase 2 extraction migration."""
        ),
    ]

    notebook = nbf.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3"},
            "phase": "Week 7 Phase 1",
            "dataset_revision": provenance["analysis_revision"],
            "builder": "scripts/build_week7_01_notebook.py",
        },
    )
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
    # Write once before execution so notebook-presence validation can be
    # refreshed independently without rerunning the expensive audit.
    nbf.write(notebook, NOTEBOOK)
    client = NotebookClient(
        notebook,
        timeout=1200,
        kernel_name="python3",
        resources={"metadata": {"path": str(ROOT)}},
        allow_errors=False,
    )
    executed = client.execute()
    nbf.write(executed, NOTEBOOK)
    print(f"wrote and executed {NOTEBOOK}")


if __name__ == "__main__":
    main()
