"""Tests for alse.data: pins, population checks, hashing, name parsing, ledgers, registry."""

from __future__ import annotations

import hashlib
import math
import sys
import types

import numpy as np
import pandas as pd
import pytest

from alse import data
from alse.config import ARCHIVE_OUTPUTS, POPULATION_CSV
from alse.io import sha256_text_lf

NAME = (
    "P-102p928146519_VX-0p633805217924_LS-5p29394366699e-05_ST-318p223787128_M-TI64"
    "_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-7p61136145079e-06_H-6c9c68731f"
)
NAME_HASH = "7d4f78e00d09eeb0491ce2e4e9977d38b82ea6f7cec7ff63da21e2460b469e5a"  # frozen population value
PHASE1 = ARCHIVE_OUTPUTS / "week7_01_sph_v2_audit"
PHASE6 = ARCHIVE_OUTPUTS / "week7_06_real_data_boundary_active_level_set"


@pytest.fixture(scope="module")
def population() -> pd.DataFrame:
    return data.load_population()


def synthetic_ledger() -> pd.DataFrame:
    """Three experiments: persistent keyhole, transient two-episode keyhole, conduction only."""
    rows = []

    def add(partition, name, seq, timesteps=None):
        for row, label in enumerate(seq):
            rows.append({"partition": partition, "name": name, "timestep": (timesteps or list(range(len(seq))))[row], "label_final": label})

    add("old-data-local", "B", ["Initial Emptiness", "Forming Phase", "Keyhole", "Keyhole", "Scanning Stopped"])
    add("new-data", NAME, ["Forming Phase", "Keyhole", "Conduction", "Keyhole", "Conduction", "Unsure"])
    # unsorted timesteps: frames are ordered by (timestep, frame_row) not by file order
    add("new-data", "C", ["Conduction", "Forming Phase", "Initial Emptiness"], timesteps=[20, 10, 0])
    return pd.DataFrame(rows)


def fake_ledger(name: str, labels: list[str]) -> pd.DataFrame:
    parsed = data.parse_experiment_name(name)
    encode = lambda value: repr(value).replace(".", "p")  # noqa: E731
    return pd.DataFrame(
        [[name, "h", encode(parsed["P"]), encode(parsed["VX"]), encode(parsed["LS"]), encode(parsed["ST"]), True, True, 10 * step, label, label, label]
         for step, label in enumerate(labels)],
        columns=data.LEDGER_COLUMNS,
    )


# --- fast unit tests ---------------------------------------------------------


def test_pins_and_units():
    assert data.SPH_DATASET_REPO == "ioandanielc/sph_dataset"
    assert data.SPH_DATASET_REVISION == "0e859b748fdbc8454f66e58e101e333ac0479d42"
    assert data.SPH_V2_REPO == "ioandanielc/sph_v2"
    assert data.SPH_V2_REVISION_AUDIT == "d69dac5bda8b622bc0de316b112815c6056c06ec"
    assert data.SPH_V2_REVISION == "b6dc254a2b607a31cb9f97b40990339c3d5ca1e8"
    assert data.FEATURE_UNITS == {"P": "W", "VX": "m/s", "LS": "m", "ST": "K"}
    assert data.FEATURE_COLUMNS == ["P", "VX", "LS", "ST"]
    assert data.LABEL_FILES is data.PARTITIONS and data.PARTITION_ORDER == ["new-data", "old-data-local", "old-data-remote-clean"]
    assert data.PHYSICAL_LABELS.isdisjoint(data.TECHNICAL_LABELS) and len(data.TECHNICAL_LABELS) == 5


def test_decode_number():
    assert data.decode_number("101p25") == 101.25
    assert data.decode_number("-0p0002") == -0.0002
    assert data.decode_number("5p29394366699e-05") == 5.29394366699e-05
    assert data.decode_number(3) == 3.0 and data.decode_number(np.float32(1.5)) == 1.5
    assert all(math.isnan(data.decode_number(value)) for value in [None, "", "  ", float("nan")])


def test_parse_experiment_name():
    parsed = data.parse_experiment_name(NAME)
    assert parsed["folder_name_valid"] is True and parsed["experiment_name"] == NAME
    assert parsed["P"] == 102.928146519 and parsed["ST"] == 318.223787128
    assert parsed["LS"] == 5.29394366699e-05 and parsed["XF"] == 0.0014 and parsed["DT"] == 7.61136145079e-06
    assert parsed["material"] == "TI64" and parsed["folder_hash"] == "6c9c68731f"
    bad = data.parse_experiment_name("not_a_folder")
    assert bad["folder_name_valid"] is False and math.isnan(bad["P"]) and bad["material"] == "" and bad["folder_hash"] == ""
    assert set(bad) == set(parsed)


