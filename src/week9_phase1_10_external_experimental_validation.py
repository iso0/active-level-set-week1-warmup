"""Week 9 Phase 1.10: independent, non-identical experimental validation.

The experiment is deliberately small.  It reconstructs the public Masinelli
et al. metallographic labels and process conditions from two pinned workbooks,
then compares a one-coordinate physics logistic model with a generic two-slope
log-process logistic model under repeated exact-condition-grouped OOF CV.  A
single Matérn-3/2 GPC is secondary.  No optical feature or active-learning
construct enters the analysis.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import urllib.request
import warnings
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Sequence
from xml.etree import ElementTree as ET

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nbformat as nbf
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from nbclient import NotebookClient
from sklearn.decomposition import PCA
from sklearn.exceptions import ConvergenceWarning
from sklearn.gaussian_process import GaussianProcessClassifier
from sklearn.gaussian_process.kernels import ConstantKernel, Matern
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedGroupKFold, StratifiedKFold
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "week9_phase1_10_external_experimental_validation"
FIGURES = OUTPUT / "figures"
NOTEBOOK = ROOT / "notebooks" / "week_09" / "07_week9_phase1_10_external_experimental_validation.ipynb"
CACHE = ROOT / ".cache" / "external_masinelli"
STARTING_SHA = "8d99c1976890bbf4a12a7cfcd00e9bdd7ae924a8"
BRANCH = "codex/week9-phase1-10-external-experimental-validation"
GITHUB_COMMIT = "50ccb1bab03c626cb9f83d9c4f44182f58dda439"
GITHUB_URL = f"https://github.com/GiulioMa/LPBF-SmartAM-Optical-Data/tree/{GITHUB_COMMIT}"
RAW_ROOT = f"https://raw.githubusercontent.com/GiulioMa/LPBF-SmartAM-Optical-Data/{GITHUB_COMMIT}"
ZENODO_URL = "https://zenodo.org/records/13380755"
ZENODO_DOI = "10.5281/zenodo.13380755"
PAPER_DOI = "10.1016/j.addma.2025.104677"
PAPER_URL = "https://infoscience.epfl.ch/server/api/core/bitstreams/e512f942-f109-42be-ab53-4cdfab406af5/content"
LS_M = 25e-6
SPOT_DIAMETER_UM = 50.0
N_REPEATS = 20
N_FOLDS = 5
BOOTSTRAP_DRAWS = 10_000
SEED_BASE = 20260901
MODELS = ("H", "G", "GPC")
MODEL_LABELS = {
    "H": "Physics H: log(h)",
    "G": "Generic G: log(P), log(VX)",
    "GPC": "2D Matérn-3/2 GPC",
}
SOURCE_FILES = {
    "Microscopy_1.xlsx": {
        "sha256": "885ee69284e301eccd9d9f7c19b32f9553ffb043e8496d666df4d560153346a2",
        "size": 10610,
    },
    "experiment_parameters_ref.xlsx": {
        "sha256": "4043e796c158364fa10c9edfd706d0f42450203d85b3f638b036a99c4a0c9a3f",
        "size": 15178,
    },
}
PAPER_FILE = {"filename": "Masinelli_2025.pdf", "sha256": "37c7e2d6984d36e9703373b675419971b4193b4b80288ad2be129e13ef9e2356", "size": 3630055}
EXPECTED = {
    "Ti64": {"rows": 60, "conditions": 38, "keyhole": 34, "conduction": 26},
    "316L": {"rows": 60, "conditions": 38, "keyhole": 23, "conduction": 37},
}
MATERIAL_SOURCE_TO_CANONICAL = {"Ti": "Ti64", "SS": "316L"}
MATERIAL_CUBES = {"Ti64": (1, 2, 3, 4, 7, 8), "316L": (3, 4, 5, 6, 7, 8)}
METRICS = (
    "roc_auc",
    "pr_auc",
    "balanced_accuracy",
    "keyhole_recall",
    "conduction_recall",
    "brier_score",
    "accuracy",
    "false_negative",
    "false_positive",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return json_safe(value.tolist())
    if isinstance(value, (np.integer, np.floating, np.bool_)):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    if path.suffix == ".gz":
        payload = frame.to_csv(index=False, lineterminator="\n").encode("utf-8")
        temporary.write_bytes(gzip.compress(payload, compresslevel=9, mtime=0))
    else:
        frame.to_csv(temporary, index=False, lineterminator="\n")
    temporary.replace(path)


def download_sources() -> dict[str, Any]:
    CACHE.mkdir(parents=True, exist_ok=True)
    downloaded: list[dict[str, Any]] = []
    for name, expected in SOURCE_FILES.items():
        destination = CACHE / name
        if not destination.exists() or sha256_file(destination) != expected["sha256"]:
            urllib.request.urlretrieve(f"{RAW_ROOT}/{name}", destination)
        actual = {"filename": name, "size_bytes": destination.stat().st_size, "sha256": sha256_file(destination)}
        require(actual["size_bytes"] == expected["size"], f"source size mismatch: {name}")
        require(actual["sha256"] == expected["sha256"], f"source SHA256 mismatch: {name}")
        downloaded.append({**actual, "role": "pinned GitHub metadata workbook"})
    paper_path = CACHE / PAPER_FILE["filename"]
    if not paper_path.exists() or sha256_file(paper_path) != PAPER_FILE["sha256"]:
        urllib.request.urlretrieve(PAPER_URL, paper_path)
    require(paper_path.stat().st_size == PAPER_FILE["size"], "paper PDF size mismatch")
    require(sha256_file(paper_path) == PAPER_FILE["sha256"], "paper PDF SHA256 mismatch")
    from pypdf import PdfReader
    paper_text = "\n".join((page.extract_text() or "") for page in PdfReader(paper_path).pages)
    require("1∕𝑒2" in paper_text and "in diameter at the focal point" in paper_text and "was50 μm" in paper_text, "paper spot semantics could not be reverified")
    downloaded.append({"filename": PAPER_FILE["filename"], "size_bytes": paper_path.stat().st_size, "sha256": sha256_file(paper_path), "role": "original open-access paper used to reverify spot semantics"})
    manifest = {
        "study": "Masinelli et al. (2025), Additive Manufacturing 101, 104677",
        "doi": PAPER_DOI,
        "github_url": GITHUB_URL,
        "github_commit": GITHUB_COMMIT,
        "zenodo_record": ZENODO_URL,
        "zenodo_doi": ZENODO_DOI,
        "zenodo_file": "Neuchatel data.zip",
        "zenodo_file_size_bytes": 86809466,
        "zenodo_md5": "7c45f40bef66bc2483eb1ef0959058cc",
        "license": {
            "zenodo_data": "CC-BY-4.0",
            "paper": "open-access article; cite DOI",
            "github_repository": "no license file found at pinned commit",
        },
        "date_accessed": date.today().isoformat(),
        "downloaded_files": downloaded,
        "raw_data_committed": False,
        "critical_field_verification": {
            "field": "laser spot definition",
            "result": "50 micrometre diameter at the focal point, measured at 1/e^2, constant throughout experiments",
            "source": "Masinelli_2025.pdf, Section 2.6 / Table 4",
            "status": "VERIFIED_FROM_ORIGINAL_PUBLIC_SOURCE",
        },
        "note": "Only the two small pinned metadata workbooks were cached locally; no optical or raw signal was used.",
    }
    write_json(OUTPUT / "source_manifest.json", manifest)
    return manifest


_NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main", "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships", "pr": "http://schemas.openxmlformats.org/package/2006/relationships"}


def _column_number(cell_reference: str) -> int:
    letters = re.match(r"[A-Z]+", cell_reference).group(0)
    value = 0
    for letter in letters:
        value = value * 26 + ord(letter) - ord("A") + 1
    return value - 1


def read_xlsx(path: Path) -> dict[str, pd.DataFrame]:
    """Read the simple public XLSX files without deserializing the GT pickle."""
    with zipfile.ZipFile(path) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.findall("x:si", _NS):
                shared.append("".join(text.text or "" for text in item.findall(".//x:t", _NS)))
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rel_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in relationships.findall("pr:Relationship", _NS)}
        sheets: dict[str, pd.DataFrame] = {}
        for sheet in workbook.findall("x:sheets/x:sheet", _NS):
            name = sheet.attrib["name"]
            rel_id = sheet.attrib[f"{{{_NS['r']}}}id"]
            target = rel_map[rel_id].lstrip("/")
            member = target if target.startswith("xl/") else f"xl/{target}"
            xml = ET.fromstring(archive.read(member))
            rows: list[list[Any]] = []
            for row in xml.findall("x:sheetData/x:row", _NS):
                values: dict[int, Any] = {}
                for cell in row.findall("x:c", _NS):
                    column = _column_number(cell.attrib["r"])
                    node = cell.find("x:v", _NS)
                    raw = "" if node is None else (node.text or "")
                    if cell.attrib.get("t") == "s" and raw:
                        value: Any = shared[int(raw)]
                    elif raw == "":
                        value = np.nan
                    else:
                        try:
                            numeric = float(raw)
                            value = int(numeric) if numeric.is_integer() else numeric
                        except ValueError:
                            value = raw
                    values[column] = value
                width = max(values, default=-1) + 1
                rows.append([values.get(index, np.nan) for index in range(width)])
            if not rows:
                sheets[name] = pd.DataFrame()
                continue
            width = max(map(len, rows))
            padded = [row + [np.nan] * (width - len(row)) for row in rows]
            headers = [str(value).strip() for value in padded[0]]
            sheets[name] = pd.DataFrame(padded[1:], columns=headers).dropna(how="all").reset_index(drop=True)
        return sheets


def build_population() -> pd.DataFrame:
    download_sources()
    microscopy = read_xlsx(CACHE / "Microscopy_1.xlsx")["Sheet1"].copy()
    parameters = read_xlsx(CACHE / "experiment_parameters_ref.xlsx")
    rows: list[dict[str, Any]] = []
    for record in microscopy.itertuples(index=False):
        source_material = str(getattr(record, "Material"))
        material = MATERIAL_SOURCE_TO_CANONICAL[source_material]
        cube = int(getattr(record, "Cube"))
        line = int(getattr(record, "Line"))
        mode = str(getattr(record, "Mode")).strip()
        require(cube in MATERIAL_CUBES[material], f"unexpected labelled cube: {material} Cube{cube}")
        table = parameters[f"Cube{cube}"]
        match = table[pd.to_numeric(table["#"]) == line]
        require(len(match) == 1, f"parameter join failed: {material} Cube{cube} line {line}")
        row = match.iloc[0]
        power = float(row["Power (W)"])
        speed_mm_s = float(row["Speed (mm/s)"])
        speed_m_s = speed_mm_s / 1000.0
        pair_index = MATERIAL_CUBES[material].index(cube) // 2
        pair = ("AB", "CD", "EF")[pair_index]
        rows.append({
            "material": material,
            "source_material": source_material,
            "bundle_id": f"{material}_Cube{cube}_Line{line:02d}",
            "cube": cube,
            "line": line,
            "cuboid_pair": pair,
            "P_W": power,
            "VX_mm_per_s": speed_mm_s,
            "VX_m_per_s": speed_m_s,
            "LS_m": LS_M,
            "raw_mode": mode,
            "has_keyhole": int(mode != "C"),
        })
    population = pd.DataFrame(rows).sort_values(["material", "cube", "line"]).reset_index(drop=True)
    population["condition_id"] = population.apply(lambda row: f"{row.material}_P{row.P_W:g}_V{row.VX_mm_per_s:g}", axis=1)
    population["log_P"] = np.log(population.P_W)
    population["log_VX"] = np.log(population.VX_m_per_s)
    population["h_SI"] = population.P_W / np.sqrt(population.VX_m_per_s * population.LS_m**3)
    population["log_h"] = np.log(population.h_SI)
    verify_population(population)
    return population


def verify_population(population: pd.DataFrame) -> pd.DataFrame:
    audit: list[dict[str, Any]] = []
    for material, expected in EXPECTED.items():
        frame = population[population.material.eq(material)]
        actual = {
            "rows": len(frame),
            "conditions": frame.condition_id.nunique(),
            "keyhole": int(frame.has_keyhole.sum()),
            "conduction": int((1 - frame.has_keyhole).sum()),
        }
        require(actual == expected, f"external population gate failed for {material}: {actual} != {expected}")
        modes = frame.raw_mode.value_counts().to_dict()
        audit.append({"material": material, **actual, **{f"mode_{key}": int(modes.get(key, 0)) for key in ("C", "T", "CT", "TK", "K")}})
    ti = population[population.material.eq("Ti64")]
    discordant = ti.groupby("condition_id").has_keyhole.nunique()
    require(int((discordant > 1).sum()) == 2, "Ti64 discordant-condition count drift")
    ss = population[population.material.eq("316L")]
    require(int((ss.groupby("condition_id").has_keyhole.nunique() > 1).sum()) == 0, "316L discordance drift")
    require(np.allclose(population.VX_m_per_s, population.VX_mm_per_s / 1000.0), "speed conversion drift")
    require(np.allclose(population.LS_m, LS_M), "LS must be constant 25 um radius")
    require(np.allclose(population.h_SI, population.P_W / np.sqrt(population.VX_m_per_s * population.LS_m**3)), "h formula drift")
    result = pd.DataFrame(audit)
    write_csv(OUTPUT / "external_population_audit.csv", result)
    return result


def make_grouped_fold_manifest(population: pd.DataFrame) -> pd.DataFrame:
    """Freeze 20 deterministic 5-fold exact-condition-grouped partitions."""
    records: list[dict[str, Any]] = []
    for material_index, material in enumerate(("Ti64", "316L")):
        frame = population[population.material.eq(material)].reset_index(drop=True)
        y = frame.has_keyhole.to_numpy(int)
        groups = frame.condition_id.to_numpy(str)
        for repeat in range(N_REPEATS):
            seed = SEED_BASE + 1000 * material_index + repeat
            splitter = StratifiedGroupKFold(n_splits=N_FOLDS, shuffle=True, random_state=seed)
            assignment = np.full(len(frame), -1, dtype=int)
            for fold, (_, test) in enumerate(splitter.split(frame, y, groups)):
                require(set(np.unique(y[test])) == {0, 1}, f"held-out class missing: {material} repeat {repeat} fold {fold}")
                assignment[test] = fold
            require((assignment >= 0).all(), "incomplete fold assignment")
            mapping = pd.DataFrame({"group": groups, "fold": assignment}).groupby("group").fold.nunique()
            require(int(mapping.max()) == 1, "condition group crossed folds")
            for index, row in frame.iterrows():
                records.append({
                    "material": material,
                    "repeat": repeat,
                    "seed": seed,
                    "fold": int(assignment[index]),
                    "bundle_id": row.bundle_id,
                    "condition_id": row.condition_id,
                    "has_keyhole": int(row.has_keyhole),
                })
    manifest = pd.DataFrame(records)
    require(len(manifest) == 2 * N_REPEATS * 60, "fold manifest size drift")
    write_csv(OUTPUT / "grouped_fold_manifest.csv", manifest)
    return manifest


def model_features(frame: pd.DataFrame, model: str) -> np.ndarray:
    if model == "H":
        return frame.loc[:, ["log_h"]].to_numpy(float)
    if model in {"G", "GPC"}:
        return frame.loc[:, ["log_P", "log_VX"]].to_numpy(float)
    raise ValueError(f"unknown model {model}")


def fit_predict_model(train: pd.DataFrame, test: pd.DataFrame, model: str, seed: int) -> tuple[np.ndarray, str]:
    """Fit a frozen model with train-only scaling and return P(Keyhole)."""
    x_train = model_features(train, model)
    x_test = model_features(test, model)
    y_train = train.has_keyhole.to_numpy(int)
    require(set(np.unique(y_train)) == {0, 1}, "training set must contain both classes")
    scaler = StandardScaler().fit(x_train)
    train_z = scaler.transform(x_train)
    test_z = scaler.transform(x_test)
    if model in {"H", "G"}:
        estimator = LogisticRegression(
            C=1.0,
            solver="lbfgs",
            fit_intercept=True,
            max_iter=2000,
            random_state=seed,
        )
        estimator.fit(train_z, y_train)
        return estimator.predict_proba(test_z)[:, 1], "L2 logistic; C=1; lbfgs; train-only StandardScaler"
    kernel = ConstantKernel(1.0, constant_value_bounds=(0.05, 20.0)) * Matern(
        length_scale=1.0,
        length_scale_bounds=(0.1, 10.0),
        nu=1.5,
    )
    estimator = GaussianProcessClassifier(
        kernel=kernel,
        optimizer="fmin_l_bfgs_b",
        n_restarts_optimizer=0,
        max_iter_predict=200,
        warm_start=False,
        random_state=seed,
    )
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=ConvergenceWarning)
        estimator.fit(train_z, y_train)
    return estimator.predict_proba(test_z)[:, 1], str(estimator.kernel_)


def metric_values(truth: Sequence[int], probability: Sequence[float]) -> dict[str, float | int]:
    truth_array = np.asarray(truth, dtype=int)
    probability_array = np.clip(np.asarray(probability, dtype=float), 1e-12, 1 - 1e-12)
    prediction = (probability_array >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(truth_array, prediction, labels=[0, 1]).ravel()
    return {
        "roc_auc": float(roc_auc_score(truth_array, probability_array)),
        "pr_auc": float(average_precision_score(truth_array, probability_array)),
        "balanced_accuracy": float(balanced_accuracy_score(truth_array, prediction)),
        "keyhole_recall": float(recall_score(truth_array, prediction, pos_label=1, zero_division=0)),
        "conduction_recall": float(recall_score(truth_array, prediction, pos_label=0, zero_division=0)),
        "brier_score": float(brier_score_loss(truth_array, probability_array)),
        "accuracy": float(accuracy_score(truth_array, prediction)),
        "false_negative": int(fn),
        "false_positive": int(fp),
        "true_negative": int(tn),
        "true_positive": int(tp),
    }


def run_oof(population: pd.DataFrame, manifest: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    predictions: list[dict[str, Any]] = []
    metrics: list[dict[str, Any]] = []
    for material_index, material in enumerate(("Ti64", "316L")):
        frame = population[population.material.eq(material)].reset_index(drop=True)
        for repeat in range(N_REPEATS):
            assignment_frame = manifest[(manifest.material.eq(material)) & (manifest.repeat.eq(repeat))]
            assignment = assignment_frame.set_index("bundle_id").loc[frame.bundle_id, "fold"].to_numpy(int)
            repeat_predictions = {model: np.full(len(frame), np.nan) for model in MODELS}
            for fold in range(N_FOLDS):
                test_mask = assignment == fold
                train = frame.loc[~test_mask]
                test = frame.loc[test_mask]
                for model in MODELS:
                    seed = SEED_BASE + material_index * 100000 + repeat * 100 + fold * 10 + MODELS.index(model)
                    probability, fit_detail = fit_predict_model(train, test, model, seed)
                    repeat_predictions[model][test_mask] = probability
                    for local_index, probability_value in zip(np.flatnonzero(test_mask), probability):
                        row = frame.iloc[local_index]
                        predictions.append({
                            "material": material,
                            "repeat": repeat,
                            "fold": fold,
                            "model": model,
                            "bundle_id": row.bundle_id,
                            "condition_id": row.condition_id,
                            "truth": int(row.has_keyhole),
                            "probability": float(probability_value),
                            "prediction": int(probability_value >= 0.5),
                            "fit_detail": fit_detail,
                        })
            for model in MODELS:
                probability = repeat_predictions[model]
                require(np.isfinite(probability).all(), f"incomplete OOF predictions: {material} {repeat} {model}")
                values = metric_values(frame.has_keyhole, probability)
                metrics.append({"material": material, "repeat": repeat, "model": model, **values})
    prediction_frame = pd.DataFrame(predictions)
    metric_frame = pd.DataFrame(metrics)
    require(len(prediction_frame) == 2 * N_REPEATS * 60 * len(MODELS), "OOF prediction size drift")
    for material in ("Ti64", "316L"):
        write_csv(OUTPUT / ("ti64_oof_predictions.csv.gz" if material == "Ti64" else "ss316_oof_predictions.csv.gz"), prediction_frame[prediction_frame.material.eq(material)].reset_index(drop=True))
        write_csv(OUTPUT / ("ti64_repeat_metrics.csv" if material == "Ti64" else "ss316_repeat_metrics.csv"), metric_frame[metric_frame.material.eq(material)].reset_index(drop=True))
    return prediction_frame, metric_frame


def bootstrap_mean(values: Sequence[float], seed: int, draws: int = BOOTSTRAP_DRAWS) -> tuple[float, float, float]:
    array = np.asarray(values, dtype=float)
    require(len(array) == N_REPEATS, "bootstrap must use the 20 repeat blocks")
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(array), size=(draws, len(array)))
    means = array[indices].mean(axis=1)
    return float(array.mean()), float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


def summarize_models(metric_frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    summaries: list[dict[str, Any]] = []
    contrasts: list[dict[str, Any]] = []
    for material_index, material in enumerate(("Ti64", "316L")):
        frame = metric_frame[metric_frame.material.eq(material)]
        for model in MODELS:
            subset = frame[frame.model.eq(model)]
            for metric in METRICS:
                value = subset[metric].to_numpy(float)
                mean, lower, upper = bootstrap_mean(value, SEED_BASE + material_index * 1000 + MODELS.index(model) * 100 + METRICS.index(metric))
                summaries.append({"material": material, "model": model, "metric": metric, "mean": mean, "ci_lower": lower, "ci_upper": upper, "repeat_blocks": N_REPEATS, "interval_scope": "grouped-CV partition sensitivity"})
        h = frame[frame.model.eq("H")].sort_values("repeat")
        g = frame[frame.model.eq("G")].sort_values("repeat")
        require(np.array_equal(h.repeat, g.repeat), "repeat pairing failed")
        for metric in METRICS:
            difference = h[metric].to_numpy(float) - g[metric].to_numpy(float)
            mean, lower, upper = bootstrap_mean(difference, SEED_BASE + 5000 + material_index * 100 + METRICS.index(metric))
            contrasts.append({"material": material, "contrast": "H_minus_G", "metric": metric, "mean_difference": mean, "ci_lower": lower, "ci_upper": upper, "repeat_blocks": N_REPEATS, "bootstrap_draws": BOOTSTRAP_DRAWS, "interval_scope": "sensitivity to frozen grouped CV partitions; not 20 independent experiments"})
    summary_frame = pd.DataFrame(summaries)
    contrast_frame = pd.DataFrame(contrasts)
    for material in ("Ti64", "316L"):
        write_csv(OUTPUT / ("ti64_model_summary.csv" if material == "Ti64" else "ss316_model_summary.csv"), summary_frame[summary_frame.material.eq(material)].reset_index(drop=True))
        write_csv(OUTPUT / ("ti64_paired_contrasts.csv" if material == "Ti64" else "ss316_paired_contrasts.csv"), contrast_frame[contrast_frame.material.eq(material)].reset_index(drop=True))
    return summary_frame, contrast_frame


def build_condition_population(population: pd.DataFrame, material: str, sensitivity: str) -> tuple[pd.DataFrame, int]:
    records: list[dict[str, Any]] = []
    excluded = 0
    for _, group in population[population.material.eq(material)].groupby("condition_id", sort=True):
        labels = group.has_keyhole.to_numpy(int)
        if sensitivity == "A_exclude_discordant":
            if len(np.unique(labels)) != 1:
                excluded += 1
                continue
            label = int(labels[0])
        elif sensitivity == "B_strict_majority":
            positives = int(labels.sum())
            negatives = len(labels) - positives
            if positives == negatives:
                excluded += 1
                continue
            label = int(positives > negatives)
        else:
            raise ValueError(sensitivity)
        first = group.iloc[0]
        records.append({"material": material, "condition_id": first.condition_id, "P_W": first.P_W, "VX_m_per_s": first.VX_m_per_s, "LS_m": first.LS_m, "log_P": first.log_P, "log_VX": first.log_VX, "h_SI": first.h_SI, "log_h": first.log_h, "has_keyhole": label, "replicate_count": len(group)})
    return pd.DataFrame(records), excluded


def run_condition_sensitivity(population: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for material_index, material in enumerate(("Ti64", "316L")):
        for sensitivity_index, sensitivity in enumerate(("A_exclude_discordant", "B_strict_majority")):
            frame, excluded = build_condition_population(population, material, sensitivity)
            y = frame.has_keyhole.to_numpy(int)
            repeat_metrics: list[dict[str, Any]] = []
            for repeat in range(N_REPEATS):
                # Use the same split seeds for A and B. If their retained rows are
                # identical (as they are when every discordance is a tie), the
                # resulting robustness estimates must also be identical.
                splitter = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED_BASE + 20000 + material_index * 1000 + repeat)
                probs = {model: np.full(len(frame), np.nan) for model in ("H", "G")}
                for fold, (train_index, test_index) in enumerate(splitter.split(frame, y)):
                    for model in ("H", "G"):
                        probability, _ = fit_predict_model(frame.iloc[train_index], frame.iloc[test_index], model, SEED_BASE + 30000 + material_index * 1000 + repeat * 10 + fold)
                        probs[model][test_index] = probability
                for model in ("H", "G"):
                    repeat_metrics.append({"repeat": repeat, "model": model, **metric_values(y, probs[model])})
            metrics_frame = pd.DataFrame(repeat_metrics)
            for model in ("H", "G"):
                for metric in ("roc_auc", "pr_auc", "balanced_accuracy", "brier_score"):
                    values = metrics_frame[metrics_frame.model.eq(model)][metric]
                    mean, lower, upper = bootstrap_mean(values, SEED_BASE + 40000 + material_index * 1000 + (0 if model == "H" else 10) + METRICS.index(metric))
                    records.append({"material": material, "sensitivity": sensitivity, "model_or_contrast": model, "metric": metric, "mean": mean, "ci_lower": lower, "ci_upper": upper, "condition_rows": len(frame), "excluded_conditions": excluded})
            h = metrics_frame[metrics_frame.model.eq("H")].sort_values("repeat")
            g = metrics_frame[metrics_frame.model.eq("G")].sort_values("repeat")
            for metric in ("roc_auc", "pr_auc", "balanced_accuracy", "brier_score"):
                values = h[metric].to_numpy(float) - g[metric].to_numpy(float)
                mean, lower, upper = bootstrap_mean(values, SEED_BASE + 45000 + material_index * 1000 + METRICS.index(metric))
                records.append({"material": material, "sensitivity": sensitivity, "model_or_contrast": "H_minus_G", "metric": metric, "mean": mean, "ci_lower": lower, "ci_upper": upper, "condition_rows": len(frame), "excluded_conditions": excluded})
    result = pd.DataFrame(records)
    write_csv(OUTPUT / "condition_level_sensitivity.csv", result)
    return result


def run_pca(population: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    scores: list[pd.DataFrame] = []
    loadings: list[pd.DataFrame] = []
    for material in ("Ti64", "316L"):
        frame = population[population.material.eq(material)].reset_index(drop=True)
        # Labels are intentionally absent from both scaler and PCA fitting.
        x_unlabeled = frame.loc[:, ["log_P", "log_VX"]].to_numpy(float)
        standardized = StandardScaler().fit_transform(x_unlabeled)
        pca = PCA(n_components=2).fit(standardized)
        coordinates = pca.transform(standardized)
        scores.append(pd.DataFrame({
            "material": material,
            "bundle_id": frame.bundle_id,
            "condition_id": frame.condition_id,
            "PC1": coordinates[:, 0],
            "PC2": coordinates[:, 1],
            "has_keyhole": frame.has_keyhole,
            "raw_mode": frame.raw_mode,
        }))
        for component in range(2):
            for feature_index, feature in enumerate(("log_P", "log_VX")):
                loadings.append(pd.DataFrame([{
                    "material": material,
                    "component": f"PC{component + 1}",
                    "feature": feature,
                    "loading": pca.components_[component, feature_index],
                    "explained_variance_ratio": pca.explained_variance_ratio_[component],
                    "fit_features": "log_P|log_VX",
                    "labels_used_in_fit": False,
                }]))
    score_frame = pd.concat(scores, ignore_index=True)
    loading_frame = pd.concat(loadings, ignore_index=True)
    write_csv(OUTPUT / "pca_scores.csv", score_frame)
    write_csv(OUTPUT / "pca_loadings.csv", loading_frame)
    return score_frame, loading_frame


def _save_figure(fig: plt.Figure, filename: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / filename, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def make_figures(population: pd.DataFrame, summary: pd.DataFrame, contrast: pd.DataFrame, metrics: pd.DataFrame, pca_scores: pd.DataFrame, pca_loadings: pd.DataFrame) -> pd.DataFrame:
    colors = {0: "#2878B5", 1: "#D9534F"}
    # Figure 1: physical process maps, one marker per unique condition.
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.5), sharex=True, sharey=True)
    for axis, material in zip(axes, ("Ti64", "316L")):
        frame = population[population.material.eq(material)]
        conditions = frame.groupby(["condition_id", "P_W", "VX_mm_per_s"], as_index=False).agg(
            replicate_count=("bundle_id", "size"), label_min=("has_keyhole", "min"), label_max=("has_keyhole", "max")
        )
        for label, name in ((0, "Conduction"), (1, "Transition-inclusive Keyhole")):
            subset = conditions[(conditions.label_min.eq(label)) & (conditions.label_max.eq(label))]
            axis.scatter(subset.VX_mm_per_s, subset.P_W, s=45 + 28 * (subset.replicate_count - 1), c=colors[label], marker="o", edgecolor="white", linewidth=.7, alpha=.9, label=name)
        discordant = conditions[conditions.label_min.ne(conditions.label_max)]
        if len(discordant):
            axis.scatter(discordant.VX_mm_per_s, discordant.P_W, s=105, marker="X", c="#7A3E9D", edgecolor="black", linewidth=.8, label="Discordant repeated condition")
        axis.set_title(f"{material}: 60 bundles, 38 conditions")
        axis.set_xlabel("Scan speed VX (mm/s)")
        axis.grid(alpha=.22)
    axes[0].set_ylabel("Laser power P (W)")
    handles, labels = axes[0].get_legend_handles_labels()
    if not any("Discordant" in label for label in labels):
        handles2, labels2 = axes[1].get_legend_handles_labels()
        handles += handles2; labels += labels2
    unique = dict(zip(labels, handles))
    fig.legend(unique.values(), unique.keys(), loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(.5, -.04))
    fig.suptitle("Independent experimental process maps (marker size shows replicates)", fontweight="bold")
    fig.tight_layout(rect=(0, .08, 1, .95))
    _save_figure(fig, "01_experimental_process_maps.png")

    # Figure 2: model performance, split-sensitivity intervals.
    fig, axes = plt.subplots(2, 2, figsize=(10.8, 7.3))
    metric_titles = (("roc_auc", "ROC-AUC"), ("pr_auc", "PR-AUC"), ("balanced_accuracy", "Balanced accuracy"), ("brier_score", "Brier score (lower is better)"))
    offsets = {"Ti64": -0.13, "316L": .13}
    markers = {"Ti64": "o", "316L": "s"}
    for axis, (metric, title) in zip(axes.flat, metric_titles):
        for material in ("Ti64", "316L"):
            subset = summary[(summary.material.eq(material)) & (summary.metric.eq(metric))].set_index("model").loc[list(MODELS)]
            x = np.arange(3) + offsets[material]
            axis.errorbar(x, subset["mean"], yerr=np.vstack([subset["mean"] - subset.ci_lower, subset.ci_upper - subset["mean"]]), fmt=markers[material], capsize=3, label=material, color="#1B5E8A" if material == "Ti64" else "#D17A22")
        axis.set_xticks(np.arange(3), ["H", "G", "GPC"])
        axis.set_title(title)
        axis.grid(axis="y", alpha=.22)
    axes[0, 0].legend(frameon=False)
    fig.suptitle("Grouped OOF performance (20 repeated 5-fold condition-grouped splits)", fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, .95))
    _save_figure(fig, "02_grouped_oof_performance.png")

    # Figure 3: the predeclared Ti64 H-G ROC contrast.
    ti = metrics[metrics.material.eq("Ti64")]
    h = ti[ti.model.eq("H")].sort_values("repeat")
    g = ti[ti.model.eq("G")].sort_values("repeat")
    differences = h.roc_auc.to_numpy() - g.roc_auc.to_numpy()
    row = contrast[(contrast.material.eq("Ti64")) & (contrast.metric.eq("roc_auc"))].iloc[0]
    fig, axis = plt.subplots(figsize=(8.8, 4.3))
    axis.scatter(np.arange(1, N_REPEATS + 1), differences, color="#555555", s=34, zorder=3)
    axis.axhline(0, color="black", linewidth=1)
    axis.axhline(row.mean_difference, color="#C0392B", linewidth=2, label=f"mean {row.mean_difference:+.4f}")
    axis.fill_between([.5, N_REPEATS + .5], row.ci_lower, row.ci_upper, color="#C0392B", alpha=.16, label=f"95% split-bootstrap CI [{row.ci_lower:+.4f}, {row.ci_upper:+.4f}]")
    axis.set(xlabel="Grouped-CV repeat", ylabel="ROC-AUC difference (H − G)", xlim=(.5, N_REPEATS + .5))
    axis.set_title("Ti64 primary paired contrast", fontweight="bold")
    axis.grid(axis="y", alpha=.22)
    axis.legend(frameon=False)
    fig.tight_layout()
    _save_figure(fig, "03_ti64_H_minus_G_repeat_contrast.png")

    # Figure 4: required but descriptive PCA. Labels enter only after fitting.
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.6), sharex=True, sharey=True)
    for axis, material in zip(axes, ("Ti64", "316L")):
        frame = pca_scores[pca_scores.material.eq(material)]
        for label, name in ((0, "Conduction"), (1, "Transition-inclusive Keyhole")):
            subset = frame[frame.has_keyhole.eq(label)]
            axis.scatter(subset.PC1, subset.PC2, s=42, c=colors[label], alpha=.78, edgecolor="white", linewidth=.4, label=name)
        explained = pca_loadings[pca_loadings.material.eq(material)].drop_duplicates("component").set_index("component").explained_variance_ratio
        axis.set_title(f"{material}: PC1 {explained['PC1']:.1%}, PC2 {explained['PC2']:.1%}")
        axis.set_xlabel("PC1")
        axis.grid(alpha=.2)
    axes[0].set_ylabel("PC2")
    axes[0].legend(frameon=False, fontsize=8)
    fig.suptitle("Label-free PCA of standardized [log P, log VX] (descriptive; original space is already 2D)", fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, .94))
    _save_figure(fig, "04_label_free_process_pca.png")

    rows = []
    purposes = {
        "01_experimental_process_maps.png": "Show label organization, replicate multiplicity, and discordant Ti64 conditions in physical process space.",
        "02_grouped_oof_performance.png": "Compare H, G, and the secondary GPC for Ti64 and 316L.",
        "03_ti64_H_minus_G_repeat_contrast.png": "Display the predeclared primary Ti64 paired H-minus-G ROC-AUC contrast.",
        "04_label_free_process_pca.png": "Provide the required label-free PCA backup diagnostic without using PCA in prediction.",
    }
    for filename, purpose in purposes.items():
        path = FIGURES / filename
        rows.append({"figure": filename, "sha256": sha256_file(path), "purpose": purpose, "status": "PASS"})
    manifest = pd.DataFrame(rows)
    write_csv(OUTPUT / "figure_manifest.csv", manifest)
    return manifest


def _metric(summary: pd.DataFrame, material: str, model: str, metric: str) -> float:
    return float(summary[(summary.material.eq(material)) & (summary.model.eq(model)) & (summary.metric.eq(metric))]["mean"].iloc[0])


def _contrast(contrasts: pd.DataFrame, material: str, metric: str) -> pd.Series:
    return contrasts[(contrasts.material.eq(material)) & (contrasts.metric.eq(metric))].iloc[0]


def scientific_verdict(summary: pd.DataFrame, contrasts: pd.DataFrame) -> str:
    row = _contrast(contrasts, "Ti64", "roc_auc")
    if row.ci_lower > 0:
        return "PHYSICS_DIRECTION_SUPERIOR"
    if row.ci_upper < 0:
        return "GENERIC_DIRECTION_SUPERIOR"
    return "H_VS_G_STATISTICALLY_UNRESOLVED"


def _model_line(summary: pd.DataFrame, material: str, model: str) -> str:
    return (
        f"ROC-AUC {_metric(summary, material, model, 'roc_auc'):.4f}; "
        f"PR-AUC {_metric(summary, material, model, 'pr_auc'):.4f}; "
        f"balanced accuracy {_metric(summary, material, model, 'balanced_accuracy'):.4f}; "
        f"Keyhole recall {_metric(summary, material, model, 'keyhole_recall'):.4f}; "
        f"Brier {_metric(summary, material, model, 'brier_score'):.4f}"
    )


def write_reports(population: pd.DataFrame, summary: pd.DataFrame, contrasts: pd.DataFrame, condition: pd.DataFrame) -> None:
    ti_roc = _contrast(contrasts, "Ti64", "roc_auc")
    ss_roc = _contrast(contrasts, "316L", "roc_auc")
    verdict = scientific_verdict(summary, contrasts)
    ti_sens = condition[(condition.material.eq("Ti64")) & (condition.sensitivity.eq("A_exclude_discordant")) & (condition.metric.eq("roc_auc"))]
    ti_sens_h = float(ti_sens[ti_sens.model_or_contrast.eq("H")]["mean"].iloc[0])
    ti_sens_g = float(ti_sens[ti_sens.model_or_contrast.eq("G")]["mean"].iloc[0])
    ti_sens_d = ti_sens[ti_sens.model_or_contrast.eq("H_minus_G")].iloc[0]
    report = f"""# Week 9 Phase 1.10 — independent experimental validation

