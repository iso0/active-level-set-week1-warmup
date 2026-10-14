"""Figures from saved results only; no model fitting."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

root=Path(__file__).resolve().parent
s=json.loads((root/"RESULTS_SUMMARY.json").read_text())
d=json.loads((root/"SUPPLEMENTAL_DIAGNOSTICS.json").read_text())["V1_sparse_case"]
fig,axes=plt.subplots(1,3,figsize=(17,5.7),gridspec_kw={"width_ratios":[1,1.45,1.2]})
fig.suptitle("V2 controlled evidence: reduced forced sharing, unresolved rare-negative generalization",fontsize=16,fontweight="bold")
p=d["probabilities"];ref=d["reference"]
values=[p["V1_Laplace"],p["rho1_EP"],ref["probability_mean"],p["V2_EP_mixture"]]
axes[0].bar(np.arange(4),values,color=["#a4a8b0","#b77734","#374d68","#087f8c"])
axes[0].errorbar(2,values[2],yerr=2*ref["batch_MCSE"],fmt="none",ecolor="black",capsize=4)
axes[0].axhline(.5,color="#a33b35",lw=1,ls="--")
for i,v in enumerate(values):axes[0].text(i,v+.025,f"{v:.3f}",ha="center")
axes[0].set_xticks(range(4),["V1\nLaplace","Fixed ρ=1\nEP","Fixed V1\nMCMC","V2\nmixture"])
axes[0].set_ylim(0,.92)
axes[0].set_ylabel("P(Keyhole) at the already paid negative")
axes[0].set_title("More accurate inference does not\nmake the fixed bridge favorable",fontsize=12)
rows=[r for r in s["static"] if r["budget"]==16]
labels=["Informative","Redundant","Local contradiction","Harmful bridge","Shifted threshold",
        "0 paid negatives","1 paid negative","2 paid negatives","Missing depth","Model-generated"]
y=np.arange(len(rows))
db=[r["arms"]["V2_EP_mixture"]["BA"]-r["arms"]["Binary_V2_EP"]["BA"] for r in rows]
dv=[r["arms"]["V2_EP_mixture"]["BA"]-r["arms"]["V1_Laplace"]["BA"] for r in rows]
axes[1].scatter(db,y-.1,label="V2 − Binary EP",color="#087f8c",s=40,zorder=3)
axes[1].scatter(dv,y+.1,label="V2 − V1",color="#b77734",marker="s",s=30,zorder=3)
axes[1].set_yticks(y,labels);axes[1].invert_yaxis()
axes[1].axvline(0,color="#aaa",lw=1)
axes[1].set_xlim(-.06,.25);axes[1].set_xlabel("BA difference at B16; two fixed seeds")
axes[1].set_title("Benefit depends on the world",fontsize=12)
axes[1].legend(loc="lower right",fontsize=9)
seq=s["sequential"]
colors={"informative_depth":"#087f8c","local_contradiction":"#b77734","harmful_bridge":"#374d68"}
labels_short={"informative_depth":"Informative","local_contradiction":"Local contradiction","harmful_bridge":"Harmful bridge"}
for k,name in enumerate(colors):
    rr=[r for r in seq if r["world"]==name]
    val=[r["paired_minus_margin_AULC"]["BA"] for r in rr]
    axes[2].scatter(val,np.arange(3)+k*3,color=colors[name],s=45)
axes[2].set_yticks(np.arange(9),[labels_short[r["world"]]+"\n"+str(r["seed"]) for r in seq],fontsize=9)
axes[2].invert_yaxis();axes[2].axvline(0,color="#aaa",lw=1)
axes[2].set_xlabel("Paired − margin BA AULC, B6–B10")
axes[2].set_title("Different paths, mixed outcomes\nsame V2 model in both arms",fontsize=12)
for ax in axes:
    ax.spines[["top","right"]].set_visible(False)
    ax.grid(axis="x",alpha=.15)
fig.text(.5,.005,"Synthetic mechanism checks only. No SPH superiority, calibrated physical uncertainty or query savings established.",ha="center",fontsize=10)
fig.tight_layout(rect=(0,.035,1,.94))
fig.savefig(root/"V2_MECHANISMS.png",dpi=160,bbox_inches="tight")
print("Saved V2_MECHANISMS.png")
