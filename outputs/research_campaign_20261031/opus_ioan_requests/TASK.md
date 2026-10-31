# IR task: a comprehensive answer to Ioan's requests of 30 October 2026

**Owner request (2026-10-31):** "yüzeysel değil kapsamlı bi çalışma yapmanı istiyorum ioan ın istekleri için."

The day before, Opus had sent the owner a one-table first look (see `PROTOCOL_IR.md` §0). The owner wants a full study instead.

**Clock:** Opus started at **2026-10-31T16:09:01Z**. The hard limit is **48 h, ending 2026-11-02T16:09:01Z**. Quota waits, session changes and restarts do not reset it.

## Source: the meeting of 2026-10-30 (owner's transcript)

The transcript gives Burak as Speaker A and Ioan as Speaker B. Ioan's requests, in his words (lightly cleaned):

1. On kinetic energy:
   - "And you couldn't find a relation between depth and kinetic energy, for example." Burak: not checked.
   - "That would also be worth checking."
2. "So you tried that to go directly from … kinetic energy to the label, right?" Burak: yes.
   - "Okay, just try doing that as well. With … the depth."
3. The reasoning behind it:
   - "You already researched and proved that there is a correlation between depth and the label. You also saw now that there is a correlation between the inputs and the hidden thing."
   - Burak: "if there's a correlation between kinetic energy, temperature versus depth".
4. "This one could be like the most useful maybe. Did you try to see if there's a correlation between melt pool width and melt pool depth?"
5. "It's not like reinventing the whole thing again, just add another."

**Opus reads the requests as one chain:** inputs → hidden physical quantities (kinetic energy, temperature, flow, melt-pool width) → depth → label.

**The thesis question behind it:** "Can we distinguish Keyhole from conduction with as few simulations as possible?" A complete answer therefore has to cover four things:
- how strongly each quantity is tied to depth;
- whether that tie remains once the inputs are known;
- what it means physically;
- whether using the tie lowers the number of simulations.

## Fixed setting

| item | value |
|---|---|
| main method | C1 + margin (`src/ea_cand.py` SYSTEMS["C1"]); code and earlier results frozen |
| reference arm | HA_LEAN + margin (diagnostics only) |
| data | the one 541-run pool (`POOLED_MANIFEST.csv`, unchanged) plus a NEW derived table of melt-pool width / length and time series, extracted read-only from the verified raw copy in the main checkout (`C:\Users\ozgur\Documents\thesis\data\raw\sph_v2`) by the unchanged Week 19 code; no new simulation |
| learner contract | a learner sees only public inputs and the outcomes of PAID runs; width enters only through a paid-only reveal wrapper |
| unchanged | labels, exclusions, decision threshold 0.5, error weights, q20 definition |
| not used | the 49 withheld Bug NEW runs; OLD/NEW routing; test labels or unopened outputs inside a learner; simulator, paid service, cloud |
| compute | at most 3 heavy single-thread workers (BLAS/OpenMP = 1) |
| coordination | `C:\Users\ozgur\Documents\thesis_shared_runtime\campaign_20261031\opus_state.json`; Astra's campaign is CLOSED (2026-10-29); Astra's files are not touched |
| outputs | `outputs/research_campaign_20261031/opus_ioan_requests/` |
| branch | `ioan-requests-20261031` (from b0e9569f); push to GitHub, verify the remote SHA; no main merge, no force push |

## Already known (cited, not repeated)

- RC19 / RC23: sharing GP lengthscales across physical outputs (SHQ) helped a little. RC23 then found the depth-only upstream non-inferior, so it became the thesis learner's upstream.
- RC20 / RC22: temperature (T) and velocity spike (S) as classifier features help without log h, but are useless after h + depth.
- PHYSICAL_PILOT (2026-10-16): 5 / 7 NEW-batch summaries are learnable from x; KE timing is not.
- EA (2026-10-26): early errors are limited by the depth prediction at unopened inputs. With the true depth, 8 labels already give BA 0.957.

## Order of work

1. Registration (`PROTOCOL_IR.md`, this commit), before any new number.
2. Data extraction and validation (V1–V6).
3. Descriptive parts A (structure), F (time series), G (literature) and B (learnability).
4. Method screen C on DEV paths, with a pre-registered carry rule.
5. Only if a candidate is carried: D (downstream DEV); and only if D passes, a separately registered fresh test E.
6. Reports: Turkish final report, English summary for Ioan, figures, ledger, memory, commit, push.
