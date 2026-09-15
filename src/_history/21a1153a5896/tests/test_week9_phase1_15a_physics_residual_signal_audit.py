from __future__ import annotations

import hashlib
import json
from pathlib import Path

import nbformat as nbf
import numpy as np
import pandas as pd

from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13
from src import week9_phase1_15a_physics_residual_signal_audit as p15


ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"outputs"/"week9_phase1_15a_physics_residual_signal_audit"


def test_parent_population_and_paths() -> None:
    gate=json.loads((OUT/"baseline_gate.json").read_text()); population,specs,a0,p1=p15.load_inputs()
    assert gate["phase114_parent_sha"]==p15.PHASE114_SHA
    assert (len(population),int(population.has_keyhole.sum()))==(405,73)
    assert len(specs)==len(a0)==len(p1)==100
    assert all(len(path)==len(set(path))==80 for path in p1.values())


def test_frozen_component_table_is_pre_reveal_only() -> None:
    pre=pd.read_csv(OUT/"component_candidate_table.csv.gz"); freeze=json.loads((OUT/"pre_reveal_freeze.json").read_text())
    assert tuple(pre.columns)==p15.PRE_REVEAL_COLUMNS
    assert not {"truth","has_keyhole","B1_distance","is_q20","is_q30"}&set(pre.columns)
    assert freeze["sha256"]==p15.sha256_file(OUT/"component_candidate_table.csv.gz")
    assert pre.score_inputs_are_pre_reveal_only.all()


def test_probability_component_identities() -> None:
    pre=pd.read_csv(OUT/"component_candidate_table.csv.gz")
    assert pre.p_H.between(0,1).all() and pre.p_M3.between(0,1).all()
    assert np.allclose(pre.delta_p,pre.p_M3-pre.p_H,rtol=0,atol=2e-15)
    assert np.allclose(pre.abs_delta_p,pre.delta_p.abs(),rtol=0,atol=2e-15)
    assert np.array_equal(pre.class_flip_H_to_M3,(pre.p_H.ge(.5)!=pre.p_M3.ge(.5)))


def test_exact_m3_architecture_and_prefixes() -> None:
    population,specs,_,p1=p15.load_inputs(); kernel=p13.residual_kernel("M3")
    assert p15.FEATURES==("P","VX","LS","ST") and kernel.k2.nu==1.5
    assert len(np.ravel(kernel.k2.length_scale))==4
    assert all(len(set(p1[s.run_id][:b]))==b for s in specs for b in p15.BUDGETS)


def test_retrospective_join_is_separate() -> None:
    retro=pd.read_csv(OUT/"component_candidate_retrospective.csv.gz")
    assert {"truth","B1_distance_retrospective","fold_q20_like_retrospective","fold_q30_like_retrospective"}.issubset(retro.columns)
    source=(ROOT/"src/week9_phase1_15a_physics_residual_signal_audit.py").read_text()
    start=source.rindex("def finalize()")
    body=source[start:source.index("def main()",start)]
    assert body.index("freeze_pre_reveal(raw)")<body.index("retrospective_join(pre")


def test_repeat_block_inference_and_decision() -> None:
    inference=pd.read_csv(OUT/"repeat_block_inference.csv"); manifest=json.loads((OUT/"run_manifest.json").read_text())
    assert inference.repeat_blocks.eq(20).all() and inference.bootstrap_draws.eq(10_000).all()
    assert manifest["decision"] in {"CORRECTION_SIGNAL_SUPPORTED","CORRECTION_SIGNAL_PARTIAL","CORRECTION_SIGNAL_NOT_SUPPORTED","CORRECTION_SIGNAL_NUMERICALLY_UNRELIABLE"}
    assert manifest["protocol"]["new_acquisition_trajectory"] is False


def test_literature_and_claim_discipline() -> None:
    literature=pd.read_csv(OUT/"literature_comparison.csv"); ledger=(OUT/"claim_ledger.md").read_text(); designs=(OUT/"candidate_acquisition_designs.md").read_text()
    assert len(literature)>=7 and literature.source.str.startswith("http").all()
    assert "New acquisition improves active-learning efficiency. | NOT TESTED" in ledger
    assert designs.count("## A")==3 and "No trajectory was generated" in designs


def test_notebook_is_executed() -> None:
    notebook=nbf.read(ROOT/"notebooks/week_09/13_week9_phase1_15a_physics_residual_signal_audit.ipynb",as_version=4); code=[c for c in notebook.cells if c.cell_type=="code"]
    assert code and all(c.execution_count is not None for c in code)
    assert not [o for c in code for o in c.get("outputs",[]) if o.get("output_type")=="error"]


def test_figure_and_artifact_hashes() -> None:
    figures=pd.read_csv(OUT/"figure_manifest.csv")
    assert len(figures)<=5 and all(p15.sha256_file(OUT/"figures"/r.figure)==r.sha256 for r in figures.itertuples(index=False))
    manifest=json.loads((OUT/"run_manifest.json").read_text())
    for item in manifest["files"]:
        payload=p15.artifact_bytes(ROOT/item["path"])
        assert hashlib.sha256(payload).hexdigest()==item["sha256"]


def test_validation_and_historical_outputs() -> None:
    validation=json.loads((OUT/"validation_report.json").read_text()); manifest=json.loads((OUT/"run_manifest.json").read_text())
    assert validation["status"]=="PASS" and validation==manifest["validation"]
    assert p15.historical_changes()==[] and manifest["historical_changes"]==[]
