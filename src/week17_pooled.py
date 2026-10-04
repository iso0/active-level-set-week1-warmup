"""Week 17 — pooled out-of-fold metrics per repeat (Week 12 convention) and paired contrasts vs G3.

For each (set, repeat, budget, model): predictions of the repeat's folds are pooled (each campaign row once),
metrics as in week12_development_common.metrics; q20 = mean over folds of the historical q20 accuracy.
Contrasts: per-repeat difference to G3, mean and 95% bootstrap interval over repeats (repeats are overlapping
partitions of one campaign — descriptive, not independent replications).
"""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
P1 = ROOT / "outputs/week17_model_and_acquisition/phase1"


def pooled_metrics(y, p, minority):
    p = np.clip(p, 1e-12, 1 - 1e-12); yh = (p >= .5).astype(int)
    rec = [np.mean(yh[y == k] == k) for k in (0, 1)]
    pr = p if minority == 1 else 1 - p
    return {"BA": (rec[0] + rec[1]) / 2, "minority_recall": rec[minority], "AUC": roc_auc_score(y, p),
            "minority_AP": average_precision_score((y == minority).astype(int), pr), "brier": float(np.mean((p - y) ** 2)),
            "logloss": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))}


def repeat_of(split):
    s = str(split)
    if s.startswith("external__r"):
        return int(s.split("__r")[1].split("_")[0])
    if s.startswith("w85__r"):
        return int(s.split("__r")[1].split("_")[0])
    return 0


def pooled(df, labels):
    rows = []
    for (st, model, budget, rep), g in df.assign(repeat=df.split.map(repeat_of)).groupby(["set", "model", "budget", "repeat"]):
        camp = "OLD" if st == "old_a0" else "NEW"
        y = labels[camp]
        idx = np.concatenate([np.array(r.split(","), int) for r in g.pred_rows])
        p = np.concatenate([np.array(r.split(","), float) for r in g.pred_p])
        q = []
        for r in g.itertuples():
            ii = np.array(r.pred_rows.split(","), int); pp = np.array(r.pred_p.split(","), float); qq = np.array(r.pred_q20.split(","), int).astype(bool)
            if qq.any():
                q.append(np.mean((pp[qq] >= .5) == y[ii][qq]))
        rows.append({"set": st, "model": model, "budget": budget, "repeat": rep, "folds": len(g), "rows": len(idx),
                     **pooled_metrics(y[idx], p, 0 if camp == "NEW" else 1), "q20_meanfold": float(np.mean(q)) if q else np.nan})
    return pd.DataFrame(rows)


def contrasts(P, ref="G3", n=4000):
    out = []
    keys = ["BA", "minority_recall", "AUC", "minority_AP", "brier", "logloss", "q20_meanfold"]
    for (st, budget), g in P.groupby(["set", "budget"]):
        w = g.pivot_table(index="repeat", columns="model", values=keys)
        for model in g.model.unique():
            if model == ref:
                continue
            r = {"set": st, "budget": budget, "model": model, "repeats": len(w)}
            for k in keys:
                d = (w[k][model] - w[k][ref]).dropna().values
                if len(d) == 0:
                    continue
                b = np.random.default_rng(0).choice(d, (n, len(d))).mean(1) if len(d) > 1 else np.array([d[0]])
                r[f"{k}_diff"] = float(d.mean()); r[f"{k}_lo"] = float(np.quantile(b, .025)); r[f"{k}_hi"] = float(np.quantile(b, .975))
            out.append(r)
    return pd.DataFrame(out)


def main(path=P1 / "diagnose_real.csv.gz", tag="diagnose"):
    from src.week17_audit import campaigns
    C = campaigns(); labels = {k: v[2] for k, v in C.items()}
    df = pd.read_csv(path)
    tr = df[df.set == "transfer"].copy()
    P = pooled(df[df.set != "transfer"], labels)
    P.to_csv(P1 / f"{tag}_pooled.csv", index=False)
    Cn = contrasts(P); Cn.to_csv(P1 / f"{tag}_contrasts_vs_G3.csv", index=False)
    agg = P.groupby(["set", "model"])[["BA", "minority_recall", "AUC", "minority_AP", "brier", "logloss", "q20_meanfold"]].mean()
    agg.to_csv(P1 / f"{tag}_pooled_summary.csv")
    return P, Cn, agg, tr


if __name__ == "__main__":
    P, Cn, agg, tr = main()
    pd.set_option("display.width", 220)
    print(agg.round(4).to_string())
    print(tr[["model", "BA", "minority_recall", "AUC", "minority_AP", "brier", "logloss", "q20_accuracy"]].round(4).to_string())
