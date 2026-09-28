"""Command line entry points for the frozen external-validation workflow."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from . import analysis, freeze, intake, reference_manifests, runner
from .common import FEATURES, require, sha


class _SyntheticEvaluator:
    """Cheap deterministic predictor used only by the infrastructure dry run."""
    def fit_predict(self, x, revealed, revealed_labels, train, predict, run_id, budget):
        x = np.asarray(x, float)
        score = (x[np.asarray(predict), 0] - np.median(x[np.asarray(train), 0])) / 30.0
        return 1 / (1 + np.exp(-score)), {"synthetic_mock": True}, object()


def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _manifest(path, frozen):
    path = Path(path)
    require(sha(path.read_bytes()) == frozen["batch_manifest_sha256"], "Batch manifest hash drift")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        require(tuple(reader.fieldnames or ()) == intake.MANIFEST_COLUMNS, "Manifest schema drift")
        rows = list(reader)
    by_id = {row["sim_id"]: row for row in rows}
    require(len(by_id) == len(rows), "Duplicate manifest IDs")
    require(set(frozen["included_ids"]).issubset(by_id), "Frozen included IDs absent from manifest")
    selected = [by_id[value] for value in frozen["included_ids"]]
    x = np.asarray([[float(row[name]) for name in FEATURES] for row in selected], float)
    require(np.isfinite(x).all() and (x[:, :3] > 0).all(), "Invalid frozen manifest features")
    return selected, x


def command_intake(args):
    intake.intake(args.manifest, args.old407, args.old405, args.inventory, args.output,
                  provenance=_json(args.provenance), units=_json(args.units))


def command_freeze(args):
    freeze.generate(args.intake, args.output_directory, _json(args.decisions))


def command_export_references(args):
    reference_manifests.export(args.output_directory)


def command_execute(args):
    frozen = runner.preflight_execution(args.freeze, args.freeze_commit, args.output_root)
    rows, x = _manifest(args.manifest, frozen)
    sim_ids = [row["sim_id"] for row in rows]
    groups = [row["group_token"] for row in rows]
    splits = runner.build_splits(groups, frozen)
    oracle = runner.open_oracle(args.oracle, frozen)
    labels = np.asarray([oracle[value] for value in sim_ids], int)
    run = runner.run_locked(x, sim_ids, labels, splits, frozen)
    result = None
    analysis_error = None
    if run["complete"]:
        try:
            result = analysis.analyze(run, x, labels, sim_ids, frozen)
        except Exception as error:
            analysis_error = error
            run["complete"] = False
            run["failures"].append({"split_id": None, "arm": None, "event": "ANALYSIS_STOP",
                                    "error_type": type(error).__name__, "message": str(error)})
    runner.write_run(run, frozen, args.output_root)
    if result is not None:
        analysis.write_frozen_outputs(result, frozen, args.output_root)
    if analysis_error is not None:
        raise analysis_error
    require(run["complete"], "Locked execution stopped; inspect preserved failure artifacts")


def command_synthetic(args):
    """Exercise intake-independent locked execution and inference on fake data only."""
    # Equal feature rows make every boundary distance tie. Alternating stable IDs
    # then guarantee both classes in each synthetic q20 subset; this fixture tests
    # plumbing and carries no process interpretation.
    x = np.tile(np.array([200.0, 1.0, 0.00008, 400.0]), (105, 1))
    labels = np.arange(105) % 2
    ids = [f"SYNTHETIC_{i:04d}" for i in range(len(x))]
    frozen = {"usable_sample_count": len(x), "random_seeds": [101, 202],
              "initial_design_seed_namespace": "w85.seed_u32(w85.seed_key('run',split_id,'initial_design'))",
              "arms": list(runner.ARMS), "repeat_count": 2,
              "primary_endpoint": runner.PRIMARY, "exact_feasible_budgets": runner.BUDGETS,
              "paired_interval_method": analysis.SUPPORTED_INTERVAL,
              "q20_scaling_scope": analysis.SUPPORTED_Q_SCALING}
    splits = []
    for repeat in (1, 2):
        for fold in range(1, 6):
            start = (fold - 1) * 21
            test = list(range(start, start + 21))
            train = [i for i in range(105) if i not in set(test)]
            splits.append({"split_id": f"external__r{repeat:03d}_f{fold:02d}",
                           "repeat": repeat, "fold": fold, "train_indices": train,
                           "test_indices": test, "split_seed": frozen["random_seeds"][repeat - 1]})
    run = runner.run_locked(x, ids, labels, splits, frozen, _SyntheticEvaluator())
    result = analysis.analyze(run, x, labels, ids, frozen)
    evidence = {"status": "PASS", "data": "FAKE_SYNTHETIC_ONLY", "rows": len(x),
                "splits": len(splits), "arms": run["arms"],
                "budgets": [16, 80], "prediction_rows": len(run["predictions"]),
                "path_rows": len(run["paths"]), "diagnostic_rows": len(run["fit_diagnostics"]),
                "claim_ledger_exercised_not_scientific_evidence": result["claim_ledger"]}
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(required=True)
    blind = commands.add_parser("intake", help="run label-blind intake")
    for name in ("manifest", "old407", "old405", "inventory", "output", "provenance", "units"):
        blind.add_argument(f"--{name}", required=True)
    blind.set_defaults(function=command_intake)
    seal = commands.add_parser("freeze", help="write the pre-label dataset addendum")
    seal.add_argument("--intake", required=True)
    seal.add_argument("--decisions", required=True)
    seal.add_argument("--output-directory", required=True)
    seal.set_defaults(function=command_freeze)
    references = commands.add_parser("export-references", help="export label-free OLD-407/405 manifests")
    references.add_argument("--output-directory", required=True)
    references.set_defaults(function=command_export_references)
    bind = commands.add_parser("verify-bindings", help="import the pinned real method modules")
    bind.set_defaults(function=lambda _: runner.bind_real_implementations())
    synthetic = commands.add_parser("synthetic-dry-run", help="exercise locked plumbing on fake data")
    synthetic.add_argument("--output", required=True)
    synthetic.set_defaults(function=command_synthetic)
    execute = commands.add_parser("execute", help="open labels and run only after committed freeze")
    for name in ("manifest", "oracle", "freeze", "freeze-commit", "output-root"):
        execute.add_argument(f"--{name}", required=True)
    execute.set_defaults(function=command_execute)
    return root


def main():
    args = parser().parse_args()
    args.function(args)


if __name__ == "__main__":
    main()