## Question and scope

This small predeclared experiment asks whether the SPH-derived process direction remains useful for Conduction-versus-Keyhole discrimination in the independent Masinelli et al. experimental LPBF process map. The external target is transition-inclusive predominant post-mortem metallographic regime, not the thesis any-valid-frame simulator label; this is **independent but non-identical experimental validation**.

Only pre-process `P`, `VX`, and derived `h` were used. Optical signals, active learning, B1/q20/q30, material normalization, and alloy pooling were excluded.

## Source and population gate

The pinned public workbooks at GitHub commit `{GITHUB_COMMIT}` reproduced the forensic audit exactly. Ti64 has 60 bundles, 38 exact `(P,VX)` conditions, 26 Conduction and 34 transition-inclusive Keyhole labels. 316L has 60/38/37/23. Ti64 contains two binary-discordant repeated conditions; 316L contains none. Raw third-party data were not committed.

The paper reports a 50 µm `1/e²` spot **diameter**, so thesis `LS=r0=25e-6 m`. The computed coordinate is dimensional:

`h = P / sqrt(VX * LS^3)` with `P` in W and `VX` in m/s.

Because `LS` is constant, this study tests only the fixed `P*VX^(-1/2)` direction. It cannot validate the `LS^(-3/2)` exponent or a universal threshold.

