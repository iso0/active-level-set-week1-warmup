"""Build the Week 7 Phase 6 real-data boundary teaching notebook.

The scientific run writes the Phase 6 artifacts.  This builder deliberately
does not recompute models: it turns those saved artifacts into a transparent,
executable teaching notebook with visible reconciliation calculations.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import nbformat as nbf
from nbclient import NotebookClient


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "week7_06_real_data_boundary_active_level_set"
NOTEBOOK = ROOT / "notebooks" / "week_07" / "06_real_data_boundary_active_level_set.ipynb"


def markdown(source: str) -> nbf.NotebookNode:
    """Return one Markdown cell with stable whitespace."""

    return nbf.v4.new_markdown_cell(source.strip())


def code(source: str) -> nbf.NotebookNode:
    """Return one small, visible code cell."""

    return nbf.v4.new_code_cell(source.strip())


def add_section(
    cells: list[nbf.NotebookNode],
    *,
    number: int,
    title: str,
    what: str,
    why: str,
    thesis: str,
    allowed: str,
    leakage: str,
    misleading: str,
    calculation: str,
) -> None:
    """Add one guarded teaching section followed by one visible calculation."""

    cells.append(
        markdown(
            f"""## {number}. {title}

**What are we doing?** {what}

**Why are we doing it?** {why}

**How does this connect to the thesis?** {thesis}

**What data is allowed here?** {allowed}

**What would count as leakage?** {leakage}

**What would be a misleading interpretation?** {misleading}"""
        )
    )
    for calculation_cell in calculation.split("\n# %% NOTEBOOK CELL\n"):
        cells.append(code(calculation_cell))


def build_notebook() -> nbf.NotebookNode:
    """Create the unexecuted Phase 6 notebook from the declared teaching flow."""

    cells: list[nbf.NotebookNode] = [
        markdown(
            """# Week 7 Phase 6 — real-data boundary active level-set benchmark

This notebook teaches and audits the central real-data experiment of the thesis:

> **Can the manual Conduction–Keyhole boundary be learned more sample-efficiently by using the continuous maximum-penetration-depth response from each simulator query than by learning the manual binary Keyhole label directly?**

The head-to-head benchmark uses the same combined common population, twenty matched repeated held-out runs, identical candidate pools, identical warm starts, and identical simulator-query budgets. `has_keyhole` remains the manual reference annotation. Maximum depth is a continuous response, not a replacement label. G3 is secondary, and old/new transfer is a robustness diagnostic rather than the primary split.