def test_input_tuple_hash_known_vector():
    frame = pd.DataFrame({"P": [100.0], "VX": [0.5], "LS": [5e-5], "ST": [300.0]})
    expected = hashlib.sha256(b"100|0.5|5.0000000000000002e-05|300").hexdigest()
    assert data.input_tuple_hash(frame).iloc[0] == expected
    assert data.input_tuple_hash(pd.DataFrame([data.parse_experiment_name(NAME)])).iloc[0] == NAME_HASH


def test_load_population_checks(population):
    assert len(population) == 405 and population.index.equals(pd.RangeIndex(405))
    assert int(population["has_keyhole"].sum()) == 73 and population["experiment_name"].is_unique
    for column in data.POPULATION_BOOL_COLUMNS:
        assert population[column].dtype == bool, column
    assert population["partition"].value_counts().to_dict() == {"old-data-local": 178, "new-data": 164, "old-data-remote-clean": 63}
    assert population["input_tuple_sha256"].is_unique  # no duplicate input groups
    assert np.isfinite(population[data.FEATURE_COLUMNS].to_numpy()).all()
    assert population.loc[0, "experiment_name"] == NAME  # frozen row order


@pytest.mark.parametrize(
    "mutate",
    [
        lambda frame: frame.iloc[:404],
        lambda frame: frame.assign(has_keyhole=~frame["has_keyhole"]),
        lambda frame: frame.assign(experiment_name=np.where(frame.index == 404, frame["experiment_name"].iloc[0], frame["experiment_name"])),
        lambda frame: frame.assign(source_label_modified=True),
        lambda frame: frame.assign(has_keyhole=frame["has_keyhole"].astype(str).replace({"True": "yes"})),
    ],
    ids=["rows", "keyhole_count", "duplicate_name", "modified_label", "bad_bool"],
)
def test_load_population_rejects_drift(tmp_path, population, mutate):
    path = tmp_path / "pop.csv"
    mutate(population).to_csv(path, index=False)
    with pytest.raises(RuntimeError):
        data.load_population(path)


def test_input_tuple_hash_matches_stored_column(population):
    assert (data.input_tuple_hash(population) == population["input_tuple_sha256"]).all()


def test_parse_experiment_name_round_trips_population(population):
    parsed = pd.DataFrame([data.parse_experiment_name(name) for name in population["experiment_name"]])
    assert parsed["folder_name_valid"].all() and (parsed["material"] == "TI64").all()
    for feature in data.FEATURE_COLUMNS:
        assert np.array_equal(parsed[feature].to_numpy(), population[feature].to_numpy()), feature


def test_collapsed_and_keyhole_segments():
    seq = ["A", "A", "Keyhole", "Keyhole", "B", "Keyhole"]
    assert data.collapsed(seq) == ["A", "Keyhole", "B", "Keyhole"] and data.collapsed([]) == []
    assert data.keyhole_segments(seq) == [(2, 3), (5, 5)]
    assert data.keyhole_segments([]) == [] and data.keyhole_segments(["Keyhole"]) == [(0, 0)]


def test_experiment_registry_synthetic():
    registry = data.experiment_registry(synthetic_ledger()).set_index("experiment_name")
    assert list(registry.index) == ["C", NAME, "B"]  # sorted by (partition, name)
    assert "inputs_match_partition_ledger" not in registry.columns
    b = registry.loc["B"]
    assert bool(b["has_keyhole"]) and not bool(b["has_conduction"])
    assert bool(b["keyhole_persistent_to_last_physical_frame"]) and not bool(b["keyhole_transient_by_sequence"])
    assert b["keyhole_fraction_of_relevant_physical_frames"] == 2 / 3 and b["relevant_physical_frame_count"] == 3
    assert b["collapsed_physical_sequence"] == "Forming Phase -> Keyhole" and b["label_change_count"] == 3
    assert b["distinct_label_count"] == 4 and b["first_keyhole_frame_index"] == 2 and b["last_keyhole_frame_index"] == 3
    assert not bool(b["folder_name_valid"]) and math.isnan(b["P"]) and math.isnan(b["first_conduction_frame_index"])
    a = registry.loc[NAME]
    assert bool(a["keyhole_transient_by_sequence"]) and bool(a["repeated_keyhole_episodes"])
    assert a["keyhole_segment_count"] == 2 and a["maximum_keyhole_segment_frames"] == 1 and a["keyhole_frame_count"] == 2
    assert a["first_keyhole_timestep"] == 1 and a["last_keyhole_timestep"] == 3 and a["first_conduction_timestep"] == 2
    assert a["P"] == 102.928146519 and a["input_tuple_sha256"] == NAME_HASH
    assert a["label_sequence_sha256"] == hashlib.sha256(b"Forming Phase\nKeyhole\nConduction\nKeyhole\nConduction\nUnsure").hexdigest()
    c = registry.loc["C"]
    assert c["collapsed_label_sequence"] == "Initial Emptiness -> Forming Phase -> Conduction"
    assert c["last_physical_label"] == "Conduction" and not bool(c["has_keyhole"]) and c["keyhole_frame_count"] == 0
    assert c["keyhole_fraction_of_relevant_physical_frames"] == 0.0 and c["first_conduction_frame_index"] == 2
    empty = data.experiment_registry(synthetic_ledger().assign(label_final="Unsure")).set_index("experiment_name")
    assert math.isnan(empty.loc["B", "keyhole_fraction_of_relevant_physical_frames"]) and empty.loc["B", "last_physical_label"] == ""


