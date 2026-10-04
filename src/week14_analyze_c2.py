"""Evaluate pre-registered predictions P5-P6 on the C2 transfer benchmark."""
import json
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "outputs/week14_research_program/synthetic/transfer/transfer_confirm.csv"
OUT = ROOT / "outputs/week14_research_program/benchmarks"
df = pd.read_csv(D)
fails = int((~df.ok).sum())
df = df[df.ok]
mets = ["BA", "minority_recall", "AUC", "BEF1", "NSD_0.1", "ASSD"]


def paired(a, b, metric, draws=4000, seed=3):
    x = df[df.model == a].set_index(["family", "setting", "rep"])[metric]
    y = df[df.model == b].set_index(["family", "setting", "rep"])[metric]
    d = (x - y).dropna()
    out = []
    rng = np.random.default_rng(seed)
    for (f, s), g in d.groupby(level=[0, 1]):
        v = g.to_numpy()
        boot = rng.choice(v, (draws, len(v))).mean(1)
        out.append({"family": f, "setting": s, "contrast": f"{a}-{b}", "metric": metric, "mean": float(v.mean()),
                    "ci_low": float(np.quantile(boot, .025)), "ci_high": float(np.quantile(boot, .975)),
                    "positive": int((v > 0).sum()), "n": len(v)})
    return out


rows = []
for a, b in (("G3C", "G3"), ("M3", "G3"), ("G3S", "G3"), ("GRC", "GR"), ("H", "G3")):
    for m in mets:
        rows += paired(a, b, m)
C = pd.DataFrame(rows)
C.to_csv(OUT / "C2_paired_contrasts.csv", index=False)
p5 = C[(C.contrast == "G3C-G3") & (C.metric == "BA")]
shifted = p5[p5.setting != "indomain80"]
P5a = bool((p5["mean"] >= 0).all())
P5b = bool((p5["mean"] >= -0.01).all())
cm = shifted[shifted.family == "curvedMono"]
P5c = bool((cm.ci_low > 0).mean() >= .5)
p6 = C[(C.contrast == "M3-G3") & (C.metric == "BA")]
P6a = bool((p6[p6.setting != "indomain80"]["mean"] < 0).sum() > len(p6[p6.setting != "indomain80"]) / 2)
P6b = bool((p6[p6.setting == "indomain80"]["mean"] >= -0.005).all())
means = df.groupby(["family", "setting", "model"])[mets].mean().round(4)
means.to_csv(OUT / "C2_means.csv")
verdict = {"fit_failures": fails, "P5a_G3C_ge_G3_every_cell": P5a, "P5b_no_cell_below_-0.01": P5b,
           "P5c_curvedMono_ci_excludes0_in_half_shifted": P5c, "P6a_M3_lt_G3_majority_shifted": P6a,
           "P6b_M3_ge_G3_minus_0.005_indomain": P6b,
           "G3C_minus_G3_BA": p5[["family", "setting", "mean", "ci_low", "ci_high", "positive", "n"]].round(4).to_dict("records"),
           "M3_minus_G3_BA": p6[["family", "setting", "mean", "ci_low", "ci_high"]].round(4).to_dict("records")}
(OUT / "C2_transfer_verdict.json").write_text(json.dumps(verdict, indent=2))
pd.set_option("display.width", 250)
print(json.dumps({k: v for k, v in verdict.items() if k.startswith(("P", "fit"))}, indent=1))
print(C[C.metric.isin(["BA", "NSD_0.1", "ASSD"])].pivot_table(index=["family", "setting"], columns=["contrast", "metric"], values="mean").round(3).to_string())
print(means["BA"].unstack("model").to_string())
