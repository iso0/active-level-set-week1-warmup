"""Build the corrected Week 6 Phase 1 audit notebook.

The notebook is deliberately a compact, executable evidence report.  The
full deterministic data build lives in ``src/week6_phase1_melt_pool_data_audit.py``
so notebook execution does not redownload data or hide long-running work in
cell state.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = (
    ROOT
    / "notebooks"
    / "week_06"
    / "01_melt_pool_monitor_data_audit.ipynb"
)


def markdown(source: str, *, tags: list[str] | None = None):
    cell = nbf.v4.new_markdown_cell(dedent(source).strip())
    if tags:
        cell.metadata["tags"] = tags
    return cell


def code(source: str, *, tags: list[str] | None = None):
    cell = nbf.v4.new_code_cell(dedent(source).strip())
    if tags:
        cell.metadata["tags"] = tags
    return cell


def build_notebook() -> None:
    cells = [
        markdown(
            """
            # Week 6, Phase 1 — corrected melt-pool monitor data audit

            ## 1. Scope

            This notebook reports the rebuilt, pagination-safe audit of
            `ioandanielc/sph_dataset` at immutable revision
            `0e859b748fdbc8454f66e58e101e333ac0479d42`.

            The reproducible build is implemented in
            `src/week6_phase1_melt_pool_data_audit.py`. It enumerates the
            repository before any scientific parsing, audits all simulation
            folders, and produces one response row per actual folder. This
            notebook reads those generated artifacts and checks their central
            claims. It does not perform GP modelling or any Phase 2 work.
            """,
            tags=["scope"],
        ),
        code(
            """
            from pathlib import Path
            import json
            import pandas as pd
            from IPython.display import Image, Markdown, display

            ROOT = Path.cwd().resolve()
            OUT = ROOT / "outputs" / "week6_01_melt_pool_data_audit"
            assert (ROOT / "src" / "week6_phase1_melt_pool_data_audit.py").exists()
            assert OUT.exists()

            summary = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
            pd.Series({
                "chosen_revision": summary["chosen_revision"],
                "actual_simulation_folders": summary["actual_simulation_folder_count"],
                "numeric_id_range": (
                    f"{summary['minimum_numeric_simulation_id']}–"
                    f"{summary['maximum_numeric_simulation_id']}"
                ),
                "numeric_id_gaps": summary["numeric_id_gaps"],
                "dataset_shape": summary["final_dataset_shape"],
            })
            """,
            tags=["provenance"],
        ),
        markdown(
            """
            ## 2. Immutable source and population controls

            The audit is pinned to one immutable revision. The complete
            population contains 241 folders spanning numeric IDs 1–242, with
            only ID 136 absent; therefore row count must not be inferred from
            the largest contiguous prefix.
            """
        ),
        code(
            """
            pd.Series({
                "retired_method": "HfApi.repo_info(...).siblings",
                "single_payload_file_paths": (
                    summary["enumeration"]["faulty_sibling_file_count"]
                ),
                "lexicographically_last_path": (
                    summary["enumeration"]["faulty_last_path"]
                ),
                "corrected_primary_method": (
                    summary["enumeration"]["primary_method"]
                ),
                "independent_http_pages_consumed": (
                    summary["enumeration"]["independent_http_pages"]
                ),
            })
            """,
            tags=["root-cause"],
        ),
        markdown(
            """
            ## 3. Why the previous listing failed

            The retired result came from treating a single incomplete global
            `repo_info().siblings` payload as a complete directory listing.
            Direct path probes prove that later folders exist at the same SHA.

            ## 4. Pagination-safe enumeration
            """
        ),
        code(
            """
            tree = pd.read_csv(OUT / "repository_tree_audit.csv")
            direct = pd.read_csv(OUT / "revision_path_existence_checks.csv")
            display(tree)
            display(
                direct.pivot(
                    index="simulation_id",
                    columns="revision_label",
                    values="exists",
                )
            )
            """,
            tags=["repository-enumeration", "path-checks"],
        ),
        markdown(
            """
            The primary directory-aware iterator and the independent
            explicitly paginated HTTP enumeration both reach `sim_00242` and
            agree on all 241 folders. Direct path probes also confirm the six
            boundary/control simulations at the old revision, chosen revision,
            and current `main` SHA.

            ## 5. Master reconciliation and folder inventory
            """
        ),
        code(
            """
            folders = pd.read_csv(OUT / "simulation_folder_inventory.csv")
            reconciliation = pd.read_csv(
                OUT / "experiments_folder_reconciliation.csv"
            )
            gaps = pd.read_csv(OUT / "numeric_simulation_id_gaps.csv")

            display(reconciliation["membership_class"].value_counts())
            display(gaps)
            display(folders.iloc[[0, 116, 117, -2, -1]][[
                "simulation_id",
                "numeric_simulation_id",
                "recursive_pages_consumed",
                "recursive_item_count",
                "file_count",
            ]])
            """,
            tags=["reconciliation", "folder-inventory"],
        ),
        markdown(
            """
            `experiments.csv` and the repository tree match exactly: there are
            no master-only or folder-only simulations and no duplicate IDs.
            The boundary rows demonstrate that enumeration continues past
            `sim_00117` through `sim_00242`.

            ## 6. File completeness, monitor types, and schemas
            """
        ),
        code(
            """
            sim_files = pd.read_csv(OUT / "simulation_file_inventory.csv")
            missing = pd.read_csv(OUT / "missing_file_report.csv")
            dat_types = pd.read_csv(OUT / "dat_file_type_inventory.csv")

            pd.Series({
                "simulations": len(sim_files),
                "all_have_34_monitor_dat_files": bool(
                    sim_files["monitor_dat_count"].eq(34).all()
                ),
                "all_have_required_metadata": bool(
                    sim_files[
                        [
                            "experiment_details_available",
                            "parameters_available",
                            "metadata_available",
                            "labeling_provenance_available",
                            "frames_csv_available",
                            "monitor_available",
                        ]
                    ].all(axis=1).all()
                    and sim_files["complete_for_phase1"].all()
                ),
                "missing_report_rows": len(missing),
                "monitor_file_types": len(dat_types),
            })
            """,
            tags=["file-inventory", "quality-issues"],
        ),
        markdown(
            """
            Every folder has the required metadata, provenance, frame index,
            time/iteration streams, melt bounds, and all 34 monitor `.dat`
            types. The missing-file report is empty.
            """
        ),
        code(
            """
            schemas = pd.read_csv(OUT / "monitor_schema_audit.csv")
            dictionary = pd.read_csv(OUT / "monitor_data_dictionary.csv")

            display(
                schemas.groupby("file_name").agg(
                    sampled_simulations=("simulation_id", "nunique"),
                    distinct_column_counts=("column_count", "nunique"),
                    schema_consistency=(
                        "schema_consistent_across_audited_simulations",
                        "all",
                    ),
                ).head(12)
            )
            display(dictionary.head(12))
            """,
            tags=["monitor-audit", "data-dictionary"],
        ),
        markdown(
            """
            The broad 13-simulation schema sample covers early, boundary,
            parameter-extreme, and late simulations. It parses all monitor
            types consistently, while the data dictionary records units,
            semantics, and the role of each stream.

            ## 7. Full-population bounds, time, and iteration parsing
            """
        ),
        code(
            """
            bounds_manifest = pd.read_csv(OUT / "melt_bounds_manifest.csv")
            pd.Series({
                "simulations_parsed": len(bounds_manifest),
                "total_bounds_rows": int(bounds_manifest["row_count"].sum()),
                "valid_melt_rows": int(bounds_manifest["valid_row_count"].sum()),
                "sentinel_rows": int(bounds_manifest["sentinel_row_count"].sum()),
                "all_stream_lengths_align": bool(
                    bounds_manifest["row_alignment_passed"].all()
                ),
                "all_accepted_bounds_ordered": bool(
                    bounds_manifest["ordered_bounds_passed"].all()
                ),
                "all_time_streams_monotonic": bool(
                    bounds_manifest["time_monotonic_passed"].all()
                ),
                "all_iteration_streams_monotonic": bool(
                    bounds_manifest["iteration_monotonic_passed"].all()
                ),
            })
            """,
            tags=["bounds-manifest"],
        ),
        markdown(
            """
            All 241 melt-bounds streams parse and align exactly with their
            `time.dat` and `iter.dat` streams. Sentinel rows are retained as
            explicit missing-melt states, while accepted bounds obey min/max
            ordering.

            ## 8. Physical-axis evidence
            """
        ),
        code(
            """
            axis = pd.read_csv(OUT / "axis_evidence_summary.csv")
            display(axis)
            """,
            tags=["axis-evidence"],
        ),
        markdown(
            """
            Full-population configuration and trajectory evidence identify X
            as the scan/length direction, Y as transverse/width, and Z as
            vertical. Penetration below the original surface is therefore
            `max(0, -z_min)`. The median center displacement is overwhelmingly
            along X, reinforcing the metadata-based mapping.

            ## 9. Response and scalar-target selection
            """
        ),
        code(
            """
            responses = pd.read_csv(OUT / "selected_response_summary.csv")
            candidates = pd.read_csv(
                OUT / "scalar_target_candidate_comparison.csv"
            )
            display(responses)
            display(
                candidates[
                    [
                        "response",
                        "candidate",
                        "available_simulation_count",
                        "median_window_cv",
                        "p90_window_cv",
                        "selected_primary",
                    ]
                ]
            )
            """,
            tags=["response-selection", "target-comparison"],
        ),
        markdown(
            """
            Width, length, and penetration depth are all retained. The primary
            scalar is the median over the final 20% of melt-present time before
            the laser reaches 90% of the +X domain. This rule is available for
            all simulations and is more robust to boundary exit and terminal
            invalid rows than the final-recorded value.

            ## 10. Final one-row-per-folder dataset
            """
        ),
        code(
            """
            data = pd.read_csv(
                OUT / "week6_phase1_simulation_level_responses.csv"
            )
            target_columns = [
                "melt_pool_width_selected_primary_scalar_target_m",
                "melt_pool_length_selected_primary_scalar_target_m",
                "melt_pool_depth_below_surface_selected_primary_scalar_target_m",
            ]
            pd.Series({
                "rows": len(data),
                "columns": len(data.columns),
                "unique_simulation_ids": data["simulation_id"].nunique(),
                "complete_primary_targets": int(
                    data[target_columns].notna().all(axis=1).sum()
                ),
                "valid_final_recorded_bounds": int(
                    data["final_row_has_valid_melt_bounds"].sum()
                ),
                "laser_exits_before_recording_end": int(
                    data[
                        "laser_exits_domain_before_recording_end"
                    ].sum()
                ),
                "selected_window_instability_flags": int(
                    data["flag_primary_window_unstable"].sum()
                ),
            })
            """,
            tags=["final-dataset"],
        ),
        markdown(
            """
            The rebuilt table has one unique row for every actual folder and a
            complete three-response target vector for all 241 simulations.
            Terminal-row and boundary-exit diagnostics remain explicit rather
            than silently removing affected runs.

            ## 11. Quality flags and frame-based cross-checks
            """
        ),
        code(
            """
            frame_evidence = pd.read_csv(OUT / "frame_axis_evidence.csv")
            display(
                frame_evidence.groupby(["view", "selection_reason"]).agg(
                    simulations=("simulation_id", "nunique"),
                    images=("relative_path", "count"),
                    min_frame_index=("frame_index", "min"),
                    max_frame_index=("frame_index", "max"),
                )
            )
            """,
            tags=["axis-figures", "quality-issues"],
        ),
        markdown(
            """
            Frame validation spans the complete population through
            parameter/response extrema and late simulations, with front, side,
            and top views sampled at early, middle, late, and
            near-boundary-exit times.
            """,
            tags=["axis-figures"],
        ),
        code(
            """
            for filename in [
                "repository_enumeration_diagnostics.png",
                "axis_center_motion.png",
                "response_time_series_diagnostics.png",
                "frame_axis_validation.png",
                "target_candidate_comparison.png",
            ]:
                print(filename)
                display(Image(filename=str(OUT / filename)))
            """
        ),
        markdown(
            """
            The figures provide complementary diagnostics: enumeration
            completion, center motion, response time series, multi-view frame
            evidence, and candidate stability. They are diagnostics, not
            modelling results.

            ## 12. Anti-truncation and scientific validation
            """
        ),
        code(
            """
            master = pd.read_csv(
                ROOT
                / "data"
                / "raw"
                / "huggingface"
                / "sph_dataset"
                / "final_data_processed"
                / "experiments.csv"
            )
            checks = pd.Series({
                "241 folders": len(folders) == 241,
                "sim_00242 present": "sim_00242" in set(folders["simulation_id"]),
                "only numeric gap is 136": gaps["missing_numeric_id"].tolist() == [136],
                "master/tree exact set match": (
                    set(master["experiment_id"]) == set(folders["simulation_id"])
                ),
                "all monitor inventories complete": sim_files["monitor_dat_count"].eq(34).all(),
                "one response row per folder": (
                    len(data) == len(folders)
                    and data["simulation_id"].is_unique
                ),
                "all primary targets available": data[target_columns].notna().all().all(),
                "no incomplete simulation flags": (
                    ~data["flag_incomplete_simulation"].astype(bool)
                ).all(),
            })
            display(checks)
            assert checks.all()
            """,
            tags=["validations"],
        ),
        markdown(
            """
            ## 13. Conclusions and Phase 1 readiness

            All notebook-level assertions pass. The corrected Phase 1 table is
            complete, population-wide, traceable to the immutable source
            revision, and ready for later modelling. Phase 2 remains out of
            scope.
            """,
            tags=["conclusions"],
        ),
    ]

    notebook = nbf.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3",
            },
        },
    )
    NOTEBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(notebook, NOTEBOOK_PATH)


if __name__ == "__main__":
    build_notebook()
    print(NOTEBOOK_PATH)
