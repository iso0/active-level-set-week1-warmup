"""Invariant checks for the joint depth-label study (branch joint-depth-label-dev).

Most checks read committed tables; the leakage and Stage A checks also fit a few small joint models (one thread).
"""
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "joint_depth_label_development"
REL = "outputs/joint_depth_label_development"
FREEZE, STAGE_M_RESULTS, TEMPORAL_FREEZE, EX_FREEZE = "0c0ce614", "23acbaa3", "29ca7364", "3afad1dc"
needs_stage_m = pytest.mark.skipif(not (OUT / "stage_m" / "STAGE_M_DECISION.json").exists(), reason="Stage M outputs absent")


def _git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True, cwd=ROOT)


def _added_in(path):
    """Commit (full SHA) that first added `path`, or None if it is not committed."""
    c = _git("log", "--format=%H", "--diff-filter=A", "--", path).stdout.split()
    return c[-1] if c else None


def _strictly_before(a, b):
    return a != b and _git("merge-base", "--is-ancestor", a, b).returncode == 0


def _tasks_or_skip():
    try:
        import src.jdl_stage_m as SMM
        return SMM, SMM.build_tasks()
    except Exception as e:                                                   # raw data are git-ignored
        pytest.skip(f"study data unavailable: {e}")


def test_freeze_precedes_every_comparative_result():
    fz = _added_in(f"{REL}/STUDY_MANIFEST.json")
    assert fz and fz.startswith(FREEZE)
    for out in ("stage_m/predictions_all.csv.gz", "stage_m/fit_log.csv", "stage_m/STAGE_M_DECISION.json", "stage_m/paired_contrasts.csv"):
        c = _added_in(f"{REL}/{out}")
        assert c and _strictly_before(fz, c), out
    for out in ("validation/validation_results.json", "stage_m/paths.csv", "stage_m/path_verification_NEW_vs_week19.csv", "C4_STABILITY_DRAFT.md"):
        assert _added_in(f"{REL}/{out}") == fz, out                          # frozen together with the manifest


def test_frozen_code_unchanged_since_freeze():
    man = json.loads((OUT / "STUDY_MANIFEST.json").read_text(encoding="utf-8"))
    import hashlib
    for f in ("src/jdl_model.py", "src/jdl_validation.py", "src/jdl_stage_m.py", "src/jdl_evaluate.py", "src/week19_dev_pilot.py", "src/week18_tasks.py"):
        assert hashlib.sha256((ROOT / f).read_bytes()).hexdigest() == man["code_sha256"][f], f


def test_validation_passed_before_results():
    v = json.loads((OUT / "validation" / "validation_results.json").read_text(encoding="utf-8"))
    assert v["status"] == "PASS"
    ref = json.loads((OUT / "validation" / "reference_checks_reproduced.json").read_text(encoding="utf-8"))
    assert "PASS" in json.dumps(ref)


@needs_stage_m
def test_stage_m_complete_converged_and_on_frozen_paths():
    f = pd.read_csv(OUT / "stage_m" / "fit_log.csv")
    assert len(f) == 360 and (f.status == "ok").all()
    assert (f.groupby(["population", "arm"]).size() == 20).all() and f.groupby(["population", "arm"]).ngroups == 18
    jf = f[f.arm.isin(["J", "J_fixed_theta", "J_no_delta", "Binary_matched"])]
    assert len(jf) == 240 and jf.gradient_accepted.astype(bool).all() and (jf.gradient_inf < 2e-6).all()
    pv = pd.read_csv(OUT / "stage_m" / "path_verification_NEW_vs_week19.csv")
    assert len(pv) == 10 and pv.identical_to_week19_saved_path.astype(bool).all()
    paths = pd.read_csv(OUT / "stage_m" / "paths.csv")
    pre = paths[paths.query_index <= 40].groupby(["population", "repeat", "fold"]).sim_id.apply(tuple)
    for (pop, r, fo), g in f[f.budget == 40].groupby(["population", "repeat", "fold"]):
        import hashlib
        assert g.prefix_sha256.nunique() == 1                                # every arm saw the same paid prefix
        assert g.prefix_sha256.iloc[0] == hashlib.sha256("\n".join(pre[(pop, r, fo)]).encode()).hexdigest()