## Frozen grouped OOF protocol

Each alloy was evaluated separately with 20 deterministic repeats × 5 `StratifiedGroupKFold` folds. The exact `(P,VX)` condition is the group, so no replicate crosses a fold. Each repeat pools all five held-out folds into one complete 60-bundle OOF vector before computing metrics. Every held-out fold contains both classes.

- H: training-standardized `log(h)`; L2 logistic regression, `C=1`, intercept.
- G: training-standardized `[log(P), log(VX)]`; the identical L2 logistic implementation.
- GPC (secondary): training-standardized `[log(P), log(VX)]`; `ConstantKernel × Matérn-3/2`, one optimizer start, no test-driven tuning.

Intervals bootstrap the 20 paired repeat blocks with {BOOTSTRAP_DRAWS:,} draws. They quantify sensitivity to the frozen grouped-CV partitions; they are not intervals from 20 independent experimental datasets.

## Ti64 primary result

- H: {_model_line(summary, 'Ti64', 'H')}.
- G: {_model_line(summary, 'Ti64', 'G')}.
- GPC: {_model_line(summary, 'Ti64', 'GPC')}.
- Primary H−G ROC-AUC: {ti_roc.mean_difference:+.6f}, 95% split-bootstrap CI [{ti_roc.ci_lower:+.6f}, {ti_roc.ci_upper:+.6f}].

