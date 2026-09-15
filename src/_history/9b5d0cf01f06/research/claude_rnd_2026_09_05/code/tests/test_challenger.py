import sys, json, math
from pathlib import Path
import numpy as np, pandas as pd, pytest
HERE = Path(__file__).resolve().parents[1]
for p in (HERE, HERE.parent.parent):
    if str(p) not in sys.path: sys.path.insert(0, str(p))
from scipy.special import ndtr
from scipy.stats import norm
from tmodel import lookahead_terms, acq_threshold_variance
from challenger import select, FrozenThresholdPosterior, physics_coordinate, context
from label_oracle import Oracle, Evaluator


def test_tv_closed_form_equals_two_outcome_expectation():
    rng = np.random.default_rng(0)
    m_c = rng.normal(0, 2, 50); v_c = rng.uniform(0.1, 3, 50); C = rng.normal(0, 1, (50, 30))
    p1, (a0, a1), (b0, b1) = lookahead_terms(m_c, v_c)
    expected = (p1 * b1 + (1 - p1) * b0)[:, None] * (C * C)      # E_y[variance reduction] per reference point
    assert np.allclose(expected.sum(1), acq_threshold_variance(m_c, v_c, C), rtol=1e-10)


def test_lookahead_moments_match_exact_probit_gaussian_moments():
    # single-site: E[g|y=1] and Var[g|y=1] for g~N(m,v), P(y=1|g)=Phi(g) by numerical integration
    m, v = 0.4, 1.7; g = np.linspace(-12, 12, 200001); w = norm.pdf(g, m, math.sqrt(v)) * ndtr(g); Z = np.trapezoid(w, g)
    mean1 = np.trapezoid(g * w, g) / Z; var1 = np.trapezoid(g * g * w, g) / Z - mean1 ** 2
    p1, (a0, a1), (b0, b1) = lookahead_terms(np.array([m]), np.array([v]))
    assert abs(p1[0] - Z) < 1e-6 and abs(m + a1[0] * v - mean1) < 1e-6 and abs(v - b1[0] * v * v - var1) < 1e-6


def test_select_tie_break_smallest_index():
    assert select(np.array([9, 3, 5]), np.array([1.0, 1.0, 0.5])) == 3
    assert select(np.array([9, 3, 5]), np.array([0.2, 0.1, 0.5])) == 5


def test_frozen_posterior_is_deterministic_and_fast():
    rng = np.random.default_rng(1); n = 60
    P = rng.uniform(60, 400, n); VX = rng.uniform(0.2, 1.0, n); LS = rng.uniform(4e-5, 9e-5, n); ST = rng.uniform(300, 400, n)
    logh = physics_coordinate(P, VX, LS); Z = context(VX, LS, ST); train = np.arange(n)
    y = (logh > np.median(logh)).astype(int); rev = np.arange(20)
    T1 = FrozenThresholdPosterior(logh, Z, train).fit(rev, y[rev]); T2 = FrozenThresholdPosterior(logh, Z, train).fit(rev, y[rev])
    s1 = T1.tv_scores(np.arange(20, n)); s2 = T2.tv_scores(np.arange(20, n))
    assert np.array_equal(s1, s2) and np.all(np.isfinite(s1)) and s1.max() > 0


def test_oracle_logs_and_refuses(tmp_path):
    lab = pd.DataFrame({"experiment_name": [f"e{i}" for i in range(6)], "has_keyhole": [0, 1, 0, 1, 0, 1]}); lab.to_csv(tmp_path / "l.csv", index=False)
    parts = {"r1": {"train": ["e0", "e1", "e2"], "test": ["e3", "e4", "e5"]}}; json.dump(parts, open(tmp_path / "p.json", "w"))
    o = Oracle(str(tmp_path / "l.csv"), str(tmp_path / "p.json"), str(tmp_path / "log.jsonl"))
    assert o.reveal("r1", ["e1"]) == {"e1": 1}
    with pytest.raises(PermissionError):
        o.reveal("r1", ["e4"])
    log = o.access_log(); assert log[0]["event"] == "open" and "label_sha256" in log[0] and log[1]["ids"] == ["e1"] and log[2]["event"] == "refused"


def test_evaluator_q20_matches_repository_definition_on_old_pool(tmp_path):
    from core import Data, w85
    d = Data(); spec = d.specs[3]
    inp = d.population[["experiment_name", "P", "VX", "LS", "ST"]]; lab = d.population[["experiment_name", "has_keyhole"]].assign(has_keyhole=lambda f: f.has_keyhole.astype(int))
    inp.to_csv(tmp_path / "i.csv", index=False); lab.to_csv(tmp_path / "l.csv", index=False)
    ids = inp.experiment_name.astype(str).to_numpy()
    parts = {spec.run_id: {"train": [ids[i] for i in spec.train_indices], "test": [ids[i] for i in spec.test_indices]}}; json.dump(parts, open(tmp_path / "p.json", "w"))
    ev = Evaluator(str(tmp_path / "l.csv"), str(tmp_path / "i.csv"), str(tmp_path / "p.json"))
    test, flags = ev.flags(spec.run_id); ref = w85.boundary_flags(spec, d.population, w85.b1_distance(d.population))
    order = np.argsort(test)  # evaluator test order follows partitions.json order == spec order
    assert np.array_equal(flags["q20"], ref["B1_q20"]) and np.array_equal(flags["q30"], ref["B1_q30"])
