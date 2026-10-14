"""Descriptive summaries only; no fitting, reselection or additional arms."""
from pathlib import Path
import json,csv,sys
sys.stdout.reconfigure(encoding="utf-8")
import numpy as np
from controlled_worlds import WORLDS,ARMS
from run_controlled import save,ROOT

data=json.loads((ROOT/"CONTROLLED_RESULTS.json").read_text())
records=[r for r in data["records"] if "arm" in r]
queries=[r for r in data["records"] if "arm" not in r]
summary={"status":"DESCRIPTIVE","static":[],"sequential":[],
         "fit_failures":[r for r in records if r["status"]!="ok"],
         "query_stops":[r for r in queries if r["status"]!="ok"],
         "fallbacks":[r["key"] for r in records if r.get("diagnostics",{}).get("fallback")],
         "run_state":data["run_state"]}
metrics=("BA","specificity","sensitivity","Brier","log_loss","probability_MSE",
         "pi_90_coverage","pi_90_width")
for world in WORLDS:
    for budget in (8,16):
        row={"world":world,"budget":budget,"arms":{}}
        for arm in ARMS:
            rr=[r for r in records if r["key"].startswith("static_") and
                r["world"]==world and r["budget"]==budget and r["arm"]==arm and r["status"]=="ok"]
            if not rr:continue
            values={metric:float(np.mean([r["metrics"][metric] for r in rr
                      if r["metrics"][metric] is not None])) for metric in metrics}
            values["n"]=len(rr)
            negatives=[p for r in rr for y,p in zip(r["y_paid"],r["paid_probabilities"]) if y==0]
            values["paid_negative_probabilities"]=negatives
            values["rho_weights_mean"]=np.mean([r["diagnostics"]["rho_weights"] for r in rr],axis=0).tolist()
            row["arms"][arm]=values
        summary["static"].append(row)

def trapezoid(values):
    return float(np.trapezoid(values,dx=1)/(len(values)-1))

for world in ("informative_depth","local_contradiction","harmful_bridge"):
    for seed in (2301,2302,2303):
        row={"world":world,"seed":seed,"arms":{}}
        paths={}
        for rule in ("paired","margin"):
            rr=sorted([r for r in records if r["key"].startswith(f"seq_{world}_{seed}_{rule}_")
                       and r["status"]=="ok"],key=lambda r:r["budget"])
            if not rr:continue
            row["arms"][rule]={"budgets":[r["budget"] for r in rr],
                 "final":rr[-1]["metrics"],"final_paid_ids":rr[-1]["paid_ids"],
                 "curves":{m:[r["metrics"][m] for r in rr] for m in metrics}}
            if len(rr)==5:
                row["arms"][rule]["AULC"]={m:trapezoid([r["metrics"][m] for r in rr]) for m in metrics}
            paths[rule]=rr[-1]["paid_ids"]
        if len(paths)==2:
            a,b=paths["paired"],paths["margin"]
            row["first_divergence_budget"]=next((i+1 for i,(x,y) in enumerate(zip(a,b)) if x!=y),None)
            row["final_jaccard"]=len(set(a)&set(b))/len(set(a)|set(b))
            if all("AULC" in row["arms"][r] for r in ("paired","margin")):
                row["paired_minus_margin_AULC"]={m:row["arms"]["paired"]["AULC"][m]-row["arms"]["margin"]["AULC"][m] for m in metrics}
        summary["sequential"].append(row)
save(ROOT/"RESULTS_SUMMARY.json",summary)
lines=["**Controlled descriptive results — no real-simulation performance evidence**","",
       "Static table: B16 averages over two frozen seeds; all worlds and arms are retained.",
       "","| World | V2 BA | V1 BA | Binary EP BA | V2 − binary specificity | V2 − binary Brier | V2 pi coverage / width |",
       "|---|---:|---:|---:|---:|---:|---:|"]
for row in summary["static"]:
    if row["budget"]!=16:continue
    a=row["arms"];v=a["V2_EP_mixture"];b=a["Binary_V2_EP"]
    lines.append(f"| {row['world']} | {v['BA']:.3f} | {a['V1_Laplace']['BA']:.3f} | {b['BA']:.3f} | {v['specificity']-b['specificity']:+.3f} | {v['Brier']-b['Brier']:+.3f} | {v['pi_90_coverage']:.3f} / {v['pi_90_width']:.3f} |")
lines.extend(["","Sequential table: paired minus margin AULC over B6–B10 with the same V2 model and paid-output contract.",
              "","| World / seed | BA | Specificity | Sensitivity | Brier | Log loss | First divergence |",
              "|---|---:|---:|---:|---:|---:|---:|"])
for row in summary["sequential"]:
    d=row.get("paired_minus_margin_AULC")
    if d:
        lines.append(f"| {row['world']} / {row['seed']} | {d['BA']:+.3f} | {d['specificity']:+.3f} | {d['sensitivity']:+.3f} | {d['Brier']:+.3f} | {d['log_loss']:+.3f} | {row['first_divergence_budget']} |")
    else:
        lines.append(f"| {row['world']} / {row['seed']} | incomplete | | | | | |")
lines.extend(["","BA differences use the fixed p>=0.5 decision. Coverage is of the known synthetic probability law, not of a binary event. Narrower intervals are not necessarily better.",
              "",f"Fit failures: {len(summary['fit_failures'])}; numerical query stops: {len(summary['query_stops'])}; fallbacks: {len(summary['fallbacks'])}."])
(ROOT/"CONTROLLED_SUMMARY.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
print("\n".join(lines))
