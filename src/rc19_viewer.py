"""RC19 interactive pooled boundary view (recorded predictions only; nothing is interpolated or fitted here).
Every run is a test point exactly once per repeat, so the 5 folds of one repeat give one recorded prediction per run and budget.
3D axes: log P, log VX, laser spot radius LS; the fourth input ST is controlled explicitly by a band filter.
    python -m src.rc19_viewer [final|dev] [repeat]   -> opus_pooled/report/pooled_boundary_view.html (+ .json)
"""
from __future__ import annotations

import json
import sys

import numpy as np

import src.rc18_common as RC
import src.rc19_eval as EV
import src.rc19_pool as P


def build(stage="final", repeat=None):
    M = P.manifest(); ids = M.index.to_numpy(str); pos = {s: i for i, s in enumerate(ids)}
    jobs = {"region": f"{stage}-region" if stage == "final" else "dev-region", "label": f"{stage}-label" if stage == "final" else "dev-label"}
    out = {"stage": stage, "runs": {"logP": np.round(np.log(M.P), 4).tolist(), "logVX": np.round(np.log(M.VX), 4).tolist(), "LS_um": np.round(M.LS * 1e6, 2).tolist(),
                                    "ST": np.round(M.ST, 1).tolist(), "y": M.y.astype(int).tolist(), "batch": M.source_batch.tolist(),
                                    "spike": [None if not np.isfinite(v) else round(float(v), 4) for v in M.vmax_spike_logratio], "id": ids.tolist()},
           "tau": float(np.log(2.0)), "tasks": {}}
    for task, job in jobs.items():
        U = EV.load_units(P.OUT / stage / job)
        reps = sorted({u["repeat"] for u in U}); r = repeat or reps[0]; out["repeat"] = r; arms = {}
        for u in U:
            if u["repeat"] != r:
                continue
            key = f"{u['model']}|{u['acq']}" if task == "region" else u["arm"]
            A = arms.setdefault(key, {"pred": {}, "paid": {}})
            tix = [pos[s] for s in u["test_ids"]]
            for e in u["evals"]:
                b = e["budget"]
                if b % 2 and b not in (P.B0,):
                    continue                                                   # every 2nd budget keeps the page small
                vals = e["mean"] if task == "region" else e["p"]
                row = A["pred"].setdefault(str(b), [None] * len(ids))
                if vals is not None:
                    for i, v in zip(tix, vals):
                        row[i] = None if v is None else round(float(v), 4)
            A["paid"][str(u["fold"])] = [pos[s] for s in u["paid_ids"]]
        out["tasks"][task] = arms
    return out


