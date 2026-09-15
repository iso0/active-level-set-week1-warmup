import numpy as np, pandas as pd
OUT = "/home/claude/rnd/followup/results/"
n = pd.read_csv(OUT + "nested_subsets.csv.gz"); pd.set_option("display.width", 250)
# average seeds within (run, seq, n, model)
g = n.groupby(["run_id", "repeat", "seq", "n", "model"])[["q20_acc", "q30_acc", "full_acc", "q20_ba", "q20_khrec", "frac_band_in_train"]].mean().reset_index()
sizes = sorted(g.n.unique())
rows = []
for (seq, model), gg in g.groupby(["seq", "model"]):
    piv = gg.pivot_table(index="run_id", columns="n", values="q20_acc"); mean = piv.mean()
    # consecutive-size decreases: per run, fraction of steps with decrease; and mean-curve decreases with block CI
    d = piv.diff(axis=1).iloc[:, 1:]
    rep = gg.groupby("run_id").repeat.first().loc[piv.index]
    dec_steps = []
    for col in d.columns:
        blocks = d[col].groupby(rep).mean(); m = blocks.mean(); se = blocks.std(ddof=1) / np.sqrt(len(blocks))
        dec_steps.append({"seq": seq, "model": model, "to_n": col, "mean_delta_q20": m, "lo": m - 1.96 * se, "hi": m + 1.96 * se, "frac_runs_decrease": (d[col] < 0).mean()})
    ds = pd.DataFrame(dec_steps); ds.to_csv(OUT + f"nested_steps_{seq}_{model}.csv", index=False)
    sig_dec = ds[ds.hi < 0];
    rows.append({"seq": seq, "model": model, "q20_at_16": mean.get(16, np.nan), "q20_at_40": mean.get(40, np.nan), "q20_at_80": mean.get(80, np.nan), "q20_at_120": mean.get(120, np.nan), "q20_at_324": mean.get(324, np.nan),
                 "q20_max": mean.max(), "n_at_max": mean.idxmax(), "n_steps_signif_decrease": len(sig_dec), "steps_signif_decrease": sig_dec.to_n.tolist(), "mean_frac_steps_decrease_per_run": (d < 0).mean().mean(),
                 "q30_at_324": gg[gg.n == 324].q30_acc.mean(), "full_at_324": gg[gg.n == 324].full_acc.mean(), "khrec_q20_at_324": gg[gg.n == 324].q20_khrec.mean()})
summ = pd.DataFrame(rows); summ.to_csv(OUT + "nested_summary.csv", index=False); print(summ.round(4).to_string())
# mean curves table
tab = g[g.model == "M3"].groupby(["seq", "n"])[["q20_acc", "q30_acc", "full_acc", "q20_khrec"]].mean().unstack(0)
print("\nM3 mean q20 by size and sequence:"); print(tab["q20_acc"].loc[[16, 24, 32, 40, 48, 60, 80, 100, 120, 160, 200, 260, 324]].round(4).to_string())
print("\nM3 mean full acc by size and sequence:"); print(tab["full_acc"].loc[[16, 24, 40, 80, 120, 200, 324]].round(4).to_string())
print("\nM3R05 minus M3 q20 by size (mean over sequences):"); dm = g.pivot_table(index=["run_id", "seq", "n"], columns="model", values="q20_acc"); print((dm.M3R05 - dm.M3).groupby(level="n").mean().loc[[16, 40, 80, 120, 200, 324]].round(4).to_string())