def test_read_partition_ledgers_schema(tmp_path):
    paths = {}
    for number, (partition, filename) in enumerate(data.PARTITIONS.items(), start=1):
        paths[partition] = tmp_path / filename
        pd.DataFrame(
            [[f"exp{number}", "h", "100p5", "0p5", "5e-05", "300", True, True, 0, "Keyhole", "Keyhole", "Keyhole"]],
            columns=data.LEDGER_COLUMNS,
        ).to_csv(paths[partition], index=False)
    labels = data.read_partition_ledgers(paths)
    assert labels.columns.tolist()[:4] == ["partition_number", "partition", "partition_label_file", "frame_row_in_partition"]
    assert labels["partition_number"].tolist() == [1, 2, 3] and labels["partition"].tolist() == data.PARTITION_ORDER
    assert labels["P_numeric"].tolist() == [100.5] * 3 and labels["LS_numeric"].tolist() == [5e-05] * 3
    assert labels["experiment_name"].tolist() == ["exp1", "exp2", "exp3"]
    pd.DataFrame(columns=data.LEDGER_COLUMNS[:-1]).to_csv(paths["new-data"], index=False)
    with pytest.raises(RuntimeError, match="unexpected label schema"):
        data.read_partition_ledgers(paths)


def test_download_and_ledgers_use_pinned_revision(tmp_path, monkeypatch):
    """No network: a fake ``huggingface_hub`` records the call and serves ledgers."""
    calls = []
    ledgers = {
        data.PARTITIONS["new-data"]: fake_ledger(NAME, ["Forming Phase", "Keyhole", "Keyhole"]),
        data.PARTITIONS["old-data-local"]: fake_ledger(NAME.replace("6c9c68731f", "aaaaaaaaaa"), ["Conduction"]),
        data.PARTITIONS["old-data-remote-clean"]: fake_ledger(NAME.replace("6c9c68731f", "bbbbbbbbbb"), ["Unsure", "Conduction"]),
    }

    def hf_hub_download(**kwargs):
        calls.append(kwargs)
        path = kwargs["local_dir"] / kwargs["filename"]
        ledgers[kwargs["filename"]].to_csv(path, index=False)
        return str(path)

    monkeypatch.setitem(sys.modules, "huggingface_hub", types.SimpleNamespace(hf_hub_download=hf_hub_download))
    monkeypatch.setattr(data, "DATA_DIR", tmp_path)
    path = data.download_pinned_file("labels_partition_1_new-data.csv")
    assert path == tmp_path / "raw" / "sph_v2" / data.SPH_V2_REVISION / "labels_partition_1_new-data.csv" and path.is_file()
    assert calls[-1] == {"repo_id": "ioandanielc/sph_v2", "repo_type": "dataset", "revision": data.SPH_V2_REVISION,
                         "filename": "labels_partition_1_new-data.csv", "local_dir": path.parent, "force_download": False}
    labels = data.load_partition_labels(data.SPH_V2_REVISION_AUDIT, tmp_path / "custom")
    assert {call["revision"] for call in calls[1:]} == {data.SPH_V2_REVISION_AUDIT}
    assert all(call["local_dir"] == tmp_path / "custom" for call in calls[1:])
    assert len(labels) == 6 and labels["partition_number"].tolist() == [1, 1, 1, 2, 3, 3]
    assert labels["P_numeric"].iloc[0] == 102.928146519 and labels["experiment_name"].iloc[0] == NAME
    registry = data.experiment_registry(labels)
    assert registry["inputs_match_partition_ledger"].all() and registry["has_keyhole"].tolist() == [True, False, False]
    assert registry.loc[0, "input_tuple_sha256"] == NAME_HASH and registry["first_keyhole_timestep"].iloc[0] == 10


