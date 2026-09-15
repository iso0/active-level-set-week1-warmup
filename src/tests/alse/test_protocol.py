"""Protocol reproduction gates against the frozen manifests."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from alse import protocol
from alse.config import ARCHIVE_OUTPUTS
from alse.data import load_population


@pytest.fixture(scope="module")
def population():
    return load_population()


def test_declared_budgets_grid():
    b = protocol.declared_budgets(160)
    assert b[:65] == list(range(16, 81)) and b[65:85] == list(range(82, 121, 2)) and b[85:] == list(range(124, 161, 4))
    assert len(protocol.declared_budgets(80)) == 65


def test_seed_keys_are_namespaced():
    spec = protocol.SplitSpec("w85__r01_f01", 1, 1, (0, 1), (2,))
    assert protocol.fit_seed_key(spec, "binary_margin", 1, 16) == "week8_5_frozen_confirmation|v1|run|w85__r01_f01|arm|binary_margin|fit|budget|016"
    assert protocol.fit_seed_key(spec, "binary_uncertainty_repulsion", 1, 16).count("|h|0.15|") == 1
    assert protocol.random_order_key(spec, 3).endswith("continuation|03|order")
    assert len(protocol.SEED_ROOTS) == 15


def test_splits_and_designs_basic(population):
    specs = protocol.build_splits(population)
    assert len(specs) == 100 and all(len(s.train_indices) == 324 and len(s.test_indices) == 81 for s in specs)
    groups = population["input_tuple_sha256"].to_numpy()
    for s in specs[:10]:
        assert set(groups[list(s.train_indices)]).isdisjoint(groups[list(s.test_indices)])
        design = protocol.initial_design(s, population)
        assert len(design) == 16 and len(set(design)) == 16 and set(design) <= set(s.train_indices)


@pytest.mark.archive
def test_frozen_splits_match_manifest(population):
    manifest = pd.read_csv(
        ARCHIVE_OUTPUTS / "week8_5_frozen_confirmation" / "grouped_split_manifest.csv",
        usecols=["run_id", "role", "population_row_index"],
    )
    by_run = {k: g for k, g in manifest.groupby("run_id", sort=False)}
    for spec in protocol.build_splits(population):
        g = by_run[spec.run_id]
        train = g.loc[g.role.eq("training_pool"), "population_row_index"].astype(int).tolist()
        test = g.loc[g.role.eq("untouched_test"), "population_row_index"].astype(int).tolist()
        assert list(spec.train_indices) == train and list(spec.test_indices) == test


@pytest.mark.archive
def test_frozen_initial_designs_match_manifest(population):
    manifest = pd.read_csv(
        ARCHIVE_OUTPUTS / "week8_5_frozen_confirmation" / "initial_design_manifest.csv",
        usecols=["run_id", "query_order", "population_row_index"],
    ).sort_values(["run_id", "query_order"])
    expected = {k: g.population_row_index.astype(int).tolist() for k, g in manifest.groupby("run_id")}
    for spec in protocol.build_splits(population):
        assert protocol.initial_design(spec, population) == expected[spec.run_id]


@pytest.mark.archive
def test_phase6_splits_and_warm_starts(population):
    manifest = pd.read_csv(
        ARCHIVE_OUTPUTS / "week7_06_real_data_boundary_active_level_set" / "outer_split_manifest.csv",
        usecols=["run_id", "role", "population_row_index"],
    )
    audit = pd.read_csv(ARCHIVE_OUTPUTS / "week7_06_real_data_boundary_active_level_set" / "active_initialization_audit.csv")
    audit = audit.set_index("run_id")
    labels = population["has_keyhole"].astype(int).to_numpy()
    for spec in protocol.build_outer_splits(population):
        g = manifest[manifest.run_id == spec.run_id]
        assert list(spec.train_indices) == g.loc[g.role.eq("training_pool"), "population_row_index"].tolist()
        assert list(spec.test_indices) == g.loc[g.role.eq("untouched_test"), "population_row_index"].tolist()
        warm, _ = protocol.warm_start_indices(spec, population)
        row = audit.loc[spec.run_id]
        assert len(warm) == int(row.effective_warm_start)
        assert int(labels[warm].sum()) == int(row.positive_count)


@pytest.mark.archive
def test_frozen_paths_load():
    a0 = protocol.load_a0_paths()
    p1 = protocol.load_p1_paths()
    assert len(a0) == 100 and all(len(v) == 80 for v in a0.values())
    assert len(p1) == 100 and all(len(v) == 80 for v in p1.values())
    # both paths share the 16-point initial design
    assert all(a0[k][:16] == p1[k][:16] for k in a0)


@pytest.mark.archive
def test_sequential_runner_reproduces_margin_prefix(population):
    """Replaying binary_margin with the ported surrogate + rule must give the frozen A0 path."""
    from alse.acquisition import choose_binary_candidate
    from alse.surrogates import fit_gpc, predict_gpc

    a0 = protocol.load_a0_paths()
    specs = {s.run_id: s for s in protocol.build_splits(population)}
    x = population.loc[:, list(protocol.FEATURES)].to_numpy(float)
    for run_id in ("w85__r01_f01", "w85__r07_f03"):
        spec = specs[run_id]
        scaler = StandardScalerHolder(x, list(spec.train_indices))
        design = protocol.initial_design(spec, population)

        def fit_fn(xr, yr, key):
            return fit_gpc(xr, yr, protocol.seed_u32(key), scaler=scaler.scaler)

        def choose_fn(model, xc, candidates, revealed):
            p = predict_gpc(model, xc)
            idx, _ = choose_binary_candidate("binary_margin", candidates, p, scaler.scaled, revealed)
            return idx

        revealed, _ = protocol.sequential_runner(
            spec, population, design, 40, fit_fn, choose_fn,
            seed_key_fn=lambda b: protocol.fit_seed_key(spec, "binary_margin", 1, b),
        )
        assert revealed == a0[run_id][:40]


class StandardScalerHolder:
    """Scaler fitted on the training pool, as the archive's run_trajectory does."""

    def __init__(self, x: np.ndarray, train: list[int]):
        from sklearn.preprocessing import StandardScaler

        self.scaler = StandardScaler().fit(x[train])
        self.scaled = self.scaler.transform(x)
