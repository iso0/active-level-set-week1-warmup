# Research campaign 20261018 (Opus) — status log

This file is updated about every 6 hours. Live machine state is in `runner/HEARTBEAT.json` and `runner/STATUS.md`. The coordination record is `outputs/joint_depth_label_development/pool/POOL_PLAN.json`; attempts are in `outputs/joint_depth_label_development/ATTEMPT_LEDGER.md` (rows RC18-*).

## Update 1 — 2026-10-18 09:50 UTC (elapsed 1.1 h of 48 h)

**Resource sharing.** Established at 08:46:11 UTC, before any heavy Opus computation.
- Host `Burak`: 8 logical CPUs / 4 physical cores, 31.8 GB RAM. 4 numerical threads in total.
- **Opus: 2 threads (active). Astra: 2 threads (reserved for her new campaign; Opus never uses them without her completion or release record).**
- At the start there were no unrelated numerical workers. Background load was about 1 logical CPU (Claude, ChatGPT/Codex UI, Task Manager).

**Live jobs (PID, start UTC):**
- Runner supervisor PID 7136 (08:56:02), started detached via WMI so it survives the chat or app closing.
- Runner PID 29180 (08:56:03), 1 of the 2 Opus slots. The other slot is kept for interactive development.
- Development batch `python -m src.rc18_campaign dev-reg3` (interactive slot): launcher 4524, worker 22272, started 09:49:48.
- Astra share: no registered jobs yet.

**Restart after a reboot:** `powershell -NoProfile -ExecutionPolicy Bypass -File src\rc18_start_runner.ps1` (idempotent; finished units are skipped).

**Done so far:**
1. **Astra's frozen pilot**, run once from a verbatim copy of the 17 Oct final package (SHA-256 identical; her workspace not written). COMPLETE: 578 fits, 650 solves, 10.6 s; references PASS. In the island worlds the surprise trigger never fired, because no straddle-type arm paid an island run by B24. Reference result: a level-set-focused global schedule does not produce the first hit a local reaction needs.
2. **Fix A1, the variance contract.** In sklearn 1.9.0 `predict(return_std)` already includes the white noise, so PHYS_DISCOVERY v1.0 counted the noise twice.
   - An exact replay of 20/20 trajectories recovered the pre-query moments; the corrected rule gives 11 extra triggers on the same paths.
   - Prospective v1.1 (frozen before running): **verdict unchanged, NO DISCOVERY GAIN**. Repair effect +0.002 (NEW), +0.007 (OLD).
3. **Fixes A2/A3, the channel-independent loader.**
   - The 56 OLD runs without velocity keep their depth (56) and KE (55).
   - Row mismatch and non-finite counts are now separate counters. H-ce04be44b1 (931 non-finite KE) and the early-ended P-423…H-e7dbd8e5ce (row-mismatched channels, 0 non-finite) are distinct. QC-REC was erratum'd: it had used another run with the same H code.
   - Duration-weighted medians equal row medians at T0 (difference ≈ 0), although 536/541 time grids are irregular.
   - **The 40-bin onset-normalised median curve keeps only 37 % (median) of the native NEW velocity peak**, with a peak-time error of 0.10 ms.
4. **Data inspection, used to choose the directions:**
   - NEW is OLD's high-power corner.
   - **A GP trained on all OLD runs predicts NEW outputs with no NEW simulation** at about NEW's own attainable accuracy: log A R² 0.94, laser 0.91, temperature 0.85, spike 0.84.
   - Residual spread is 2–4× larger in Keyhole runs.
   - 6 NEW runs have truncated records (end at 0.44–1.13 ms of 2.1 ms). They dominate NEW's low R² for energy and particle number.
5. **Engine and runner built and validated.** GP engine (equal to sklearn ML-II at 1e-13, analytic gradients, IVR and TruVaR); runner (checkpointing, deadline, heartbeat, failure pausing).

**Chosen directions (results-independent inspection):**
- **D1, partial sharing across outputs and campaigns:** transfer from the historical OLD campaign (OLD-emulator prior mean plus a residual GP), shared ARD lengthscales across outputs, and a QA-aware heteroskedastic observation model for truncated records.
- **D2, a native-time phase model** for temperature and KE (onset, peak time, amplitude, duration), with alignment predicted from x and the direct scalar GP as control.

**Priority order:**
1. Development of D1 on DEV repeats 1–2 (running).
2. Freeze the final protocol, then run the final programme on DEV repeats 5–8:
   - regression: models M0 / SH / TR-family × designs MAXIMIN / RANDOM / MOIVR;
   - region learning: velocity-spike level set, with MAXIMIN / RANDOM / STRADDLE / TRUVAR / Astra surprise vs straddle_global;
   - Keyhole label arm: G3 + margin, ACTIVE E1 + straddle, TR-E1 + straddle.
3. D2 temporal phase model.
4. Report, single results table, learning curves, boundary figure and interactive view, cost breakdown, contribution sentence.

**Open uncertainty:**
- Whether transfer keeps its B0 advantage once NEW data arrive. In development, the plain residual GP overfits the truncated-record outliers; the QA-aware variant is being tested now.
- Whether acquisition adds anything on top of a better model.
- Whether the region and label problems are discriminating: NEW's velocity-spike region is already BA ≈ 0.96 at B8.

### Türkçe özet

**Paylaşım kuruldu:** Opus 2 iş parçacığı, Astra 2 iş parçacığı. Astra'nın payı 08:46'da, ağır hesaptan önce ayrıldı.

**Tamamlananlar:** Astra'nın pilotu bir kez çalıştı, A1 düzeltmesi yapıldı (karar değişmedi), A2 ve A3 yapıldı.

**En güçlü yeni bulgu:** Tarihsel OLD koşuları, NEW'in fiziksel çıktılarını hiç NEW simülasyonu olmadan neredeyse NEW'in kendi erişilebilir doğruluğuyla öngörüyor. Ana iş, bunun öğrenme eğrilerinde gerçek bir simülasyon tasarrufuna dönüşüp dönüşmediği.