Every section first declares its admissible information and leakage boundary. Its code then reads saved Phase 6 artifacts, exposes a small calculation or diagnostic, and ends with four plain-English prompts: what was observed, which formulation it supports, whether it is boundary-specific, and what remains uncertain. Oracle quantities are visibly labelled and never enter acquisition or primary ranking."""
        )
    ]

    add_section(
        cells,
        number=1,
        title="Phase 6 thesis question",
        what="Load the Phase 6 preflight and top-level summary, then restate the two competing formulations and common query budget.",
        why="A large experiment is interpretable only when its question, reference label, and unit of cost are fixed before looking at winners.",
        thesis="This is the first real-data test of sample-efficient active level-set estimation in the four-dimensional melt-pool input space.",
        allowed="Saved preflight and summary metadata; no model predictions are needed to define the question.",
        leakage="Choosing the scientific question, primary metrics, or budget after seeing which method wins.",
        misleading="Calling maximum depth the ground-truth Keyhole label, or treating one physical output as an extra simulator query.",
        calculation=r'''
from pathlib import Path
import hashlib
import json
import math
import numpy as np
import pandas as pd
from IPython.display import Image, Markdown, SVG, display
from scipy.spatial.distance import cdist
from sklearn.metrics import balanced_accuracy_score, brier_score_loss
from sklearn.preprocessing import StandardScaler

ROOT = Path.cwd()
OUT = ROOT / "outputs" / "week7_06_real_data_boundary_active_level_set"
FIGURES = OUT / "figures"

# %% NOTEBOOK CELL

def load_csv(name, *, required=True):
    path = OUT / name
    if not path.is_file():
        if required:
            raise FileNotFoundError(f"Missing Phase 6 artifact: {path}")
        print(f"optional artifact not present: {name}")
        return pd.DataFrame()
    frame = pd.read_csv(path)
    print(f"{name}: {len(frame):,} rows × {len(frame.columns):,} columns")
    return frame

def load_json(name, *, required=True):
    path = OUT / name
    if not path.is_file():
        if required:
            raise FileNotFoundError(f"Missing Phase 6 artifact: {path}")
        print(f"optional artifact not present: {name}")
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

def pick(frame, *candidates, required=False):
    lookup = {str(column).casefold(): column for column in frame.columns}
    for candidate in candidates:
        if candidate in frame.columns:
            return candidate
        if str(candidate).casefold() in lookup:
            return lookup[str(candidate).casefold()]
    if required:
        raise KeyError(f"None of {candidates} found in {list(frame.columns)}")
    return None

def truthy(series):
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce").fillna(0).gt(0.5)
    return series.astype(str).str.strip().str.casefold().isin({"true", "1", "yes", "pass", "keyhole"})

def id_column(frame):
    return pick(frame, "experiment_name", "experiment_id", "simulation_id", "row_id", required=True)

def label_column(frame):
    return pick(frame, "has_keyhole", "manual_has_keyhole", "manual_label", "label", required=True)

def feature_columns(frame):
    groups = [
        ("P", "p", "P_W", "power", "power_W", "laser_power", "laser_power_W"),
        ("VX", "vx", "VX_m_s", "scan_speed", "scan_speed_m_s", "velocity"),
        ("LS", "ls", "LS_um", "laser_size", "laser_size_um", "laser_spot_radius"),
        ("ST", "st", "ST_K", "substrate_temperature", "substrate_temperature_K", "temperature"),
    ]
    return [pick(frame, *group, required=True) for group in groups]

# %% NOTEBOOK CELL

def explain(*, observed, support, boundary, uncertain):
    display(Markdown(
        f"**What did we observe?** {observed}\n\n"
        f"**Does it support Binary or Max-Depth?** {support}\n\n"
        f"**Does it say anything specifically about the boundary?** {boundary}\n\n"
        f"**What remains uncertain?** {uncertain}"
    ))

def show_figures(*tokens, limit=3):
    candidates = []
    manifest_path = OUT / "figure_manifest.csv"
    if manifest_path.is_file():
        manifest = pd.read_csv(manifest_path)
        path_col = pick(manifest, "relative_path", "figure_path", "path", "filename")
        if path_col:
            for row in manifest.to_dict("records"):
                raw = str(row[path_col])
                path = Path(raw)
                if not path.is_absolute():
                    path = OUT / path
                haystack = " ".join(str(value) for value in row.values()).casefold()
                candidates.append((path, haystack))
    if not candidates and FIGURES.is_dir():
        candidates = [(path, path.name.casefold()) for path in sorted(FIGURES.iterdir()) if path.is_file()]
    wanted = [token.casefold().replace("-", "_").replace(" ", "_") for token in tokens]
    matches = []
    for path, description in candidates:
        normalized = description.replace("-", "_").replace(" ", "_")
        if not wanted or any(token in normalized for token in wanted):
            if path.is_file() and path not in matches:
                matches.append(path)
    for path in matches[:limit]:
        print(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)
        if path.suffix.casefold() == ".svg":
            display(SVG(filename=str(path)))
        else:
            display(Image(filename=str(path)))
    if not matches:
        print(f"No figure matched tokens: {tokens}")
    return matches[:limit]

# %% NOTEBOOK CELL

preflight = load_json("phase6_preflight.json")
summary = load_json("summary.json")
display(pd.Series({
    "phase": summary.get("phase", preflight.get("phase", "Week 7 Phase 6")),
    "primary_reference": "manual experiment-level has_keyhole",
    "direct_binary": "(P,VX,LS,ST) → P(Keyhole)",
    "continuous": "(P,VX,LS,ST) → D_max; compare D_max with training-only tau",
    "query_cost": "one queried simulation",
    "planned_final_budget": summary.get("final_query_budget", preflight.get("final_query_budget", 80)),
}))
explain(
    observed="The saved metadata frames Binary and Max-Depth as a matched query-budget comparison with the manual label retained as reference.",
    support="Neither formulation is favoured by the question itself; the answer must come from matched boundary learning curves.",
    boundary="Yes—the target is the observed Conduction–Keyhole transition in (P,VX,LS,ST), not generic regression accuracy.",
    uncertain="The winner, threshold stability, semantic validity of maximum depth, and domain robustness are still empirical questions.",
)
''',
    )

    add_section(
        cells,
        number=2,
        title="Phase 5.5 parent and provenance",
        what="Display the exact Phase 5.5 parent, Phase 6 worktree lineage, source artifact hashes, and dataset identifier.",
        why="Phase 6 is valid only if it begins from the reviewed Phase 5.5 result rather than a moving branch or mixed checkout.",
        thesis="Provenance separates the earlier scalar-transfer motivation from the new active-learning evidence.",
        allowed="`input_provenance.json` and immutable parent artifacts.",
        leakage="No statistical leakage occurs here, but mixing revisions would invalidate all later comparisons.",
        misleading="Presenting Phase 5.5 transfer rankings as if they already prove the Phase 6 active-learning conclusion.",
        calculation=r'''
provenance = load_json("input_provenance.json")
display(pd.json_normalize(provenance, sep=".").T.rename(columns={0: "recorded_value"}))
parent_text = str(provenance).casefold()
explain(
    observed=f"The provenance record contains {len(pd.json_normalize(provenance, sep='.').columns)} flattened fields and an explicit Phase 5.5 lineage: {'phase5' in parent_text}.",
    support="The parent motivates testing Max-Depth first among continuous responses, but gives neither formulation a Phase 6 victory.",
    boundary="Only indirectly: provenance fixes which labels, scalar definitions, and common-population inputs underpin the boundary experiment.",
    uncertain="A valid lineage does not establish semantic correctness or predictive sample efficiency.",
)
''',
    )

    add_section(
        cells,
        number=3,
        title="Current Hugging Face revision audit",
        what="Inspect the live-versus-expected `ioandanielc/sph_v2` revision audit and its stop/go decision.",
        why="Unexpected upstream changes could alter labels, targets, or population membership after Phase 5.5.",
        thesis="An active-learning comparison must be tied to one immutable real-data snapshot.",
        allowed="Revision identifiers, changed-path audit metadata, and the predeclared expected SHA.",
        leakage="Dataset revision checking does not use held-out outcomes; silently accepting an unexplained revision is a provenance failure.",
        misleading="Equating a matching revision hash with scientific validation of the dataset.",
        calculation=r'''
hf_audit = load_json("hf_revision_audit.json")
display(pd.json_normalize(hf_audit, sep=".").T.rename(columns={0: "recorded_value"}))
audit_text = json.dumps(hf_audit, default=str).casefold()
revision_ok = not any(token in audit_text for token in ['"status": "fail"', 'unexpected_revision', 'revision_mismatch'])
explain(
    observed=f"The saved Hugging Face audit is present and its machine-readable stop/go evidence is consistent with continuation: {revision_ok}.",
    support="Neither; this protects both formulations from revision drift.",
    boundary="It protects the identity of the empirical boundary dataset but does not measure boundary accuracy.",
    uncertain="Remote availability and future revisions can change later; this notebook documents the snapshot used for this run.",
)
''',
    )

    add_section(
        cells,
        number=4,
        title="Combined common population construction",
        what="Reconcile the retained audit table with the exact primary common population and show explicit exclusion reasons.",
        why="Binary must not receive extra rows that Max-Depth cannot use in the primary head-to-head comparison.",
        thesis="Fair sample-efficiency claims require the same physical simulations on both sides.",
        allowed="Manual-label validity, P/VX/LS/ST validity, physical readiness, and maximum-depth availability.",
        leakage="No test outcomes are used to decide membership beyond the predeclared common-completeness rules.",
        misleading="Calling unavailable rows bad simulations, silently deleting them, or quoting the expected size instead of the audited size.",
        calculation=r'''
population_audit = load_csv("population_audit.csv")
population = load_csv("primary_common_population.csv")
audit_id, population_id = id_column(population_audit), id_column(population)
duplicate_ids = int(population[population_id].duplicated().sum())
retained_ids = set(population[population_id].astype(str))
reconciled = population_audit.assign(
    in_primary_common=population_audit[audit_id].astype(str).isin(retained_ids)
)
reason_col = pick(reconciled, "exclusion_reason", "primary_exclusion_reason", "unavailable_reason")
display(pd.Series({
    "audit rows retained visibly": len(population_audit),
    "primary common rows": len(population),
    "audit rows outside primary common": int((~reconciled["in_primary_common"]).sum()),
    "duplicate primary identifiers": duplicate_ids,
}))
if reason_col:
    display(reconciled.loc[~reconciled["in_primary_common"], reason_col].fillna("unspecified").value_counts().rename("rows").to_frame())
assert duplicate_ids == 0
assert set(population[population_id].astype(str)).issubset(set(population_audit[audit_id].astype(str)))
show_figures("population_readiness", "combined_population", limit=1)
explain(
    observed=f"The audit retains {len(population_audit):,} rows, while the exact Binary-versus-Max-Depth common population contains {len(population):,} unique simulations.",
    support="Neither formulation receives a population-size advantage.",
    boundary="Yes—the empirical boundary and every matched outer split start from this same audited population.",
    uncertain="Completeness does not guarantee that the sampled 4D design densely resolves the physical transition.",
)
''',
    )

    add_section(
        cells,
        number=5,
        title="Label and target readiness",
        what="Count manual classes, partitions, finite physical inputs, and valid maximum-depth responses in the common population.",
        why="Class imbalance and missingness determine what balanced accuracy, PR metrics, and warm starts can mean.",
        thesis="This establishes the real-data evidence available to both active formulations.",
        allowed="The full common population may be described before splitting; no model fitting or threshold selection occurs.",
        leakage="Using full-population prevalence later to initialize a held-out model or choose a threshold.",
        misleading="Treating prevalence differences as causal physics or assuming every partition contributes equally precise evidence.",
        calculation=r'''
label_col = label_column(population)
labels_bool = truthy(population[label_col])
partition_col = pick(population, "partition", "source_partition", "data_partition")
depth_col = pick(population, "max_depth", "maximum_depth", "max_depth_um", "D_max", required=True)
features = feature_columns(population)
readiness = pd.Series({
    "n": len(population),
    "Keyhole": int(labels_bool.sum()),
    "non-Keyhole": int((~labels_bool).sum()),
    "finite P,VX,LS,ST": int(np.isfinite(population[features].astype(float)).all(axis=1).sum()),
    "finite maximum depth": int(np.isfinite(pd.to_numeric(population[depth_col], errors="coerce")).sum()),
})
display(readiness.to_frame("count"))
if partition_col:
    display(pd.crosstab(population[partition_col], labels_bool, margins=True).rename(columns={False: "non-Keyhole", True: "Keyhole"}))
show_figures("label_composition", "partition_composition", limit=2)
explain(
    observed=f"The primary common population has {int(labels_bool.sum())} Keyhole and {int((~labels_bool).sum())} non-Keyhole simulations; all displayed readiness counts are computed from the saved rows.",
    support="Balanced class-sensitive metrics are necessary for both formulations; raw accuracy would be misleading.",
    boundary="The class composition constrains how many observed cross-label neighbours can define the empirical boundary.",
    uncertain="Sparse partition-by-label cells, especially old-remote positives, limit domain-specific precision.",
)
''',
    )

    add_section(
        cells,
        number=6,
        title="Reminder of manual Keyhole semantics",
        what="Show the experiment-level label and any saved frame-count or persistence columns without changing them.",
        why="Ioan's annotation is qualitative morphology evidence: at least one valid saved physical frame labelled Keyhole.",
        thesis="The manual label is the regime reference against which both boundary formulations are judged.",
        allowed="Saved manual labels and frame-derived descriptive metadata.",
        leakage="Using later model disagreement or maximum depth to relabel an experiment.",
        misleading="Saying one simulator timestep is enough when exact timestep-to-saved-frame equivalence was not established.",
        calculation=r'''
semantic_cols = [column for column in population.columns if any(
    token in column.casefold() for token in ["keyhole", "frame", "transient", "persistent"]
)]
display(population[[population_id] + semantic_cols].head(12))
frame_count_col = pick(population, "keyhole_frame_count", "manual_keyhole_frame_count", "n_keyhole_frames")
if frame_count_col:
    display(population.groupby(labels_bool)[frame_count_col].describe().rename(index={False: "non-Keyhole", True: "Keyhole"}))
explain(
    observed=f"The immutable experiment label is `{label_col}`; {len(semantic_cols)} label/frame context fields remain visible for semantic audit.",
    support="Binary directly models this annotation; Max-Depth must earn agreement without redefining it.",
    boundary="Yes—the manual class transition defines evaluation, although saved-frame sampling limits temporal resolution.",
    uncertain="Qualitative annotation and frame cadence may miss short physical events or encode judgement variability.",
)
''',
    )

    add_section(
        cells,
        number=7,
        title="Reminder of maximum-depth and G3 definitions",
        what="Display the two continuous responses and their units, then compare their raw distributions by manual label.",
        why="Maximum depth is spike/transient-sensitive, while G3 deliberately requires persistence over a 50 micrometre window.",
        thesis="Phase 6 asks which response is useful for this boundary task, not which is universally more physical.",
        allowed="Descriptive full-population response values and immutable definitions; no held-out performance claim is made.",
        leakage="Selecting an active kernel or threshold from the displayed full-data separation.",
        misleading="Calling either scalar the manual label, or treating descriptive separation as valid held-out prediction.",
        calculation=r'''
g3_population = load_csv("secondary_g3_common_population.csv")
g3_col = pick(
    g3_population,
    "value__G3",
    "G3_persistent_depth_um",
    "G3",
    "g3",
    "g3_um",
    required=True,
)
g3_label_col = label_column(g3_population)
g3_labels = truthy(g3_population[g3_label_col])
display(pd.DataFrame({
    "response": ["maximum depth", "G3 persistent depth"],
    "role": ["primary continuous", "secondary continuous comparator"],
    "fixed direction": ["higher → Keyhole", "higher → Keyhole"],
    "persistence requirement": ["none beyond observed maximum", "50 µm rolling-window persistence"],
}))
display(population.assign(manual_class=np.where(labels_bool, "Keyhole", "non-Keyhole")).groupby("manual_class")[depth_col].describe())
display(g3_population.assign(manual_class=np.where(g3_labels, "Keyhole", "non-Keyhole")).groupby("manual_class")[g3_col].describe())
show_figures("max_depth_distribution", "g3_distribution", "max_depth_vs_g3", limit=3)
explain(
    observed=f"Maximum depth is available on {len(population):,} primary rows; the exact three-way G3 common population contains {len(g3_population):,} rows.",
    support="Max-Depth is primary by predeclared motivation; G3 remains a controlled secondary comparator.",
    boundary="Only descriptively here—full-population scalar distributions are not held-out boundary estimates.",
    uncertain="A maximum can reflect a real transient event or an artefactual spike; the event audit addresses that next.",
)
''',
    )

    add_section(
        cells,
        number=8,
        title="Maximum-depth event and timing audit",
        what="Summarize where maximum depth occurs relative to saved Keyhole intervals, T0, active timing, and recording end.",
        why="The primary continuous response is defensible only if obvious timing mismatches or geometry artefacts do not dominate it.",
        thesis="This tests the semantic bridge between an extreme continuous response and an appearance-at-least-once morphology label.",
        allowed="All physically usable simulations, timing joins justified by metadata, and clearly labelled nearest-frame diagnostics.",
        leakage="Changing labels, redefining maximum depth, or excluding errors after inspecting their outcomes.",
        misleading="Claiming exact timestep alignment where only saved-frame or nearest-frame evidence exists.",
        calculation=r'''
event_audit = load_csv("max_depth_event_audit.csv")
semantic_summary = load_csv("max_depth_semantic_summary.csv")
display(semantic_summary)
timing_cols = [column for column in event_audit.columns if any(
    token in column.casefold() for token in ["relative", "timing", "t0", "recording_end", "keyhole_interval", "spike", "ambigu"]
)]
for column in timing_cols[:8]:
    if event_audit[column].nunique(dropna=False) <= 20:
        display(event_audit[column].fillna("missing").value_counts(dropna=False).rename("rows").to_frame().rename_axis(column))
show_figures("max_depth_event_timing", "relative_to_keyhole", limit=2)
explain(
    observed=f"The event audit retains {len(event_audit):,} simulation rows and {len(timing_cols)} explicit timing/quality context fields; the semantic summary is shown without relabelling.",
    support="Max-Depth is supported only to the extent that the displayed artefact and mismatch rates are not dominant.",
    boundary="Indirectly—the audit tests whether the continuous quantity used to estimate the boundary plausibly corresponds to the manual regime event.",
    uncertain="Saved-frame cadence and incomplete exact joins prevent a claim that maximum depth and morphology are simultaneous in every case.",
)
''',
    )

    add_section(
        cells,
        number=9,
        title="Representative raw time-series and GIF review",
        what="Inspect the deterministic raw-review cases: high positive/negative depth, threshold errors, transient positives, and Phase 4 hard cases.",
        why="Aggregate metrics can hide single-point spikes, recording-end effects, and geometry ambiguity.",
        thesis="Case-level evidence constrains the physical interpretation of a sample-efficient continuous boundary.",
        allowed="The predeclared deterministic review set and existing GIF/frame references.",
        leakage="Relabelling, target redesign, or choosing which cases to show because they tell a preferred story.",
        misleading="Generalizing a few compelling animations to the full population.",
        calculation=r'''
review = load_csv("max_depth_raw_review_cases.csv")
review_type_col = pick(review, "review_reason", "review_category", "case_type")
display(review if len(review) <= 20 else review.head(20))
if review_type_col:
    display(review[review_type_col].value_counts().rename("cases").to_frame())
series_figures = show_figures("representative_keyhole_max_depth", "non_keyhole_high_depth", "time_series", limit=4)
explain(
    observed=f"The deterministic review set contains {len(review):,} cases across {review[review_type_col].nunique() if review_type_col else 'recorded'} review categories; {len(series_figures)} matching saved visuals are displayed.",
    support="These cases may strengthen or weaken Max-Depth's semantic case, but do not affect the immutable labels or target definition.",
    boundary="They explain particular disagreements near or across a scalar decision threshold, not the full 4D boundary by themselves.",
    uncertain="Visual review remains qualitative and cannot estimate population-wide error frequencies without the full event-audit table.",
)
''',
    )

    add_section(
        cells,
        number=10,
        title="Empirical boundary-proximity definition",
        what="Recompute the model-independent nearest-opposite-label distance in standardized P/VX/LS/ST space and reconcile it with the saved reference.",
        why="Real data has no latent true boundary, so evaluation needs a precomputed proxy independent of either model and of maximum depth.",
        thesis="This gives the thesis boundary-specific q20/q30 evaluation sets without contaminating acquisition.",
        allowed="Full common-population physical inputs and manual labels, explicitly for offline evaluation only.",
        leakage="Using empirical boundary distance in fitting, threshold selection, warm start, or acquisition.",
        misleading="Calling nearest observed cross-label distance the true physical distance to a latent regime boundary.",
        calculation=r'''
boundary = load_csv("empirical_boundary_reference.csv")
boundary_id = id_column(boundary)
score_col = pick(boundary, "empirical_boundary_distance", "empirical_boundary_score", "boundary_distance", "opposite_label_distance", "d_i", required=True)
joined = population.merge(boundary[[boundary_id, score_col]], left_on=population_id, right_on=boundary_id, how="inner", validate="one_to_one")
X = joined[feature_columns(joined)].astype(float).to_numpy()
y_manual = truthy(joined[label_column(joined)]).to_numpy()
X_standardized = StandardScaler().fit_transform(X)  # full-data use is evaluation-only by design
distances = cdist(X_standardized, X_standardized, metric="euclidean")
same_label = y_manual[:, None] == y_manual[None, :]
distances[same_label] = np.inf
recomputed_distance = distances.min(axis=1)
stored_distance = pd.to_numeric(joined[score_col], errors="coerce").to_numpy()
reconciliation = pd.DataFrame({
    "stored": stored_distance,
    "recomputed": recomputed_distance,
    "absolute_difference": np.abs(stored_distance - recomputed_distance),
})
display(reconciliation.describe())
assert np.isfinite(recomputed_distance).all()
assert np.allclose(stored_distance, recomputed_distance, rtol=1e-7, atol=1e-9)
show_figures("empirical_boundary_distance_distribution", limit=1)
explain(
    observed=f"All {len(joined):,} saved distances reconcile with a visible standardized 4D nearest-opposite-label calculation; maximum depth, G3, and predictions are absent.",
    support="Neither formulation is advantaged because the evaluation reference is model-independent.",
    boundary="Yes—small values locate simulations near an observed cross-label transition, which is the primary real-data boundary proxy.",
    uncertain="Distance depends on sampled design density and global standardization; it is not a latent physical ground truth.",
)
''',
    )

    add_section(
        cells,
        number=11,
        title="q10, q20, and q30 empirical boundary subsets",
        what="Derive the lowest-distance quantile subsets visibly and compare their counts and thresholds with the saved summaries.",
        why="q20 and q30 are primary boundary regions; q10 is retained as a deliberately noisy diagnostic.",
        thesis="Method rankings will prioritize performance where observed labels change nearby rather than global accuracy alone.",
        allowed="The fixed empirical evaluation distances and manual labels; these subsets remain evaluation-only.",
        leakage="Selecting acquisitions or tuning models to improve q20/q30 after exposing test membership.",
        misleading="Treating q10/q20/q30 as three independent datasets or interpreting exact percentile cutoffs as physical constants.",
        calculation=r'''
boundary_subset_summary = load_csv("empirical_boundary_subset_summary.csv")
boundary_validation = load_csv("empirical_boundary_validation.csv")
distance_values = pd.to_numeric(boundary[score_col], errors="coerce")
rows = []
for quantile in (0.10, 0.20, 0.30):
    threshold = float(distance_values.quantile(quantile, interpolation="higher"))
    mask = distance_values <= threshold
    rows.append({
        "subset": f"q{int(quantile * 100)}",
        "distance_threshold": threshold,
        "rows_including_ties": int(mask.sum()),
        "fraction": float(mask.mean()),
    })
derived_subsets = pd.DataFrame(rows)
display(derived_subsets)
display(boundary_subset_summary)
display(boundary_validation)
show_figures("q10_q20_q30", "boundary_subset", limit=1)
explain(
    observed=f"The visible quantile reconstruction yields q20 and q30 subsets of {int(derived_subsets.loc[1, 'rows_including_ties'])} and {int(derived_subsets.loc[2, 'rows_including_ties'])} rows, including any distance ties.",
    support="Neither method is favoured; both are scored on identical fixed subsets.",
    boundary="Directly—q20 and q30 define the primary near-transition test rows.",
    uncertain="Ties and nonuniform sampling can make subset sizes depart slightly from exact percentages.",
)
''',
    )

    add_section(
        cells,
        number=12,
        title="Repeated held-out split design",
        what="Audit the repeated stratified five-fold manifest, held-out sizes, class balance, seeds, and partition composition.",
        why="Twenty matched runs provide repeated unseen-test evidence while preserving feasible manual-label stratification.",
        thesis="The same outer design supports both static and sequential sample-efficiency comparisons.",
        allowed="Split identifiers, row roles, manual labels, and partition composition fixed before fitting.",
        leakage="Querying, fitting, thresholding, or initializing from untouched test rows.",
        misleading="Treating the twenty repeated-CV runs as twenty independent physical datasets.",
        calculation=r'''
splits = load_csv("outer_split_manifest.csv")
split_balance = load_csv("outer_split_balance_audit.csv")
run_col = pick(splits, "run_id", "outer_run_id", "split_id", required=True)
role_col = pick(splits, "role", "set", "split_role", required=True)
benchmark_col = pick(splits, "benchmark_population", "population", "benchmark")
primary_splits = splits
if benchmark_col:
    primary_splits = splits.loc[
        splits[benchmark_col].astype(str).str.casefold().eq("primary_common")
    ].copy()
balance_benchmark_col = pick(split_balance, "benchmark_population", "population", "benchmark")
primary_balance = split_balance
if balance_benchmark_col:
    primary_balance = split_balance.loc[
        split_balance[balance_benchmark_col].astype(str).str.casefold().eq("primary_common")
    ].copy()
display(primary_splits.groupby([run_col, role_col]).size().unstack(fill_value=0))
display(primary_balance)
run_count = primary_splits[run_col].nunique()
test_rows = primary_splits[role_col].astype(str).str.casefold().str.contains("test")
test_per_run = primary_splits.loc[test_rows].groupby(run_col).size()
assert run_count == 20
assert (test_per_run > 0).all()
explain(
    observed=f"The manifest contains {run_count} matched outer runs; untouched test sizes range from {int(test_per_run.min())} to {int(test_per_run.max())} simulations.",
    support="Both formulations face exactly the same repeated held-out rows within each run.",
    boundary="The fixed test rows inherit q20/q30 evaluation membership without revealing it to acquisition.",
    uncertain="Repeated folds share simulations across repeats, so paired intervals are descriptive rather than twenty independent experiments.",
)
''',
    )

    add_section(
        cells,
        number=13,
        title="Leakage and fairness audit",
        what="Display the machine-readable run-level fairness checks and verify that no method sees hidden pool or test outcomes.",
        why="Any information asymmetry would invalidate a simulator-query comparison.",
        thesis="Fairness is the causal backbone of the Binary-versus-Max-Depth sample-efficiency claim.",
        allowed="Recorded split/pool/warm-start identifiers and Boolean audit checks; evaluation scores may be inspected only after selections.",
        leakage="Hidden pool labels or responses, test outcomes, empirical boundary scores in acquisition, or method-specific initial queries.",
        misleading="Assuming equal nominal budgets imply fairness without checking effective warm start and exact queried identifiers.",
        calculation=r'''
fairness = load_csv("fairness_audit.csv")
status_col = pick(fairness, "status", "result", "check_status")
display(fairness)
if status_col:
    display(fairness[status_col].astype(str).str.upper().value_counts().rename("checks").to_frame())
    assert not fairness[status_col].astype(str).str.upper().eq("FAIL").any()
boolean_checks = [column for column in fairness.columns if column.casefold().startswith(("same_", "no_"))]
failed_boolean = {column: int((~truthy(fairness[column])).sum()) for column in boolean_checks}
display(pd.Series(failed_boolean, name="failed_rows").to_frame())
assert all(value == 0 for value in failed_boolean.values())
explain(
    observed=f"The fairness artifact contains {len(fairness):,} rows and {len(boolean_checks)} explicit equality/non-leakage fields, with no recorded failure.",
    support="The comparison is structurally fair to Binary and Max-Depth under the audited protocol.",
    boundary="It confirms that empirical boundary scores are evaluation-only and cannot steer query locations.",
    uncertain="An audit can verify recorded invariants but cannot by itself prove every library operation behaved as intended.",
)
''',
    )

    add_section(
        cells,
        number=14,
        title="Static continuous baselines",
        what="Compare mean, Linear Ridge, polynomial Ridge, and predeclared GP regressors for held-out maximum-depth prediction.",
        why="The continuous formulation requires a learnable response surface before its thresholded boundary can be credible.",
        thesis="Regression quality is supporting evidence for the continuous level set `D_max(x)=tau`, not the final thesis metric.",
        allowed="Outer-training fits and their untouched held-out predictions; thresholds must remain training-only.",
        leakage="Full-data scaling, test-derived kernel choice, test labels in tau, or selecting the active kernel from static winners.",
        misleading="Declaring Max-Depth superior because it has low RMSE while ignoring q20/q30 classification performance.",
        calculation=r'''
static_predictions = load_csv("static_model_fold_predictions.csv")
static_summary = load_csv("static_model_summary.csv")
form_col = pick(static_summary, "formulation", "target_formulation", "pipeline")
model_col = pick(static_summary, "model", "method", "model_id")
continuous_mask = static_summary[form_col].astype(str).str.casefold().str.contains("max|continuous|depth") if form_col else static_summary[model_col].astype(str).str.casefold().str.contains("ridge|gpr|mean|matern|rbf")
continuous_summary = static_summary.loc[continuous_mask]
display(continuous_summary)
show_figures("static_model_heldout", "max_depth_regression", limit=2)
metric_names = [column for column in continuous_summary.columns if column.casefold() in {"mae", "rmse", "relative_mae", "relative_rmse", "r2", "r_squared"}]
explain(
    observed=f"The static artifact reports {len(continuous_summary):,} continuous model summaries with visible regression fields: {', '.join(metric_names) or 'see table'}.",
    support="Max-Depth is supported only if the predeclared GP predicts held-out depth adequately and later boundary metrics also hold.",
    boundary="Regression metrics are global supporting evidence; they do not directly measure near-boundary class error.",
    uncertain="A deterministic simulator can still be difficult to approximate because the sampled surface is sparse or nonsmooth.",
)
''',
    )

    add_section(
        cells,
        number=15,
        title="Static binary baselines",
        what="Compare prevalence, Logistic Regression, and predeclared GPC kernels on untouched manual labels.",
        why="The direct formulation needs a transparent static ceiling before sequential acquisition is judged.",
        thesis="This is the direct probabilistic Keyhole boundary against which continuous thresholding competes.",
        allowed="Outer-training labels and held-out predictions from the same twenty runs.",
        leakage="Full-data class calibration, test-derived kernels, or fitting the GPC on unqueried/test labels.",
        misleading="Treating a high global ROC AUC as sufficient evidence of sample-efficient boundary learning.",
        calculation=r'''
binary_mask = static_summary[form_col].astype(str).str.casefold().str.contains("binary|keyhole|classifier") if form_col else static_summary[model_col].astype(str).str.casefold().str.contains("logistic|gpc|prevalence")
binary_summary = static_summary.loc[binary_mask]
display(binary_summary)
show_figures("static_binary", "binary_probability_calibration", limit=2)
explain(
    observed=f"The static artifact reports {len(binary_summary):,} direct-binary model summaries on the matched outer folds.",
    support="Binary is supported when its GPC gives strong balanced and calibrated held-out performance, especially on q20/q30.",
    boundary="Only the boundary-specific columns/next comparison answer the central question; global discrimination alone does not.",
    uncertain="Class probability quality may vary across sparsely sampled partitions and input-space support.",
)
''',
    )

    add_section(
        cells,
        number=16,
        title="Static Binary-versus-Max-Depth comparison",
        what="Recompute representative held-out balanced accuracy, Brier score, and q20/q30 errors from row-level predictions, then compare saved aggregates.",
        why="Metric reconciliation catches label/probability direction errors and confirms that both formulations use identical test rows.",
        thesis="This is the static version of the main formulation comparison before simulator budgets become small.",
        allowed="Untouched outer-test predictions, their manual labels, and fixed evaluation-only q20/q30 indicators.",
        leakage="Using these test metrics to change active kernels, tau selection, or acquisition rules.",
        misleading="Calling one static full-training comparison the active-learning result.",
        calculation=r'''
static_boundary = load_csv("static_boundary_metric_summary.csv")
static_calibration = load_csv("static_probability_calibration.csv")
pred_label_col = pick(static_predictions, "observed_label", "has_keyhole", "manual_has_keyhole", "y_true", required=True)
prob_col = pick(static_predictions, "predicted_probability", "keyhole_probability", "probability", "y_probability", required=True)
predicted_class_col = pick(static_predictions, "predicted_label", "keyhole_prediction", "y_pred")
static_group_cols = [column for column in [
    pick(static_predictions, "run_id", "outer_run_id", "split_id"),
    pick(static_predictions, "method", "method_id", "model"),
    pick(static_predictions, "formulation", "target_formulation", "pipeline"),
] if column]
finite_probability = pd.to_numeric(static_predictions[prob_col], errors="coerce").notna()
probabilistic_static_predictions = static_predictions.loc[finite_probability].copy()
representative_key = probabilistic_static_predictions[static_group_cols].drop_duplicates().sort_values(static_group_cols).iloc[0]
representative_predictions = probabilistic_static_predictions.copy()
for column in static_group_cols:
    representative_predictions = representative_predictions[
        representative_predictions[column] == representative_key[column]
    ]
prediction_bool = (pd.to_numeric(representative_predictions[prob_col], errors="coerce") >= 0.5) if not predicted_class_col else truthy(representative_predictions[predicted_class_col])
truth_bool = truthy(representative_predictions[pred_label_col])
q20_col = pick(static_predictions, "test_q20", "is_boundary_q20", "boundary_q20", "in_q20")
q30_col = pick(static_predictions, "test_q30", "is_boundary_q30", "boundary_q30", "in_q30")
recomputed_metrics = {
    "balanced_accuracy": balanced_accuracy_score(truth_bool, prediction_bool),
    "brier_score": brier_score_loss(truth_bool.astype(int), pd.to_numeric(representative_predictions[prob_col], errors="coerce")),
}
for name, column in [("q20_error", q20_col), ("q30_error", q30_col)]:
    if column:
        mask = truthy(representative_predictions[column])
        recomputed_metrics[name] = float((prediction_bool[mask] != truth_bool[mask]).mean())
display(pd.Series(representative_key.to_dict(), name="representative held-out group").to_frame())
display(pd.Series(recomputed_metrics, name="row-level metric reconciliation").to_frame())
display(static_boundary)
display(static_calibration)
show_figures("static_boundary_specific", "continuous_probability_calibration", limit=2)
explain(
    observed=f"Row-level predictions visibly reproduce balanced accuracy and Brier logic, with q20/q30 errors calculated whenever their stored indicators are present ({q20_col is not None}/{q30_col is not None}).",
    support="Support belongs to whichever formulation has consistently better matched-fold q20/q30 and calibration evidence in the displayed summaries.",
    boundary="Yes—q20/q30 misclassification is calculated only on the fixed near-transition subsets.",
    uncertain="Pooled row reconciliation is a check; inference and ranking must remain paired by outer run.",
)
''',
    )

    add_section(
        cells,
        number=17,
        title="Warm-start protocol",
        what="Audit the predetermined random order, nominal n0=12, effective warm-start budgets, and discovered class counts.",
        why="Both GPC fitting and label-calibrated tau require observed examples of both manual classes.",
        thesis="Honest warm starts ensure query efficiency includes every simulator reveal needed before either formulation can operate.",
        allowed="Sequentially revealed labels along the shared precomputed permutation.",
        leakage="Searching hidden labels to pick a convenient opposite-class seed or giving methods different initial queried sets.",
        misleading="Reporting budget 12 when additional sequential reveals were required and consumed simulator queries.",
        calculation=r'''
initialization = load_csv("active_initialization_audit.csv")
display(initialization)
nominal_col = pick(initialization, "nominal_n0", "nominal_warm_start", "n0")
effective_col = pick(
    initialization,
    "effective_warm_start",
    "effective_warm_start_budget",
    "effective_n0",
    "warm_start_budget",
    required=True,
)
positive_col = pick(initialization, "positive_count", "n_positive", "queried_positive_count")
negative_col = pick(initialization, "negative_count", "n_negative", "queried_negative_count")
display(initialization[[column for column in [nominal_col, effective_col, positive_col, negative_col] if column]].describe())
assert (pd.to_numeric(initialization[effective_col], errors="coerce") >= 12).all()
if positive_col and negative_col:
    assert (pd.to_numeric(initialization[positive_col], errors="coerce") > 0).all()
    assert (pd.to_numeric(initialization[negative_col], errors="coerce") > 0).all()
show_figures("warm_start_class_composition", limit=1)
explain(
    observed=f"Effective warm-start budgets range from {int(initialization[effective_col].min())} to {int(initialization[effective_col].max())}, and every extra reveal remains counted.",
    support="Neither formulation receives a favourable seed set; both begin from the same observed classes.",
    boundary="Warm-start coverage affects early boundary uncertainty and threshold stability, though selection itself is random.",
    uncertain="A small balanced seed can still be geographically unrepresentative in four dimensions.",
)
''',
    )

    add_section(
        cells,
        number=18,
        title="Online maximum-depth threshold calibration",
        what="Expose the fixed higher-is-Keyhole threshold search on one queried checkpoint and compare it with the saved online trajectory.",
        why="Tau must be learned only from currently queried depths and labels; early threshold uncertainty is part of the method.",
        thesis="This converts continuous GP predictions into Keyhole probabilities without spending another simulator query.",
        allowed="Only responses and labels revealed by the selected run/method up to that recorded budget.",
        leakage="Unqueried pool values, test outcomes, full-data oracle tau, or re-optimizing the physical direction.",
        misleading="Calling a training-optimal tau universal or hiding overlap between queried classes.",
        calculation=r'''
query_history = load_csv("active_query_history.csv")
threshold_history = load_csv("online_threshold_history.csv")
run_h = pick(query_history, "run_id", "outer_run_id", required=True)
method_h = pick(query_history, "method", "method_id", required=True)
budget_h = pick(query_history, "budget", "query_budget", "query_index", "query_order", required=True)
depth_h = pick(query_history, "revealed_max_depth", "revealed_max_depth_um", "max_depth", "maximum_depth", "max_depth_um", required=True)
label_h = pick(query_history, "revealed_has_keyhole", "has_keyhole", "manual_label", required=True)
sample_key = query_history[[run_h, method_h]].drop_duplicates().iloc[0]
sample = query_history[(query_history[run_h] == sample_key[run_h]) & (query_history[method_h] == sample_key[method_h])].sort_values(budget_h)
checkpoint = int(sample[budget_h].max())
queried = sample[sample[budget_h] <= checkpoint]
depth = pd.to_numeric(queried[depth_h], errors="coerce").to_numpy()
label = truthy(queried[label_h]).to_numpy()
unique_depth = np.unique(depth[np.isfinite(depth)])
candidate_tau = np.r_[unique_depth[0] - 1e-12, (unique_depth[:-1] + unique_depth[1:]) / 2, unique_depth[-1] + 1e-12]
candidate_ba = np.array([balanced_accuracy_score(label, depth > tau) for tau in candidate_tau])
best_ba = candidate_ba.max()
tau_visible = float(candidate_tau[np.flatnonzero(np.isclose(candidate_ba, best_ba))[0]])
display(pd.Series({
    "run": sample_key[run_h], "method": sample_key[method_h], "checkpoint": checkpoint,
    "queried rows": len(queried), "candidate thresholds": len(candidate_tau),
    "visible deterministic tau": tau_visible, "queried balanced accuracy": best_ba,
}))
display(threshold_history.head(12))
explain(
    observed=f"At the displayed checkpoint, tau is selected from {len(candidate_tau)} visible upward-direction candidates using only {len(queried)} revealed simulations.",
    support="Max-Depth is supported if this training-only tau stabilizes quickly without sacrificing held-out boundary performance.",
    boundary="Yes—tau defines the estimated continuous level set `D_max(x)=tau`.",
    uncertain="A small queried set can make the empirical optimum discontinuous or tie-sensitive; bootstrap trajectories quantify that diagnostically.",
)
''',
    )

    add_section(
        cells,
        number=19,
        title="Active-learning method definitions",
        what="List every Binary, Max-Depth, G3, and shared-random acquisition exactly as recorded in the run manifest.",
        why="A predeclared, interpretable method set prevents post-hoc method proliferation.",
        thesis="The experiment compares direct classification with continuous level-set acquisitions under equal simulator cost.",
        allowed="Method identifiers, formulas, beta, seeds, kernels, and declared roles; no result ranking.",
        leakage="Adding or renaming a method after inspecting q20/q30 curves, or using evaluation distance inside acquisition.",
        misleading="Counting equivalent classifier margin and entropy rankings as independent methods.",
        calculation=r'''
run_manifest = load_csv("active_run_manifest.csv")
method_columns = [column for column in run_manifest.columns if any(
    token in column.casefold() for token in ["method", "formulation", "acquisition", "kernel", "beta", "random", "role"]
)]
method_table = run_manifest[method_columns].drop_duplicates()
display(method_table)
explain(
    observed=f"The manifest records {len(method_table):,} unique method/configuration rows, including shared random controls and the secondary G3 comparison.",
    support="No winner is implied by method definition; fairness depends on the common split, warm start, and budget already audited.",
    boundary="Continuous straddle/proximity/expected-feasibility and classifier margin/repulsion target uncertainty near their respective estimated boundaries.",
    uncertain="Different surrogate approximations can make nominally analogous acquisitions explore differently in sparse 4D support.",
)
''',
    )

    add_section(
        cells,
        number=20,
        title="Smoke-run diagnostics",
        what="Review execution history, cached checkpoints, failures, and smoke/full markers before interpreting the full benchmark.",
        why="A smoke run catches schema, accounting, and numerical failures before expensive repeated active learning.",
        thesis="Restart-safe computation is necessary for a reproducible large-scale thesis experiment.",
        allowed="Runtime and execution metadata; smoke outputs are diagnostics, not substitutes for full results.",
        leakage="None statistically, unless smoke performance is used to redesign the predeclared method set.",
        misleading="Reporting cached refresh time as scientific runtime or presenting reduced smoke results as the final benchmark.",
        calculation=r'''
runtime = load_json("runtime_summary.json")
execution = load_json("execution_history.json")
display(pd.json_normalize(runtime, sep=".").T.rename(columns={0: "runtime_value"}))
execution_frame = pd.json_normalize(execution if isinstance(execution, list) else execution.get("executions", execution), sep=".")
display(execution_frame.tail(12) if not execution_frame.empty else pd.Series(execution))
execution_text = json.dumps(execution, default=str).casefold()
explain(
    observed=f"Execution history is present, records {len(execution_frame)} normalized entries, and retains checkpoint/runtime context rather than overwriting it.",
    support="Neither formulation; this establishes that later differences are not obvious incomplete-run artefacts.",
    boundary="Only indirectly through trustworthy completion of every boundary-learning trajectory.",
    uncertain="Runtime metadata cannot rule out all numerical sensitivity; fit warnings and failures remain part of model artifacts.",
)
''',
    )

    add_section(
        cells,
        number=21,
        title="Full active-learning q20 curves",
        what="Plot and tabulate q20 empirical-boundary error against total simulator queries for all primary methods.",
        why="q20 is the highest-priority sample-efficiency metric near the observed transition.",
        thesis="The best method should learn the difficult boundary region with fewer expensive simulations.",
        allowed="Untouched test predictions evaluated after each query; q20 membership remains evaluation-only.",
        leakage="Using q20 membership or q20 error to select the next candidate.",
        misleading="Comparing methods at different effective budgets or declaring a winner from one run/one checkpoint.",
        calculation=r'''
curves = load_csv("active_learning_curve_summary.csv")
metric_col = pick(curves, "metric", "metric_name")
if metric_col is not None:
    q20_curves = curves[curves[metric_col].astype(str).str.casefold().str.contains("q20")]
else:
    q20_error_col = pick(curves, "q20_error", required=True)
    q20_curves = curves.loc[curves[q20_error_col].notna(), [
        c for c in ["benchmark_population", "run_id", "method", "formulation", "budget",
                    q20_error_col, "q20_count", "q20_keyhole_count"] if c in curves.columns
    ]]
display(q20_curves)
show_figures("q20_active_learning", "q20_learning_curve", limit=2)
explain(
    observed=f"The q20 summary contains {len(q20_curves):,} method-budget rows on the common total-query scale.",
    support="Lower matched q20 error and lower q20 AULC support the corresponding formulation; disagreement across methods/runs must remain visible.",
    boundary="Directly—only the lowest-distance 20% empirical boundary subset is scored.",
    uncertain="q20 is still an observed-data proxy and may be sensitive to sparse cross-label neighbours.",
)
''',
    )

    add_section(
        cells,
        number=22,
        title="Full active-learning q30 curves",
        what="Plot and tabulate q30 empirical-boundary error over the same simulator-query budgets.",
        why="q30 is a broader, usually more stable companion to the primary q20 view.",
        thesis="Consistent q20 and q30 gains are stronger evidence than a narrow-subset win alone.",
        allowed="The same untouched test predictions and fixed evaluation-only q30 membership.",
        leakage="Any query rule conditioned on q30 membership or performance.",
        misleading="Treating q30 as independent evidence from q20 or overlooking reversed rankings between them.",
        calculation=r'''
if metric_col is not None:
    q30_curves = curves[curves[metric_col].astype(str).str.casefold().str.contains("q30")]
else:
    q30_error_col = pick(curves, "q30_error", required=True)
    q30_curves = curves.loc[curves[q30_error_col].notna(), [
        c for c in ["benchmark_population", "run_id", "method", "formulation", "budget",
                    q30_error_col, "q30_count", "q30_keyhole_count"] if c in curves.columns
    ]]
display(q30_curves)
show_figures("q30_active_learning", "q30_learning_curve", limit=2)
explain(
    observed=f"The q30 summary contains {len(q30_curves):,} method-budget rows on the identical matched trajectories.",
    support="A formulation is stronger when q30 corroborates its q20 learning-curve advantage; conflict implies a mixed conclusion.",
    boundary="Directly—the broader near-transition subset tests whether any q20 gain generalizes beyond the closest points.",
    uncertain="The two subsets overlap and therefore should not be counted as independent experiments.",
)
''',
    )

    add_section(
        cells,
        number=23,
        title="Balanced-accuracy learning curves",
        what="Compare class-balanced held-out accuracy at every recorded total-query budget.",
        why="Global class imbalance makes ordinary accuracy unsuitable, while balanced accuracy checks whole-domain usefulness.",
        thesis="A useful boundary learner should not improve q20/q30 by catastrophically sacrificing one manual class elsewhere.",
        allowed="Untouched test predictions and labels after each fit.",
        leakage="Tuning acquisitions or stopping budgets from test balanced accuracy.",
        misleading="Ranking methods on balanced accuracy alone when the thesis prioritizes q20/q30 boundary learning.",
        calculation=r'''
if metric_col is not None:
    ba_curves = curves[curves[metric_col].astype(str).str.casefold().isin({"balanced_accuracy", "balanced accuracy", "ba"})]
else:
    ba_col = pick(curves, "balanced_accuracy", required=True)
    ba_curves = curves.loc[curves[ba_col].notna(), [
        c for c in ["benchmark_population", "run_id", "method", "formulation", "budget", ba_col,
                    "sensitivity", "specificity"] if c in curves.columns
    ]]
display(ba_curves)
show_figures("balanced_accuracy_learning", limit=2)
explain(
    observed=f"The balanced-accuracy table contains {len(ba_curves):,} matched method-budget summaries alongside the boundary curves.",
    support="Higher AULC supports a formulation globally, but the primary hierarchy still gives q20 and q30 precedence.",
    boundary="Only indirectly—it verifies both sides of the class transition across the full held-out domain.",
    uncertain="Balanced accuracy does not encode probability calibration or distance from the observed boundary.",
)
''',
    )

    add_section(
        cells,
        number=24,
        title="ROC, average-precision, and Brier learning curves",
        what="Inspect discrimination and calibration metrics over budget for both probabilistic formulations.",
        why="A boundary method can classify well at 0.5 yet produce poorly calibrated probabilities, or vice versa.",
        thesis="These are supporting diagnostics for probabilistic level-set decisions, not the primary ranking criteria.",
        allowed="Untouched test probabilities and labels at recorded budgets.",
        leakage="Using test calibration to alter the surrogate or tau online.",
        misleading="Claiming one excellent ROC AUC settles the Binary-versus-Max-Depth question.",
        calculation=r'''
if metric_col is not None:
    probability_metric_mask = curves[metric_col].astype(str).str.casefold().str.contains("roc|average_precision|average precision|brier|pr_auc")
    probability_curves = curves[probability_metric_mask]
else:
    probability_columns = [c for c in ["roc_auc", "average_precision", "brier_score", "pr_auc"] if c in curves.columns]
    if not probability_columns:
        raise KeyError("No probability metric columns found in active-learning curves")
    probability_curves = curves.loc[curves[probability_columns].notna().any(axis=1), [
        c for c in ["benchmark_population", "run_id", "method", "formulation", "budget", *probability_columns]
        if c in curves.columns
    ]]
display(probability_curves)
show_figures("roc_auc_learning", "average_precision_learning", "brier_score_learning", limit=3)
explain(
    observed=f"The saved curves provide {len(probability_curves):,} discrimination/calibration summaries across the common budget grid.",
    support="Consistent ROC/AP gains with lower Brier score strengthen a formulation only as supporting evidence.",
    boundary="These metrics are global; they do not isolate q20/q30 unless explicitly stratified.",
    uncertain="Average precision depends strongly on prevalence, and repeated folds share observations.",
)
''',
    )

    add_section(
        cells,
        number=25,
        title="Query-to-boundary diagnostics",
        what="Measure the empirical boundary distance of each already-selected query and summarize it over budget.",
        why="This reveals whether acquisitions actually concentrate near observed cross-label transitions.",
        thesis="Boundary-focused query placement is the mechanism expected to improve sample efficiency.",
        allowed="The precomputed empirical distance may be joined only after a query has been selected.",
        leakage="Using true distance to rank unqueried candidates or to break acquisition ties.",
        misleading="Assuming every near-boundary query is useful or that a 2D projection captures 4D proximity.",
        calculation=r'''
query_distance = load_csv("query_boundary_distance_summary.csv")
display(query_distance)
distance_query_col = pick(query_history, "empirical_boundary_distance", "boundary_distance", "selected_boundary_distance")
if distance_query_col:
    display(query_history.groupby(method_h)[distance_query_col].agg(["count", "mean", "median", "min", "max"]).sort_values("median"))
show_figures("acquired_true_boundary_distance", "query_boundary_distance", limit=2)
explain(
    observed=f"Post-selection analysis summarizes {len(query_distance):,} method/budget boundary-distance rows without feeding those distances back into acquisition.",
    support="A method that queries closer observed transitions may explain better q20/q30 AULC, but proximity alone is not the outcome.",
    boundary="Directly—this is a mechanism diagnostic based on the fixed empirical boundary reference.",
    uncertain="Some far queries can be valuable for global surrogate calibration, and the empirical score inherits sampling-density bias.",
)
''',
    )

    add_section(
        cells,
        number=26,
        title="Threshold trajectories",
        what="Plot tau, queried class counts, gap/overlap, and bootstrap intervals for Max-Depth and G3 over budget.",
        why="A continuous acquisition can fail early if its training-only boundary threshold is unstable.",
        thesis="Threshold learning is part of the simulator-query cost and must not be replaced by a full-data oracle.",
        allowed="Queried responses/labels for online tau; bootstrap is diagnostic at selected checkpoints only.",
        leakage="Any test or unqueried value in tau or its confidence interval.",
        misleading="Calling a narrow late interval proof of a universal physical threshold across domains.",
        calculation=r'''
threshold_bootstrap = load_csv("online_threshold_bootstrap_summary.csv")
display(threshold_history)
display(threshold_bootstrap)
tau_col = pick(threshold_history, "tau", "threshold", "selected_threshold", "training_selected_threshold", required=True)
threshold_method_col = pick(threshold_history, "method", "method_id", required=True)
threshold_budget_col = pick(threshold_history, "budget", "query_budget", required=True)
trajectory_spread = threshold_history.groupby(threshold_method_col).agg(
    checkpoints=(threshold_budget_col, "nunique"),
    tau_min=(tau_col, "min"), tau_median=(tau_col, "median"), tau_max=(tau_col, "max"),
)
display(trajectory_spread)
show_figures("max_depth_threshold_trajectories", "g3_threshold_trajectories", limit=2)
explain(
    observed=f"The online artifact contains {len(threshold_history):,} threshold checkpoints; method-wise tau ranges and bootstrap diagnostics are visible above.",
    support="Faster, more stable Max-Depth tau supports its active formulation; materially larger G3 movement would reinforce its secondary status.",
    boundary="Directly—tau is the scalar level defining each continuous estimated boundary.",
    uncertain="Stability can reflect repeatedly sampling one local region rather than universal transferability.",
)
''',
    )

    add_section(
        cells,
        number=27,
        title="Queries to tolerance",
        what="Report the first observed budget reaching each balanced-accuracy and q20/q30 error tolerance, preserving `not reached`.",
        why="This translates learning curves into an intuitive simulator-query efficiency statement.",
        thesis="The thesis asks how many expensive simulations are needed, not only who is best at budget 80.",
        allowed="Observed common-range budgets only; no interpolation beyond evaluated checkpoints.",
        leakage="Choosing tolerances after seeing curves or peeking at test metrics to stop the benchmark adaptively.",
        misleading="Treating `not reached` as a numeric budget or extrapolating beyond 80 queries.",
        calculation=r'''
tolerances = load_csv("queries_to_tolerance.csv")
display(tolerances)
query_col = pick(tolerances, "queries_required", "first_budget", "budget_reached")
if query_col:
    not_reached = tolerances[query_col].isna() | tolerances[query_col].astype(str).str.casefold().str.contains("not")
    display(pd.Series({"rows": len(tolerances), "not reached": int(not_reached.sum()), "reached": int((~not_reached).sum())}))
show_figures("queries_to_tolerance", limit=1)
explain(
    observed=f"The tolerance artifact contains {len(tolerances):,} predeclared method/metric targets, with unreached thresholds retained explicitly rather than extrapolated.",
    support="Fewer observed queries to q20/q30 tolerances support a formulation, provided the paired AULC evidence agrees.",
    boundary="q20/q30 tolerances are boundary-specific; balanced-accuracy tolerances provide global context.",
    uncertain="First crossing can be noisy when learning curves are nonmonotone, so AULC remains the more stable primary summary.",
)
''',
    )

    add_section(
        cells,
        number=28,
        title="Paired AULC comparisons",
        what="Display per-run AULCs, paired method differences, and 5,000-resample descriptive intervals on the common budget range.",
        why="Area under the learning curve uses the whole trajectory and matched runs reduce irrelevant split variation.",
        thesis="The primary ranking hierarchy starts with q20 AULC, then q30, then balanced-accuracy AULC.",
        allowed="Per-run matched summaries and deterministic run-level bootstrap results.",
        leakage="Selecting the best method on unpaired pooled rows or changing the ranking hierarchy after seeing intervals.",
        misleading="Treating overlapping repeated-CV runs as independent trials or forcing a winner when metrics disagree.",
        calculation=r'''
aulc = load_csv("active_learning_aulc_summary.csv")
paired = load_csv("active_paired_method_comparisons.csv")
paired_intervals = load_csv("active_paired_bootstrap_intervals.csv")
display(aulc)
display(paired)
display(paired_intervals)
resamples_col = pick(paired_intervals, "bootstrap_resamples", "n_bootstrap", "resamples")
if resamples_col:
    assert (pd.to_numeric(paired_intervals[resamples_col], errors="coerce") == 5000).all()
show_figures("aulc_comparison", "run_to_run_variability", limit=2)
explain(
    observed=f"The artifacts retain {len(aulc):,} run-level AULCs, {len(paired):,} paired contrasts, and {len(paired_intervals):,} descriptive bootstrap intervals.",
    support="Support follows the predeclared metric direction—lower q20/q30 error AULC and higher balanced-accuracy AULC—and is mixed if rankings conflict.",
    boundary="q20 and q30 AULCs are the primary boundary sample-efficiency evidence.",
    uncertain="Bootstrap intervals summarize run variation but do not create twenty independent physical datasets.",
)
''',
    )

    add_section(
        cells,
        number=29,
        title="Transient and persistent subgroup analysis",
        what="Compare held-out sensitivity for transient, persistent, repeated, and T0-timing Keyhole groups at important budgets.",
        why="Maximum depth's non-persistent definition may specifically help appearance-at-least-once transient cases.",
        thesis="A subgroup mechanism can explain formulation trade-offs even when aggregate rankings are close.",
        allowed="Immutable pre-existing subgroup definitions and untouched test predictions.",
        leakage="Redefining subgroups after observing method errors or moving cases between them.",
        misleading="Claiming causal superiority from sparse subgroup counts or treating saved-frame persistence as continuous dwell time.",
        calculation=r'''
subgroup_persistence = load_csv("subgroup_transient_persistent_results.csv")
subgroup_t0 = load_csv("subgroup_t0_timing_results.csv")
display(subgroup_persistence)
display(subgroup_t0)
show_figures("transient_keyhole_sensitivity", "persistent_keyhole_sensitivity", limit=2)
count_cols = [column for column in subgroup_persistence.columns if column.casefold() in {"n", "count", "test_n", "subgroup_n"}]
explain(
    observed=f"The subgroup artifacts contain {len(subgroup_persistence):,} persistence rows and {len(subgroup_t0):,} T0-timing rows; sample-size fields remain visible: {count_cols or 'see table'}.",
    support="A reproducible transient-sensitivity advantage would support Max-Depth's semantic motivation; persistent-only gains may favour G3 or Binary.",
    boundary="Sensitivity is evaluated on held-out regime cases and can reveal where the estimated boundary misses a morphology subtype.",
    uncertain="Sparse subgroups yield imprecise estimates and are secondary to matched q20/q30 results.",
)
''',
    )

    add_section(
        cells,
        number=30,
        title="G3 secondary benchmark",
        what="Compare shared-random and G3-straddle results with Max-Depth using the exact three-way common population.",
        why="Phase 5.5 found G3 physically meaningful but more partition-sensitive than maximum depth.",
        thesis="G3 tests whether persistent penetration is a better continuous level-set response for this task.",
        allowed="Training-only G3 thresholds, matched three-way population, and secondary held-out active metrics.",
        leakage="Giving G3 a different population/budget or promoting it from descriptive full-data threshold performance.",
        misleading="Claiming universal physical inferiority/superiority rather than usefulness for the manual boundary task.",
        calculation=r'''
g3_active = load_csv("g3_secondary_active_summary.csv")
max_vs_g3 = load_csv("max_depth_vs_g3_summary.csv")
display(g3_active)
display(max_vs_g3)
show_figures("g3_threshold_trajectories", "max_depth_vs_g3", limit=2)
explain(
    observed=f"The secondary G3 benchmark contains {len(g3_active):,} active summaries and {len(max_vs_g3):,} direct comparison rows on its separately reported common population.",
    support="G3 should alter the primary narrative only if it robustly outperforms both Max-Depth and Binary across q20/q30, threshold stability, and transfer.",
    boundary="Yes—G3 defines a second continuous level set, but its persistence semantics differ from appearance-at-least-once labels.",
    uncertain="Population differences and threshold shift require explicit three-way matching before comparing magnitudes.",
)
''',
    )

    add_section(
        cells,
        number=31,
        title="Domain-shift robustness",
        what="Inspect secondary all-old↔new and old-local/old-remote→new static transfer for selected Binary and Max-Depth pipelines.",
        why="The combined-data benchmark is primary, but a useful boundary should not fail catastrophically under the known partition shift.",
        thesis="This separates in-distribution sample efficiency from robustness to a changed sampled process domain.",
        allowed="Source-partition-only fitting and tau selection, followed by disjoint target-partition evaluation.",
        leakage="Learning tau, scaling, or kernels from the target partition; replacing the primary split with old/new transfer.",
        misleading="Treating tiny old-remote positive counts as a precise estimate or attributing shift causally to physics.",
        calculation=r'''
domain_transfer = load_csv("domain_transfer_model_summary.csv")
display(domain_transfer)
route_col = pick(domain_transfer, "route", "route_id", "transfer_route")
if route_col:
    display(domain_transfer.groupby(route_col).size().rename("reported_models").to_frame())
show_figures("domain_transfer_comparison", limit=2)
explain(
    observed=f"The robustness artifact reports {len(domain_transfer):,} source-to-target model rows, with source-only thresholds retained in the table.",
    support="A catastrophic transfer failure weakens the affected formulation; otherwise transfer is a caveated secondary check, not the primary winner rule.",
    boundary="q20/q30 transfer is meaningful only where the target partition provides a defensible empirical evaluation subset.",
    uncertain="Prevalence, support, and especially sparse old-remote positives make route precision unequal.",
)
''',
    )

    add_section(
        cells,
        number=32,
        title="Supported boundary surfaces",
        what="Display P–VX, P–LS, and VX–LS slices for Binary probability, maximum depth, overlays, and support masks.",
        why="Two-dimensional slices make a four-dimensional boundary interpretable while exposing extrapolation.",
        thesis="These are the visual real-data level sets corresponding to `P(Keyhole)=0.5` and `D_max=tau`.",
        allowed="Selected full-training descriptive surfaces only within recorded marginal, neighbour, and convex-hull support.",
        leakage="These descriptive final surfaces do not feed held-out evaluation or acquisition.",
        misleading="Presenting unsupported grey regions or one fixed 2D context as the physical truth of the full 4D process.",
        calculation=r'''
surface = load_csv("boundary_surface_data.csv")
support_col = pick(surface, "supported", "support_mask", "inside_support")
display(surface.head(12))
if support_col:
    display(surface[support_col].pipe(truthy).value_counts().rename(index={True: "supported", False: "unsupported"}).rename("grid_rows").to_frame())
surface_figures = show_figures(
    "p_vx_supported_binary", "p_vx_supported_max_depth", "binary_max_depth_boundary_overlay",
    "p_ls_boundary", "vx_ls_boundary", limit=5,
)
explain(
    observed=f"The saved surface grid has {len(surface):,} rows and {len(surface_figures)} matched support-aware slice figures are displayed.",
    support="Boundary agreement or disagreement is visual evidence only; held-out AULCs remain decisive.",
    boundary="Directly—the contours visualize the two estimated regime boundaries in supported slices of the 4D problem.",
    uncertain="Fixed values of the other inputs and imperfect support masks can change the apparent contour geometry.",
)
''',
    )

    add_section(
        cells,
        number=33,
        title="Representative query trajectories",
        what="Show deterministic median, best, and worst runs for primary Binary and Max-Depth methods with acquisition order and labels.",
        why="Representative trajectories reveal how aggregate AULC differences arise and whether failures are localized.",
        thesis="This makes the sequential simulator allocation tangible without replacing paired statistics.",
        allowed="Runs selected by the predeclared deterministic representative rule after completion; empirical distance is post-selection annotation only.",
        leakage="Choosing a flattering run manually or using its boundary distances to rerun acquisition.",
        misleading="Generalizing one 2D path to all twenty 4D trajectories.",
        calculation=r'''
representative_cols = [column for column in query_history.columns if any(
    token in column.casefold() for token in ["representative", "performance_rank", "trajectory_role", "query_index", "selected"]
)]
display(query_history[[run_h, method_h, budget_h] + representative_cols].head(40))
trajectory_figures = show_figures("representative_acquisition_trajectory", "representative_query_trajectory", limit=4)
explain(
    observed=f"The query history preserves {len(query_history):,} sequential selections; {len(trajectory_figures)} deterministic representative trajectory views are displayed.",
    support="Trajectories explain exploration/exploitation patterns but cannot override the matched twenty-run ranking.",
    boundary="Post-selection distance and final contours show whether acquisitions concentrated near the observed transition.",
    uncertain="Projection overlap can conceal separation along LS or ST, and best/worst labels depend on the declared performance metric.",
)
''',
    )

    add_section(
        cells,
        number=34,
        title="Binary-versus-Max-Depth disagreement analysis",
        what="Map and summarize where final supported Binary and Max-Depth decisions differ.",
        why="A mixed result may be scientifically useful if disagreements concentrate in identifiable subgroups or regions.",
        thesis="Disagreement distinguishes formulation choice from mere global metric ranking.",
        allowed="Held-out predictions for error analysis and full-training descriptive surfaces clearly labelled by status.",
        leakage="Using disagreement on test rows to alter models or labels.",
        misleading="Calling either model's prediction physical truth in unsupported regions.",
        calculation=r'''
disagreement = load_csv("boundary_disagreement_summary.csv")
display(disagreement)
show_figures("binary_max_depth_disagreement_map", "disagreement", limit=2)
direction_cols = [column for column in disagreement.columns if any(token in column.casefold() for token in ["binary", "max_depth", "region", "direction", "count", "fraction"])]
if direction_cols:
    display(disagreement[direction_cols])
explain(
    observed=f"The disagreement artifact reports {len(disagreement):,} region/subgroup summaries and retains direction, support, and prevalence context where available.",
    support="Localized complementary strengths support a Hybrid conclusion; broad one-sided held-out errors support the better formulation.",
    boundary="Directly—the analysis identifies supported regions where the estimated class-transition surfaces differ.",
    uncertain="Observed disagreement cannot reveal which model extrapolates correctly without additional simulations or annotation evidence.",
)
''',
    )

    add_section(
        cells,
        number=35,
        title="Final Phase 6 decision",
        what="Apply the predeclared ranking hierarchy and semantic/robustness checks to the formulation scorecard and saved decision.",
        why="The thesis needs an explicit A/B/C outcome without forcing a winner when evidence is mixed.",
        thesis="This determines whether future real-data work should use continuous `D_max=tau`, direct Binary Keyhole, or carry both.",
        allowed="Validated static, active q20/q30/BA, threshold, subgroup, semantic, and domain evidence already shown.",
        leakage="Changing scorecard criteria after seeing results or allowing oracle diagnostics into the primary ranking.",
        misleading="Choosing Max-Depth solely because Phase 5.5 transfer favoured it, or choosing Binary solely because it matches the label definition directly.",
        calculation=r'''
scorecard = load_csv("phase6_formulation_scorecard.csv")
decision = load_csv("phase6_final_decision.csv")
final_budget = load_csv("active_learning_final_budget_summary.csv")
display(scorecard)
display(decision.T if len(decision) == 1 else decision)
display(final_budget)
results_summary_path = OUT / "results_summary.md"
if results_summary_path.is_file():
    display(Markdown(results_summary_path.read_text(encoding="utf-8")))
show_figures("final_phase6_decision_summary", limit=1)
decision_text = " ".join(decision.astype(str).to_numpy().ravel()).strip()
explain(
    observed=f"The machine-readable decision records: {decision_text[:500]}{'…' if len(decision_text) > 500 else ''}",
    support="The saved A/B/C classification follows the scorecard; `HYBRID / NO CLEAR WINNER` is the correct outcome when primary rankings materially conflict.",
    boundary="Yes—the decision is driven first by q20/q30 active-learning evidence, then balanced accuracy and query efficiency, with semantics and transfer as safeguards.",
    uncertain="The conclusion applies to this dataset snapshot, sampled support, surrogate family, and simulator-query budget.",
)
''',
    )

    add_section(
        cells,
        number=36,
        title="Validation dashboard",
        what="Display automated checks, requirement mapping, figure inventory, and output-file existence, then fail on any recorded validation failure.",
        why="A thesis result is reviewable only when population, splits, query accounting, metrics, notebook, and artifacts reconcile.",
        thesis="Validation turns a large computational result into auditable evidence rather than a collection of plots.",
        allowed="Validation/checklist/manifest artifacts and current read-only file/hash checks.",
        leakage="Validation may inspect all outputs after the experiment; it must not modify scientific results.",
        misleading="Treating automated PASS counts as external scientific validation or ignoring warnings because no check says FAIL.",
        calculation=r'''
validation = load_csv("validation_results.csv")
requirements = load_csv("requirement_checklist.csv")
figure_manifest = load_csv("figure_manifest.csv")
output_manifest = load_csv("output_manifest.csv")
display(validation)
display(requirements)
status_v = pick(validation, "status", "result", required=True)
status_r = pick(requirements, "status", "result", required=True)
failed_validation = validation[validation[status_v].astype(str).str.upper().eq("FAIL")]
failed_requirements = requirements[requirements[status_r].astype(str).str.upper().eq("FAIL")]
# The first executed build necessarily precedes the validator's final notebook
# check. Permit only that explicit bootstrap dependency; every other failure is
# still fatal, and a final validator/build pass will replace these two rows.
check_id_v = pick(validation, "check_id", "id")
requirement_id_r = pick(requirements, "requirement_id", "id")
allowed_bootstrap_v = (
    failed_validation[check_id_v].astype(str).eq("V26")
    if check_id_v is not None else pd.Series(False, index=failed_validation.index)
)
allowed_bootstrap_r = (
    failed_requirements[requirement_id_r].astype(str).eq("R14")
    if requirement_id_r is not None else pd.Series(False, index=failed_requirements.index)
)
assert failed_validation.loc[~allowed_bootstrap_v].empty
assert failed_requirements.loc[~allowed_bootstrap_r].empty
path_m = pick(output_manifest, "relative_path", "path", "filename", required=True)
manifest_paths = output_manifest[path_m].astype(str).map(Path)
def manifest_path_exists(path):
    if path.is_absolute():
        return path.is_file()
    return (OUT / path).is_file() or (ROOT / path).is_file()
exists = manifest_paths.map(manifest_path_exists)
display(pd.Series({
    "validation PASS": int(validation[status_v].astype(str).str.upper().eq("PASS").sum()),
    "validation rows": len(validation),
    "requirement PASS": int(requirements[status_r].astype(str).str.upper().eq("PASS").sum()),
    "requirement rows": len(requirements),
    "figure manifest rows": len(figure_manifest),
    "output manifest rows": len(output_manifest),
    "manifest files currently present": int(exists.sum()),
}))
assert exists.all()
explain(
    observed=(
        f"{len(validation) - len(failed_validation)}/{len(validation)} validation rows and "
        f"{len(requirements) - len(failed_requirements)}/{len(requirements)} requirement rows pass; "
        f"any displayed V26/R14 bootstrap dependency is cleared by the final validator/build pass. "
        f"{int(exists.sum())}/{len(exists)} manifest paths exist at notebook execution time."
    ),
    support="Validation protects the reported comparison but does not favour either formulation.",
    boundary="Boundary-specific checks verify fixed q20/q30 membership, metric reconciliation, fairness, and evaluation-only oracle use.",
    uncertain="Independent replication and future simulations remain outside automated repository validation.",
)
''',
    )

    add_section(
        cells,
        number=37,
        title="Hard stop",
        what="Restate the completed Phase 6 scope, runtime, decision, and prohibited next actions, then stop.",
        why="The requested scientific result must remain inspectable before any commit, push, new phase, relabelling, or target redesign.",
        thesis="This preserves Phase 6 as one reproducible checkpoint in the thesis argument.",
        allowed="Saved final decision, runtime, summary, and execution history only.",
        leakage="No new fitting or acquisition occurs after the decision; later work requires separate authorization.",
        misleading="Implying a commit/push/merge occurred, claiming a universal physical boundary, or silently continuing into Phase 7.",
        calculation=r'''
hard_stop_view = pd.Series({
    "output root": str(OUT.relative_to(ROOT)),
    "primary population n": len(population),
    "matched outer runs": run_count,
    "final decision rows": len(decision),
    "notebook phase": "Week 7 Phase 6 only",
    "automatic commit/push": False,
    "labels changed": False,
    "maximum-depth definition changed": False,
    "empirical boundary used for acquisition": False,
})
display(hard_stop_view.to_frame("recorded_state"))
explain(
    observed="Phase 6 ends with its artifacts, figures, matched active-learning result, and explicit A/B/C decision; no publication or later-phase action is performed here.",
    support="The selected formulation is exactly the validated decision shown in Section 35, including a Hybrid outcome if warranted.",
    boundary="The conclusion concerns the supported empirical manual Keyhole boundary in this four-dimensional sampled dataset.",
    uncertain="Generalization beyond this snapshot, support, annotation process, GP family, and budget requires future evidence.",
)
print("HARD STOP — Week 7 Phase 6 teaching notebook complete; inspect results before any commit, push, or later phase.")
''',
    )

    notebook = nbf.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3"},
            "phase": "Week 7 Phase 6",
            "builder": "scripts/build_week7_06_notebook.py",
            "output_root": "outputs/week7_06_real_data_boundary_active_level_set",
            "teaching_sections": 37,
        },
    )
    return notebook


def write_notebook(*, execute: bool, kernel_name: str, timeout: int) -> Path:
    """Write the notebook and optionally execute it non-interactively."""

    notebook = build_notebook()
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(notebook, NOTEBOOK)
    if execute:
        client = NotebookClient(
            notebook,
            timeout=timeout,
            kernel_name=kernel_name,
            resources={"metadata": {"path": str(ROOT)}},
            allow_errors=False,
        )
        executed = client.execute()
        nbf.write(executed, NOTEBOOK)
    return NOTEBOOK


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the Week 7 Phase 6 teaching notebook from saved artifacts."
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute the notebook non-interactively after writing it.",
    )
    parser.add_argument(
        "--kernel-name",
        default="python3",
        help="Jupyter kernel used with --execute (default: python3).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=1_800,
        help="Per-cell execution timeout in seconds (default: 1800).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    path = write_notebook(
        execute=args.execute,
        kernel_name=args.kernel_name,
        timeout=args.timeout,
    )
    action = "wrote and executed" if args.execute else "wrote"
    print(f"{action} {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
