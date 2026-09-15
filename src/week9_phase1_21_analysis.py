"""Week 9 Phase 1.21 — pre-registered inference, verdict and secondary endpoints.

Every threshold below is copied into PHASE1_21_PREREGISTERED_PROTOCOL.json at freeze time and the
protocol file is re-read and compared here, so the analysis cannot silently drift from it.
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13
from src import week9_phase1_20_acquisition_search as search
from src import week9_phase1_21_simplification_replication as rep

OUT = rep.OUTPUT
DRAWS = 10_000
ALPHA = 0.05
MAIN_WINDOWS = ((16, 80), (16, 40))
SECONDARY_WINDOWS = ((41, 80),)
GUARD_KH_RECALL_B40 = -0.03
GUARD_FULL81_ACCURACY_B80 = -0.01
NONINFERIORITY_MARGIN = {"16-80": 0.0010, "16-40": 0.0025}   # ~half of Phase 1.20's confirmed CCM effects, rounded down
SAVED_LEVEL_BUDGETS = (24, 32, 40, 60)
PAIRS = {rep.CANDIDATE_A: "cov_then_misfit_B40", rep.CANDIDATE_B: "early8__cov_then_misfit_B40"}


def load_metrics(policy: str, root: Path = rep.CHECKPOINTS) -> pd.DataFrame:
    rows = []
    for path in sorted((root / policy).glob("*.json.gz")):
        payload = json.loads(gzip.decompress(path.read_bytes()).decode())
        if payload["metrics"][0]["repeat"] in set(rep.REPLICATION_REPEATS):
            rows.extend(payload["metrics"])
    frame = pd.DataFrame(rows)
    search.require(frame.run_id.nunique() == 5 * len(rep.REPLICATION_REPEATS),
                   f"{policy}: {frame.run_id.nunique()} replication runs, expected {5 * len(rep.REPLICATION_REPEATS)}")
    return frame


def block_series(metrics: pd.DataFrame, lo: int, hi: int, metric="accuracy", subset="B1_q20") -> pd.Series:
    runs = search.window_aulc(metrics, lo, hi, metric, subset)
    repeat_of = metrics.drop_duplicates("run_id").set_index("run_id").repeat
    return runs.groupby(repeat_of).mean().sort_index()


def paired(diff: np.ndarray, key: str) -> dict:
    diff = np.asarray(diff, float)
    rng = np.random.default_rng(p13.seed_u32("phase1_21-boot", key))
    boot = diff[rng.integers(0, len(diff), size=(DRAWS, len(diff)))].mean(axis=1)
    rng = np.random.default_rng(p13.seed_u32("phase1_21-flip", key))
    null = (rng.choice((-1.0, 1.0), size=(DRAWS, len(diff))) * np.abs(diff)).mean(axis=1)
    return {"mean": float(diff.mean()), "ci_low": float(np.quantile(boot, 0.025)),
            "ci_high": float(np.quantile(boot, 0.975)),
            "signflip_p": float((np.sum(np.abs(null) >= abs(diff.mean())) + 1) / (DRAWS + 1)),
            "positive_blocks": int((diff > 0).sum()), "blocks": int(len(diff))}


def holm(ps: dict[str, float]) -> dict[str, float]:
    out, running = {}, 0.0
    ordered = sorted(ps.items(), key=lambda kv: kv[1])
    for rank, (key, p) in enumerate(ordered):
        running = max(running, (len(ordered) - rank) * p)
        out[key] = min(1.0, running)
    return out


def at_budget(metrics: pd.DataFrame, budget: int, subset: str, metric: str) -> float:
    return float(metrics[(metrics.budget == budget) & (metrics.subset == subset)][metric].mean())


def mean_curve(metrics: pd.DataFrame, subset="B1_q20", metric="accuracy") -> pd.Series:
    return metrics[metrics.subset == subset].groupby("budget")[metric].mean()


def simulations_saved(candidate: pd.DataFrame, control: pd.DataFrame) -> list[dict]:
    c_curve, m_curve = mean_curve(candidate), mean_curve(control)
    rows = []
    for b in SAVED_LEVEL_BUDGETS:
        level = float(m_curve.loc[b])
        reached = c_curve[(c_curve >= level - 1e-12) & (c_curve.index >= 16)]
        first = int(reached.index.min()) if len(reached) else None
        rows.append({"margin_budget": b, "margin_q20_accuracy": level, "candidate_first_budget": first,
                     "simulations_saved": None if first is None else b - first,
                     "percent_fewer": None if first is None else round(100 * (b - first) / b, 1)})
    return rows


def analyse() -> dict:
    protocol = json.loads((OUT / "PHASE1_21_PREREGISTERED_PROTOCOL.json").read_text(encoding="utf-8"))
    frozen = protocol["decision"]
    search.require(frozen["alpha"] == ALPHA and frozen["noninferiority_margin"] == NONINFERIORITY_MARGIN
                   and frozen["guardrails"] == {"B40_q20_KH_recall_change_min": GUARD_KH_RECALL_B40,
                                                "B80_full81_accuracy_change_min": GUARD_FULL81_ACCURACY_B80},
                   "analysis constants differ from the frozen protocol")
    metrics = {p: load_metrics(p) for p in (rep.CONTROL, rep.CANDIDATE_A, rep.CANDIDATE_B, *rep.REFERENCES)}
    control = metrics[rep.CONTROL]

    tests, pvals = [], {}
    for cand in (rep.CANDIDATE_A, rep.CANDIDATE_B):
        for lo, hi in MAIN_WINDOWS:
            a, b = block_series(metrics[cand], lo, hi), block_series(control, lo, hi)
            search.require(list(a.index) == list(b.index), "repeat mismatch")
            r = paired((a - b).to_numpy(), f"{cand}|{lo}-{hi}")
            r.update({"policy": cand, "window": f"{lo}-{hi}", "candidate_AULC": float(a.mean()),
                      "margin_AULC": float(b.mean())})
            tests.append(r)
            pvals[f"{cand}|{lo}-{hi}"] = r["signflip_p"]
    adjusted = holm(pvals)
    for r in tests:
        r["holm_p"] = adjusted[f"{r['policy']}|{r['window']}"]

    verdicts = {}
    for cand in (rep.CANDIDATE_A, rep.CANDIDATE_B):
        mine = [r for r in tests if r["policy"] == cand]
        win = any(r["holm_p"] < ALPHA and r["ci_low"] > 0 for r in mine)
        other_nonnegative = all(r["mean"] >= 0 for r in mine)
        kh = at_budget(metrics[cand], 40, "B1_q20", "keyhole_recall") - at_budget(control, 40, "B1_q20", "keyhole_recall")
        full = at_budget(metrics[cand], 80, "full81", "accuracy") - at_budget(control, 80, "full81", "accuracy")
        guard = kh >= GUARD_KH_RECALL_B40 and full >= GUARD_FULL81_ACCURACY_B80
        verdicts[cand] = {"REPLICATED": bool(win and other_nonnegative and guard),
                          "window_passing": [r["window"] for r in mine if r["holm_p"] < ALPHA and r["ci_low"] > 0],
                          "other_window_nonnegative": bool(other_nonnegative),
                          "guardrails": {"B40_q20_KH_recall_change": kh, "B80_full81_accuracy_change": full,
                                         "pass": bool(guard)}}

    # descriptive: is the late misfit component needed?  candidate minus its CCM reference
    comparisons = []
    for cand, ref in PAIRS.items():
        for lo, hi in (*MAIN_WINDOWS, *SECONDARY_WINDOWS):
            a, b = block_series(metrics[cand], lo, hi), block_series(metrics[ref], lo, hi)
            r = paired((a - b).to_numpy(), f"{cand}-minus-{ref}|{lo}-{hi}")
            window = f"{lo}-{hi}"
            r.update({"candidate": cand, "reference": ref, "window": window,
                      "noninferiority_margin": NONINFERIORITY_MARGIN.get(window),
                      "noninferior": (None if window not in NONINFERIORITY_MARGIN
                                      else bool(r["ci_low"] > -NONINFERIORITY_MARGIN[window])),
                      "reference_better_ci_excludes_zero": bool(r["ci_high"] < 0)})
            comparisons.append(r)

    def misfit_verdict(cand: str) -> str:
        if not verdicts[cand]["REPLICATED"]:
            return "NOT_REPLICATED"
        mine = [c for c in comparisons if c["candidate"] == cand and c["noninferior"] is not None]
        if all(c["noninferior"] for c in mine):
            return "COVERAGE_SUFFICIENT"
        if any(c["reference_better_ci_excludes_zero"] for c in mine):
            return "COVERAGE_WORKS_BUT_CCM_MEASURABLY_BETTER"
        return "COVERAGE_WORKS_NONINFERIORITY_INCONCLUSIVE"

    secondary = {}
    for policy in (rep.CANDIDATE_A, rep.CANDIDATE_B, *rep.REFERENCES):
        row = {}
        for name, (lo, hi, metric, subset) in {
                "AULC 41-80 q20 accuracy": (41, 80, "accuracy", "B1_q20"),
                "q30 accuracy AULC 16-80": (16, 80, "accuracy", "B1_q30"),
                "q20 balanced accuracy AULC 16-80": (16, 80, "balanced_accuracy", "B1_q20"),
                "q20 Keyhole recall AULC 16-80": (16, 80, "keyhole_recall", "B1_q20"),
                "full81 accuracy AULC 16-80": (16, 80, "accuracy", "full81")}.items():
            a = block_series(metrics[policy], lo, hi, metric, subset)
            b = block_series(control, lo, hi, metric, subset)
            row[name] = paired((a - b).to_numpy(), f"secondary|{policy}|{name}")
        row["B40 q20 Keyhole recall change"] = (at_budget(metrics[policy], 40, "B1_q20", "keyhole_recall")
                                                - at_budget(control, 40, "B1_q20", "keyhole_recall"))
        row["B80 full81 accuracy change"] = (at_budget(metrics[policy], 80, "full81", "accuracy")
                                             - at_budget(control, 80, "full81", "accuracy"))
        row["simulations_saved"] = simulations_saved(metrics[policy], control)
        for lo, hi in MAIN_WINDOWS:                      # descriptive for the references
            a, b = block_series(metrics[policy], lo, hi), block_series(control, lo, hi)
            row[f"vs margin AULC {lo}-{hi}"] = paired((a - b).to_numpy(), f"descriptive|{policy}|{lo}-{hi}")
        secondary[policy] = row

    result = {"primary_tests": tests, "verdicts": verdicts, "misfit_question": comparisons,
              "misfit_verdict": {c: misfit_verdict(c) for c in PAIRS}, "secondary": secondary,
              "replication": {"repeats": [min(rep.REPLICATION_REPEATS), max(rep.REPLICATION_REPEATS)],
                              "repeat_blocks": len(rep.REPLICATION_REPEATS),
                              "outer_cv_runs_per_policy": 5 * len(rep.REPLICATION_REPEATS),
                              "what_a_run_is": "one outer cross-validation run over the same 405 simulations; "
                                               "not an independent simulation"}}
    (OUT / "REPLICATION_RESULT.json").write_text(json.dumps(result, indent=2, default=float), encoding="utf-8")
    return result


if __name__ == "__main__":
    out = analyse()
    print(json.dumps({"verdicts": out["verdicts"], "misfit_verdict": out["misfit_verdict"]}, indent=2))