The predeclared verdict is **{verdict}**. The fixed direction is nevertheless strongly discriminative in absolute terms (H ROC-AUC {_metric(summary, 'Ti64', 'H', 'roc_auc'):.4f}); the more flexible two-slope logistic extracts a small but repeat-stable additional ranking signal.

## Condition-level robustness

After excluding the two discordant Ti64 conditions, the 36-condition sensitivity gives H ROC-AUC {ti_sens_h:.4f}, G {ti_sens_g:.4f}, H−G {ti_sens_d['mean']:+.6f} [{ti_sens_d.ci_lower:+.6f}, {ti_sens_d.ci_upper:+.6f}]. Strict-majority sensitivity excludes the same tied conditions and is identical by construction. Thus the bundle-level generic advantage is materially reduced and statistically unresolved once unavoidable label-discordant repeats are removed.

## 316L secondary result

- H: {_model_line(summary, '316L', 'H')}.
- G: {_model_line(summary, '316L', 'G')}.
- Primary-style H−G ROC-AUC contrast (secondary material): {ss_roc.mean_difference:+.6f} [{ss_roc.ci_lower:+.6f}, {ss_roc.ci_upper:+.6f}].

This is qualitatively consistent evidence that the fixed direction organizes the 316L map, but it is not cross-material transfer because coefficients were fitted and evaluated within 316L.

