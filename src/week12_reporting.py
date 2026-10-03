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


def transfer_addendum():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sklearn.metrics import roc_curve,precision_recall_curve
    root=OUT/"models/transfer"
    pred=pd.read_csv(root/"predictions.csv.gz")
    fig,axes=plt.subplots(1,2,figsize=(10.5,4.5))
    for name,g in pred.groupby("model"):
        if name=="empirical_prior":continue
        y,p=g.truth.to_numpy(),g.probability.to_numpy()
        fpr,tpr,_=roc_curve(y,p)
        axes[0].plot(fpr,tpr,label=name)
        precision,recall,_=precision_recall_curve(1-y,1-p)
        axes[1].step(recall,precision,where="post",label=name)
    axes[0].plot([0,1],[0,1],"k:",lw=1)
    axes[1].axhline(12/136,color="grey",ls=":",label="Rare-class prevalence")
    axes[0].set(xlabel="False-positive rate",ylabel="Keyhole recall",title="ROC")
    axes[1].set(xlabel="Non-Keyhole recall",ylabel="Non-Keyhole precision",title="Rare-class precision-recall")
    for ax in axes:ax.legend(fontsize=8);ax.grid(alpha=.2)
    fig.suptitle("Strict OLD-trained predictions on NEW-136; no NEW fitting")
    fig.tight_layout();fig.savefig(root/"transfer_roc_rare_pr.png",dpi=180);plt.close(fig)
    boot=pd.read_csv(root/"class_stratified_bootstrap.csv.gz")
    rows=[]
    for subset in ["full","q20"]:
        p=boot[boot.subset==subset].pivot(index="draw",columns="model",values="pr_auc_non_keyhole")
        for control in ["H","G0","G3"]:
            d=(p.M3-p[control]).dropna()
            rows.append({"contrast":"M3-"+control,"subset":subset,"metric":"pr_auc_non_keyhole",
                         "bootstrap_mean":d.mean(),"low":d.quantile(.025),"high":d.quantile(.975),
                         "draws":len(d),"scope":"Paired fixed-prediction class-stratified cohort resampling"})
    write_csv(root/"rare_AP_paired_bootstrap.csv",pd.DataFrame(rows))


