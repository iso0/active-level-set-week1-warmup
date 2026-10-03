"""Additional read-only summaries and figures for the Week 12 synthesis."""
from __future__ import annotations
import argparse
import json
import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from scipy.stats import spearmanr
from sklearn.preprocessing import StandardScaler
from src.week12_development_common import OUT, FEATURES, load_new, load_old, metrics, write_csv, write_json

LABELS = {"maximin":"Maximin", "physics_stratified_geometry":"Physics strata",
          "adaptive_physics":"Adaptive physics", "uniform_random":"Uniform random"}


def startup_figures():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    root=OUT/"startup/benchmark"
    costs=pd.read_csv(root/"discovery_costs.csv")
    coverage=pd.read_csv(root/"coverage_summary.csv")
    fig, axes=plt.subplots(1,2,figsize=(11.5,4.5))
    for rule,g in costs.groupby("rule"):
        b=np.arange(1,49)
        axes[0].step(b,[(g.discovery_cost<=k).mean() for k in b],where="post",label=LABELS[rule])
    axes[0].axvline(16,color="grey",ls=":",lw=1)
    axes[0].set(xlabel="Paid queries",ylabel="Fraction discovering both classes",ylim=(0,1.03),xlim=(1,48))
    axes[0].legend(fontsize=8);axes[0].grid(alpha=.2)
    for rule,g in coverage.groupby("rule"):
        g=g[g.budget<=24]
        axes[1].plot(g.budget,g.mean_nearest_std4,marker="o",label=LABELS[rule])
    axes[1].set(xlabel="Paid queries in standalone startup sequence",ylabel="Mean nearest queried distance (4D standardized)")
    axes[1].legend(fontsize=8);axes[1].grid(alpha=.2)
    fig.suptitle("NEW-136 development: class discovery and geometric coverage")
    fig.tight_layout()
    fig.savefig(root/"discovery_and_coverage.png",dpi=180)
    fig.savefig(root/"discovery_and_coverage.pdf")
    plt.close(fig)
    table=costs.groupby("rule").discovery_cost.agg(["mean","median","max"])
    table["release_min8_mean"]=costs.groupby("rule").discovery_cost.apply(lambda s:np.maximum(8,s).mean())
    write_csv(root/"discovery_release_summary.csv",table.reset_index())


