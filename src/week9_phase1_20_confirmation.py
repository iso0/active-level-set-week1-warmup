"""Week 9 Phase 1.20 — confirmation analysis (Protocol + Amendment 1).

Reads checkpoints produced by week9_phase1_20_acquisition_search for the frozen finalists and
the margin control on the confirmation repeats (11-60), and applies the pre-registered rule:

    CONFIRMED if, for a finalist,
      * Holm-adjusted sign-flip p < 0.05 AND 95% repeat-block bootstrap CI > 0 on at least one of
        {q20 accuracy AULC 16-80, q20 accuracy AULC 16-40}   (Holm over finalists x 2 windows)
      * the other window has a non-negative point estimate
      * guardrails: B40 q20 Keyhole recall drop <= 0.03 and B80 full81 accuracy drop <= 0.01

Repeats 11-20 alone are reported as a secondary transparency check.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13
from src import week9_phase1_20_acquisition_search as search

DRAWS = 10_000
WINDOWS = ((16, 80), (16, 40))


def repeat_series(policy: str, repeats, lo: int, hi: int, metric="accuracy", subset="B1_q20") -> pd.Series:
    metrics = search.load_metrics(policy, repeats)
    runs = search.window_aulc(metrics, lo, hi, metric, subset)
    repeat_of = metrics.drop_duplicates("run_id").set_index("run_id").repeat
    return runs.groupby(repeat_of).mean().sort_index()


def paired_test(diff: np.ndarray, key: str) -> dict:
    diff = np.asarray(diff, float)
    rng = np.random.default_rng(p13.seed_u32("confirm-boot", key))
    boot = diff[rng.integers(0, len(diff), size=(DRAWS, len(diff)))].mean(axis=1)
    rng = np.random.default_rng(p13.seed_u32("confirm-flip", key))
    null = (rng.choice((-1.0, 1.0), size=(DRAWS, len(diff))) * np.abs(diff)).mean(axis=1)
    p = (np.sum(np.abs(null) >= abs(diff.mean())) + 1) / (DRAWS + 1)
    return {"mean": float(diff.mean()), "ci_low": float(np.quantile(boot, 0.025)),
            "ci_high": float(np.quantile(boot, 0.975)), "signflip_p": float(p),
            "positive_blocks": int((diff > 0).sum()), "blocks": int(len(diff))}


def holm(ps: dict[str, float]) -> dict[str, float]:
    out, running = {}, 0.0
    items = sorted(ps.items(), key=lambda kv: kv[1])
    for rank, (key, p) in enumerate(items):
        running = max(running, (len(items) - rank) * p)
        out[key] = min(1.0, running)
    return out


def guardrails(policy: str, repeats) -> dict:
    fin = search.load_metrics(policy, repeats)
    ctl = search.load_metrics("margin", repeats)
    def at(frame, budget, subset, metric):
        return float(frame[(frame.budget == budget) & (frame.subset == subset)][metric].mean())
    kh = at(fin, 40, "B1_q20", "keyhole_recall") - at(ctl, 40, "B1_q20", "keyhole_recall")
    full = at(fin, 80, "full81", "accuracy") - at(ctl, 80, "full81", "accuracy")
    return {"B40_q20_KH_recall_change": kh, "B80_full81_accuracy_change": full,
            "pass": bool(kh >= -0.03 and full >= -0.01)}


def confirm(finalists: list[str], repeats, label: str) -> dict:
    tests, rows = {}, []
    for policy in finalists:
        for lo, hi in WINDOWS:
            a = repeat_series(policy, repeats, lo, hi)
            b = repeat_series("margin", repeats, lo, hi)
            require = search.require
            require(list(a.index) == list(b.index), f"repeat mismatch {policy}")
            key = f"{policy}|{lo}-{hi}"
            res = paired_test((a - b).to_numpy(), f"{label}|{key}")
            res.update({"policy": policy, "window": f"{lo}-{hi}", "finalist_AULC": float(a.mean()),
                        "margin_AULC": float(b.mean())})
            tests[key] = res["signflip_p"]
            rows.append(res)
    adjusted = holm(tests)
    for r in rows:
        r["holm_p"] = adjusted[f"{r['policy']}|{r['window']}"]
    verdicts = {}
    for policy in finalists:
        mine = [r for r in rows if r["policy"] == policy]
        win = any(r["holm_p"] < 0.05 and r["ci_low"] > 0 for r in mine)
        other_ok = all(r["mean"] >= 0 for r in mine) if win else False
        guard = guardrails(policy, repeats)
        verdicts[policy] = {"CONFIRMED": bool(win and other_ok and guard["pass"]), "guardrails": guard}
    return {"label": label, "tests": rows, "verdicts": verdicts}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--finalists", nargs="+", required=True)
    args = parser.parse_args()
    primary = confirm(args.finalists, search.CONFIRMATION, "pooled_repeats_11_60")
    secondary = confirm(args.finalists, search.CONF_REPEATS, "repeats_11_20_only")
    out = search.OUTPUT / "CONFIRMATION_RESULT.json"
    out.write_text(json.dumps({"primary": primary, "secondary": secondary}, indent=2), encoding="utf-8")
    for block in (primary, secondary):
        print(f"\n=== {block['label']} ===")
        frame = pd.DataFrame(block["tests"])[["policy", "window", "finalist_AULC", "margin_AULC", "mean",
                                               "ci_low", "ci_high", "positive_blocks", "blocks", "signflip_p", "holm_p"]]
        print(frame.to_string(index=False, float_format=lambda v: f"{v:+.5f}"))
        print(json.dumps(block["verdicts"], indent=2))


if __name__ == "__main__":
    main()