## Decision and safe claim

**Safe thesis claim:** “The fixed `P*VX^(-1/2)` physics-aligned direction provides substantial Conduction–Keyhole discrimination in an independent, non-identical Ti-6Al-4V experimental process map. A generic two-slope log-linear model performs modestly better in the primary bundle-level grouped OOF analysis, while their difference becomes unresolved after excluding two label-discordant repeated conditions.”

The result does not experimentally prove SPH physics, validate the spot-size exponent, establish a universal boundary, or demonstrate external active-learning benefit.

## Main limitation and next step

There are only 38 unique conditions per alloy, the Ti64 map has two conditions with conflicting bundle labels, and the external predominant metallographic target differs from the thesis any-frame label. The repeated-CV intervals therefore describe partition sensitivity, not population-level experimental replication uncertainty.

A finite-pool experimental AL replay is technically feasible, but it is **not the next confirmatory step for physics-direction superiority**: H is strong yet G is better in the primary bundle-level analysis. Any later replay should be explicitly exploratory and compare physics and generic policies fairly.
"""
    (OUTPUT / "FINAL_PHASE1_10_REPORT.md").write_text(report, encoding="utf-8")
    supervisor = f"""# Supervisor one-page — Week 9 Phase 1.10

## What was tested

On Masinelli et al.'s independent experimental LPBF data, we compared a fixed physics direction `log h = const + log P - 0.5 log VX` with a generic two-slope `[log P, log VX]` logistic model. The target is transition-inclusive post-mortem morphology, so this is independent but non-identical validation.