def mechanism_addendum():
    """Fixed descriptive k=5 OLD neighborhood, not a model-selection exercise."""
    new,old=load_new(),load_old()
    scaler=StandardScaler().fit(old[FEATURES])
    xn,xo=scaler.transform(new[FEATURES]),scaler.transform(old[FEATURES])
    dist=cdist(xn,xo)
    nearest=np.argsort(dist,axis=1,kind="stable")[:,:5]
    frame=new[["row_index","sim_id",*FEATURES,"log_h","has_keyhole"]].copy()
    frame["nearest_old_distance"]=dist.min(1)
    frame["old_5nn_keyhole_fraction"]=old.has_keyhole.to_numpy()[nearest].mean(1)
    frame["old_5nn_label_heterogeneity"]=4*frame.old_5nn_keyhole_fraction*(1-frame.old_5nn_keyhole_fraction)
    for feature in FEATURES:
        frame[feature+"_outside_old_range"]=(new[feature]<old[feature].min())|(new[feature]>old[feature].max())
    pred=pd.read_csv(OUT/"models/transfer/predictions.csv.gz")
    m=pred[pred.model=="M3"].sort_values("row_index")
    for col in ["probability","physics_latent","residual_latent","latent_variance"]:
        frame["M3_"+col]=m[col].to_numpy()
    frame["M3_wrong"]=(frame.M3_probability>=.5)!=frame.has_keyhole
    frame["M3_squared_error"]=(frame.M3_probability-frame.has_keyhole)**2
    p=np.clip(frame.M3_probability.to_numpy(),1e-12,1-1e-12)
    frame["M3_entropy"]=-p*np.log(p)-(1-p)*np.log(1-p)
    root=OUT/"interpretation"
    write_csv(root/"support_and_error.csv",frame)
    rows=[]
    for variable in ["nearest_old_distance","old_5nn_label_heterogeneity","M3_entropy","M3_latent_variance","log_h","VX","ST"]:
        for error in ["M3_wrong","M3_squared_error"]:
            rho,pval=spearmanr(frame[variable],frame[error])
            rows.append({"variable":variable,"error":error,"spearman_rho":rho,"descriptive_p_not_adjusted":pval})
    write_csv(root/"support_error_associations.csv",pd.DataFrame(rows))
    subgroup=[]
    for name,mask in [("all",np.ones(len(frame),bool)),("ST_inside_OLD",~frame.ST_outside_old_range),
                      ("ST_outside_OLD",frame.ST_outside_old_range), ("rare_non_keyhole",frame.has_keyhole.eq(0))]:
        subgroup.append({"subgroup":name,**metrics(frame.has_keyhole[mask],frame.M3_probability[mask]),
                         "mean_abs_discrepancy_logit":float(frame.M3_residual_latent[mask].abs().mean())})
    write_csv(root/"transfer_subgroups.csv",pd.DataFrame(subgroup))
    diag=json.loads((OUT/"models/transfer/fit_diagnostics.json").read_text())
    cvdiag=json.loads((OUT/"models/new_only/fit_diagnostics.json").read_text())
    ard=[]
    oldm=next(x for x in diag if x["model"]=="M3")
    for i,feature in enumerate(FEATURES):
        newvals=np.array([x["length_scales"][i] for x in cvdiag if x["model"]=="M3" and x["fit_status"]!="FAILED"])
        ard.append({"feature":feature,"old_standardized_scale":oldm["length_scales"][i],
                    "new_cv_median_standardized_scale":np.median(newvals),"new_cv_min":newvals.min(),"new_cv_max":newvals.max(),
                    "new_cv_upper_bound_fraction":np.isclose(newvals,100).mean(),
                    "meaning":"Different scaler distributions and repeated data; not causal feature importance"})
    write_csv(root/"ard_comparison.csv",pd.DataFrame(ard))
    write_json(root/"config.json",{"classification":"EXPLORATORY","old_neighbor_k":5,"no_tuning":True,
                                   "subgroups":"ST inside/outside historical marginal range; descriptive only"})


def new_model_figures():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    root=OUT/"models/new_only"
    f=pd.read_csv(root/"pooled_oof_per_repeat.csv")
    f=f[f.subset=="full"]
    summary=f.groupby("model").agg({c:["mean","std","min","max"] for c in ["accuracy","balanced_accuracy","roc_auc","pr_auc_non_keyhole","brier","keyhole_recall","non_keyhole_recall"]})
    summary.columns=["_".join(c) for c in summary.columns]
    write_csv(root/"pooled_summary_expanded.csv",summary.reset_index())
    fig,axes=plt.subplots(1,3,figsize=(11,4.5))
    for ax,metric,title in zip(axes,["balanced_accuracy","non_keyhole_recall","brier"],["Balanced accuracy","Non-Keyhole recall","Brier score (lower is better)"]):
        grouped=f.groupby("model")[metric]
        names=list(grouped.mean().index)
        ax.bar(np.arange(len(names)),grouped.mean().to_numpy(),yerr=grouped.std().to_numpy(),capsize=3)
        ax.set_xticks(np.arange(len(names)),[n if n!="empirical_prior" else "Prior" for n in names],rotation=25)
        ax.set_title(title,fontsize=10)
    fig.suptitle("NEW-only model CV: mean and partition SD over 20 repeats")
    fig.tight_layout();fig.savefig(root/"model_comparison.png",dpi=180);plt.close(fig)
    pairs=[]
    for metric in ["balanced_accuracy","roc_auc","brier","non_keyhole_recall"]:
        pv=f.pivot(index="repeat",columns="model",values=metric)
        for control in ["H","G0","G3"]:
            d=pv.M3-pv[control]
            pairs.append({"contrast":"M3-"+control,"metric":metric,"mean_delta":d.mean(),"sd_delta":d.std(),"min_delta":d.min(),"max_delta":d.max(),"positive_repeats":int((d>0).sum()),"repeats":len(d)})
    write_csv(root/"paired_partition_differences.csv",pd.DataFrame(pairs))


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("mode",choices=["startup","models"]);a=p.parse_args()
    if a.mode=="startup":startup_figures()
    else:mechanism_addendum();new_model_figures()
