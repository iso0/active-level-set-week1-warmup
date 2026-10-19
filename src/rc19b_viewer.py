"""RC19B single-learner boundary view (replaces the RC19 mixed-fold reading; DEV evidence; presentation only).

One learner = (task, arm / probability construction, repeat, fold). At each shown budget b the learner is refitted on ITS OWN
first b paid runs (its recorded path) with the same code path as the trajectory (rc19b_keyhole.constructions with extra grid
rows; rc18_campaign.fit_model for the region model), and evaluated on
  (i)  a regular grid over log P x log VX at a chosen spot-radius slice LS, with the fourth input ST FIXED, and
  (ii) the same fold's held-out test runs.
The refitted test-run predictions are compared with the trajectory's recorded predictions (max |difference| is stored and shown).
Nothing on the page mixes fold learners. The point overlay shows only runs within +-LS_BAND_UM of the LS slice and +-ST_BAND_K of
the fixed ST (stated on the page); the side statistics use ALL held-out runs of that fold.
The single learner shown is pre-declared (first final repeat, first fold), not chosen by its result.
    python -m src.rc19b_viewer build      -> opus_rc19b/viewer/single_learner_view.html (+ .json)
    python -m src.rc19b_viewer relabel    -> opus_rc19b/viewer/pooled_boundary_view_RC19_relabelled.html
"""
from __future__ import annotations

import base64
import json
import sys
import warnings

import numpy as np
from scipy.special import ndtr

import src.rc18_campaign as C
import src.rc18_common as RC
import src.rc19_learn as LN
import src.rc19_pool as P
import src.rc19b_keyhole as K

OUT = RC.ROOT / "outputs" / "research_campaign_20261018" / "opus_rc19b"
VIEW = OUT / "viewer"
NG = 36
LS_SLICES_UM = (45.0, 55.0, 65.0, 75.0, 85.0)
ST_FIXED_K = (325.0, 400.0, 475.0)
LS_BAND_UM, ST_BAND_K = 5.0, 37.5
BUDGETS = (8, 12, 16, 20, 24, 32, 40, 48, 60)
LABEL_LEARNERS = (("E1S", "E1RAW"), ("E1S", "E1CAL"), ("ATSCF_MARGIN", "ATSCF"), ("DEPTHCF_MARGIN", "DEPTHCF"), ("G3_MARGIN", "G3"),
                  ("ATSAPPROX_MARGIN", "ATSAPPROX"))
LABEL_RF = (11, 1)                                  # first final repeat, first fold (pre-declared)
REGION_LEARNER = ("SHQ", "STRADDLE")
REGION_RF = (3, 1)                                  # RC19 final: first final repeat, first fold
DESC = {"E1RAW": "E1: GP on log depth + depth threshold from the paid (depth, label) pairs; p = Φ((μ − u)/σ). Path: E1 straddle.",
        "E1CAL": "E1 passed through the honest out-of-fold small-sample probability map (same path as E1RAW).",
        "ATSCF": "Logistic classifier on honestly cross-fitted predicted (log depth, T0 temperature, spike log-ratio). Path: its own margin.",
        "DEPTHCF": "Logistic classifier on honestly cross-fitted predicted log depth only. Path: its own margin.",
        "G3": "Week 18 direct GP classifier on the labels. Path: its own margin.",
        "ATSAPPROX": "RC19 PHYSCF_ATS (closed-form leave-one-out with full-fit hyperparameters: an approximation). Path: its own margin.",
        "SHQ": "Region: SHQ GP on the spike log-ratio (lengthscales shared by the 8 outputs + record quality); inside = mean ≥ log 2. Path: straddle."}


def grid(M):
    lp = np.linspace(np.log(M.P.min()), np.log(M.P.max()), NG); lv = np.linspace(np.log(M.VX.min()), np.log(M.VX.max()), NG)
    G = [(np.exp(a), np.exp(b), ls * 1e-6, st) for st in ST_FIXED_K for ls in LS_SLICES_UM for b in lv for a in lp]   # [st][ls][vx][p]
    return lp, lv, np.asarray(G, float)


