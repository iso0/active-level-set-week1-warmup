"""RC19 addendum AX report (Astra v2 selector on the pooled region; PROTOCOL_RC19_ADDENDUM_AX.md). Paired by task (the 8 frozen
final tasks), metrics on each task's own test fold; the main-study SHQ STRADDLE / MAXIMIN units on the same tasks are references.
    python -m src.rc19_ax_report
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import src.rc19_astra as AX
import src.rc19_eval as EV
import src.rc19_pool as P

REP = P.OUT / "report"


def task_curves(units, M, tau):
    rows = []
    for u in units:
        y = M.reindex(u["test_ids"]).vmax_spike_logratio.to_numpy(float); ok = np.isfinite(y); t = y[ok] >= tau
        for e in u["evals"]:
            m = np.asarray([np.nan if v is None else v for v in e["mean"]], float)[ok]; q = np.where(np.isfinite(m), m >= tau, ~t)
            rin, rout = float(np.mean(q[t])), float(np.mean(~q[~t]))
            rows.append({"arm": u["acq"] if u["acq"].startswith("ASTRA") else f"MAIN_{u['acq']}", "repeat": u["repeat"], "fold": u["fold"], "budget": e["budget"],
                         "BA": 0.5 * (rin + rout), "recall_in": rin, "recall_out": rout})
    return pd.DataFrame(rows)


def main():
    M = P.manifest(); tau = float(np.log(2.0)); A = EV.load_units(AX.AX_DIR)
    main_u = [u for u in EV.load_units(P.OUT / "final" / "final-region") if u["model"] == "SHQ" and u["acq"] in ("STRADDLE", "MAXIMIN")
              and (u["repeat"], u["fold"]) in set(AX.AX_TASKS)]
    for u in main_u:                                                           # same horizon as AX (B40)
        u["evals"] = [e for e in u["evals"] if e["budget"] <= 40]
    T = task_curves(A + main_u, M, tau); T.to_csv(REP / "ax_task_curves.csv", index=False, lineterminator="\n")
    from src.rc19_report import md
    AU = T[T.budget >= P.B0].groupby(["arm", "repeat", "fold"]).BA.mean().unstack(0)
    L = ["## Addendum AX — Astra's frozen v2 selector on the pooled region (8 frozen tasks; SHQ posterior; exploratory, DEV)", "",
         "Her synthetic v2 TEST was still running and her own scientific endpoints were not inspected at registration: this is an integration and stability check on inspected simulations, not a confirmation of her method.", "",
         "BA-AULC over B8–B40 per task (each task's own test fold):", "", md(AU.round(4).reset_index(), 4), ""]
    rows = []
    for name, a, b in (("(1) local response: boundary_regional − sur_global", "ASTRA_BOUNDARY_REGIONAL", "ASTRA_SUR_GLOBAL"),
                       ("(2) surprise anchors at fixed share: quota_surprise − quota_no_surprise", "ASTRA_QUOTA_SURPRISE", "ASTRA_QUOTA_NO_SURPRISE"),
                       ("(3a) same model, selector: sur_global − main STRADDLE", "ASTRA_SUR_GLOBAL", "MAIN_STRADDLE"),
                       ("(3b) same model, selector: sur_global − main MAXIMIN", "ASTRA_SUR_GLOBAL", "MAIN_MAXIMIN")):
        if a in AU and b in AU:
            d = (AU[a] - AU[b]).dropna(); rows.append({"contrast": name, "mean": float(d.mean()), "tasks_positive": f"{int((d > 0).sum())}/{len(d)}", "min": float(d.min()), "max": float(d.max())})
    L += ["Paired contrasts (per task):", "", md(pd.DataFrame(rows), 4), ""]
    R = T[T.budget.isin([16, 24, 32, 40])].groupby(["arm", "budget"])[["BA", "recall_in", "recall_out"]].mean().reset_index()
    L += ["Both recalls at the readouts (mean over the 8 tasks):", "", md(R), ""]
    ev = []
    for u in A:
        e = pd.DataFrame(u["astra_events"]); y = M.reindex(u["paid_ids"][P.B0:]).vmax_spike_logratio.to_numpy(float); okk = np.isfinite(y)
        ev.append({"arm": u["acq"], "repeat": u["repeat"], "fold": u["fold"], "triggers": int(e.triggered.sum()), "confirmations": int(e.confirmed_now.sum()),
                   "local_queries": int(e.reason.str.startswith("local").sum()), "global_random": int((e.reason == "global_random").sum()),
                   "near_ties": int(e.near_tie.sum()), "band_share_paid": float(np.mean(np.abs(y[okk] - tau) <= 0.25)) if okk.any() else np.nan, "seconds": u["seconds"]})
    E = pd.DataFrame(ev); E.to_csv(REP / "ax_events.csv", index=False, lineterminator="\n")
    L += ["Mechanism counts per trajectory (mean over tasks) and cost:", "", md(E.groupby("arm")[["triggers", "confirmations", "local_queries", "global_random", "near_ties", "band_share_paid", "seconds"]].mean().reset_index(), 2), ""]
    acc = json.loads((AX.COPY / "ADAPTER_ACCEPTANCE.json").read_text(encoding="utf-8"))
    L += [f"Adapter acceptance before the run: {acc['status']} (information fraction vs dense rank-one update: max |Δ| = {acc['info_fraction_vs_dense_max_abs_diff']:.1e}).", ""]
    (REP / "AX_RESULTS.md").write_text("\n".join(L) + "\n", encoding="utf-8"); print("\n".join(L))


if __name__ == "__main__":
    main()
