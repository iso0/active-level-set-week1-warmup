"""Registered scientific summaries and fixed-world slices, with charged reconstruction fits."""
import argparse
import csv
import gzip
import json
import os
from pathlib import Path
import time
import traceback
import psutil
from coordination import ROOT, Slot, now
from ledger import add_units, claim, finish, Meter, atomic_json, sha256, connection


def run():
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import posterior
    from posterior import Posterior
    from worlds import World
    manifest = json.loads((ROOT/"FROZEN_TEST_V1.json").read_text())
    for name, digest in manifest["source_hashes"].items():
        assert sha256(ROOT/name) == digest
    out = ROOT/"figures"
    out.mkdir(exist_ok=True)
    analysis = ROOT/"results/analysis"
    def csvrows(name):
        with (analysis/name).open(newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    rows = csvrows("per_world_readouts.csv")
    colors = {"existing__h1": "#3b6fb6", "existing__h2": "#0e355e",
              "local__h1": "#db8b24", "local__h2": "#8c4716",
              "ard__h1": "#7a4fa0", "ard__straddle": "#20826a",
              "existing__straddle": "#9f6e88", "local__straddle": "#c44343",
              "existing__mixture_h1": "#658ba0", "local__mixture_h1": "#aeae32"}
    labels = {k: k.replace("__", " / ").replace("mixture_h1", "mixture h1") for k in colors}
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                         "savefig.dpi": 170})
    index = []
    def save(fig, name, caption):
        fig.savefig(out/(name+".png"), bbox_inches="tight")
        fig.savefig(out/(name+".pdf"), bbox_inches="tight")
        plt.close(fig)
        index.append({"name": name, "png": str((out/(name+".png")).relative_to(ROOT)),
                      "pdf": str((out/(name+".pdf")).relative_to(ROOT)), "caption": caption,
                      "png_sha256": sha256(out/(name+".png"))})

    families = list(manifest["family_counts"])
    fig, axs = plt.subplots(3, 4, figsize=(16, 10), sharex=True)
    for ax, family in zip(axs.flat, families):
        for arm in colors:
            rs = [r for r in rows if r["family"] == family and r["panel"] == "prefix" and r["arm"] == arm]
            if not rs:
                continue
            budgets = sorted({int(r["budget"]) for r in rs})
            means = [np.mean([float(r["error"]) for r in rs if int(r["budget"]) == b]) for b in budgets]
            ax.plot(budgets, means, color=colors[arm], label=labels[arm], lw=1.5, marker=".", ms=4)
        ax.set_title(family.replace("_", " "))
        ax.set_ylabel("Uniform sign error")
        ax.set_xlabel("Paid queries, including common prefix")
        ax.grid(alpha=.18)
    axs.flat[-1].axis("off")
    handles, ls = axs.flat[0].get_legend_handles_labels()
    axs.flat[-1].legend(handles, ls, loc="center left", frameon=False)
    fig.suptitle("All fixed TEST families: common-prefix learning curves\nMeans over independent worlds; no family omitted; uncertainty is in paired contrast tables")
    fig.tight_layout(rect=(0, 0, 1, .94))
    save(fig, "all_family_learning_curves", "Uniform sign error by all eleven families. Descriptive means; primary uncertainty is whole-world simultaneous, not a pointwise curve guarantee.")

    primary = json.loads((analysis/"PRIMARY_CONTRASTS.json").read_text())
    fig, ax = plt.subplots(figsize=(10, 5))
    for k, (key, r) in enumerate(primary["contrasts"].items()):
        lo, hi = r["ci95_simultaneous"]
        if r["estimate"] is not None and lo is not None and hi is not None:
            ax.errorbar(r["estimate"], k, xerr=[[r["estimate"]-lo], [hi-r["estimate"]]],
                        fmt="o", color="#3b6fb6", capsize=4)
    ax.set_yticks(range(6), [k.replace("island_error", "Conditional island error").replace("error", "Global error").replace("__", ": ") for k in primary["contrasts"]])
    ax.axvline(0, color="black", lw=1)
    ax.set_xlabel("Paired loss contrast: negative favors new factor")
    ax.set_title("Six registered primary contrasts at B48\nApproximate 95% simultaneous whole-world bootstrap intervals")
    ax.grid(axis="x", alpha=.2)
    fig.tight_layout()
    save(fig, "primary_mechanism_contrasts", "Representation R, horizon H and interaction I on global and conditional post-hit island error. Degenerate/missing coordinates cannot pass the mechanism gate.")

    costs = csvrows("same_target_query_cost.csv")
    costrows = [r for r in costs if r["panel"] == "prefix" and r["group"] == "equal_family"]
    fig, axs = plt.subplots(1, 3, figsize=(16, 5))
    for j, (metric, title) in enumerate([("attainment_fraction", "Two-readout target attainment by B48"),
                                       ("restricted_paid_query_burden", "Restricted burden min(T,48)"),
                                       ("mean_decision_cpu", "Mean selection CPU (seconds)")]):
        for k, r in enumerate(costrows):
            if r[metric]:
                axs[j].barh(k, float(r[metric]), color=colors[r["arm"]])
        axs[j].set_yticks(range(len(costrows)), [labels[r["arm"]] for r in costrows])
        axs[j].set_title(title)
        axs[j].grid(axis="x", alpha=.2)
    axs[0].set_xlim(0, 1)
    fig.suptitle("Same frozen joint target, all families equally weighted\nRestricted burden alone is not query savings; no physical runtime was measured")
    fig.tight_layout(rect=(0, 0, 1, .9))
    save(fig, "target_query_compute_cost", "Attainment, censored restricted burden and decision CPU. Outcomes that miss the target remain censored; the side-by-side bars do not establish physical time savings.")

    cs = csvrows("equal_compute_summary.csv")
    fig, axs = plt.subplots(1, 2, figsize=(13, 5))
    for ax, scope in zip(axs, ("decision", "total")):
        for arm in colors:
            rs = sorted([r for r in cs if r["panel"] == "prefix" and r["scope"] == scope and r["arm"] == arm and r["error"]], key=lambda r: float(r["cap_seconds"]))
            if rs:
                ax.plot([float(r["cap_seconds"]) for r in rs], [float(r["error"]) for r in rs],
                        color=colors[arm], label=labels[arm], marker="o", lw=1)
        ax.set_xscale("log")
        ax.set_xlabel(scope+" CPU cap (seconds)")
        ax.set_ylabel("Global sign error, available predictions")
        ax.grid(alpha=.2)
    axs[1].legend(loc="upper left", bbox_to_anchor=(1, 1), frameon=False)
    fig.suptitle("Descriptive equal-compute readouts, capped at B48\nAvailability differs at small caps; use paired-common-available tables for comparisons")
    fig.tight_layout(rect=(0, 0, 1, .9))
    save(fig, "equal_compute_readouts", "Last observed budget within each CPU cap. No extrapolation after B48. This graphic is availability-conditional; paired effects and denominators are separate.")

    search = json.loads((ROOT/"results/SEARCH_CONTROLS.json").read_text())["paths"]
    endpoints = csvrows("per_world_endpoints.csv")
    fig, axs = plt.subplots(1, 2, figsize=(13, 5))
    for ax, family in zip(axs, ("island_small", "island_large")):
        for arm in ("existing__h1", "existing__h2", "local__h1", "local__h2", "ard__straddle"):
            rs = [r for r in endpoints if r["panel"] == "e2e" and r["family"] == family and r["arm"] == arm and r["complete"] == "True"]
            if rs:
                times = [int(r["first_hit"]) if r["first_hit"] else 49 for r in rs]
                ax.step(range(8, 49), [np.mean(np.array(times) <= b) for b in range(8, 49)],
                        where="post", label=labels[arm], color=colors[arm])
        for selector, color in (("random", "#888888"), ("maximin", "#171717")):
            rs = [r for r in search if r["family"] == family and r["selector"] == selector]
            times = [r["first_valid_hit"] or 49 for r in rs]
            ax.step(range(8, 49), [np.mean(np.array(times) <= b) for b in range(8, 49)],
                    where="post", label=selector.upper()+" search only", color=color, linestyle="--")
        ax.set_title(family.replace("_", " "))
        ax.set_xlim(8, 48); ax.set_ylim(0, 1)
        ax.set_xlabel("All paid queries, including startup")
        ax.set_ylabel("Fraction with a valid island hit")
        ax.grid(alpha=.2)
    axs[1].legend(loc="upper left", bbox_to_anchor=(1, 1), frameon=False)
    fig.suptitle("First-hit opportunity is separate from learning after a hit\nUnconditional end-to-end worlds; no-pool-candidate and no-hit cases retained")
    fig.tight_layout(rect=(0, 0, 1, .9))
    save(fig, "end_to_end_first_hit", "Descriptive first-valid-hit empirical fractions. Search-only controls have no learned classification outcomes. Sixteen independent worlds per island family.")

    # Fixed worlds and fixed geometric slice, chosen before scientific TEST.
    slice_families = ("smooth", "coordinate", "rotated", "local_scale", "island_small", "island_large", "corrupt_correlated")
    arms = ("existing__h1", "existing__h2", "local__h1", "local__h2", "local__straddle", "ard__straddle")
    all_slice_rows = []
    for family in slice_families:
        ws = next(w for w in manifest["worlds"] if w["family"] == family)
        spec = {"id": "reference_slice__"+family, "kind": "registered_fixed_slice", "world_id": ws["world_id"]}
        add_units([spec], "REFERENCE")
        receipt = out/("slice_"+family+".json")
        with connection() as c:
            state = c.execute("SELECT status FROM units WHERE id=?", (spec["id"],)).fetchone()[0]
        if state == "COMPLETE":
            old = json.loads(receipt.read_text())
            index.append(old["figure"]); all_slice_rows.extend(old["reconstructions"])
            continue
        if state == "FAILED":
            all_slice_rows.append({"family": family, "status": "FAILED_PRESERVED"})
            continue
        selected = claim(spec["id"], os.getpid(), psutil.Process().create_time())
        if selected is None:
            continue
        attempt, _ = selected
        posterior.METER = Meter(attempt, reference=True)
        try:
            world = World(family, ws["seed"], **manifest["world_options"])
            t = np.linspace(0, 1, 81)
            a, b = np.meshgrid(t, t)
            grid = np.column_stack([a.ravel(), b.ravel(), np.full(a.size, .5), np.full(a.size, .5)])
            truth, _, _ = world.truth(grid)
            fig, axs = plt.subplots(2, 6, figsize=(18, 7.3), sharex=True, sharey=True)
            data = {"grid": grid, "truth": truth}
            reconstructed, local_cache = [], {}
            for col, arm in enumerate(arms):
                unit_id = f"test__{ws['world_id']}__prefix__{arm}"
                resultfile = ROOT/"results/TEST"/(unit_id+".json.gz")
                if not resultfile.exists():
                    for row in range(2):
                        axs[row, col].text(.5, .5, "INCOMPLETE", ha="center", va="center")
                    continue
                result = json.loads(gzip.decompress(resultfile.read_bytes()))
                kind = arm.split("__")[0]
                for row, budget in enumerate((32, 48)):
                    ax = axs[row, col]
                    ids = result["paid_ids"][:budget]
                    observations = [r["outputs"][0] for r in result["observations"][:budget]]
                    key = (kind, tuple(ids))
                    if key not in local_cache:
                        model = Posterior(kind, ard_options=manifest["options"]["ard_options"])
                        if kind == "ard" and budget == 48:
                            checkpoint = json.loads((ROOT/"runtime/checkpoints"/(unit_id+".json")).read_text())["policy"]
                            model.ard_theta = np.array(checkpoint["ard_theta"])
                            model.ard_last_budget = checkpoint["ard_last_budget"]
                        model.fit(world.x[ids], observations, ids)
                        _, _, p = model.predict(grid)
                        metrics = world.evaluate(model, ids)
                        expected = next(q for q in result["readouts"] if q["budget"] == budget)
                        delta = max(abs(metrics[k]-expected[k]) for k in ("error", "brier", "log_loss", "RMSE"))
                        assert delta < 1e-8, "Visual reconstruction does not match original predictions"
                        local_cache[key] = (p, delta)
                    p, delta = local_cache[key]
                    im = ax.pcolormesh(a, b, p.reshape(a.shape), cmap="coolwarm", vmin=0, vmax=1, shading="auto", rasterized=True)
                    if p.min() < .5 < p.max():
                        ax.contour(a, b, p.reshape(a.shape), levels=[.5], colors="black", linewidths=1)
                    if truth.min() < 0 < truth.max():
                        ax.contour(a, b, truth.reshape(a.shape), levels=[0], colors="black", linewidths=1.2, linestyles=":")
                    obs = np.array([np.nan if v is None else v for v in observations])
                    ax.scatter(world.x[ids, 0], world.x[ids, 1], c=np.nan_to_num(obs) > 0, cmap="bwr",
                               vmin=0, vmax=1, s=11, edgecolors="white", linewidths=.3, alpha=.55)
                    if budget > 32:
                        new = ids[32:]
                        ax.plot(world.x[new, 0], world.x[new, 1], color="white", lw=.5, alpha=.6)
                        ax.scatter(world.x[new[-1], 0], world.x[new[-1], 1], marker="x", s=35, c="black")
                    ax.set_title(labels[arm]+f", B{budget}")
                    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
                    ax.set_xlabel("x0"); ax.set_ylabel("x1")
                    data[arm+"__B"+str(budget)+"__p"] = p
                    data[arm+"__B"+str(budget)+"__paid_ids"] = np.array(ids)
                    reconstructed.append({"family": family, "world_id": ws["world_id"], "arm": arm,
                                          "budget": budget, "metric_max_abs_error": delta})
            fig.suptitle(f"Fixed TEST realization: {family}; x2=x3=0.5\nColor: P(f>0); solid: prediction contour; dotted: latent boundary. Paid points/paths are 4D projections, not slice observations.")
            fig.tight_layout(rect=(0, .02, .94, .9))
            cb = fig.add_axes([.95, .14, .012, .60]); fig.colorbar(im, cax=cb, label="Latent sign probability")
            save(fig, "slice_"+family, "Prespecified first world and fixed x2=x3=0.5 slice. Projected points can lie away from this plane. Reconstruction metrics match saved outputs; these are illustrative slices, not whole-domain boundary recovery.")
            np.savez_compressed(out/("slice_"+family+"_data.npz"), **data)
            record = {"status": "COMPLETE", "figure": index[-1], "reconstructions": reconstructed,
                      "actual_budget": posterior.METER.actual}
            atomic_json(receipt, record)
            finish(spec["id"], attempt, "COMPLETE", receipt.relative_to(ROOT).as_posix())
            all_slice_rows.extend(reconstructed)
        except Exception:
            finish(spec["id"], attempt, "FAILED", note=traceback.format_exc())
            raise
    output = {"status": "GENERATED_PENDING_VISUAL_REVIEW", "utc": now().isoformat(),
              "figures": index, "slice_reconstruction_checks": all_slice_rows,
              "source_sha256": sha256(__file__)}
    atomic_json(out/"FIGURE_INDEX.json", output)
    print(json.dumps({"status": output["status"], "figures": len(index)}, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--threads", type=int, choices=[1], required=True); p.parse_args()
    with Slot():
        run()