def _ext_task(task, Xg):
    n = len(task["ids"]); t = dict(task); t["X"] = np.vstack([task["X"], Xg])
    return t, np.arange(n, n + len(Xg))


def _ext_rev(task, M, paid_rows, ng):
    """Reveal of the ORIGINAL task replayed on the paid prefix, padded with unknown rows for the grid (never candidates)."""
    rev = K._rev_with(task, M, paid_rows)
    rev._y = np.r_[rev._y, np.full(ng, -1, int)]; rev._A = np.r_[rev._A, np.full(ng, np.nan)]
    rev._Y = np.vstack([rev._Y, np.full((ng, rev._Y.shape[1]), np.nan)]); rev._short = np.r_[rev._short, np.zeros(ng, bool)]; rev.n += ng
    return rev


def _enc(p):
    q = np.where(np.isfinite(p), np.round(np.clip(p, 0, 1) * 250), 255).astype(np.uint8)
    return base64.b64encode(q.tobytes()).decode("ascii")


def label_learner(task, unit, M, arm, cons, Kf, Xg):
    te, gr = _ext_task(task, Xg); Ze = P.zstd(te); pos = {s: i for i, s in enumerate(task["ids"])}; paid = [pos[s] for s in unit["paid_ids"]]
    rec = {e["budget"]: e["p"][cons] for e in unit["evals"]}; out = {}
    rng = np.random.default_rng([P.SPLIT_SEED, 19, task["repeat"], task["fold"]])
    for b in BUDGETS:
        rev = _ext_rev(task, M, paid[:b], len(Xg))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            o, _, info, _ = K.constructions(te, rev, Ze, K.ADAPTIVE[arm], rng, K=Kf, extra=gr)
        pt = np.asarray(o[cons], float); pg = np.asarray(info["_extra"][cons], float); r = np.asarray([np.nan if v is None else v for v in rec[b]], float)
        out[str(b)] = {"grid": _enc(pg), "paid": [int(i) for i in paid[:b]], "test_p": [round(float(v), 5) for v in pt],
                       "check": float(np.nanmax(np.abs(pt - r))), "constant": bool(np.nanstd(pg) < 1e-9)}
    return out


def region_learner(task, unit, M, model, Xg):
    te, gr = _ext_task(task, Xg); Ze = LN.design_inputs(te, model); pos = {s: i for i, s in enumerate(task["ids"])}; paid = [pos[s] for s in unit["paid_ids"]]
    rec = {e["budget"]: e["mean"] for e in unit["evals"]}; out = {}; shared = LN.base(model).startswith("SH"); cols = list(P.TARGETS) if shared else [LN.RESP]
    for b in BUDGETS:
        rev = _ext_rev(task, M, paid[:b], len(Xg)); Yp = rev.paid_Y() if shared else rev.paid_Y()[:, [LN.TI[LN.RESP]]]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            f = C.fit_model(LN.base(model), Ze, Yp, rev.paid, cols, emu=None, short=rev.paid_short()).get(LN.RESP)
        if f is None:
            out[str(b)] = {"grid": _enc(np.full(len(gr), np.nan)), "paid": [int(i) for i in paid[:b]], "test_p": [None] * len(task["test"]), "check": np.nan, "constant": True}
            continue
        mt, lt, _ = f.predict(task["test"]); mg, lg, _ = f.predict(gr); r = np.asarray([np.nan if v is None else v for v in (rec[b] or [None] * len(mt))], float)
        pt = ndtr((mt - LN.TAU) / np.sqrt(np.maximum(lt, 1e-12))); pg = ndtr((mg - LN.TAU) / np.sqrt(np.maximum(lg, 1e-12)))
        out[str(b)] = {"grid": _enc(pg), "paid": [int(i) for i in paid[:b]], "test_p": [round(float(v), 5) for v in pt],
                       "check": float(np.nanmax(np.abs(mt - r))), "constant": False}
    return out