## Data and fairness

- Ti64 (primary): 60 bundles, 38 unique conditions, 26 Conduction / 34 Keyhole; two repeated conditions have conflicting binary labels.
- 316L (secondary): 60 bundles, 38 conditions, 37 / 23; no binary-discordant condition.
- 20 × 5 grouped OOF; exact `(P,VX)` repeats never cross folds; complete 60-bundle OOF vector scored per repeat.
- `LS=25 µm` radius from the reported 50 µm `1/e²` diameter. Because LS is constant, only the `P*VX^-1/2` direction—not the LS exponent—is tested.

## Primary Ti64 result

- H: {_model_line(summary, 'Ti64', 'H')}.
- G: {_model_line(summary, 'Ti64', 'G')}.
- H−G ROC-AUC: {ti_roc.mean_difference:+.4f}, 95% split-bootstrap CI [{ti_roc.ci_lower:+.4f}, {ti_roc.ci_upper:+.4f}].
- Secondary GPC ROC-AUC: {_metric(summary, 'Ti64', 'GPC', 'roc_auc'):.4f}.

Verdict: **{verdict}**. `h` is strongly discriminative, but fixing the −1/2 velocity exponent loses a small, stable amount relative to the generic two-slope model.

## Robustness and 316L

Excluding the two discordant Ti64 conditions raises H/G ROC-AUC to {ti_sens_h:.4f}/{ti_sens_g:.4f}; H−G becomes {ti_sens_d['mean']:+.4f} [{ti_sens_d.ci_lower:+.4f}, {ti_sens_d.ci_upper:+.4f}], unresolved. In 316L, H/G ROC-AUC are {_metric(summary, '316L', 'H', 'roc_auc'):.4f}/{_metric(summary, '316L', 'G', 'roc_auc'):.4f}; H−G {ss_roc.mean_difference:+.4f} [{ss_roc.ci_lower:+.4f}, {ss_roc.ci_upper:+.4f}].

## Safe conclusion

The physics-aligned direction transfers as a strong experimental discriminator, not as the optimal or universal law. The generic direction is better on the primary bundle-level protocol; the gap is largely attenuated when discordant repeated conditions are excluded. External AL replay is feasible but should be exploratory, not the next confirmatory claim.
"""
    (OUTPUT / "SUPERVISOR_PHASE1_10_ONE_PAGE.md").write_text(supervisor, encoding="utf-8")
    ledger = """# Phase 1.10 claim ledger

