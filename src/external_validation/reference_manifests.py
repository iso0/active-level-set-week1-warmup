"""Export label-free OLD-407/OLD-405 overlap references without historical loaders."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from .common import ROOT, require, write_new_bytes
from .intake import MANIFEST_COLUMNS

OLD407 = ROOT / "outputs/week7_05_5_g3_robustness_transfer_analysis/current_revision_simulation_level_targets.parquet"
OLD405 = ROOT / "outputs/week7_06_real_data_boundary_active_level_set/primary_common_population.csv"


def _token(row):
    text = "|".join(f"{float(row[name]):.17g}" for name in ("P", "VX", "LS", "ST"))
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def export(output_directory):
    output_directory = Path(output_directory)
    a = pd.read_parquet(OLD407, columns=["experiment_name", "P_W", "VX_m_per_s", "LS_m", "ST_K"])
    a = a.rename(columns={"experiment_name": "sim_id", "P_W": "P", "VX_m_per_s": "VX",
                          "LS_m": "LS", "ST_K": "ST"})
    a["config_token"] = a.apply(_token, axis=1)
    a["group_token"] = a["config_token"]
    b = pd.read_csv(OLD405, usecols=["experiment_name", "P", "VX", "LS", "ST", "input_tuple_sha256"])
    b = b.rename(columns={"experiment_name": "sim_id", "input_tuple_sha256": "config_token"})
    b["group_token"] = b["config_token"]
    require(len(a) == 407 and len(b) == 405 and a.sim_id.is_unique and b.sim_id.is_unique,
            "Historical reference row/ID gate failed")
    require((b.apply(_token, axis=1) == b.config_token).all(), "OLD-405 input hash drift")
    a = a.loc[:, MANIFEST_COLUMNS]
    b = b.loc[:, MANIFEST_COLUMNS]
    by_id = a.set_index("sim_id")
    for row in b.itertuples(index=False):
        require(row.sim_id in by_id.index and row.config_token == by_id.loc[row.sim_id, "config_token"],
                "OLD-405 is not an exact input subset of OLD-407")
    output_directory.mkdir(parents=True, exist_ok=True)
    paths = {"OLD-407": output_directory / "OLD407_LABEL_FREE.csv",
             "OLD-405": output_directory / "OLD405_LABEL_FREE.csv"}
    write_new_bytes(paths["OLD-407"], a.to_csv(index=False, lineterminator="\n").encode())
    write_new_bytes(paths["OLD-405"], b.to_csv(index=False, lineterminator="\n").encode())
    return paths