# --- archive comparisons ------------------------------------------------------


@pytest.mark.archive
def test_population_is_the_archive_frozen_file():
    archive_csv = PHASE6 / "primary_common_population.csv"
    assert POPULATION_CSV.read_bytes().replace(b"\r\n", b"\n") == archive_csv.read_bytes().replace(b"\r\n", b"\n")
    assert sha256_text_lf(POPULATION_CSV) == data.POPULATION_SHA256_LF
    manifest = pd.read_csv(PHASE6 / "output_manifest.csv")
    row = manifest[manifest["relative_path"].str.endswith("week7_06_real_data_boundary_active_level_set/primary_common_population.csv")]
    assert row["sha256"].tolist() == [data.POPULATION_SHA256_LF]


@pytest.mark.archive
def test_constants_match_archive(archive_src):
    import src.week7_phase6_real_data_boundary_active_level_set as p6
    import src.week7_sph_v2_common as common

    assert (data.SPH_V2_REPO, data.SPH_V2_REVISION_AUDIT) == (common.SPH_V2_REPO_ID, common.SPH_V2_REVISION)
    assert (data.SPH_DATASET_REPO, data.SPH_DATASET_REVISION) == (common.WEEK6_REPO_ID, common.WEEK6_REVISION)
    assert (data.SPH_V2_REPO, data.SPH_V2_REVISION) == (p6.SPH_V2_REPO_ID, p6.EXPECTED_HF_REVISION)
    assert data.PARTITIONS == common.PARTITIONS == p6.LABEL_FILES
    assert data.PARTITION_ORDER == common.PARTITION_ORDER == p6.PARTITION_ORDER
    assert data.FEATURE_UNITS == common.FEATURE_UNITS == p6.FEATURE_UNITS and data.FEATURE_COLUMNS == p6.FEATURE_COLUMNS
    assert data.PHYSICAL_LABELS == common.PHYSICAL_LABELS and data.TECHNICAL_LABELS == common.TECHNICAL_LABELS
    assert data.FOLDER_KEYS == common.FOLDER_KEYS and data.FOLDER_PATTERN.pattern == common.FOLDER_PATTERN.pattern


@pytest.mark.archive
def test_name_parsing_matches_archive(archive_src, population):
    import src.week7_sph_v2_common as common

    for name in [*population["experiment_name"], NAME + "_extra"]:
        assert data.parse_experiment_name(name) == common.parse_experiment_name(name)
    ours, theirs = data.parse_experiment_name("not_a_folder"), common.parse_experiment_name("not_a_folder")
    assert {k: v for k, v in ours.items() if not isinstance(v, float)} == {k: v for k, v in theirs.items() if not isinstance(v, float)}
    for value in ["101p25", "-0p0002", "7p61136145079e-06", "", "  ", 3, np.int64(4), None, float("nan")]:
        ours, theirs = data.decode_number(value), common.decode_number(value)
        assert ours == theirs or (math.isnan(ours) and math.isnan(theirs))


@pytest.mark.archive
def test_input_tuple_hash_matches_archive(archive_src, population):
    import src.week7_phase6_real_data_boundary_active_level_set as p6

    assert (data.input_tuple_hash(population) == p6.input_tuple_hash(population)).all()