@needs_stage_m
def test_stage_m_decision_follows_frozen_rule():
    d = json.loads((OUT / "stage_m" / "STAGE_M_DECISION.json").read_text(encoding="utf-8"))
    ct = pd.read_csv(OUT / "stage_m" / "paired_contrasts.csv")
    g = lambda m: ct[(ct.population == "NEW") & (ct.arm == "J") & (ct.ref == "Binary_matched") & (ct.budget == 40) & (ct.metric == m)].iloc[0].estimate_mean_over_repeats
    ba, sp, ll = g("BA"), g("specificity"), g("log_loss")
    assert abs(ba - d["NEW_B40_J_minus_Binary"]["BA"]) < 1e-12
    recommend = d["numerical_and_leakage_checks_pass"] and ba >= 0.01 - 1e-12 and sp >= -1e-12 and ll <= 1e-12
    assert d["decision"] == ("RECOMMEND STAGE A" if recommend else "SCREEN FAILED - Stage A not recommended")
    assert d["decision"].startswith("SCREEN FAILED")                          # the recorded outcome is preserved


def test_c3_decision_preserved():
    diff = _git("diff", "--stat", "e2bcf97a55736cdd2933b6761678d8b695358205", "HEAD", "--", "outputs/week20_active_temporal_development/c3").stdout
    assert diff.strip() == ""


def test_leakage_invariance_of_joint_fit():
    """Corrupting every unpaid and held-out label and depth leaves the joint fit's test predictions unchanged."""
    SMM, tasks = _tasks_or_skip()
    import src.jdl_model as JM
    paths = pd.read_csv(OUT / "stage_m" / "paths.csv")
    t = [t for t in tasks if (t["population"], t["repeat"], t["fold"]) == ("NEW", 1, 2)][0]
    g = paths[(paths.population == "NEW") & (paths.repeat == 1) & (paths.fold == 2)].sort_values("query_index")
    pos = {s: i for i, s in enumerate(t["ids"])}; t["path"] = g.sim_id.map(pos).to_numpy(int)
    rec, preds = SMM.fit_joint(t, "J", 16)
    bad = dict(t); paid = set(t["path"][:16].tolist())
    unpaid = np.array([i for i in range(len(t["y"])) if i not in paid])
    bad["y"] = t["y"].copy(); bad["y"][unpaid] = 1 - bad["y"][unpaid]
    bad["A"] = t["A"].copy(); bad["A"][unpaid] = np.where(np.isfinite(bad["A"][unpaid]), 5.0 * bad["A"][unpaid], 300.0)
    rec2, preds2 = SMM.fit_joint(bad, "J", 16)
    assert rec["status"] == rec2["status"] == "ok" and rec["prefix_sha256"] == rec2["prefix_sha256"]
    p1 = np.array([p["p"] for p in preds]); p2 = np.array([p["p"] for p in preds2])
    assert np.array_equal(p1, p2)                                             # bitwise: the learner never saw those rows
    o1 = np.array([p["p_oracle_response_NOT_DEPLOYABLE"] for p in preds]); o2 = np.array([p["p_oracle_response_NOT_DEPLOYABLE"] for p in preds2])
    assert not np.allclose(o1, o2, equal_nan=True)                            # the evaluator-only oracle column does use them


def test_missing_response_keeps_label_and_cost():
    SMM, tasks = _tasks_or_skip()
    found = 0
    for t in tasks:
        miss = np.where(~(np.isfinite(t["A"]) & (t["A"] > 0)))[0]
        for i in miss[:2]:
            paid = SMM.Oracle(t).reveal([t["pool"][0], i])
            assert len(paid.ids) == 2 and len(paid.y) == 2
            assert np.isnan(paid.z[1]) and paid.y[1] == t["y"][i] and paid.ids[1] == t["ids"][i]   # label and cost kept
            found += 1
    if not found:
        pytest.skip("no missing response in the study tasks")


def test_exploratory_manifests_precede_their_results():
    for d, man, outs in (("EX1_ba_aligned_decision_rule", "EX1_MANIFEST.json", ("EX1_RESULTS.json", "contrasts.csv", "metrics_per_repeat.csv", "fit_log.csv")),
                         ("EX2_trained_response_prior", "EX2_MANIFEST.json", ("EX2_RESULTS.json", "contrasts.csv", "metrics_per_repeat.csv", "fit_log.csv"))):
        m = _added_in(f"{REL}/exploratory/{d}/{man}")
        assert m and m.startswith(EX_FREEZE)
        for o in outs:
            c = _added_in(f"{REL}/exploratory/{d}/{o}")
            if c is not None:
                assert _strictly_before(m, c), o
        spec = json.loads((OUT / "exploratory" / d / man).read_text(encoding="utf-8"))
        frozen = json.loads(_git("show", f"{m}:{REL}/exploratory/{d}/{man}").stdout)
        assert spec == frozen                                                 # manifest not edited after the freeze


