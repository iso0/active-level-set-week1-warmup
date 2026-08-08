"""Build the explanatory Week 6 Phase 3.5 notebook from validated outputs."""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "week_06" / "05_phase3_5_regime_target_design.ipynb"


def markdown(text: str):
    return nbf.v4.new_markdown_cell(text.strip())


def code(text: str):
    return nbf.v4.new_code_cell(text.strip())


def build() -> Path:
    notebook = nbf.v4.new_notebook()
    notebook.metadata = {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python", "version": "3.14"},
    }
    notebook.cells = [
        markdown(
            r"""
# Week 6 Phase 3.5 — Regime-target design

This notebook asks whether the Phase 1–3 late-window median depth target is
also a good target for persistent conduction-like versus keyhole-like
behaviour. It does **not** replace T0 silently, fit a GP classifier, or begin
active learning.

```text
Phase 3.5
├── A. Provenance, label and time-alignment audit
├── B. Scan-position and geometry evolution
├── C. Representative simulation case studies
├── D. Candidate regime-target construction
├── E. Candidate-versus-label evaluation
├── F. Robustness and sensitivity checks
└── G. Final target recommendation
```

## Terms used in this notebook

- **Instantaneous melt-pool extent:** the coordinate span at one monitor row,
  not the cumulative melted-track length.
- **Penetration depth:** `max(0, -z_min)`, measured below the original surface.
- **Aspect ratio:** penetration depth divided by transverse width. Both are
  lengths, so the ratio is dimensionless.
- **Normalized scan position:** physical laser position mapped to `s=0` at the
  positive-X start and `s=1` at domain exit.
- **Right-censoring:** a simulation stops being observed before a later event
  could be seen. For example, a run ending at `s=0.7` cannot tell us what would
  happen at `s=0.9`.
- **Transient:** a short-lived excursion. A one-frame peak is a transient
  candidate, not automatically persistent behaviour.
- **Quasi-steady state:** a period whose geometry changes relatively slowly,
  without claiming perfect equilibrium.
- **Rolling window:** a moving physical-distance interval.
- **Rolling median:** the median inside that interval. For `[0.3, 0.4, 3.0]`,
  the median is `0.4`, so the isolated `3.0` spike is suppressed.
- **Persistence:** geometry that remains elevated over a declared physical
  distance, here tested at 20, 50, and 100 µm.
- **Quantile:** a distribution cutoff. **q95** is the value exceeded by only
  5% of observations.
- **Spike:** an isolated or very brief extreme value.
- **Cluster bootstrap:** resampling complete simulations so correlated frames
  from one simulation stay together.
- **ROC AUC:** the probability that a random positive receives a higher score
  than a random negative.
- **Precision–recall AUC:** ranking quality focused on the positive class.
- **Prevalence baseline:** the positive fraction; random PR performance is
  approximately this value.
- **Balanced accuracy:** the mean of sensitivity and specificity.
- **Sensitivity / recall:** fraction of positives correctly detected.
- **Specificity:** fraction of negatives correctly rejected.
- **Precision:** fraction of predicted positives that are positive.
- **F1:** harmonic mean of precision and recall.
- **Nested leave-one-out:** one simulation is held out while any threshold is
  selected only from the other simulations.
- **Circular validation:** evaluating a depth-derived proxy against labels
  initially seeded using depth.
- **Regime proxy:** a continuous geometric summary intended to reflect, but
  not define as ground truth, the physical regime.
- **Continuous level-set target:** a scalar whose threshold could later define
  a boundary; no such boundary is estimated here.
"""
        ),
        code(
            """
from pathlib import Path
import json
import pandas as pd
from IPython.display import Image, display

ROOT = Path.cwd()
OUT = ROOT / "outputs" / "week6_03_5_regime_target_design"
configuration = json.loads((OUT / "phase3_5_configuration.json").read_text(encoding="utf-8"))
summary = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
print("Branch:", configuration["branch"])
print("HEAD:", configuration["head"])
print("Pinned revision:", configuration["huggingface"]["revision"])
display(Image(filename=str(OUT / "figures" / "01_phase3_5_experiment_tree.png")))
"""
        ),
        markdown(
            """
The experiment tree fixes the order of evidence. Provenance and alignment are
checked before candidate scores are interpreted. This cell does not establish
which target is best; it only verifies the analysis boundary and inputs.
"""
        ),
        markdown(
            """
## A. Provenance, label and time-alignment audit

Physical labels are kept separate from technical/annotation states.
`Screenshot Bug` is never used as a physical Keyhole-negative class.
"""
        ),
        code(
            """
label_dictionary = pd.read_csv(OUT / "label_dictionary.csv")
label_population = pd.read_csv(OUT / "label_population_audit.csv")
alignment = pd.read_csv(OUT / "label_monitor_alignment_audit.csv")
display(label_dictionary)
display(label_population)
print("Exact aligned frames:", int(alignment["exact_alignment_count"].sum()))
print("Ambiguous frames:", int(alignment["ambiguous_alignment_count"].sum()))
display(Image(filename=str(OUT / "figures" / "03_label_count_overview.png")))
"""
        ),
        markdown(
            """
All labelled frames align exactly by stored timestep to `iter.dat`; alignment
uncertainty is therefore zero for this pinned revision. The important
limitation is different: only nine simulations contain Keyhole, and every
provenance record retains a depth-based automatic seed. Agreement with depth
is descriptive and potentially circular, even when frames were human-verified.
"""
        ),
        markdown(
            """
## B. Scan-position and geometry evolution

Raw monitor time is converted into physical laser X, then into normalized
position using fixed domain bounds. Each simulation keeps its real stopping
position; it is never stretched to make its final row look like `s=1`.
"""
        ),
        code(
            """
coverage = pd.read_csv(OUT / "scan_coverage_summary.csv")
active = pd.read_csv(OUT / "simulation_active_interval_summary.csv")
display(active[[
    "last_active_melt_position_s", "global_max_depth_position_s",
    "persistent_max_depth_position_s", "global_max_ratio_position_s",
    "persistent_max_ratio_position_s"
]].describe())
display(Image(filename=str(OUT / "figures" / "04_scan_coverage_curve.png")))
display(Image(filename=str(OUT / "figures" / "14_T0_window_vs_maximum_and_persistent_event_locations.png")))
"""
        ),
        markdown(
            """
The support curve shows substantial right-censoring near domain exit. The
event-location comparison also shows why T0 and a regime target answer
different questions: many strongest or persistent events occur before T0's
late window. This does not make T0 wrong; it makes it a geometry summary.
"""
        ),
        markdown(
            """
## C. Representative simulation case studies

Examples are selected only after the population audit using explicit rules:
closest to a group median, strongest reproducible transition support, or a
declared maximum-versus-persistence disagreement score.
"""
        ),
        code(
            """
representatives = pd.read_csv(OUT / "representative_simulation_selection.csv")
display(representatives)
for name in [
    "28_case_typical_conduction_only.png",
    "29_case_typical_keyhole_containing.png",
    "30_case_mixed_conduction_to_keyhole.png",
    "31_case_spike_vs_persistent_disagreement.png",
]:
    display(Image(filename=str(OUT / "figures" / name)))
display(Image(filename=str(OUT / "figures" / "34_actual_frame_sequence_mixed_keyhole_case.png")))
"""
        ),
        markdown(
            """
The conduction, Keyhole-containing, mixed, and spike-disagreement cases
illustrate different reasons a scalar may succeed or fail. The three image
panels are actual files from the pinned Hugging Face revision. A case study is
an explanation aid, not a population estimate or independent label validation.
"""
        ),
        markdown(
            """
## D. Candidate regime-target construction

`G` candidates use absolute depth; `R` candidates use depth/width. Global
maxima are deliberately retained as spike-sensitive references. Persistence is
defined over physical distance, not a fixed number of monitor rows.
"""
        ),
        code(
            """
definitions = pd.read_csv(OUT / "regime_target_candidate_definitions.csv")
candidates = pd.read_csv(OUT / "regime_target_candidates.csv")
display(definitions)
display(candidates.groupby("candidate_id").agg(
    available=("available", "sum"),
    median_value=("value", "median"),
))
display(Image(filename=str(OUT / "figures" / "15_global_maximum_q95_persistent_depth_scatter.png")))
display(Image(filename=str(OUT / "figures" / "16_global_maximum_vs_persistent_aspect_ratio.png")))
"""
        ),
        markdown(
            """
Global maximum, q95, and rolling persistence are intentionally different.
The maximum answers “what was the single deepest observation?” while G3/R3
answer “what was the strongest geometry sustained across a physical window?”
No candidate is preferred solely because it is numerically larger.
"""
        ),
        markdown(
            """
## E. Candidate-versus-label evaluation

Frame-level intervals resample whole simulations. Simulation-level thresholds
use exact nested leave-one-simulation-out, so the held-out label never selects
its threshold.
"""
        ),
        code(
            """
frame_metrics = pd.read_csv(OUT / "frame_level_candidate_label_metrics.csv")
simulation_metrics = pd.read_csv(OUT / "simulation_level_candidate_label_metrics.csv")
nested_metrics = pd.read_csv(OUT / "nested_threshold_metrics.csv")
display(frame_metrics)
display(simulation_metrics)
display(nested_metrics)
display(Image(filename=str(OUT / "figures" / "23_candidate_precision_recall_curves_with_prevalence.png")))
display(Image(filename=str(OUT / "figures" / "25_nested_heldout_confusion_matrices.png")))
"""
        ),
        markdown(
            """
ROC and PR results quantify agreement with the current labels, not physical
truth. PR AUC is compared with the prevalence baseline because only 9/241
simulations are positive. Perfect or near-perfect ranking by a depth maximum is
not decisive: the labels were initially depth-seeded and the maximum remains
spike-sensitive.
"""
        ),
        markdown(
            """
## F. Robustness and sensitivity checks

The analysis predeclares 20, 50, and 100 µm windows plus 1%, 2.5%, and 5% of
track length. It also compares common/adaptive interiors, three width guards,
the 241/230 populations, coverage groups, and VX strata.
"""
        ),
        code(
            """
persistence = pd.read_csv(OUT / "persistence_window_sensitivity.csv")
domain = pd.read_csv(OUT / "candidate_domain_sensitivity.csv")
unstable = pd.read_csv(OUT / "candidate_unstable_subset_sensitivity.csv")
censoring = pd.read_csv(OUT / "candidate_censoring_sensitivity.csv")
display(persistence[persistence["record_type"].eq("summary")])
display(domain[domain["record_type"].eq("summary")])
display(unstable)
display(Image(filename=str(OUT / "figures" / "17_persistence_window_sensitivity.png")))
display(Image(filename=str(OUT / "figures" / "26_candidate_robustness_across_analysis_domains.png")))
display(Image(filename=str(OUT / "figures" / "27_candidate_robustness_with_without_unstable_simulations.png")))
"""
        ),
        markdown(
            """
These checks prevent a post-hoc “best window” story. R3 is interpreted at 50
µm only alongside the other predeclared scales. Large changes across windows,
domains, censoring groups, or unstable exclusions would weaken the
recommendation even if one AUC looked strong.
"""
        ),
        markdown(
            """
## G. Final target recommendation

Evidence dimensions remain separate. The decision matrix does not hide
physical interpretation, spike robustness, coverage, and label agreement
inside an arbitrary weighted score.
"""
        ),
        code(
            """
decision = pd.read_csv(OUT / "phase3_5_candidate_decision_matrix.csv")
recommendation = pd.read_csv(OUT / "phase3_5_final_target_recommendation.csv")
display(decision)
display(recommendation)
display(Image(filename=str(OUT / "figures" / "36_final_candidate_decision_matrix.png")))
display(Image(filename=str(OUT / "figures" / "37_final_recommended_geometry_regime_active_learning_roles.png")))
"""
        ),
        markdown(
            """
The recommendation is to retain T0 for typical geometry and provisionally
carry R3 as persistent regime propensity, with G3 as a companion. Two outputs
should remain separate until Ioan confirms the physical target and independent
updated labels exist. No active-learning or level-set algorithm is run here.
"""
        ),
        code(
            """
validation_path = OUT / "validation_results.csv"
checklist_path = OUT / "phase3_5_requirement_checklist.csv"
if validation_path.exists() and checklist_path.exists():
    validation = pd.read_csv(validation_path)
    checklist = pd.read_csv(checklist_path)
    print("Validation:", validation["status"].value_counts().to_dict())
    print("Requirement checklist:", checklist["status"].value_counts().to_dict())
else:
    print("Notebook calculations completed; automated closeout runs immediately afterward.")
"""
        ),
        markdown(
            """
The final cell independently reads the machine-readable closeout. A completely
green validation/checklist confirms reproducibility and scope compliance; it
does not remove the scientific limitation created by sparse, provisional,
depth-seeded labels.
"""
        ),
    ]
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(notebook, NOTEBOOK)
    return NOTEBOOK


if __name__ == "__main__":
    print(build())