@pytest.mark.archive
def test_experiment_registry_flags_match_frozen_phase1_tables(population):
    sequence = pd.read_csv(PHASE1 / "experiment_label_sequences.csv")
    frozen_registry = pd.read_csv(PHASE1 / "experiment_registry.csv")
    assert len(sequence) == 407 and len(frozen_registry) == 407
    # One frame per collapsed label: every field that does not depend on run
    # lengths or timesteps must be reproduced exactly for all 407 experiments.
    rows = [
        {"partition": record.partition, "name": record.experiment_name, "timestep": step, "label_final": label}
        for record in sequence.itertuples(index=False)
        for step, label in enumerate(record.collapsed_label_sequence.split(" -> "))
    ]
    registry = data.experiment_registry(pd.DataFrame(rows))
    assert registry["experiment_name"].tolist() == sequence["experiment_name"].tolist()
    for column in [
        "partition", "has_keyhole", "has_conduction", "collapsed_label_sequence", "collapsed_physical_sequence",
        "first_physical_label", "last_physical_label", "distinct_label_count", "label_change_count",
        "keyhole_segment_count", "keyhole_transient_by_sequence", "keyhole_persistent_to_last_physical_frame",
        "repeated_keyhole_episodes",
    ]:
        assert registry[column].fillna("").tolist() == sequence[column].fillna("").tolist(), column
    assert int(registry["has_keyhole"].sum()) == 73 and int(registry["has_conduction"].sum()) == 373
    # inputs decoded from the folder name equal the frozen parameters.json values
    frozen_registry = frozen_registry.sort_values(["partition", "experiment_name"], kind="stable").reset_index(drop=True)
    assert frozen_registry["experiment_name"].tolist() == registry["experiment_name"].tolist()
    assert frozen_registry["parameter_values_match_folder_and_partition"].all()
    assert frozen_registry["parameter_units_match_week6"].all()
    for feature in data.FEATURE_COLUMNS:
        assert np.allclose(registry[feature], frozen_registry[feature], rtol=0.0, atol=data.INPUT_MATCH_ATOL), feature
        assert (frozen_registry[f"{feature}_unit"] == data.FEATURE_UNITS[feature]).all()
    # the 405-row population inherits has_keyhole and input_tuple_sha256 from the registry
    merged = population[["experiment_name", "has_keyhole", "input_tuple_sha256"]].merge(
        registry[["experiment_name", "has_keyhole", "input_tuple_sha256"]], on="experiment_name", suffixes=("", "_reg")
    )
    assert len(merged) == 405
    assert (merged["has_keyhole"] == merged["has_keyhole_reg"]).all()
    assert (merged["input_tuple_sha256"] == merged["input_tuple_sha256_reg"]).all()


@pytest.mark.archive
def test_experiment_registry_counts_match_frozen_keyhole_episodes():
    """Rebuild per-frame ledgers for the 73 Keyhole experiments from the frozen episode table."""
    sequence = pd.read_csv(PHASE1 / "experiment_label_sequences.csv")
    episodes = pd.read_csv(PHASE1 / "keyhole_episodes.csv")
    keyhole = sequence[sequence["has_keyhole"]].reset_index(drop=True)
    assert len(keyhole) == 73 and len(episodes) == 124
    rows = []
    for record in keyhole.itertuples(index=False):
        count = int(record.labelled_frame_count)
        physical = int(record.relevant_physical_frame_count) - int(record.keyhole_frame_count)
        labels = np.array(["Scanning Stopped"] * count, dtype=object)
        timesteps = np.arange(count, dtype=np.int64)
        for segment in episodes[episodes["experiment_name"] == record.experiment_name].itertuples(index=False):
            labels[segment.start_frame_index : segment.end_frame_index + 1] = "Keyhole"
            timesteps[segment.start_frame_index] = segment.start_timestep
            timesteps[segment.end_frame_index] = segment.end_timestep
        timesteps = np.maximum.accumulate(timesteps)  # monotone; ties broken by frame_row_in_partition
        labels[np.flatnonzero(labels != "Keyhole")[:physical]] = "Conduction"
        rows.extend(
            {"partition": record.partition, "experiment_name": record.experiment_name, "timestep": int(t), "label_final": str(l)}
            for t, l in zip(timesteps, labels)
        )
    registry = data.experiment_registry(pd.DataFrame(rows))
    assert registry["experiment_name"].tolist() == keyhole["experiment_name"].tolist()
    for column in [
        "labelled_frame_count", "keyhole_frame_count", "relevant_physical_frame_count", "keyhole_segment_count",
        "maximum_keyhole_segment_frames", "first_keyhole_frame_index", "last_keyhole_frame_index",
        "first_keyhole_timestep", "last_keyhole_timestep", "repeated_keyhole_episodes",
    ]:
        assert np.array_equal(registry[column].to_numpy(dtype=float), keyhole[column].to_numpy(dtype=float)), column
    # the frozen CSV stores the fraction with 16 significant digits (last-bit rounding on read-back)
    fraction = registry["keyhole_fraction_of_relevant_physical_frames"].to_numpy()
    assert np.allclose(fraction, keyhole["keyhole_fraction_of_relevant_physical_frames"].to_numpy(), rtol=0.0, atol=1e-15)
    assert np.array_equal(fraction, registry["keyhole_frame_count"].to_numpy() / registry["relevant_physical_frame_count"].to_numpy())
