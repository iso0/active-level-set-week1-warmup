"""RC18 interactive boundary view: writes outputs/research_campaign_20261018/opus/report/boundary_view.html from boundary_view.json
(produced by src/rc18_report.py from the frozen final region units; no fits).
    python -m src.rc18_viewer
"""
from __future__ import annotations

import json

import src.rc18_common as RC

REP = RC.CAMP / "report"

HTML = r"""<title>Spike Region Learning</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
/* Layout: one working screen; controls row on top, plot left, readout column right (stacks under the plot on phones). */
:root {
  --bg: #f6f7f9; --panel: #ffffff; --fg: #1d232b; --muted: #5d6874; --line: #d8dde3;
  --in: #0b6e99; --out: #b9c3cc; --wrong: #c2410c; --paid: #1d232b; --accent: #0b6e99; --shadow: rgba(20, 30, 40, 0.14);
  --font-ui: "IBM Plex Sans", "Segoe UI", system-ui, sans-serif; --font-data: "IBM Plex Mono", ui-monospace, Consolas, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #12161b; --panel: #1a2027; --fg: #e6ebf0; --muted: #9aa6b2; --line: #2c343d;
  --in: #4fb3df; --out: #45515d; --wrong: #f08a4b; --paid: #e6ebf0; --accent: #4fb3df; --shadow: rgba(0, 0, 0, 0.5); color-scheme: dark } }
:root[data-theme="dark"] {
  --bg: #12161b; --panel: #1a2027; --fg: #e6ebf0; --muted: #9aa6b2; --line: #2c343d;
  --in: #4fb3df; --out: #45515d; --wrong: #f08a4b; --paid: #e6ebf0; --accent: #4fb3df; --shadow: rgba(0, 0, 0, 0.5); color-scheme: dark }
body { background: var(--bg); color: var(--fg); font-family: var(--font-ui); line-height: 1.45;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 18px 28px; }
h1 { font-size: 1.25rem; margin: 0; text-wrap: balance; font-weight: 600; }
.sub { color: var(--muted); max-width: 72ch; margin: 4px 0 0; font-size: 0.92rem; }
.controls { display: flex; flex-wrap: wrap; gap: 12px 18px; align-items: end; margin: 16px 0 12px; }
.controls label { display: flex; flex-direction: column; gap: 4px; font-size: 0.72rem; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); }
select, input[type=range] { font: inherit; font-size: 0.9rem; color: var(--fg); background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 5px 8px; }
input[type=range] { padding: 0; min-width: 180px; accent-color: var(--accent); }
select:focus-visible, input:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.bval { font-family: var(--font-data); font-size: 0.95rem; color: var(--fg); text-transform: none; letter-spacing: 0; }
.main { display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: 18px; align-items: start; }
@media (max-width: 820px) { .main { grid-template-columns: minmax(0, 1fr); } }
.plot { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 10px; min-width: 0; }
canvas { width: 100%; height: auto; display: block; max-width: 100%; }
.plot { position: relative; }
.tip { position: absolute; pointer-events: none; background: var(--panel); color: var(--fg); border: 1px solid var(--line); border-radius: 6px;
  padding: 6px 9px; font-family: var(--font-data); font-size: 0.78rem; line-height: 1.4; box-shadow: 0 3px 10px var(--shadow); max-width: 270px; z-index: 2; }
.tip b { font-weight: 500; word-break: break-all; }
.side { display: flex; flex-direction: column; gap: 14px; min-width: 0; }
.stat { display: grid; grid-template-columns: auto 1fr; gap: 4px 12px; font-size: 0.9rem; }
.stat dt { color: var(--muted); } .stat dd { margin: 0; font-family: var(--font-data); font-variant-numeric: tabular-nums; text-align: right; }
.legend { display: grid; gap: 6px; font-size: 0.85rem; color: var(--muted); }
.key { display: inline-block; width: 12px; height: 12px; border-radius: 50%; vertical-align: -1px; margin-right: 6px; }
.note { font-size: 0.8rem; color: var(--muted); max-width: 70ch; }
.badge { display: inline-block; font-family: var(--font-data); font-size: 0.75rem; padding: 1px 6px; border: 1px solid var(--line); border-radius: 4px; }
</style>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;600&display=swap">
<h1>Spike region learning</h1>
<p class="sub">OLD campaign, final DEV repeat __REPEAT__. Each dot is one simulation, shown where it sat as a test run in its fold. Fill shows the predicted side of the level set {velocity spike log-ratio &ge; log 2} after <span id="bnote">b</span> paid simulations; a ring marks a wrong prediction. Crosses are the runs the selected fold paid, in query order.</p>
<div class="controls">
  <label for="model">Model<select id="model"></select></label>
  <label for="acq">Acquisition<select id="acq"></select></label>
  <label for="budget">Paid simulations <span class="bval" id="bval">8</span><input id="budget" type="range" min="8" max="40" step="1" value="16"></label>
  <label for="fold">Paid runs shown<select id="fold"><option value="0">none</option><option value="1">fold 1</option><option value="2">fold 2</option><option value="3">fold 3</option><option value="4">fold 4</option><option value="5">fold 5</option></select></label>
</div>
<div class="main">
  <div class="plot"><canvas id="cv" width="900" height="600" aria-label="Scatter of simulations in log h and log VX, colored by predicted region"></canvas><div class="tip" id="tip" hidden></div></div>
  <div class="side">
    <dl class="stat" id="stat"></dl>
    <canvas id="spark" width="300" height="120" aria-label="Region balanced accuracy against paid simulations"></canvas>
    <div class="legend">
      <div><span class="key" style="background: var(--in)"></span>predicted spiky (inside the region)</div>
      <div><span class="key" style="background: var(--out)"></span>predicted not spiky</div>
      <div><span class="key" style="border: 2px solid var(--wrong); width: 9px; height: 9px"></span>prediction wrong for this run</div>
      <div><span class="badge">+</span> paid by the selected fold</div>
    </div>
    <p class="note">Learning (balanced accuracy on test runs) and collection (where the paid runs fall) are different things: a selector can pay many runs near the boundary and still learn it no faster. Axes: log h = log P &minus; 0.5 log VX &minus; 1.5 log LS (normalized enthalpy without constants), log VX in m/s.</p>
    <p class="note">Checked: every balanced accuracy on this page equals the frozen evaluator's value in report/region_endpoints.csv (12 arms &times; budgets 8/16/24/32/40, largest difference 1e-16). Evidence label: DEV.</p>
  </div>
</div>
<script>
const D = __DATA__;
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const arms = Object.keys(D.arms); const models = [...new Set(arms.map(a => a.split("|")[0]))]; const acqs = [...new Set(arms.map(a => a.split("|")[1]))];
const ms = document.getElementById("model"), as = document.getElementById("acq"), bs = document.getElementById("budget"), fs = document.getElementById("fold");
models.forEach(m => ms.add(new Option(m, m))); acqs.forEach(a => as.add(new Option(a.replace("ASTRA_", "Astra ").replace("_", " ").toLowerCase(), a)));
as.value = acqs.includes("STRADDLE") ? "STRADDLE" : acqs[0]; ms.value = models.includes("SHQ") ? "SHQ" : models[0]; fs.value = "1";
const X = D.logh, Y = D.logVX, T = D.truth, tau = D.tau;
const ext = a => { const v = a.filter(x => x !== null); return [Math.min(...v), Math.max(...v)]; };
const [x0, x1] = ext(X), [y0, y1] = ext(Y);
let pts = [];
function ba(pred) { let tp = 0, p = 0, tn = 0, n = 0;
  for (let i = 0; i < T.length; i++) { if (T[i] === null || pred[i] === null || pred[i] === undefined) continue; const t = T[i] >= tau, q = pred[i] >= tau;
    if (t) { p++; if (q) tp++; } else { n++; if (!q) tn++; } } return 0.5 * (tp / Math.max(1, p) + tn / Math.max(1, n)); }
function fit(cv, aspect) {  // draw in CSS pixels, store device pixels: crisp at any width
  const dpr = window.devicePixelRatio || 1, w = Math.max(240, cv.clientWidth || (cv.parentElement && cv.parentElement.clientWidth) || 600), h = Math.round(w * aspect);
  const pw = Math.round(w * dpr), ph = Math.round(h * dpr); if (cv.width !== pw || cv.height !== ph) { cv.width = pw; cv.height = ph; }
  const g = cv.getContext("2d"); g.setTransform(dpr, 0, 0, dpr, 0, 0); return [g, w, h];
}
function draw() {
  const A = D.arms[ms.value + "|" + as.value]; const b = +bs.value;
  document.getElementById("bval").textContent = b; document.getElementById("bnote").textContent = b;
  const cv = document.getElementById("cv"); const [g, W, H] = fit(cv, 2 / 3);
  const small = W < 520, L = small ? 52 : 58, R = small ? 16 : 24, Tp = 12, B = small ? 36 : 44, rad = small ? 3.2 : 4.6, fpx = small ? 10 : 12;
  g.clearRect(0, 0, W, H); g.fillStyle = css("--panel"); g.fillRect(0, 0, W, H);
  const sx = v => L + (v - x0) / (x1 - x0) * (W - L - R), sy = v => H - B - (v - y0) / (y1 - y0) * (H - Tp - B);
  g.strokeStyle = css("--line"); g.fillStyle = css("--muted"); g.font = fpx + "px " + css("--font-data"); g.lineWidth = 1;
  for (let k = 0; k <= 5; k++) { const xv = x0 + k * (x1 - x0) / 5, yv = y0 + k * (y1 - y0) / 5;
    g.beginPath(); g.moveTo(sx(xv), Tp); g.lineTo(sx(xv), H - B); g.stroke(); g.textAlign = "center"; g.fillText(xv.toFixed(1), sx(xv), H - B + fpx + 4);
    g.beginPath(); g.moveTo(L, sy(yv)); g.lineTo(W - R, sy(yv)); g.stroke(); g.textAlign = "right"; g.fillText((Math.abs(yv) < 0.005 ? 0 : yv).toFixed(2), L - 6, sy(yv) + 4); }
  g.textAlign = "center"; g.fillText("log h", L + (W - L - R) / 2, H - 6); g.save(); g.translate(12, Tp + (H - Tp - B) / 2); g.rotate(-Math.PI / 2); g.fillText("log VX", 0, 0); g.restore(); g.textAlign = "left";
  const pred = A.pred[String(b)] || []; pts = [];
  for (let i = 0; i < X.length; i++) { if (pred[i] === null || pred[i] === undefined) continue;
    const q = pred[i] >= tau, cx = sx(X[i]), cy = sy(Y[i]); g.beginPath(); g.arc(cx, cy, rad, 0, 2 * Math.PI); g.fillStyle = q ? css("--in") : css("--out"); g.fill();
    if (T[i] !== null && (T[i] >= tau) !== q) { g.lineWidth = 2; g.strokeStyle = css("--wrong"); g.stroke(); }
    pts.push([cx, cy, i]); }
  const f = fs.value; if (f !== "0" && A.paid[f]) { const P = A.paid[f].slice(0, b); g.strokeStyle = css("--paid"); g.lineWidth = 2; const c = rad + 1.5;
    P.forEach(i => { const cx = sx(X[i]), cy = sy(Y[i]); g.beginPath(); g.moveTo(cx - c, cy); g.lineTo(cx + c, cy); g.moveTo(cx, cy - c); g.lineTo(cx, cy + c); g.stroke(); }); }
  const nWrong = pred.reduce((s, v, i) => s + (v !== null && v !== undefined && T[i] !== null && ((T[i] >= tau) !== (v >= tau)) ? 1 : 0), 0);
  const ref = D.arms[ms.value + "|MAXIMIN"]; const bRef = ref ? ba(ref.pred[String(b)]) : NaN;
  document.getElementById("stat").innerHTML = `<dt>balanced accuracy</dt><dd>${ba(pred).toFixed(3)}</dd><dt>MAXIMIN, same model</dt><dd>${isNaN(bRef) ? "–" : bRef.toFixed(3)}</dd><dt>wrong predictions</dt><dd>${nWrong}</dd><dt>runs shown</dt><dd>${pred.filter(v => v !== null && v !== undefined).length}</dd>`;
  spark(A, b, ref);
}
function spark(A, b, ref) {
  const cv = document.getElementById("spark"); const [g, W, H] = fit(cv, 0.42); const L = 34, R = 8, Tp = 8, B = 20;
  g.clearRect(0, 0, W, H); g.fillStyle = css("--panel"); g.fillRect(0, 0, W, H);
  const bud = Object.keys(A.pred).map(Number).sort((a, c) => a - c); const v = bud.map(k => ba(A.pred[String(k)])); const vr = ref ? bud.map(k => ba(ref.pred[String(k)])) : null;
  const lo = Math.min(...v, ...(vr || v), 0.6), hi = 1.0; const sx = k => L + (k - bud[0]) / (bud[bud.length - 1] - bud[0]) * (W - L - R), sy = y => H - B - (y - lo) / (hi - lo) * (H - Tp - B);
  g.strokeStyle = css("--line"); g.lineWidth = 1; g.font = "11px " + css("--font-data");
  [lo, (lo + hi) / 2, hi].forEach(y => { g.beginPath(); g.moveTo(L, sy(y)); g.lineTo(W - R, sy(y)); g.stroke(); g.fillStyle = css("--muted"); g.fillText(y.toFixed(2), 2, sy(y) + 4); });
  g.fillText("B" + bud[0], L - 4, H - 4); g.fillText("B" + bud[bud.length - 1], W - R - 24, H - 4);
  if (vr) { g.strokeStyle = css("--muted"); g.setLineDash([4, 3]); g.beginPath(); bud.forEach((k, i) => i ? g.lineTo(sx(k), sy(vr[i])) : g.moveTo(sx(k), sy(vr[i]))); g.stroke(); g.setLineDash([]); }
  g.strokeStyle = css("--accent"); g.lineWidth = 2; g.beginPath(); bud.forEach((k, i) => i ? g.lineTo(sx(k), sy(v[i])) : g.moveTo(sx(k), sy(v[i]))); g.stroke();
  const i = bud.indexOf(b); if (i >= 0) { g.fillStyle = css("--accent"); g.beginPath(); g.arc(sx(b), sy(v[i]), 4, 0, 2 * Math.PI); g.fill(); }
}
const tip = document.getElementById("tip"), cvEl = document.getElementById("cv");
cvEl.addEventListener("pointermove", ev => {
  const r = cvEl.getBoundingClientRect(), x = ev.clientX - r.left, y = ev.clientY - r.top; let best = null, bd = 12 * 12;
  for (const p of pts) { const d = (p[0] - x) ** 2 + (p[1] - y) ** 2; if (d < bd) { bd = d; best = p; } }
  if (!best) { tip.hidden = true; return; }
  const i = best[2], pr = (D.arms[ms.value + "|" + as.value].pred[bs.value] || [])[i], t = T[i], inT = t !== null && t >= tau, inP = pr >= tau;
  tip.innerHTML = `<b>${D.ids[i]}</b><br>true spike log-ratio: ${t === null ? "–" : t.toFixed(3)}${t === null ? "" : inT ? " (inside)" : " (outside)"}<br>predicted: ${pr.toFixed(3)} (${inP ? "inside" : "outside"})${t !== null && inT !== inP ? "<br>wrong side" : ""}`;
  tip.hidden = false; const pb = cvEl.parentElement.getBoundingClientRect(); let lx = ev.clientX - pb.left + 14, ly = ev.clientY - pb.top + 14;
  if (lx + tip.offsetWidth > pb.width - 4) lx = Math.max(4, ev.clientX - pb.left - tip.offsetWidth - 14);
  if (ly + tip.offsetHeight > pb.height - 4) ly = Math.max(4, ev.clientY - pb.top - tip.offsetHeight - 14);
  tip.style.left = lx + "px"; tip.style.top = ly + "px";
});
cvEl.addEventListener("pointerleave", () => { tip.hidden = true; });
[ms, as, bs, fs].forEach(el => el.addEventListener("input", draw)); window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", draw);
let rz = 0; window.addEventListener("resize", () => { cancelAnimationFrame(rz); rz = requestAnimationFrame(draw); }); draw();
</script>
"""


def main():
    data = json.loads((REP / "boundary_view.json").read_text(encoding="utf-8"))
    html = HTML.replace("__DATA__", json.dumps(data, separators=(",", ":"))).replace("__REPEAT__", str(data["repeat"]))
    (REP / "boundary_view.html").write_text(html, encoding="utf-8"); print(REP / "boundary_view.html", len(html) // 1024, "KB")


if __name__ == "__main__":
    main()