def test_exploratory_runs_complete_on_fresh_repeats():
    e1 = OUT / "exploratory" / "EX1_ba_aligned_decision_rule"
    if not (e1 / "EX1_RESULTS.json").exists():
        pytest.skip("EX1 not run")
    f1 = pd.read_csv(e1 / "fit_log.csv"); f2 = pd.read_csv(OUT / "exploratory" / "EX2_trained_response_prior" / "fit_log.csv")
    assert len(f1) == 320 and (f1.status == "ok").all() and set(f1.repeat) == {5, 6, 7, 8}
    assert len(f2) == 120 and (f2.status == "ok").all() and set(f2.repeat) == {5, 6, 7, 8}
    sm = pd.read_csv(OUT / "stage_m" / "fit_log.csv")
    assert set(sm.repeat) == {1, 2}                                           # no overlap with Stage M; 3-4 stay reserved for Stage A
    r = json.loads((e1 / "EX1_RESULTS.json").read_text(encoding="utf-8"))
    assert r["EX1-P1_primary"]["supported"] == (r["EX1-P1_primary"]["estimate"] > 0)
    assert r["EX1-P3_control"]["supported"] == (r["EX1-P3_control"]["estimate"] <= 0)


def test_stage_a_refuses_without_owner_authorization():
    import src.jdl_stage_a as SA
    with pytest.raises(SystemExit):
        SA.run([])
    if not (OUT / "stage_a" / "STAGE_A_MANIFEST.json").exists():
        with pytest.raises(SystemExit):
            SA.run(["--owner-authorized"])                                    # no committed manifest either
    v = json.loads((OUT / "stage_a" / "stage_a_runner_validation.json").read_text(encoding="utf-8"))
    assert v["passed"] is True and v["leakage_first_selection_identical"] and v["tie_rule_ok"] and v["score_log_complete"]
    assert not (OUT / "_cache" / "stage_a").exists() or not any((OUT / "_cache" / "stage_a").iterdir())


def test_reports_use_full_simulation_ids():
    """H suffixes are not unique; a bare suffix may appear only in a sentence that is about suffixes."""
    import re
    pat = re.compile(r"(?<![0-9A-Za-z_])H-[0-9a-f]{10}")
    files = sorted(OUT.glob("*.md")) + sorted((OUT / "exploratory").glob("*.md")) + [OUT / "JOINT_MODEL_WALKTHROUGH.ipynb"]
    bad = []
    for f in files:
        if f.exists():
            for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                bad += [f"{f.name}:{i}: {m.group(0)}" for m in pat.finditer(line) if "suffix" not in line.lower()]
    assert not bad, bad[:10]


def test_temporal_freeze_precedes_temporal_fits_and_protocol_unchanged():
    fz = _added_in(f"{REL}/temporal_repair/TEMPORAL_MANIFEST.json")
    assert fz and fz.startswith(TEMPORAL_FREEZE)
    for out in ("temporal_repair/functional_ppca_fits.jsonl", "temporal_repair/svgp_ngd_fits.jsonl", "TEMPORAL_REPAIR_REPORT.md"):
        c = _added_in(f"{REL}/{out}")
        if c is not None:
            assert _strictly_before(fz, c), out
    # amendment T-A2 changed scheduling only: model, optimiser, stopping rule and prediction code are byte-identical to the freeze
    frozen = _git("show", f"{fz}:src/jdl_temporal_svgp.py").stdout.replace("\r\n", "\n")
    now = (ROOT / "src" / "jdl_temporal_svgp.py").read_text(encoding="utf-8").replace("\r\n", "\n")
    cut = lambda s, a, b: s[s.index(a):s.index(b)]
    assert cut(frozen, "PROTOCOL = {", "class NatSVGP") == cut(now, "PROTOCOL = {", "class NatSVGP")
    assert cut(frozen, "class NatSVGP", "def fit_checkpoint") == cut(now, "class NatSVGP", "def fit_checkpoint")
    assert cut(frozen, "def fit_checkpoint", '    row = {"checkpoint"') == cut(now, "def fit_checkpoint", '    row = {"checkpoint"')
    for name in ("functional_ppca_fits.jsonl", "svgp_ngd_fits.jsonl"):
        p = OUT / "temporal_repair" / name
        if p.exists():
            rows = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
            keys = [(r["checkpoint"], r.get("inducing_points")) for r in rows]
            assert len(keys) == len(set(keys))                                # no checkpoint fitted twice
