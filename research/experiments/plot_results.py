"""Render figures from sealed results only; no model fitting or selection."""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import common


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--development", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = common.load_json(args.results / "evaluation.json")
    development = common.load_json(args.development / "development.json")
    destination = common.new_directory(args.output)
    plt.rcdefaults()
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"text.usetex":False,
                         "axes.spines.top":False,"axes.spines.right":False})
    models = ["rules","entropy","raw_knn","standardised_knn","logistic","gitleaks"]
    names = ["Rules\nordering","Entropy","Raw\nKNN","Standardised\nKNN","Logistic","Gitleaks\nsnapshot"]
    colours = ["#94a3b8","#64748b","#38bdf8","#075985","#c2410c","#a3a3a3"]
    fig, axes = plt.subplots(1,2,figsize=(12,5.5),layout="constrained")
    for axis, metric, title in zip(axes,["precision_at_20","average_precision"],
                                   ["Mean repository Precision@20","Mean repository average precision"]):
        values = [report["ranking"][m]["aggregate"]["macro"][metric] for m in models]
        lower = [report["ranking"][m]["intervals"][metric]["lower"] for m in models]
        upper = [report["ranking"][m]["intervals"][metric]["upper"] for m in models]
        error = np.asarray([[max(0,v-l) for v,l in zip(values,lower)],
                            [max(0,u-v) for v,u in zip(values,upper)]])
        axis.bar(np.arange(len(models)),values,color=colours,yerr=error,capsize=4,width=.7)
        axis.set_xticks(np.arange(len(models)),names,fontsize=9)
        axis.set_ylim(0,1)
        axis.set_ylabel("Score")
        axis.set_title(title,fontsize=12,pad=12)
        axis.grid(axis="y",alpha=.2)
        axis.set_axisbelow(True)
        for index,value in enumerate(values):
            axis.text(index,max(0.03,value/2),f"{value:.3f}",ha="center",color="white",fontsize=9)
    population=report["test_population"]
    fig.suptitle("Veil Guard — held-out synthetic ranking\n"
                 f"{population['extracted_eligible_rows']:,} candidates; "
                 f"{population['repositories']} repositories; {population['connected_groups']} connected groups\n"
                 "95% group-bootstrap intervals are exploratory; Gitleaks uses a different scanning scope",
                 fontsize=12)
    fig.savefig(destination/"ranking.png",dpi=180)
    plt.close(fig)

    labels=["Length","Entropy","Digits","Uppercase","Symbols","Keyword gap","Assignment","Placeholder"]
    fig,axes=plt.subplots(1,2,figsize=(12,5.5),layout="constrained")
    correlation=np.array([[np.nan if v is None else v for v in row]
                          for row in development["training_only_correlation"]])
    image=axes[0].imshow(correlation,vmin=-1,vmax=1,cmap="RdBu_r")
    axes[0].set_xticks(range(8),labels,rotation=50,ha="right",fontsize=9)
    axes[0].set_yticks(range(8),labels,fontsize=9)
    axes[0].set_title("Training feature correlations")
    fig.colorbar(image,ax=axes[0],shrink=.8,label="Pearson correlation")
    baseline=development["selected_knn"]["standardised"]["macro_repository_AP"]
    differences=[r["macro_repository_AP"]-baseline for r in development["training_only_ablations"]]
    axes[1].barh(labels,differences,color=["#075985" if d<0 else "#c2410c" for d in differences])
    axes[1].axvline(0,color="#111827",linewidth=.8)
    axes[1].invert_yaxis()
    axes[1].set_xlabel("Change in training OOF macro AP")
    axes[1].set_title("One coordinate zeroed; eight columns retained")
    axes[1].grid(axis="x",alpha=.2)
    axes[1].set_axisbelow(True)
    fig.suptitle("Training-only diagnostics — no feature selection from held-out results",fontsize=12)
    fig.savefig(destination/"training-diagnostics.png",dpi=180)
    plt.close(fig)
    print("Sealed-result figures rendered.")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