HTML = r"""<title>Pooled Boundary View</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
:root { --bg: #f4f6f8; --panel: #ffffff; --fg: #18212b; --muted: #5a6672; --line: #d5dbe1; --accent: #0a6d8f;
  --tp: #0a6d8f; --tn: #a9b6c2; --fp: #d1495b; --fn: #e08e0b; --paid: #18212b;
  --font-ui: "IBM Plex Sans", "Segoe UI", system-ui, sans-serif; --font-data: "IBM Plex Mono", ui-monospace, Consolas, monospace; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg: #10151a; --panel: #182028; --fg: #e5eaef; --muted: #98a4b0; --line: #2a333d;
  --accent: #52b6dc; --tp: #52b6dc; --tn: #4a5663; --fp: #ff7a8a; --fn: #f5b041; --paid: #e5eaef; color-scheme: dark } }
:root[data-theme="dark"] { --bg: #10151a; --panel: #182028; --fg: #e5eaef; --muted: #98a4b0; --line: #2a333d;
  --accent: #52b6dc; --tp: #52b6dc; --tn: #4a5663; --fp: #ff7a8a; --fn: #f5b041; --paid: #e5eaef; color-scheme: dark }
body { background: var(--bg); color: var(--fg); font-family: var(--font-ui); line-height: 1.45; margin: 0;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 18px 28px; }
h1 { font-size: 1.25rem; margin: 0; font-weight: 600; text-wrap: balance; }
.sub { color: var(--muted); max-width: 78ch; margin: 4px 0 0; font-size: 0.92rem; }
.controls { display: flex; flex-wrap: wrap; gap: 12px 18px; align-items: end; margin: 14px 0 12px; }
.controls label { display: flex; flex-direction: column; gap: 4px; font-size: 0.72rem; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); }
select, input[type=range] { font: inherit; font-size: 0.9rem; color: var(--fg); background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 5px 8px; }
input[type=range] { padding: 0; min-width: 170px; accent-color: var(--accent); }
.val { font-family: var(--font-data); color: var(--fg); text-transform: none; letter-spacing: 0; font-size: 0.92rem; }
.main { display: grid; grid-template-columns: minmax(0, 1fr) 290px; gap: 16px; align-items: start; }
@media (max-width: 860px) { .main { grid-template-columns: minmax(0, 1fr); } }
.plot { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; min-width: 0; height: min(72vh, 640px); }
.side { display: flex; flex-direction: column; gap: 12px; min-width: 0; }
dl { display: grid; grid-template-columns: auto 1fr; gap: 4px 12px; margin: 0; font-size: 0.9rem; }
dt { color: var(--muted); } dd { margin: 0; text-align: right; font-family: var(--font-data); font-variant-numeric: tabular-nums; }
.legend { display: grid; gap: 6px; font-size: 0.85rem; color: var(--muted); }
.key { display: inline-block; width: 11px; height: 11px; border-radius: 50%; margin-right: 6px; vertical-align: -1px; }
.note { font-size: 0.8rem; color: var(--muted); max-width: 70ch; margin: 0; }
</style>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;600&display=swap">
<h1>Pooled boundary view</h1>
<p class="sub">One pooled pool of 541 SPH simulations, learned from scratch (__STAGE__ repeat __REPEAT__). Each dot is a run at its recorded held-out prediction after <span id="bnote">b</span> paid simulations (startup included). Colour = correct / wrong side; diamonds = runs paid by the chosen fold, in query order. The fourth input ST is filtered explicitly.</p>
<div class="controls">
  <label for="task">Task<select id="task"><option value="region">velocity-spike region</option><option value="label">Keyhole label</option></select></label>
  <label for="arm">Model / selector<select id="arm"></select></label>
  <label for="budget">Paid simulations <span class="val" id="bval"></span><input id="budget" type="range" min="0" max="10" step="1" value="0"></label>
  <label for="fold">Paid runs shown<select id="fold"><option value="0">none</option><option>1</option><option>2</option><option>3</option><option>4</option><option>5</option></select></label>
  <label for="st">ST band (K) <span class="val" id="stval"></span><select id="st"><option value="0">all</option><option value="1">300–350</option><option value="2">350–400</option><option value="3">400–450</option><option value="4">450–500</option></select></label>
</div>
<div class="main">
  <div class="plot" id="plot" aria-label="3D scatter of runs in log P, log VX and spot radius"></div>
  <div class="side">
    <dl id="stat"></dl>
    <div class="legend">
      <div><span class="key" style="background: var(--tp)"></span>inside, predicted inside</div>
      <div><span class="key" style="background: var(--tn)"></span>outside, predicted outside</div>
      <div><span class="key" style="background: var(--fp)"></span>outside, predicted inside (false alarm)</div>
      <div><span class="key" style="background: var(--fn)"></span>inside, predicted outside (miss)</div>
      <div><span class="key" style="border: 2px solid var(--paid); border-radius: 2px; transform: rotate(45deg)"></span>paid by the chosen fold</div>
    </div>
    <p class="note">"Inside" = spike log-ratio ≥ log 2 (region) or Keyhole (label). Numbers on this page are computed from the recorded predictions; they equal the evaluator's (checked when the page was built). Evidence label: DEV — all simulations were inspected before; a new split is not new physical data.</p>
  </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.27.0/plotly.min.js"></script>
<script>
const D = __DATA__;
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const R = D.runs, N = R.y.length, tau = D.tau;
const ts = document.getElementById("task"), as = document.getElementById("arm"), bs = document.getElementById("budget"), fs = document.getElementById("fold"), ss = document.getElementById("st");
const bands = [[0, 1e9], [300, 350], [350, 400], [400, 450], [450, 501]];
function arms() { return Object.keys(D.tasks[ts.value]).sort(); }
function fillArms() { const keep = as.value; as.innerHTML = ""; arms().forEach(a => as.add(new Option(a.replace("|", " · "), a))); if (arms().includes(keep)) as.value = keep;
  else { const pref = ts.value === "region" ? "SHQ|STRADDLE" : "E1_STRADDLE"; if (arms().includes(pref)) as.value = pref; } setBudgets(); }
let budgets = [];
function setBudgets() { const A = D.tasks[ts.value][as.value]; budgets = Object.keys(A.pred).map(Number).sort((a, b) => a - b); bs.max = budgets.length - 1; if (+bs.value > budgets.length - 1) bs.value = budgets.length - 1; }
function truthIn(i) { return ts.value === "region" ? (R.spike[i] === null ? null : R.spike[i] >= tau) : R.y[i] === 1; }
function predIn(v) { return v === null ? null : (ts.value === "region" ? v >= tau : v >= 0.5); }
let first = true;
function draw() {
  const A = D.tasks[ts.value][as.value], b = budgets[+bs.value], pred = A.pred[String(b)], band = bands[+ss.value];
  document.getElementById("bval").textContent = b; document.getElementById("bnote").textContent = b;
  document.getElementById("stval").textContent = +ss.value ? "" : "";
  const grp = { tp: [], tn: [], fp: [], fn: [] }; let tp = 0, p = 0, tn = 0, n = 0;
  for (let i = 0; i < N; i++) { const t = truthIn(i), q = predIn(pred[i]); if (t === null || q === null) continue;
    if (t) { p++; if (q) tp++; } else { n++; if (!q) tn++; }
    if (R.ST[i] < band[0] || R.ST[i] >= band[1]) continue;
    grp[t ? (q ? "tp" : "fn") : (q ? "fp" : "tn")].push(i); }
  const names = { tp: "inside, predicted inside", tn: "outside, predicted outside", fp: "false alarm", fn: "miss" }, cols = { tp: css("--tp"), tn: css("--tn"), fp: css("--fp"), fn: css("--fn") };
  const tr = Object.keys(grp).map(k => ({ type: "scatter3d", mode: "markers", name: names[k], x: grp[k].map(i => R.logP[i]), y: grp[k].map(i => R.logVX[i]), z: grp[k].map(i => R.LS_um[i]),
    text: grp[k].map(i => R.id[i] + "<br>ST " + R.ST[i] + " K · batch " + R.batch[i] + "<br>recorded prediction " + pred[i]), hoverinfo: "text",
    marker: { size: k === "fp" || k === "fn" ? 5 : 3.2, color: cols[k], opacity: k === "tn" ? 0.55 : 0.95 } }));
  const f = fs.value; if (f !== "0" && A.paid[f]) { const P = A.paid[f].slice(0, b).filter(i => R.ST[i] >= band[0] && R.ST[i] < band[1]);
    tr.push({ type: "scatter3d", mode: "markers", name: "paid (fold " + f + ")", x: P.map(i => R.logP[i]), y: P.map(i => R.logVX[i]), z: P.map(i => R.LS_um[i]),
      text: P.map(i => R.id[i]), hoverinfo: "text", marker: { size: 6, symbol: "diamond-open", color: css("--paid"), line: { width: 2, color: css("--paid") } } }); }
  const ax = t => ({ title: { text: t, font: { color: css("--muted"), size: 12 } }, color: css("--muted"), gridcolor: css("--line"), zerolinecolor: css("--line"), backgroundcolor: css("--panel") });
  const layout = { paper_bgcolor: css("--panel"), plot_bgcolor: css("--panel"), font: { family: css("--font-ui"), color: css("--fg") }, margin: { l: 0, r: 0, t: 0, b: 0 }, showlegend: false,
    scene: { xaxis: ax("log P (W)"), yaxis: ax("log VX (m/s)"), zaxis: ax("LS (µm)"), aspectmode: "cube" }, uirevision: "keep" };
  Plotly.react("plot", tr, layout, { displaylogo: false, responsive: true, modeBarButtonsToRemove: ["toImage"] });
  const ba = 0.5 * (tp / Math.max(1, p) + tn / Math.max(1, n));
  document.getElementById("stat").innerHTML = `<dt>balanced accuracy</dt><dd>${ba.toFixed(3)}</dd><dt>recall inside</dt><dd>${(tp / Math.max(1, p)).toFixed(3)}</dd>` +
    `<dt>recall outside</dt><dd>${(tn / Math.max(1, n)).toFixed(3)}</dd><dt>runs scored</dt><dd>${p + n}</dd><dt>shown (ST band)</dt><dd>${grp.tp.length + grp.tn.length + grp.fp.length + grp.fn.length}</dd>`;
}
ts.addEventListener("input", () => { fillArms(); draw(); }); as.addEventListener("input", () => { setBudgets(); draw(); });
[bs, fs, ss].forEach(el => el.addEventListener("input", draw));
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", draw);
fillArms(); bs.value = Math.min(budgets.length - 1, Math.round((budgets.length - 1) / 3)); fs.value = "1"; draw();
</script>
"""


