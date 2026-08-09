"""Build and execute the Week 7 Phase 2 teaching notebook."""

from __future__ import annotations

import json
from pathlib import Path

import nbformat as nbf
import pandas as pd
from nbclient import NotebookClient


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "week7_02_sph_v2_target_extraction"
NOTEBOOK = ROOT / "notebooks" / "week_07" / "02_sph_v2_physical_target_extraction.ipynb"


def code(source: str) -> nbf.NotebookNode:
    return nbf.v4.new_code_cell(source=source)


def markdown(source: str) -> nbf.NotebookNode:
    return nbf.v4.new_markdown_cell(source=source)


def main() -> None:
    summary = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
    targets = pd.read_csv(OUT / "sph_v2_simulation_level_targets.csv")
    valid = targets[targets["target_extraction_valid"]]
    invalid = targets[~targets["target_extraction_valid"]]
    compatibility = pd.read_csv(OUT / "monitor_schema_compatibility.csv")
    comparison_summary = pd.read_csv(OUT / "exact_old_new_target_comparison_summary.csv")
    depth_flags = pd.read_csv(OUT / "flagged_depth_ambiguity.csv")
    sentinel_audit = pd.read_csv(OUT / "sentinel_audit.csv")
    correction = pd.read_csv(OUT / "supervisor_correction_before_after.csv")
    readiness = pd.read_csv(OUT / "new_data_readiness_summary.csv")

    missing_monitors = compatibility[~compatibility["remote_exists"]]
    missing_experiments = int(missing_monitors["experiment_name"].nunique())
    keyhole = valid[valid["has_keyhole"]]
    reviewed = depth_flags[
        depth_flags["visual_review_status"].eq("REVIEWED")
        if "visual_review_status" in depth_flags.columns
        else pd.Series(False, index=depth_flags.index)
    ]
    max_depth_before_pct = 100 * float(valid["max_depth_relative_to_T0"].eq("before_T0").mean())
    no_keyhole_t0_pct = (
        100 * float((~keyhole["keyhole_overlaps_T0"].astype(bool)).mean()) if len(keyhole) else 0.0
    )
    new_data = targets[targets["partition"].eq("new-data")]
    new_data_valid = new_data[new_data["target_extraction_valid"]]
    changed = correction[correction["status_changed"].astype(bool)]

    cells: list[nbf.NotebookNode] = [
        markdown(
            """# Week 7 Phase 2 — migrate the Week 6 physical-target extraction to `sph_v2`

This notebook answers one bounded question: **can the executable Week 6 width, depth, total-height, kinetic-energy, active-region, T0, G3, and R3 definitions be applied to the exact pinned `sph_v2` snapshot without changing their scientific meaning?**

```text
Phase 2
├── 1. Scope and reproducible setup
├── 2. Week 6 executable definitions
├── 3. Monitor and repository compatibility
├── 3A. Supervisor clarification: no-melt 1e38 sentinel
├── 4. Active region and T0 reconstruction
├── 5. Representative physical time series
├── 6. One-row-per-experiment target table
├── 7. Exact Week 6 versus sph_v2 comparison
├── 8. Descriptive target distributions
├── 9. T0 versus extreme events and Keyhole timing
├── 10. Disconnected-depth visual diagnostic
├── 11. Explicit failures and warnings
└── 12. Validation, checklist, and hard stop
```

Scope boundary: no GP, Ridge, polynomial model, classifier, active learning, kernel comparison, target redefinition, or level-set estimation is performed."""
        ),
        markdown(
            """## 1. Scope and reproducible setup

**What are we doing?** Load the saved target table and visibly import the reusable migration/audit functions.  
**Why?** The notebook must expose scientific calculations while avoiding a second hidden target definition.  
**Question answered.** Are Phase 1, Phase 2, and every target row tied to one immutable revision and population?  
**Suspicious result.** A population mismatch, floating dataset access, silent row loss, or modelling code."""
        ),
        code(
            """from pathlib import Path
import json
import numpy as np
import pandas as pd
from IPython.display import Image, Markdown, display

from src.week7_sph_v2_common import SPH_V2_REPO_ID, SPH_V2_REVISION
from src.week7_phase2_sph_v2_physical_target_extraction import (
    descriptive_target_summary, traceability_table
)

ROOT = Path.cwd().resolve()
OUT = ROOT / "outputs" / "week7_02_sph_v2_target_extraction"
P1 = ROOT / "outputs" / "week7_01_sph_v2_audit"
assert ROOT.name == "thesis-week7-sph-v2-audit"

pd.set_option("display.max_columns", 100)
pd.set_option("display.max_colwidth", 95)

def show_figure(filename, width=980):
    display(Markdown(f"**{filename}**"))
    display(Image(filename=str(OUT / "figures" / filename), width=width))

summary = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
phase1 = json.loads((P1 / "summary.json").read_text(encoding="utf-8"))
targets = pd.read_csv(OUT / "sph_v2_simulation_level_targets.csv")
assert summary["revision"] == phase1["revision"] == SPH_V2_REVISION
assert targets["experiment_name"].is_unique
assert len(targets) == phase1["experiment_count"]
display(pd.DataFrame({
    "scope item": ["models fitted", "labels modified", "simulations removed", "active learning", "level-set estimation"],
    "value": [
        summary["scope"]["models_fitted"], summary["scope"]["labels_modified"],
        summary["scope"]["simulations_removed"], summary["scope"]["active_learning"],
        summary["scope"]["level_set_estimation"],
    ],
}))"""
        ),
        markdown(
            """**Interpretation.** Phase 2 preserves the full Phase 1 population as one row per experiment. A failed extraction remains a row with reasons; “usable” therefore means a finite physical target row, not membership in the label audit."""
        ),
        markdown(
            """## 2. Exact Week 6 definitions and formulas

**What are we doing?** Trace every migrated quantity to the actual Week 6 source file/symbol and restate the formulas.  
**Why?** The task is migration, not redesign; executable Week 6 code is the source of truth if prose differs.  
**Question answered.** Which definitions are reused directly, and what is the smallest new compatibility layer?  
**Suspicious result.** Recalling formulas from memory, moving T0, promoting length to a primary target, or changing units."""
        ),
        code(
            """# Recompute the source hashes and definitions visibly.
traceability_now = traceability_table()
stored_traceability = pd.read_csv(OUT / "week6_definition_traceability.csv")
display(traceability_now)
assert traceability_now["source_sha256"].tolist() == stored_traceability["source_sha256"].tolist()

display(pd.DataFrame({
    "quantity": ["valid melt row", "width", "length diagnostic", "penetration depth", "total height", "T0", "kinetic energy", "G3/R3 continuity"],
    "exact definition": [
        "finite ordered bounds with abs(value) < 1e30",
        "y_max - y_min",
        "x_max - x_min",
        "max(0, -z_min)",
        "z_max - z_min",
        "median over final 20% between first valid melt and min(recording end, 0.90 × laser-exit time); fallback final 50 eligible rows",
        "instantaneous aggregate melt monitor in J; T0 median reported in nJ",
        "maximum trailing 50 µm rolling median in the adaptive interior; R3 uses a 12 µm width guard",
    ],
}))"""
        ),
        markdown(
            """**Interpretation.** The scientific quantities are unchanged. Width, depth, and height remain geometric bounding-box responses; kinetic energy remains an instantaneous aggregate monitor, not a cumulative energy. Length is retained only for active-region/diagnostic continuity. The Week 7-only layer reconstructs the domain end from folder metadata and changes file paths—not target meaning."""
        ),
        markdown(
            """## 3. Monitor-file and repository compatibility

**What are we doing?** Check existence, bytes, schema, rows, non-finite values, units, and the folder-to-domain mapping for every required monitor.  
**Why?** A similarly named repository can still omit files or change schema. Fail-closed extraction must never substitute unrelated data.  
**Question answered.** Which experiments can supply the exact Week 6 inputs?  
**Suspicious result.** Unverified local-cache reuse, schema coercion, fuzzy matching, or an unreported missing monitor."""
        ),
        code(
            """compatibility = pd.read_csv(OUT / "monitor_schema_compatibility.csv")
source_plan = pd.read_csv(OUT / "monitor_source_plan.csv")
domain = pd.read_csv(OUT / "domain_mapping_compatibility.csv")

display(compatibility[[
    "monitor_file", "expected_columns", "source_unit", "reported_unit_or_use",
    "timestep_or_index_interpretation", "physical_semantics",
]].drop_duplicates().sort_values("monitor_file"))
display(
    compatibility.groupby(["partition", "monitor_file"])
    .agg(
        experiments=("experiment_name", "nunique"),
        present=("remote_exists", "sum"),
        schema_compatible=("schema_compatible", "sum"),
        nonfinite_values=("nonfinite_count", "sum"),
    ).reset_index()
)
display(
    source_plan.groupby(["partition", "source_mode"])
    .size().rename("monitor_files").reset_index()
)
display(compatibility[~compatibility["remote_exists"]][[
    "partition", "experiment_name", "monitor_file", "detail"
]])
display(domain[[
    "experiment_name", "week6_simulation_id", "sph_v2_folder_domain_max_m",
    "week6_domain_max_reconstructed_m", "absolute_error_m", "mapping_matches_week6"
]].describe(include="all"))
show_figure("01_monitor_schema_compatibility.png")"""
        ),
        markdown(
            f"""**Interpretation.** Present files parse with their Week 6 schemas and their local bytes match the pinned remote Git blobs. **{len(missing_monitors)} monitor files across {missing_experiments} experiments are absent upstream**, so those experiments fail explicitly. For exact Week 6 identifiers, local bytes are reused only after Git-blob equality. The new domain rule `min(XF, XL) + 12 µm` reproduces the Week 6 domain end for every exact match; the 12 µm is the existing three-particle boundary-wall extension."""
        ),
        markdown(
            """## 3A. Supervisor clarification: no-melt 1e38 sentinel

**What was previously flagged?** One present new-data bounds file could not be parsed because its first field was the text `s3.402823e+38`.  
**What did Ioan clarify?** Values around `1e38` are normal solver artifacts indicating that the melt is absent. They are not physical melt coordinates.  
**Why can the simulation continue?** A no-melt row is excluded, but later rows can contain valid finite melt bounds. Therefore one bad no-melt row does not require discarding the whole experiment.  
**What changed?** The parser recognizes only the exact complete field `s3.402823e+38` as the already-known positive no-melt sentinel. The unchanged Week 6 rule then rejects that row because `abs(value) >= 1e30`. No arbitrary letters are stripped, nothing is set to zero, and no interpolation is introduced.  
**Suspicious result.** Any other malformed token being repaired, a sentinel entering a width/depth/height calculation, or an unrelated previously valid target changing."""
        ),
        code(
            """sentinel_audit = pd.read_csv(OUT / "sentinel_audit.csv")
correction = pd.read_csv(OUT / "supervisor_correction_before_after.csv")
readiness = pd.read_csv(OUT / "new_data_readiness_summary.csv")

raw_example = pd.DataFrame({
    "raw bounds row": [" s3.402823e+38,-3.402823e+38,3.402823e+38,-3.402823e+38,3.402823e+38,-3.402823e+38"],
    "safe interpretation": ["complete no-melt sentinel row; exclude it from finite geometry"],
})
display(raw_example)
display(sentinel_audit[[
    "token", "count", "file_count", "experiment_count", "column_location",
    "numerically_parseable", "proposed_interpretation", "parser_action",
    "evidence_supervisor_clarification",
]])

affected_names = set(
    sentinel_audit.loc[
        sentinel_audit["token"].eq("s3.402823e+38"),
        "files_experiments_affected",
    ].astype(str)
)
affected = correction[
    correction["status_changed"].astype(bool)
    | correction["experiment_name"].isin(affected_names)
]
display(affected[[
    "experiment_name", "partition_before", "target_extraction_valid_before",
    "extraction_failure_reasons_before", "target_extraction_valid_after",
    "extraction_failure_reasons_after", "status_changed",
    "changed_due_to_confirmed_sentinel_rule",
    "previous_valid_target_changed_unexpectedly", "label_context_changed",
]])
display(readiness[readiness["partition"].eq("new-data")])
display(targets[targets["partition"].eq("new-data") & ~targets["target_extraction_valid"]][[
    "experiment_name", "geometry_monitor_available", "geometry_parse_ok",
    "geometry_target_ready", "time_monitor_available",
    "kinetic_energy_monitor_available", "kinetic_energy_parse_ok",
    "kinetic_energy_target_ready", "physical_target_extraction_success",
    "extraction_failure_reason", "label_analysis_ready",
]])

assert sentinel_audit.loc[sentinel_audit["token"].eq("other numeric/textual variants near 1e38"), "count"].eq(0).all()
assert not correction["previous_valid_target_changed_unexpectedly"].astype(bool).any()
assert not correction["label_context_changed"].astype(bool).any()"""
        ),
        markdown(
            f"""**Interpretation.** The audit found exactly the three reported raw variants: ordinary positive and negative solver sentinels plus one exact `s3.402823e+38` field; no other near-`1e38` variant was found. The correction changes extraction status for **{len(changed)}** experiment(s). New-data physical-target readiness is now **{len(new_data_valid)}/{len(new_data)}**. The remaining new-data failure is retained with machine-readable availability and readiness flags because its required monitors are absent; no data were fabricated."""
        ),
        markdown(
            """## 4. Active region and T0 reconstruction

**What are we doing?** Audit the selected active interval, T0 endpoints, sample counts, fallback use, and cooling exclusion.  
**Why?** T0 was one of Week 6's most consequential choices and must not drift during repository migration.  
**Question answered.** Does each successful window lie inside valid melt activity and before the 90%-domain cutoff?  
**Suspicious result.** Cooling-only rows, a T0 outside the active interval, too few samples without fallback, or a degenerate active region."""
        ),
        code(
            """active = pd.read_csv(OUT / "active_region_diagnostics.csv")
valid_active = active[active["target_extraction_valid"]]
valid_targets = targets[targets["target_extraction_valid"]]
display(valid_active[[
    "experiment_name", "partition", "active_region_start_row_index",
    "active_region_end_row_index", "active_region_sample_count",
    "active_region_fraction_of_monitor", "T0_start_row_index", "T0_end_row_index",
    "T0_sample_count", "T0_fallback_last_rows_used", "T0_inside_active_region",
    "recording_ends_before_90pct_domain", "flag_primary_window_unstable_week6_rule",
]].head(12))
display(valid_active[[
    "active_region_sample_count", "active_region_fraction_of_monitor", "T0_sample_count"
]].describe())
display(pd.DataFrame({
    "diagnostic": ["T0 fallback used", "T0 outside active region", "cooling rows selected", "Week 6 CV instability flag", "recording ended before cutoff"],
    "experiments": [
        int(valid_active["T0_fallback_last_rows_used"].sum()),
        int((~valid_active["T0_inside_active_region"]).sum()),
        int(valid_targets["cooling_rows_selected_in_T0"].sum()),
        int(valid_active["flag_primary_window_unstable_week6_rule"].sum()),
        int(valid_active["recording_ends_before_90pct_domain"].sum()),
    ],
}))
show_figure("02_active_region_diagnostics.png")"""
        ),
        markdown(
            f"""**Interpretation.** All **{len(valid)} successful extractions** keep T0 inside the Week 6 active interval and select zero cooling-only rows. The target table preserves fallback, short-active, recording-end, and within-window CV flags per experiment. These diagnostics test implementation and stability; they do not redefine T0."""
        ),
        markdown(
            """## 5. Representative physical time series

**What are we doing?** Plot width, depth, total height, and kinetic energy for deterministic representatives covering every partition, Keyhole/non-Keyhole status, low/high LS, low/high ST, and a suspicious depth case.  
**Why?** Scalar validations can pass while a selected window still looks physically implausible.  
**Question answered.** Do the active/T0 overlays and median targets behave as intended across ordinary and edge cases?  
**Suspicious result.** Cherry-picking only clean traces, hiding the cutoff, or failing to show a selected-median line."""
        ),
        code(
            """representatives = pd.read_csv(OUT / "representative_simulation_selection.csv")
manifest = pd.read_csv(OUT / "figure_manifest.csv")
display(representatives)
representative_figures = manifest[manifest["figure"].str.startswith("representative_")]
display(representative_figures[["figure", "question", "experiment_name"]])
for path in representative_figures["path"]:
    display(Image(filename=str(ROOT / path), width=980))"""
        ),
        markdown(
            f"""**Interpretation.** The **{len(pd.read_csv(OUT / 'representative_simulation_selection.csv'))}** selections are rule-based, not hand-picked for attractive behaviour. Each plot shows the full monitor-time context, the active interval, T0, and the selected median for all four primary responses. The explicit failed case remains listed even though no physical trace can be constructed without its missing inputs."""
        ),
        markdown(
            """## 6. Simulation-level physical-target table

**What are we doing?** Inspect the one-row-per-experiment CSV/Parquet table and recompute descriptive summaries with the reusable function.  
**Why?** Later phases need one transparent interface containing inputs, labels, targets, extrema, uncertainty/stability diagnostics, and failure reasons.  
**Question answered.** Which rows are physically usable and which quantities are retained for exact Week 6 continuity?  
**Suspicious result.** Dropped failures, missing revision/partition, negative dimensions, non-finite successful targets, or length promoted as a primary response."""
        ),
        code(
            """targets = pd.read_csv(OUT / "sph_v2_simulation_level_targets.csv")
valid = targets[targets["target_extraction_valid"]]
target_summary_now = descriptive_target_summary(targets)
stored_target_summary = pd.read_csv(OUT / "target_distribution_summary.csv")
display(targets[[
    "experiment_name", "partition", "exact_sph_v2_revision", "P_W", "VX_m_per_s",
    "LS_um", "ST_K", "has_conduction", "has_keyhole", "T0_width_um",
    "T0_depth_um", "T0_total_height_um", "T0_kinetic_energy_nJ", "max_depth_um",
    "max_total_height_um", "max_kinetic_energy_nJ", "G3_persistent_depth_um",
    "R3_persistent_depth_width_ratio", "target_extraction_valid", "extraction_status",
    "geometry_monitor_available", "geometry_parse_ok", "geometry_target_ready",
    "time_monitor_available", "kinetic_energy_monitor_available",
    "kinetic_energy_parse_ok", "kinetic_energy_target_ready",
    "physical_target_extraction_success", "extraction_failure_reason",
    "label_analysis_ready",
]].head(12))
display(targets.groupby(["partition", "target_extraction_valid"]).size().rename("experiments").reset_index())
display(target_summary_now[target_summary_now["group"].eq("overall")])
assert targets["length_is_primary_target"].fillna(False).eq(False).all()
assert targets["simulation_silently_removed"].eq(False).all()"""
        ),
        markdown(
            f"""**Interpretation.** The table retains **{len(targets)} rows**: **{len(valid)} successful** and **{len(invalid)} explicit failures**. Availability, parse, target-readiness, physical-extraction, and label-readiness fields are derived from each rerun rather than a fixed exclusion list, so future upstream repairs can make rows eligible automatically. Successful T0/extreme responses are finite and non-negative, and total height is never below penetration depth under the stored definitions. Length remains diagnostic. G3/R3 are carried forward only for continuity and depth-ambiguity diagnostics—not as a new target choice."""
        ),
        markdown(
            """## 7. Exact matched Week 6 versus `sph_v2` targets

**What are we doing?** Match only exact semantic folder identifiers from Week 6 metadata and compare T0 targets and window endpoints.  
**Why?** Old-data partitions provide a direct semantic-regression test of the migration.  
**Question answered.** Did the same bytes and definitions reproduce Week 6 numerical targets?  
**Suspicious result.** Fuzzy matches, changed endpoints, material numerical differences, or correlations used to hide offsets."""
        ),
        code(
            """comparison = pd.read_csv(OUT / "exact_old_new_target_comparison.csv")
comparison_summary = pd.read_csv(OUT / "exact_old_new_target_comparison_summary.csv")
identifier_map = pd.read_csv(OUT / "week6_exact_identifier_map.csv")
display(identifier_map.head())
display(pd.DataFrame({
    "mapping guard": ["rows", "unique semantic identifiers", "unique Week 6 simulation IDs", "metadata hashes recorded"],
    "value": [
        len(identifier_map), identifier_map["experiment_name"].nunique(),
        identifier_map["week6_simulation_id"].nunique(),
        identifier_map["week6_metadata_sha256"].notna().sum(),
    ],
}))
display(comparison_summary)
display(comparison.head(12))
display(pd.DataFrame({
    "check": ["exact identifiers in target table", "comparable exact matches", "all endpoints identical", "materially changed target values"],
    "value": [
        int(targets["week6_simulation_id"].fillna("").str.len().gt(0).sum()),
        len(comparison),
        bool(comparison["window_endpoints_identical"].all()),
        int(comparison_summary["materially_changed_count"].sum()),
    ],
}))
show_figure("11_exact_old_vs_new_target_comparison.png")"""
        ),
        markdown(
            f"""**Interpretation.** **{summary['exact_week6_match_count']} exact Week 6 identifiers** are present; **{summary['comparable_exact_week6_match_count']}** have all required monitors in the pinned `sph_v2` snapshot and can be compared. Every comparable width, depth, height, kinetic-energy value and T0 endpoint reproduces Week 6 within the declared near-machine-precision tolerances; **{summary['exact_match_material_change_count']}** material changes are detected. Unmatched/new experiments are never fuzzily paired."""
        ),
        markdown(
            """## 8. Descriptive target distributions

**What are we doing?** Compare successful target distributions overall, by partition, and by observed Keyhole presence.  
**Why?** Distribution plots can reveal unit, scale, or extraction mistakes before any modelling.  
**Question answered.** Are width, depth, height, and energy numerically plausible, and do labelled groups occupy different observed ranges?  
**Suspicious result.** Negative values, implausible orders of magnitude, or causal claims from group differences."""
        ),
        code(
            """target_summary = pd.read_csv(OUT / "target_distribution_summary.csv")
display(target_summary)
for filename in [
    "03_T0_width_um_distribution.png",
    "04_T0_depth_um_distribution.png",
    "05_T0_total_height_um_distribution.png",
    "06_T0_kinetic_energy_nJ_distribution.png",
]:
    show_figure(filename)"""
        ),
        markdown(
            """**Interpretation.** The primary responses have coherent units and finite successful rows. Partition and Keyhole-group differences are descriptive evidence only. They can reflect the strongly shifted input design as well as physical-regime differences; this notebook does not fit a predictor or claim causation."""
        ),
        markdown(
            """## 9. T0 versus maxima and transient Keyhole timing

**What are we doing?** Locate maximum depth/height/energy relative to T0 and align saved Keyhole timesteps exactly with `iter.dat`.  
**Why?** T0 describes typical late-active behaviour, whereas a brief Keyhole or extreme response may occur earlier.  
**Question answered.** How often does T0 exclude extrema or all saved Keyhole frames?  
**Suspicious result.** Treating this diagnostic as permission to redefine T0, or interpolating unmatched label timesteps silently."""
        ),
        code(
            """extreme = pd.read_csv(OUT / "t0_extreme_event_diagnostics.csv")
display(pd.DataFrame({
    "maximum depth location": ["before T0", "inside T0", "after T0"],
    "experiments": [
        int(extreme["max_depth_relative_to_T0"].eq("before_T0").sum()),
        int(extreme["max_depth_relative_to_T0"].eq("inside_T0").sum()),
        int(extreme["max_depth_relative_to_T0"].eq("after_T0").sum()),
    ],
}))
display(
    extreme[extreme["has_keyhole"]]["keyhole_timing_relative_to_T0"]
    .value_counts(dropna=False).rename("experiments").reset_index()
)
display(extreme[extreme["has_keyhole"]][[
    "experiment_name", "partition", "T0_depth_um", "max_depth_um",
    "max_depth_relative_to_T0", "keyhole_frames_before_T0",
    "keyhole_frames_inside_T0", "keyhole_frames_after_T0", "keyhole_overlaps_T0",
]].head(15))
for filename in [
    "07_T0_vs_max_penetration_depth.png",
    "08_T0_vs_max_total_height.png",
    "09_T0_vs_max_kinetic_energy.png",
    "10_keyhole_timing_relative_to_T0.png",
]:
    show_figure(filename)"""
        ),
        markdown(
            f"""**Interpretation.** Maximum depth occurs before T0 in **{summary['max_depth_before_T0_count']}/{len(valid)} successful experiments ({max_depth_before_pct:.1f}%)**. Among **{summary['keyhole_positive_successful_count']} successful Keyhole-positive experiments**, **{summary['keyhole_positive_without_T0_overlap_count']} ({no_keyhole_t0_pct:.1f}%)** have no stored Keyhole frame inside T0. This does **not** make T0 wrong: T0 and extrema answer different physical questions. It is evidence for a later target discussion, which is deliberately not made here."""
        ),
        markdown(
            """## 10. Disconnected lower-region (“blue-dot”) diagnostic

**What are we doing?** Rank bounding-box depth spikes relative to persistent G3, fetch at most four side views at the pinned revision, and record a human visual review.  
**Why?** Bounding boxes cannot identify connected components; a deep disconnected lower particle can inflate maximum depth.  
**Question answered.** Do the most justified candidates visibly warrant later sensitivity analysis?  
**Suspicious result.** Assuming Week 6's old list applies, downloading all GIFs, or permanently excluding a case from one image."""
        ),
        code(
            """depth_flags = pd.read_csv(OUT / "flagged_depth_ambiguity.csv")
selected = depth_flags[depth_flags["selected_for_visual_review"]]
display(selected[[
    "visual_review_rank", "partition", "experiment_name", "has_keyhole",
    "max_depth_um", "T0_depth_um", "G3_persistent_depth_um",
    "max_depth_minus_G3_um", "max_depth_over_G3",
    "flag_depth_bounding_box_ambiguity_candidate", "nearest_saved_frame_timestep",
    "gif_path_in_repository", "visual_review_status", "visual_review_note",
    "permanently_excluded",
]])
show_figure("12_depth_visual_review_contact_sheet.png")"""
        ),
        markdown(
            f"""**Interpretation.** **{summary['depth_ambiguity_candidate_count']} experiments** meet the automatic spike-sensitive candidate rule; the audit selected only four ranked cases for visual inspection. **{len(reviewed)}** have completed review notes. These frames are evidence aids, not segmentation: the numerical monitor still cannot prove connectedness, and no experiment is excluded. The GIF paths remain linked for future sensitivity work."""
        ),
        markdown(
            """## 11. Extraction failures and warnings

**What are we doing?** Display every failed or warning condition with experiment, partition, severity, and reason.  
**Why?** A scientifically conservative pipeline must preserve failures rather than dropping them before summary statistics.  
**Question answered.** Why is each non-successful row unusable or cautionary?  
**Suspicious result.** A mismatch between Phase 1 and Phase 2 populations, empty reasons, or unexplained row loss."""
        ),
        code(
            """anomalies = pd.read_csv(OUT / "extraction_failure_anomalies.csv")
display(
    anomalies.groupby(["severity", "reason"])
    .agg(records=("experiment_name", "size"), experiments=("experiment_name", "nunique"))
    .reset_index().sort_values(["severity", "records"], ascending=[True, False])
)
display(anomalies)
display(targets[~targets["target_extraction_valid"]][[
    "partition", "experiment_name", "extraction_status", "extraction_failure_reasons",
    "source_label_modified", "simulation_silently_removed",
]])"""
        ),
        markdown(
            f"""**Interpretation.** The **{len(invalid)} failures** correspond to missing pinned monitors or another explicitly recorded extraction condition; they are retained in both CSV and Parquet. Warning flags identify instability, early recording termination, unusual length behaviour, or depth-ambiguity candidates. No label is edited and no Phase 1 experiment disappears."""
        ),
        markdown(
            """## 12. Did we satisfy Week 7 Phase 1 and Phase 2?

**What are we doing?** Display the automatic validation dashboard and every requested-item mapping.  
**Why?** Deliverable completeness, implementation correctness, and upstream data caveats are different questions.  
**Question answered.** Which checks pass, warn, or fail, and where is the evidence?  
**Suspicious result.** A blanket PASS that hides missing files, a notebook with stored errors, or evidence that modelling began."""
        ),
        code(
            """validation = pd.read_csv(OUT / "validation_results.csv")
checklist = pd.read_csv(OUT / "phase2_requirement_checklist.csv")
phase1_validation_path = P1 / "validation_results.csv"
phase1_checklist_path = P1 / "phase1_requirement_checklist.csv"
display(Markdown("### Phase 1 validation and requested-item checklist"))
if phase1_validation_path.exists() and phase1_checklist_path.exists():
    display(pd.read_csv(phase1_validation_path))
    display(pd.read_csv(phase1_checklist_path))
else:
    missing_reports = [
        path.name for path in [phase1_validation_path, phase1_checklist_path]
        if not path.exists()
    ]
    display(Markdown(
        "The Phase 1 summary is present and supplies the pinned revision and experiment count, "
        f"but these local Phase 1 reporting files are absent: `{', '.join(missing_reports)}`. "
        "They are reported as unavailable here and were not regenerated during this targeted Phase 2 correction."
    ))
    display(pd.DataFrame({
        "Phase 1 summary field": ["revision", "experiment_count"],
        "value": [phase1["revision"], phase1["experiment_count"]],
    }))
display(Markdown("### Phase 2 validation and requested-item checklist"))
display(validation)
display(validation.groupby("status").size().rename("count").reset_index())
display(checklist)
assert summary["scope"]["models_fitted"] is False
assert summary["scope"]["active_learning"] is False
assert summary["scope"]["level_set_estimation"] is False
assert targets["source_label_modified"].eq(False).all()
assert targets["simulation_silently_removed"].eq(False).all()"""
        ),
        markdown(
            """**Interpretation and hard stop.** The Week 6 semantics transfer exactly wherever `sph_v2` supplies the required monitors; missing upstream inputs remain explicit warnings/failures rather than being repaired from another dataset. The count/units/window/old-match/no-removal guards are automatic. Phase 2 ends here—no model, classifier, active-learning acquisition, level-set estimate, or final target selection has been started."""
        ),
    ]

    notebook = nbf.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3"},
            "phase": "Week 7 Phase 2",
            "dataset_revision": summary["revision"],
            "builder": "scripts/build_week7_02_notebook.py",
        },
    )
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
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