def build():
    import src.rc19b_final as F
    RC.limit_threads(1); M = P.manifest(); lp, lv, Xg = grid(M); ids = M.index.to_numpy(str)
    data = {"grid": {"logP": np.round(lp, 4).tolist(), "logVX": np.round(lv, 4).tolist(), "LS_um": list(LS_SLICES_UM), "ST_K": list(ST_FIXED_K), "NG": NG,
                     "ls_band": LS_BAND_UM, "st_band": ST_BAND_K},
            "runs": {"logP": np.round(np.log(M.P), 4).tolist(), "logVX": np.round(np.log(M.VX), 4).tolist(), "LS_um": np.round(M.LS * 1e6, 2).tolist(),
                     "ST": np.round(M.ST, 1).tolist(), "y": M.y.astype(int).tolist(), "id": ids.tolist(),
                     "inside": [None if not np.isfinite(v) else bool(v >= LN.TAU) for v in M.vmax_spike_logratio]},
            "budgets": list(BUDGETS), "tasks": {}}
    r, f = LABEL_RF; t = {(x["repeat"], x["fold"]): x for x in P.tasks([r])}[(r, f)]; L = {}
    for arm, cons in LABEL_LEARNERS:
        u = RC.read_json_gz(OUT / "b-final-label" / "units" / f"r{r}_f{f}__{arm}.json.gz")
        L[f"{arm} · {cons}"] = {"cons": cons, "desc": DESC[cons], "budgets": label_learner(t, u, M, arm, cons, F.CF_K, Xg)}
        print(arm, cons, "max check", max(v["check"] for v in L[f"{arm} · {cons}"]["budgets"].values()), flush=True)
    data["tasks"]["label"] = {"name": "Keyhole label", "stage": f"RC19B final (fresh DEV repeat {r}), fold {f}", "repeat": r, "fold": f, "cut_name": "P(Keyhole)",
                              "test": [int(i) for i in t["test"]], "learners": L}
    r, f = REGION_RF; t = {(x["repeat"], x["fold"]): x for x in P.tasks([r])}[(r, f)]; m, a = REGION_LEARNER
    u = RC.read_json_gz(P.OUT / "final" / "final-region" / "units" / f"r{r}_f{f}__region__{m}__{a}.json.gz")
    data["tasks"]["region"] = {"name": "Velocity-spike region", "stage": f"RC19 final repeat {r}, fold {f}", "repeat": r, "fold": f, "cut_name": "P(spike ratio ≥ 2)",
                               "test": [int(i) for i in t["test"]], "learners": {f"{m} · {a}": {"cons": m, "desc": DESC[m], "budgets": region_learner(t, u, M, m, Xg)}}}
    VIEW.mkdir(parents=True, exist_ok=True); js = json.dumps(data, separators=(",", ":"))
    (VIEW / "single_learner_view.json").write_text(js, encoding="utf-8")
    (VIEW / "single_learner_view.html").write_text(HTML.replace("__DATA__", js), encoding="utf-8")
    print(VIEW / "single_learner_view.html", len(js) // 1024, "KB")


def relabel():
    """Corrected labelling of the RC19 pooled view (numbers unchanged): each dot's prediction comes from the learner of the fold
    in which that run was held out (5 learners per repeat); the diamonds are the paid runs of ONE of those learners."""
    src = (P.OUT / "report" / "pooled_boundary_view.html").read_text(encoding="utf-8")
    old = src[src.index('<p class="sub">'):src.index("</p>", src.index('<p class="sub">')) + 4]
    new = ('<p class="sub"><strong>Relabelled 2026-10-19 (RC19B erratum F; numbers unchanged).</strong> One pool of 541 SPH simulations, learned from scratch '
           '(__STAGE__ repeat __REPEAT__). Each dot is a run at its recorded held-out prediction after <span id="bnote">b</span> paid simulations. '
           '<strong>These colours come from five different learners</strong>: every run is coloured by the learner of the fold in which it was held out. '
           'The diamonds are the paid runs of <strong>one</strong> of those five learners only, so they are not the training data of most dots. '
           'For a single learner with its own grid predictions, use the single-learner view. The fourth input ST is filtered explicitly.</p>')
    out = src.replace(old, new.replace("__STAGE__", "final").replace("__REPEAT__", str(json.loads(
        (P.OUT / "report" / "pooled_boundary_view.json").read_text(encoding="utf-8"))["repeat"]))).replace(
        "paid by the chosen fold</div>", "paid by the chosen fold's learner (training runs of that one learner only)</div>").replace(
        "<title>Pooled Boundary View</title>", "<title>Pooled Boundary View (relabelled)</title>")
    VIEW.mkdir(parents=True, exist_ok=True); (VIEW / "pooled_boundary_view_RC19_relabelled.html").write_text(out, encoding="utf-8")
    print(VIEW / "pooled_boundary_view_RC19_relabelled.html", "changed:", out != src)


HTML = r"""<title>Single-Learner Boundary View</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
:root { --bg: #f3f5f6; --panel: #ffffff; --fg: #17212a; --muted: #586571; --line: #d3dade; --accent: #1d6f8a;
  --lo: #2f6f9f; --mid: #eef0f1; --hi: #c4572f; --k-pt: #7a2410; --c-pt: #10395c; --wrong: #e0a400; --paid: #17212a; --old: #7b8792;
  --font-ui: "IBM Plex Sans", "Segoe UI", system-ui, sans-serif; --font-data: "IBM Plex Mono", ui-monospace, Consolas, monospace; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg: #0f1418; --panel: #172027; --fg: #e3e8ec; --muted: #9aa6b1; --line: #2a343c;
  --accent: #5bb8d6; --lo: #4f95c8; --mid: #2a3238; --hi: #e07a4f; --k-pt: #ffc2a8; --c-pt: #b9dcff; --wrong: #ffd04d; --paid: #e3e8ec; --old: #8d99a4; color-scheme: dark } }
:root[data-theme="dark"] { --bg: #0f1418; --panel: #172027; --fg: #e3e8ec; --muted: #9aa6b1; --line: #2a343c;
  --accent: #5bb8d6; --lo: #4f95c8; --mid: #2a3238; --hi: #e07a4f; --k-pt: #ffc2a8; --c-pt: #b9dcff; --wrong: #ffd04d; --paid: #e3e8ec; --old: #8d99a4; color-scheme: dark }
body { background: var(--bg); color: var(--fg); font-family: var(--font-ui); line-height: 1.45; margin: 0;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 18px 28px; }
h1 { font-size: 1.25rem; margin: 0; font-weight: 600; text-wrap: balance; }
.sub { color: var(--muted); max-width: 80ch; margin: 4px 0 0; font-size: 0.92rem; }
.controls { display: flex; flex-wrap: wrap; gap: 12px 18px; align-items: end; margin: 14px 0 12px; }
.controls label { display: flex; flex-direction: column; gap: 4px; font-size: 0.72rem; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); }
.controls .chk { flex-direction: row; align-items: center; gap: 6px; text-transform: none; letter-spacing: 0; font-size: 0.88rem; color: var(--fg); }
select, input[type=range] { font: inherit; font-size: 0.9rem; color: var(--fg); background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 5px 8px; max-width: 100%; }
input[type=range] { padding: 0; min-width: 170px; accent-color: var(--accent); }
.val { font-family: var(--font-data); color: var(--fg); text-transform: none; letter-spacing: 0; font-size: 0.92rem; }
.main { display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: 16px; align-items: start; }
@media (max-width: 880px) { .main { grid-template-columns: minmax(0, 1fr); } }
.plot { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; min-width: 0; height: min(70vh, 620px); }
.side { display: flex; flex-direction: column; gap: 12px; min-width: 0; }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 12px 14px; display: flex; flex-direction: column; gap: 8px; }
.card h2 { font-size: 0.72rem; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); margin: 0; font-weight: 600; }
dl { display: grid; grid-template-columns: auto 1fr; gap: 4px 12px; margin: 0; font-size: 0.9rem; }
dt { color: var(--muted); } dd { margin: 0; text-align: right; font-family: var(--font-data); font-variant-numeric: tabular-nums; }
.legend { display: grid; gap: 6px; font-size: 0.85rem; color: var(--muted); }
.key { display: inline-block; width: 11px; height: 11px; border-radius: 50%; margin-right: 6px; vertical-align: -1px; }
.ramp { height: 10px; border-radius: 3px; background: linear-gradient(90deg, var(--lo), var(--mid), var(--hi)); }
.ramp-l { display: flex; justify-content: space-between; font-size: 0.75rem; color: var(--muted); font-family: var(--font-data); }
.note { font-size: 0.8rem; color: var(--muted); max-width: 72ch; margin: 0; }
.desc { font-size: 0.86rem; margin: 0; }
</style>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;600&display=swap">
<h1>Single-learner boundary view</h1>
<p class="sub">One learner at a time: one model, one repeat, one fold. The coloured field is <em>that learner's</em> prediction on a regular grid of
log P × log VX, at one spot-radius slice and with the fourth input ST held fixed. The learner was refitted on its own first <span id="bnote">b</span> paid
simulations (startup included). Diamonds = its paid runs (in query order). Circles = the same fold's held-out runs. Only runs near the LS slice and ST value are drawn.</p>
<div class="controls">
  <label for="task">Task<select id="task"><option value="label">Keyhole label</option><option value="region">velocity-spike region</option></select></label>
  <label for="lrn">Learner<select id="lrn"></select></label>
  <label for="budget">Paid simulations <span class="val" id="bval"></span><input id="budget" type="range" min="0" max="8" step="1" value="2"></label>
  <label for="ls">LS slice (µm)<select id="ls"></select></label>
  <label for="st">ST fixed (K)<select id="st"></select></label>
  <label class="chk"><input type="checkbox" id="showpaid" checked>paid runs</label>
  <label class="chk"><input type="checkbox" id="showtest" checked>held-out runs</label>
  <label class="chk"><input type="checkbox" id="trail">earlier boundaries</label>
</div>
<div class="main">
  <div class="plot" id="plot" aria-label="Prediction field of one learner over log P and log VX with paid and held-out runs"></div>
  <div class="side">
    <div class="card"><h2 id="lname">Learner</h2><p class="desc" id="ldesc"></p></div>
    <div class="card"><h2>This fold's held-out runs (all, not only the drawn band)</h2><dl id="stat"></dl></div>
    <div class="card"><h2>Key</h2>
      <div class="ramp"></div><div class="ramp-l"><span>0</span><span id="cutname">0.5 = boundary</span><span>1</span></div>
      <div class="legend">
        <div><span class="key" style="background: var(--k-pt)"></span>run is Keyhole / inside (truth)</div>
        <div><span class="key" style="background: var(--c-pt)"></span>run is conduction / outside (truth)</div>
        <div><span class="key" style="background: transparent; border: 2.5px solid var(--wrong)"></span>held-out run on the wrong side</div>
        <div><span class="key" style="background: transparent; border: 2px solid var(--paid); border-radius: 2px; transform: rotate(45deg)"></span>paid run of this learner</div>
        <div><span class="key" style="background: transparent; border-top: 2px dashed var(--old); border-radius: 0; height: 0; width: 14px"></span>earlier boundaries (lighter = earlier)</div>
      </div></div>
    <p class="note" id="note"></p>
  </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.27.0/plotly.min.js"></script>
<script>
const D = __DATA__;
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const G = D.grid, R = D.runs, NG = G.NG, BUD = D.budgets;
const ts = document.getElementById("task"), ls = document.getElementById("lrn"), bs = document.getElementById("budget"), lsl = document.getElementById("ls"), sts = document.getElementById("st");
const sp = document.getElementById("showpaid"), st_ = document.getElementById("showtest"), tr_ = document.getElementById("trail");
G.LS_um.forEach((v, i) => lsl.add(new Option(v.toFixed(0), i))); G.ST_K.forEach((v, i) => sts.add(new Option(v.toFixed(0), i))); lsl.value = 2; sts.value = 1;
bs.max = BUD.length - 1;
const cache = {};
function decode(s) { if (cache[s]) return cache[s]; const b = atob(s), a = new Uint8Array(b.length); for (let i = 0; i < b.length; i++) a[i] = b.charCodeAt(i); cache[s] = a; return a; }
function slice(arr, si, li) { const off = (si * G.LS_um.length + li) * NG * NG, z = [];
  for (let r = 0; r < NG; r++) { const row = []; for (let c = 0; c < NG; c++) { const q = arr[off + r * NG + c]; row.push(q === 255 ? null : q / 250); } z.push(row); } return z; }
function fillL() { const T = D.tasks[ts.value], keep = ls.value; ls.innerHTML = ""; Object.keys(T.learners).forEach(k => ls.add(new Option(k, k)));
  if (T.learners[keep]) ls.value = keep; }
function truth(i) { return ts.value === "label" ? R.y[i] === 1 : R.inside[i]; }
function fmt(v, d = 3) { return v === null || !isFinite(v) ? "–" : v.toFixed(d); }
function draw() {
  const T = D.tasks[ts.value], Lr = T.learners[ls.value], bi = +bs.value, b = BUD[bi], E = Lr.budgets[String(b)];
  const si = +sts.value, li = +lsl.value, LS0 = G.LS_um[li], ST0 = G.ST_K[si];
  document.getElementById("bval").textContent = b; document.getElementById("bnote").textContent = b;
  document.getElementById("lname").textContent = ls.value + " — " + T.stage; document.getElementById("ldesc").textContent = Lr.desc;
  const lo = css("--lo"), mid = css("--mid"), hi = css("--hi");
  const z = slice(decode(E.grid), si, li);
  const traces = [{ type: "heatmap", x: G.logP, y: G.logVX, z: z, zmin: 0, zmax: 1, colorscale: [[0, lo], [0.5, mid], [1, hi]], showscale: false, hoverongaps: false,
    hovertemplate: "log P %{x:.2f} · log VX %{y:.2f}<br>" + T.cut_name + " %{z:.2f}<extra></extra>" }];
  if (!E.constant) traces.push({ type: "contour", x: G.logP, y: G.logVX, z: z, contours: { start: 0.5, end: 0.5, size: 1, coloring: "none" }, line: { color: css("--fg"), width: 2.4 },
    showscale: false, hoverinfo: "skip" });
  if (tr_.checked) { const prev = BUD.slice(0, bi); prev.forEach((bb, k) => { const Eb = Lr.budgets[String(bb)]; if (Eb.constant) return;
    traces.push({ type: "contour", x: G.logP, y: G.logVX, z: slice(decode(Eb.grid), si, li), contours: { start: 0.5, end: 0.5, size: 1, coloring: "none" },
      line: { color: css("--old"), width: 1.2, dash: "dash" }, opacity: 0.25 + 0.6 * (k + 1) / Math.max(1, prev.length), showscale: false, hoverinfo: "skip" }); }); }
  const inBand = i => Math.abs(R.LS_um[i] - LS0) <= G.ls_band && Math.abs(R.ST[i] - ST0) <= G.st_band;
  let shownT = 0, shownP = 0;
  if (st_.checked) { const idx = [], wrong = []; T.test.forEach((i, k) => { const t = truth(i), p = E.test_p[k]; if (t === null || p === null || !inBand(i)) return; idx.push([i, k]); });
    shownT = idx.length;
    traces.push({ type: "scatter", mode: "markers", x: idx.map(a => R.logP[a[0]]), y: idx.map(a => R.logVX[a[0]]),
      text: idx.map(a => R.id[a[0]] + "<br>LS " + R.LS_um[a[0]] + " µm · ST " + R.ST[a[0]] + " K<br>held-out prediction " + fmt(E.test_p[a[1]])), hoverinfo: "text",
      marker: { size: idx.map(a => ((E.test_p[a[1]] >= 0.5) !== truth(a[0])) ? 11 : 7), color: idx.map(a => truth(a[0]) ? css("--k-pt") : css("--c-pt")),
        line: { width: idx.map(a => ((E.test_p[a[1]] >= 0.5) !== truth(a[0])) ? 3 : 0.6), color: idx.map(a => ((E.test_p[a[1]] >= 0.5) !== truth(a[0])) ? css("--wrong") : css("--panel")) } } }); }
  if (sp.checked) { const q = E.paid.map((i, k) => [i, k + 1]).filter(a => inBand(a[0])); shownP = q.length;
    traces.push({ type: "scatter", mode: "markers", x: q.map(a => R.logP[a[0]]), y: q.map(a => R.logVX[a[0]]),
      text: q.map(a => "paid #" + a[1] + ": " + R.id[a[0]] + "<br>LS " + R.LS_um[a[0]] + " µm · ST " + R.ST[a[0]] + " K"), hoverinfo: "text",
      marker: { symbol: "diamond", size: 10, color: q.map(a => truth(a[0]) === null ? css("--old") : (truth(a[0]) ? css("--k-pt") : css("--c-pt"))), line: { width: 2, color: css("--paid") } } }); }
  const ax = t => ({ title: { text: t, font: { color: css("--muted"), size: 12 } }, color: css("--muted"), gridcolor: css("--line"), zeroline: false });
  Plotly.react("plot", traces, { paper_bgcolor: css("--panel"), plot_bgcolor: css("--panel"), font: { family: css("--font-ui"), color: css("--fg") },
    margin: { l: 56, r: 12, t: 12, b: 48 }, showlegend: false, xaxis: ax("log P (P in W)"), yaxis: ax("log VX (VX in m/s)"), uirevision: "keep" },
    { displaylogo: false, responsive: true, modeBarButtonsToRemove: ["toImage", "lasso2d", "select2d"] });
  let tp = 0, p = 0, tn = 0, n = 0, ll = 0, m = 0;
  T.test.forEach((i, k) => { const t = truth(i), q = E.test_p[k]; if (t === null || q === null) return; const h = q >= 0.5; if (t) { p++; if (h) tp++; } else { n++; if (!h) tn++; }
    const c = Math.min(1 - 1e-6, Math.max(1e-6, q)); ll += -(t ? Math.log(c) : Math.log(1 - c)); m++; });
  const rk = tp / Math.max(1, p), rc = tn / Math.max(1, n);
  document.getElementById("stat").innerHTML = `<dt>balanced accuracy</dt><dd>${fmt(0.5 * (rk + rc))}</dd><dt>recall inside / Keyhole</dt><dd>${fmt(rk)}</dd>` +
    `<dt>recall outside / conduction</dt><dd>${fmt(rc)}</dd>` + (ts.value === "label" ? `<dt>log loss</dt><dd>${fmt(ll / Math.max(1, m))}</dd>` : "") +
    `<dt>held-out runs scored</dt><dd>${m}</dd><dt>drawn in this band</dt><dd>${shownT} held-out · ${shownP} paid</dd>` +
    `<dt>refit vs recorded</dt><dd>${E.check === null || !isFinite(E.check) ? "–" : E.check.toExponential(1)}</dd>`;
  document.getElementById("note").innerHTML = `Band drawn: LS within ±${G.ls_band} µm of ${LS0.toFixed(0)} µm and ST within ±${G.st_band} K of ${ST0.toFixed(0)} K. ` +
    `"Refit vs recorded" = largest difference between this page's refit held-out predictions and the trajectory's recorded ones${ts.value === "region" ? " (spike log-ratio mean)" : ""}. ` +
    (E.constant ? "<strong>Only one class revealed so far: the learner predicts the paid class rate everywhere.</strong> " : "") +
    `The grid outside the runs' input region is extrapolation. Evidence label: DEV — every simulation was inspected before; a new split is not new physical data.`;
}
ts.addEventListener("input", () => { fillL(); draw(); }); [ls, bs, lsl, sts, sp, st_, tr_].forEach(el => el.addEventListener("input", draw));
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", draw);
fillL(); if (D.tasks.label.learners["ATSCF_MARGIN · ATSCF"]) ls.value = "ATSCF_MARGIN · ATSCF"; draw();
</script>
"""


if __name__ == "__main__":
    {"build": build, "relabel": relabel}[sys.argv[1]]()