def check_numbers(data, stage):
    """The page's balanced accuracy must equal the evaluator's for every arm and recorded budget (region and label)."""
    M = P.manifest(); r = data["repeat"]; worst = 0.0
    G = EV.region_curves(EV.load_units(P.OUT / stage / ("final-region" if stage == "final" else "dev-region")), M, data["tau"])
    for key, A in data["tasks"]["region"].items():
        m, a = key.split("|"); g = G[(G.model == m) & (G.acq == a) & (G.repeat == r)].set_index("budget").BA
        sp = np.asarray([np.nan if v is None else v for v in data["runs"]["spike"]], float)
        for b, pred in A["pred"].items():
            pv = np.asarray([np.nan if v is None else v for v in pred], float); ok = np.isfinite(sp) & np.isfinite(pv); t = sp[ok] >= data["tau"]; q = pv[ok] >= data["tau"]
            ba = 0.5 * (np.mean(q[t]) + np.mean(~q[~t])); worst = max(worst, abs(ba - g.loc[int(b)]))
    return worst


def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else "final"; repeat = int(sys.argv[2]) if len(sys.argv) > 2 else None
    data = build(stage, repeat); REP = P.OUT / "report"; REP.mkdir(parents=True, exist_ok=True)
    worst = check_numbers(data, stage); data["check_max_abs_diff_region_BA"] = worst
    tag = "" if stage == "final" else "_dev"
    (REP / f"pooled_boundary_view{tag}.json").write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    html = HTML.replace("__DATA__", json.dumps(data, separators=(",", ":"))).replace("__REPEAT__", str(data["repeat"])).replace("__STAGE__", stage)
    (REP / f"pooled_boundary_view{tag}.html").write_text(html, encoding="utf-8")
    print(REP / f"pooled_boundary_view{tag}.html", len(html) // 1024, "KB; max |page BA - evaluator BA| (region) =", worst)


if __name__ == "__main__":
    main()