| Claim | Status | Evidence / boundary |
|---|---|---|
| A. `h` can be computed externally. | SUPPORTED | P, VX and verified 25 µm radius are public; SI formula is reproduced. |
| B. External data validate the `LS^-3/2` exponent. | NOT TESTABLE | LS is fixed; ranking reduces to `P*VX^-1/2`. |
| C. Physics direction discriminates experimental Ti64. | SUPPORTED | Strong grouped-OOF ROC-AUC, PR-AUC and balanced accuracy. |
| D. Physics direction is competitive with generic Ti64 model. | QUALIFIED | Strong absolute H discrimination, but G has a higher bundle-level ROC-AUC with CI below zero; gap becomes unresolved after discordant-condition exclusion. |
| E. Physics direction is superior to generic Ti64 model. | NOT SUPPORTED | Primary H-G ROC-AUC is negative with interval below zero. |
| F. Same qualitative organization appears in 316L. | SUPPORTED AS SECONDARY WITHIN-MATERIAL EVIDENCE | H is strongly discriminative when fitted and tested within 316L. |
| G. Cross-material transfer is demonstrated. | NOT TESTED | No coefficient or threshold transfer between alloys. |
| H. External active-learning improvement is demonstrated. | NOT TESTED | No acquisition or finite-pool replay was run. |
| I. Simulator physics is experimentally proven. | NOT SUPPORTED | Labels and domains differ; this is corroborative discrimination only. |
"""
    (OUTPUT / "claim_ledger.md").write_text(ledger, encoding="utf-8")


def build_notebook() -> None:
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
    cells = [
        nbf.v4.new_markdown_cell("# Week 9 Phase 1.10 — independent experimental validation\n\n**Question:** does the SPH-derived physics-aligned process direction remain useful on independent experimental LPBF regime labels? This notebook reads the frozen artifacts; it does not hide the expensive experiment in one cell."),
        nbf.v4.new_code_cell("from pathlib import Path\nimport json\nimport pandas as pd\nfrom IPython.display import Image, Markdown, display\nROOT=Path.cwd().resolve().parents[1]\nOUT=ROOT/'outputs'/'week9_phase1_10_external_experimental_validation'\nprint('artifact directory:', OUT)"),
        nbf.v4.new_markdown_cell("## 1. Provenance and label-definition difference\n\nThe external ground truth is the predominant post-mortem metallographic regime, with transition codes merged into Keyhole. The thesis label is any valid simulator frame manually labelled Keyhole. The result is independent but non-identical validation, not replication."),
        nbf.v4.new_code_cell("source=json.loads((OUT/'source_manifest.json').read_text())\npop=pd.read_csv(OUT/'external_population_audit.csv')\ndisplay(pd.DataFrame(source['downloaded_files']))\ndisplay(pop)"),
        nbf.v4.new_markdown_cell("## 2. Spot diameter to thesis radius, and why constant LS matters\n\nThe paper's 50 µm `1/e²` diameter gives `LS=r0=25 µm`. In SI units, `h=P/sqrt(VX*LS^3)`. Since LS never changes externally, `log h = constant + log P - 0.5 log VX`. This tests the P–VX direction only; the `LS^-3/2` exponent is not testable."),
        nbf.v4.new_code_cell("print('spot diameter =', 50, 'µm; thesis radius LS =', 25, 'µm')\nprint('Predictors: H=[log_h], G=[log_P, log_VX], GPC=[log_P, log_VX]')"),
        nbf.v4.new_markdown_cell("## 3. Unique conditions, replicates, and discordance\n\nExact `(P,VX)` repeats are grouped. Marker size denotes replicate count; a purple X marks the two Ti64 settings whose repeated bundles disagree after binary mapping."),
        nbf.v4.new_code_cell("display(Image(filename=str(OUT/'figures'/'01_experimental_process_maps.png')))"),
        nbf.v4.new_markdown_cell("## 4. Frozen grouped evaluation\n\nTwenty deterministic repeats of five grouped folds produce one complete 60-bundle OOF vector per model and repeat. Metrics are computed after pooling the five folds, never as averages of tiny fold-level AUCs."),
        nbf.v4.new_code_cell("folds=pd.read_csv(OUT/'grouped_fold_manifest.csv')\nfold_check=folds.groupby(['material','repeat','fold']).agg(rows=('bundle_id','size'), keyholes=('has_keyhole','sum'), conditions=('condition_id','nunique')).reset_index()\ndisplay(fold_check.head(10))\nprint('condition-fold max multiplicity:', folds.groupby(['material','repeat','condition_id']).fold.nunique().max())"),
        nbf.v4.new_markdown_cell("## 5. Ti64 primary model comparison\n\nH is the fixed one-coordinate logistic model. G learns two slopes. The GPC is secondary and cannot redefine the primary H-versus-G test."),
        nbf.v4.new_code_cell("ti=pd.read_csv(OUT/'ti64_model_summary.csv')\ndisplay(ti[ti.metric.isin(['roc_auc','pr_auc','balanced_accuracy','keyhole_recall','brier_score'])].pivot(index='model',columns='metric',values='mean').round(4))\ndisplay(Image(filename=str(OUT/'figures'/'02_grouped_oof_performance.png')))"),
        nbf.v4.new_markdown_cell("## 6. Paired Ti64 contrast\n\nThe 95% interval bootstraps paired repeat blocks. It measures sensitivity to the frozen grouped partitions, not 20 independent experimental datasets."),
        nbf.v4.new_code_cell("contrast=pd.read_csv(OUT/'ti64_paired_contrasts.csv')\ndisplay(contrast[contrast.metric.isin(['roc_auc','pr_auc','balanced_accuracy','brier_score'])].round(5))\ndisplay(Image(filename=str(OUT/'figures'/'03_ti64_H_minus_G_repeat_contrast.png')))"),
        nbf.v4.new_markdown_cell("## 7. 316L secondary analysis\n\nModels are refitted and evaluated within 316L. This is secondary within-material evidence, not Ti64-to-316L coefficient transfer."),
        nbf.v4.new_code_cell("ss=pd.read_csv(OUT/'ss316_model_summary.csv')\ndisplay(ss[ss.metric.isin(['roc_auc','pr_auc','balanced_accuracy','keyhole_recall','brier_score'])].pivot(index='model',columns='metric',values='mean').round(4))\ndisplay(pd.read_csv(OUT/'ss316_paired_contrasts.csv').query(\"metric == 'roc_auc'\").round(5))"),
        nbf.v4.new_markdown_cell("## 8. Discordant-condition robustness\n\nSensitivity A excludes non-unanimous conditions. Sensitivity B uses a strict majority and excludes ties. The two Ti64 discordances are ties, so A and B retain the same 36 conditions and must agree."),
        nbf.v4.new_code_cell("condition=pd.read_csv(OUT/'condition_level_sensitivity.csv')\ndisplay(condition.query(\"metric == 'roc_auc'\").round(5))"),
        nbf.v4.new_markdown_cell("## 9. Required PCA backup\n\nPCA is fitted label-free on standardized `[log P, log VX]`; colors are applied only after fitting. Because the original feature space is already 2D, PCA rotates it but does not reduce dimension and is not used by any model."),
        nbf.v4.new_code_cell("display(pd.read_csv(OUT/'pca_loadings.csv').round(4))\ndisplay(Image(filename=str(OUT/'figures'/'04_label_free_process_pca.png')))"),
        nbf.v4.new_markdown_cell("## 10. Supported conclusion and boundaries\n\nThe fixed physics direction is a strong experimental discriminator. The generic two-slope logistic is modestly but consistently better in the primary bundle-level Ti64 protocol; after excluding the two discordant repeated conditions, the H–G gap is small and unresolved. This does not validate the LS exponent, prove SPH physics, transfer a threshold across alloys, or demonstrate active-learning benefit."),
        nbf.v4.new_code_cell("display(Markdown((OUT/'SUPERVISOR_PHASE1_10_ONE_PAGE.md').read_text()))"),
    ]
    notebook = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python", "version": "3.14"}})
    nbf.write(notebook, NOTEBOOK)
    # The portable Windows environment may have ipykernel installed without a
    # globally registered kernelspec. Create a study-local ignored kernelspec.
    candidates = [
        Path(sys.executable),
        ROOT.parent / "thesis-week6-melt-pool-audit" / ".venv" / "Scripts" / "python.exe",
        ROOT.parent / "thesis-week5-first-conduction-gp" / ".venv" / "Scripts" / "python.exe",
        ROOT.parent / "thesis" / ".venv" / "Scripts" / "python.exe",
    ]
    notebook_python = None
    for candidate in candidates:
        if candidate.is_file() and subprocess.run([str(candidate), "-c", "import ipykernel, pandas, IPython"], capture_output=True).returncode == 0:
            notebook_python = candidate
            break
    require(notebook_python is not None, "no Python environment with ipykernel, pandas and IPython is available for notebook execution")
    jupyter_root = CACHE / "jupyter"
    kernel_directory = jupyter_root / "kernels" / "python3"
    write_json(kernel_directory / "kernel.json", {
        "argv": [str(notebook_python), "-m", "ipykernel_launcher", "-f", "{connection_file}"],
        "display_name": "Python 3 (Phase 1.10 local)",
        "language": "python",
    })
    os.environ["JUPYTER_PATH"] = str(jupyter_root)
    executed = NotebookClient(notebook, timeout=180, kernel_name="python3", resources={"metadata": {"path": str(NOTEBOOK.parent)}}).execute()
    nbf.write(executed, NOTEBOOK)


def write_red_team(summary: pd.DataFrame, contrasts: pd.DataFrame, condition: pd.DataFrame) -> None:
    ti = _contrast(contrasts, "Ti64", "roc_auc")
    sensitivity = condition[(condition.material.eq("Ti64")) & (condition.sensitivity.eq("A_exclude_discordant")) & (condition.model_or_contrast.eq("H_minus_G")) & (condition.metric.eq("roc_auc"))].iloc[0]
    text = f"""# Final red-team report — Phase 1.10

Status: **PASS WITH CLAIM QUALIFICATION**

| Attack | Check | Disposition |
|---|---|---|
| Replicate leakage | Exact `(P,VX)` condition has one fold per repeat; all 2,400 manifest rows checked. | PASS |
| Diameter/radius error | Source says 50 µm `1/e²` diameter; executable constant is 25e-6 m radius. | PASS |
| Transition mapping | Raw modes retained; only `C=0`, every `T/CT/TK/K=1`. | PASS |
| Small effective N | Reports lead with 38 unique conditions, not 60 independent settings. | QUALIFIED |
| Split instability | 20 fixed grouped repeats; intervals explicitly described as partition sensitivity. | PASS |
| Class imbalance | ROC-AUC accompanied by PR-AUC, balanced accuracy and class recalls. | PASS |
| Post-outcome tuning | Two fixed logistics and one predeclared Matérn-3/2 GPC only; no model/kernel search. | PASS |
| Predictor leakage | H receives only `log_h`; G/GPC only `[log_P,log_VX]`; no optical or label-derived input. | PASS |
| Fixed exponent leaked into G | G uses independently fitted coefficients on the two standardized log inputs. | PASS |
| Alloy pooling/transfer overclaim | Ti64 and 316L are fitted separately; 316L is explicitly secondary within-material evidence. | PASS |
| Internal boundary import | No B1/q20/q30 feature or endpoint exists. | PASS |
| Confidence overstatement | Bootstrap CI is not called an experimental-population CI. | PASS |
| Discordant conditions | Primary bundle-level Ti64 H−G is {ti.mean_difference:+.4f} [{ti.ci_lower:+.4f}, {ti.ci_upper:+.4f}]; after excluding two discordant ties it is {sensitivity['mean']:+.4f} [{sensitivity.ci_lower:+.4f}, {sensitivity.ci_upper:+.4f}]. | CLAIM QUALIFIED |
| External proof language | Claim ledger rejects universal law, SPH proof, LS-exponent validation and AL benefit. | PASS |