def active_addendum():
    root=OUT/"active_learning"
    oof=pd.read_csv(root/"pooled_oof_metrics.csv.gz")
    paths=pd.read_csv(root/"query_paths.csv.gz")
    endpoints=pd.read_csv(root/"repeat_endpoints.csv")
    rows=[]
    for (repeat,arm,subset),g in oof.groupby(["repeat","arm","subset"]):
        g=g[g.budget.between(16,80)].sort_values("budget")
        for metric in ["balanced_accuracy","non_keyhole_recall","brier"]:
            rows.append({"repeat":repeat,"arm":arm,"subset":subset,"metric":metric,
                         "AULC_B16_B80":np.trapezoid(g[metric],g.budget)/64})
    aux=pd.DataFrame(rows)
    write_csv(root/"secondary_repeat_aulc.csv",aux)
    summary=[]
    for arm in sorted(oof.arm.unique()):
        q=endpoints[(endpoints.arm==arm)&(endpoints.subset=="q20")&(endpoints.endpoint=="accuracy_AULC_B16_B80")]
        ba=aux[(aux.arm==arm)&(aux.subset=="full")&(aux.metric=="balanced_accuracy")]
        qr=aux[(aux.arm==arm)&(aux.subset=="q20")&(aux.metric=="balanced_accuracy")]
        rr=oof[(oof.arm==arm)&(oof.subset=="full")&(oof.budget==80)]
        budget=paths[(paths.arm==arm)&paths.selection_mode.str.startswith("paid_startup")].groupby("split_id").size()
        summary.append({"arm":arm,"q20_accuracy_AULC_B16_B80":q.value.mean(),
                        "q20_accuracy_partition_sd":q.value.std(),
                        "full_balanced_accuracy_AULC_B16_B80":ba.AULC_B16_B80.mean(),
                        "pooled_q20_balanced_accuracy_AULC_B16_B80":qr.AULC_B16_B80.mean(),
                        "full_non_keyhole_recall_B80":rr.non_keyhole_recall.mean(),
                        "full_accuracy_B80":rr.accuracy.mean(),"mean_paid_startup":budget.mean(),"max_paid_startup":budget.max()})
    summary=pd.DataFrame(summary)
    write_csv(root/"complete_protocol_scorecard.csv",summary)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    short={"M3_margin__maximin16_continue":"Margin / maximin16",
           "Candidate_A__maximin16_continue":"Candidate A / maximin16",
           "Candidate_B__maximin8_continue":"Candidate B / maximin8",
           "M3_margin__maximin8_continue":"Margin / maximin8",
           "M3_margin__adaptive_physics8":"Margin / adaptive8",
           "M3_margin__physics_stratified8":"Margin / physics strata8",
           "M3_margin__uniform8_continue":"Margin / uniform8",
           "M3_random__maximin16_continue":"Random / maximin16"}
    fig,axes=plt.subplots(1,2,figsize=(12,5.5))
    colors=plt.cm.tab10.colors
    arm_colors={arm:colors[i] for i,arm in enumerate(sorted(oof.arm.unique()))}
    for i,r in enumerate(summary.sort_values("q20_accuracy_AULC_B16_B80").itertuples()):
        axes[0].barh(i,r.q20_accuracy_AULC_B16_B80,color=arm_colors[r.arm])
        axes[0].text(r.q20_accuracy_AULC_B16_B80-.012,i,f"{r.q20_accuracy_AULC_B16_B80:.4f}",va="center",ha="right",fontsize=8,color="white")
    ordered=summary.sort_values("q20_accuracy_AULC_B16_B80")
    axes[0].set_yticks(range(len(ordered)),[short[x] for x in ordered.arm])
    axes[0].set(xlabel="Mean fold q20 accuracy AULC B16-B80",xlim=(0, max(.78,summary.q20_accuracy_AULC_B16_B80.max()+.06)))
    # The majority predictor's q20 accuracy is fixed by the evaluation masks.
    fold_metrics=pd.read_csv(root/"fold_metrics.csv.gz")
    majority_rows=fold_metrics[(fold_metrics.arm==oof.arm.iloc[0])&(fold_metrics.subset=="q20")&(fold_metrics.budget==80)]
    majority=(majority_rows.n_keyhole/majority_rows.n).mean()
    axes[0].axvline(majority,color="black",ls=":",label="Always Keyhole")
    for arm,g in oof[(oof.subset=="full")&(oof.budget>=16)].groupby("arm"):
        curve=g.groupby("budget").balanced_accuracy.mean()
        axes[1].plot(curve.index,curve.values,label=short[arm],color=arm_colors[arm])
    axes[1].axhline(.5,color="black",ls=":")
    axes[1].set(xlabel="Total paid queries",ylabel="Pooled OOF balanced accuracy")
    axes[1].legend(fontsize=7,loc="lower right");axes[0].legend(fontsize=8,loc="lower left")
    fig.suptitle("Complete NEW-only development protocols; no external confirmation")
    fig.tight_layout();fig.savefig(root/"protocol_tradeoffs.png",dpi=180);plt.close(fig)
    # Paired partition variation is conditional on this single observed campaign.
    contrast=pd.read_csv(root/"paired_contrasts.csv")
    c=contrast[(contrast.subset=="q20")&(contrast.endpoint=="accuracy_AULC_B16_B80")].reset_index(drop=True)
    fig,ax=plt.subplots(figsize=(10,5.5))
    for i,r in c.iterrows():
        ax.plot([r.partition_interval_low,r.partition_interval_high],[i,i],color="steelblue")
        ax.plot(r.mean_delta,i,"o",color="navy")
    ax.axvline(0,color="grey",ls=":")
    ax.set_yticks(range(len(c)),[short[r.arm]+" minus "+short[r.reference] for r in c.itertuples()])
    ax.set(xlabel="Paired q20 accuracy AULC difference, B16-B80",
           title="Conditional partition bootstrap intervals\nOne campaign; no multiplicity adjustment")
    fig.tight_layout();fig.savefig(root/"paired_q20_differences.png",dpi=180);plt.close(fig)
    d=pd.read_csv(root/"fit_diagnostics.csv.gz")
    d["nonconverged"]=~d.optimizer_converged.astype(bool)
    diagnostics=d.groupby("arm").agg(records=("budget","size"),nonconverged=("nonconverged","sum"),
        residual_upper_bound_fraction=("residual_sd_upper_bound_hit","mean"),
        any_length_bound_fraction=("any_length_bound_hit","mean")).reset_index()
    diagnostics["nonconverged_fraction"]=diagnostics.nonconverged/diagnostics.records
    write_csv(root/"fit_diagnostics_by_protocol.csv",diagnostics)
    write_json(root/"reporting_summary.json",{"majority_mean_fold_q20_accuracy":majority,
        "primary_aggregation":"Equal-fold within repeat, equal-repeat across20 repeats",
        "secondary_aggregation":"Pooled heldout predictions within each repeat",
        "optimizer_records_may_share_exact_prefix_fits":True,
        "number_independent_new_campaigns":1})


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("mode",choices=["startup","models","transfer","active"]);a=p.parse_args()
    if a.mode=="startup":startup_figures()
    elif a.mode=="models":mechanism_addendum();new_model_figures()
    elif a.mode=="transfer":transfer_addendum()
    else:active_addendum()