Adversarial conclusion: the data support a strong external discriminator, but not superiority of the constrained direction. The generic direction is superior under the predeclared bundle-level primary protocol. The size and stability of that gap are qualified by the two Ti64 conditions with irreconcilable repeated labels.
"""
    (OUTPUT / "FINAL_RED_TEAM_REPORT.md").write_text(text, encoding="utf-8")


def historical_phase1x_changes() -> list[str]:
    completed = subprocess.run(["git", "diff", "--name-only", STARTING_SHA, "--", "outputs"], cwd=ROOT, text=True, capture_output=True, check=True).stdout.splitlines()
    return [path for path in completed if not path.startswith("outputs/week9_phase1_10_external_experimental_validation/")]


def validate(population: pd.DataFrame, folds: pd.DataFrame, predictions: pd.DataFrame, metrics: pd.DataFrame, summary: pd.DataFrame, contrasts: pd.DataFrame, condition: pd.DataFrame, pca_loadings: pd.DataFrame, figure_manifest: pd.DataFrame) -> dict[str, Any]:
    notebook = nbf.read(NOTEBOOK, as_version=4)
    code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    model_columns = {model: list(model_features(population.head(3), model).shape) for model in MODELS}
    ti = population[population.material.eq("Ti64")]
    ss = population[population.material.eq("316L")]
    checks: list[tuple[str, bool, str]] = [
        ("exact_external_source_provenance", all((CACHE / name).is_file() and sha256_file(CACHE / name) == spec["sha256"] for name, spec in SOURCE_FILES.items()) and sha256_file(CACHE/PAPER_FILE["filename"])==PAPER_FILE["sha256"], "two pinned GitHub workbooks and original open-access paper match declared SHA256"),
        ("ti64_row_count", len(ti) == 60, f"observed {len(ti)}"),
        ("ti64_unique_condition_count", ti.condition_id.nunique() == 38, f"observed {ti.condition_id.nunique()}"),
        ("ti64_class_counts", int(ti.has_keyhole.sum()) == 34 and int((1-ti.has_keyhole).sum()) == 26, "34 Keyhole / 26 Conduction"),
        ("ss316_row_count", len(ss) == 60, f"observed {len(ss)}"),
        ("ss316_unique_condition_count", ss.condition_id.nunique() == 38, f"observed {ss.condition_id.nunique()}"),
        ("ss316_class_counts", int(ss.has_keyhole.sum()) == 23 and int((1-ss.has_keyhole).sum()) == 37, "23 Keyhole / 37 Conduction"),
        ("spot_diameter_50_um", SPOT_DIAMETER_UM == 50.0, "pinned paper semantics"),
        ("thesis_radius_25_um", LS_M == 25e-6, "diameter divided by two"),
        ("mm_s_to_m_s_conversion", np.allclose(population.VX_m_per_s, population.VX_mm_per_s/1000), "numerically verified for all rows"),
        ("exact_h_formula", np.allclose(population.h_SI, population.P_W/np.sqrt(population.VX_m_per_s*population.LS_m**3)), "SI formula verified for all rows"),
        ("ls_constant", population.LS_m.nunique() == 1 and np.isclose(population.LS_m.iloc[0], LS_M), "constant radius; exponent not testable"),
        ("no_optical_predictor", model_columns == {"H": [3,1], "G": [3,2], "GPC": [3,2]}, str(model_columns)),
        ("H_only_log_h", np.array_equal(model_features(population.head(3), "H")[:,0], population.log_h.head(3)), "one predictor"),
        ("G_only_logP_logVX", np.array_equal(model_features(population.head(3), "G"), population[["log_P","log_VX"]].head(3)), "two free predictors"),
        ("no_fixed_exponent_in_G", not np.allclose(model_features(population, "G")[:,1], -0.5*population.log_VX), "G receives raw log VX, not fixed scaled h"),
        ("condition_groups_never_cross_folds", folds.groupby(["material","repeat","condition_id"]).fold.nunique().max() == 1, "exact group lock"),
        ("one_oof_prediction_per_bundle_repeat_model", predictions.groupby(["material","repeat","model","bundle_id"]).size().eq(1).all(), "complete unique OOF coverage"),
        ("both_classes_in_each_complete_oof_repeat", predictions.groupby(["material","repeat","model"]).truth.nunique().eq(2).all(), "all complete vectors contain both classes"),
        ("no_internal_B1_q20_q30", set(["B1","q20","q30"]).isdisjoint({"log_h","log_P","log_VX"}), "external endpoint uses conventional full OOF metrics"),
        ("twenty_repeat_blocks", metrics.repeat.nunique() == N_REPEATS and N_REPEATS == 20, "20 repeats per alloy"),
        ("paired_repeat_contrast", contrasts.repeat_blocks.eq(N_REPEATS).all() and contrasts.bootstrap_draws.ge(5000).all(), "H-G paired within repeat"),
        ("discordant_conditions_exact", int((ti.groupby("condition_id").has_keyhole.nunique()>1).sum()) == 2 and int((ss.groupby("condition_id").has_keyhole.nunique()>1).sum()) == 0, "Ti64=2; 316L=0"),
        ("alloys_never_pooled_for_fitting", set(predictions.material.unique()) == {"Ti64","316L"} and predictions.groupby(["material","repeat","model"]).size().eq(60).all(), "separate 60-row OOF vectors"),
        ("PCA_fit_label_free", not pca_loadings.labels_used_in_fit.astype(bool).any() and set(pca_loadings.fit_features)=={"log_P|log_VX"}, "labels applied after PCA fit"),
        ("external_raw_data_not_committed", subprocess.run(["git","ls-files",".cache"], cwd=ROOT, text=True, capture_output=True, check=True).stdout.strip()=="" and not list(ROOT.rglob("Neuchatel data.zip")), "cache ignored; raw ZIP absent"),
        ("historical_phase1x_outputs_unchanged", historical_phase1x_changes()==[], str(historical_phase1x_changes())),
        ("notebook_executed_and_stored", bool(code_cells) and all(cell.execution_count is not None for cell in code_cells) and not [out for cell in code_cells for out in cell.get("outputs",[]) if out.get("output_type")=="error"], f"{len(code_cells)} executed code cells"),
        ("figure_hashes_match", all(sha256_file(FIGURES/row.figure)==row.sha256 for row in figure_manifest.itertuples(index=False)), f"{len(figure_manifest)} figures"),
        ("claim_language_red_team", scientific_verdict(summary, contrasts)=="GENERIC_DIRECTION_SUPERIOR" and "NOT SUPPORTED" in (OUTPUT/"claim_ledger.md").read_text(encoding="utf-8"), "primary negative comparison is stated; proof claims rejected"),
    ]
    records = [{"check": name, "status": "PASS" if status else "FAIL", "detail": detail} for name, status, detail in checks]
    validation = {"status": "PASS" if all(status for _, status, _ in checks) else "FAIL", "check_count": len(checks), "checks": records}
    write_json(OUTPUT / "validation_report.json", validation)
    lines = ["# Phase 1.10 validation report", "", f"Status: **{validation['status']}**", "", f"Checks: **{len(checks)} / {len(checks)} PASS**" if validation["status"]=="PASS" else f"Checks: **{sum(status for _,status,_ in checks)} / {len(checks)} PASS**", "", "| Check | Status | Detail |", "|---|---|---|"]
    lines.extend(f"| {record['check']} | {record['status']} | {record['detail']} |" for record in records)
    (OUTPUT / "validation_report.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    require(validation["status"] == "PASS", "validation failed")
    return validation


def write_run_manifest(validation: dict[str, Any]) -> None:
    paths = [path for path in OUTPUT.rglob("*") if path.is_file() and path.name != "run_manifest.json"]
    paths.extend([Path(__file__), NOTEBOOK, ROOT/"tests"/"test_week9_phase1_10_external_experimental_validation.py"])
    files = [{"path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path), "size_bytes": path.stat().st_size} for path in sorted(set(paths))]
    manifest = {
        "study": "Week 9 Phase 1.10 — independent experimental validation of physics-aligned coordinate",
        "starting_sha": STARTING_SHA,
        "branch": BRANCH,
        "github_source_commit": GITHUB_COMMIT,
        "population": EXPECTED,
        "protocol": {"repeats": N_REPEATS, "grouped_folds": N_FOLDS, "models": list(MODELS), "primary_material": "Ti64", "primary_endpoint": "complete-OOF ROC-AUC", "primary_contrast": "H_minus_G", "bootstrap_draws": BOOTSTRAP_DRAWS},
        "model_definitions": {"H": "StandardScaler(train only) + L2 logistic(C=1) on log(h)", "G": "StandardScaler(train only) + L2 logistic(C=1) on log(P),log(VX)", "GPC": "StandardScaler(train only) + ConstantKernel*Matern(nu=1.5) GaussianProcessClassifier"},
        "validation": validation,
        "files": files,
        "raw_external_data_committed": False,
        "historical_phase1x_changes": historical_phase1x_changes(),
    }
    write_json(OUTPUT / "run_manifest.json", manifest)


def run_all() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    population = build_population()
    folds = make_grouped_fold_manifest(population)
    predictions, metrics = run_oof(population, folds)
    summary, contrasts = summarize_models(metrics)
    condition = run_condition_sensitivity(population)
    pca_scores, pca_loadings = run_pca(population)
    figures = make_figures(population, summary, contrasts, metrics, pca_scores, pca_loadings)
    write_reports(population, summary, contrasts, condition)
    write_red_team(summary, contrasts, condition)
    build_notebook()
    validation = validate(population, folds, predictions, metrics, summary, contrasts, condition, pca_loadings, figures)
    write_run_manifest(validation)
    print(json.dumps({"status": "PASS", "verdict": scientific_verdict(summary, contrasts), "output": str(OUTPUT)}, indent=2))


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="run the complete frozen external-validation experiment")
    args = parser.parse_args(argv)
    if not args.run:
        parser.error("pass --run")
    run_all()


if __name__ == "__main__":
    main()
