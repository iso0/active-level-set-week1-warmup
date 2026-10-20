# RC21 / RC21B — using the exact public inputs better than SHQ_ATS_H (Opus, 2026-10-20 evening)

**Evidence label: DEV.** All 541 simulations were inspected earlier; new partitions are not physical validation.

**Programme and window:** continuation inside the remaining RC20 window (cap 2026-10-21 11:52:22 UTC; the clock was not restarted); 2 threads; Astra's jobs and share untouched. Local commits only.

**Commits:**

| commit | what it records |
|---|---|
| 1f198d2d | registration + acceptance |
| 7c7cf486 | Stage 1 + amendment A1 + freeze |
| ff2e4b9b | RC21 results |
| f75b7590 | RC21B registration + freeze |
| final commit of this report | RC21B results |

---

## Türkçe kısa açıklama (önce)

**Tek hüküm: KARAR ÜSTÜNLÜĞÜ YOK; olasılık kalitesinde gerçek iyileşme (DEV).**

Önceki en güçlü model SHQ_ATS_H + margin (RC20). Karşılaştırmalar aynı başlangıç ve aynı bütçeyle, taze tekrarlarda ve eşleştirilmiş yapıldı.

### Ne kazandık?

- **Olasılık kalitesi (RC21B, taze tekrarlar 35–42).** Sınıflandırıcının h eğilimine ve fiziksel özetlere ne kadar güveneceğini sabit cezayla (C = 1) değil, ödenmiş etiketlerden öğrenmek (PHR_NRMAP) olasılıkları belirgin biçimde iyileştirdi:
  - küçük bütçe log-loss AULC'si −0.030 (8/8, BETTER); tüm bütçe −0.012 (8/8, BETTER);
  - B24'te kalibrasyon eğimi 1.71'den 1.34'e indi.
- **Olasılık hedefine daha az simülasyon.** LL ≤ 0.20 hedefine 16.9'a karşı 20.6 ödenmiş simülasyonla ulaştı (−3.75; 8 tekrarın 7'sinde daha az).
- **Yaklaşık modele karşı.** Dürüst çapraz-uyumlu sınıflandırıcı artık RC19'un yaklaşık modeli ATSAPPROX'u da olasılıkta geçiyor (−0.024, 7/8). RC20'de ikisi eşitti.
- **Neden?** Eğitimde kullanılan kat-dışı özellik tahminleri gürültülü. Bu yüzden sabit C = 1 cezası sınıflandırıcıyı fazla temkinli yapıyordu (eğim > 1). Etiketler h eğiliminin gücünü yaklaşık 2–3 kat büyük seçiyor. Karar sınırının yönü neredeyse değişmiyor, olasılıklar keskinleşiyor.

### Ne kazanamadık?

- **Karar doğruluğu.** BA +0.003 (6/8; RC21B) ve +0.002 (5/8; RC21); 0.02 marjının çok altında. Keyhole duyarlılığı +0.008, iletim duyarlılığı −0.002: fark yok.
- **BA ≥ 0.93 için ödenmiş sorgu.** RC21B'de −0.4, RC21'de −1.75 simülasyon: açık fark yok. **Ana soruya yanıt iki testte de HAYIR.**
- **Kalan girdi etkileri.** h'ye dik (h eğilimini kopyalayamayan) büzülebilir artık GP işe yaramadı (LL +0.005, 0/8).
- **Gizli belirsizliği tahmine katmak.** Laplace integrasyonu olasılıkları daha da temkinli yaptı (LL +0.042). RC21'in sıralı kolu (PHR_NR) bu yüzden log-loss'ta kötüleşti (+0.020, WORSE). Bu sonuç önceden beyan edilmişti.
- **Genel kesin girdiler (4 log girdi), kendi sorgularıyla.** h'den iyi değil:
  - BA −0.007 / −0.003, LL −0.003; harcama farkı yok.
  - Aynı sorgularda BA'da açıkça kötü: −0.011, 0/8.
- **Hızlı-tarama köşesi.** Çözülmedi: B60'ta 96 iletim koşusunun 62–70'i yanlış. Bu bölgede Keyhole ve iletim koşuları girdilerde iç içe: en yakın komşu etiket uyumu 0.44, havuz genelinde 0.91. Girdilere göre pürüzsüz hiçbir model bunu ayıramaz.

### Süreç notları

- **A1 değişikliği.** RC21'in ön-kayıtlı kapısı PHR_NR'yi log-loss zararı (+0.016) yüzünden "taşınmaz" saydı; oysa aynı yollarda BA'yı +0.010 (8/8) artırıyordu. Kapının bu LL kısmı, sıralı aşamanın karar/sorgu birincil uçlarıyla çeliştiği için A1 değişikliğiyle aşıldı. Bu, hiçbir sıralı sonuç görülmeden önce yapıldı ve gerekçesiyle yazıldı (AMENDMENT_A1.md). Daha katı bir okuma burada durmayı gerektirirdi; karar sizin.
- **PHR_NRMAP'in seçimi.** PHR_NRMAP, RC21 ayrıştırması görüldükten sonra seçildi. Bu yüzden ayrı ve önceden kaydedilmiş bir doğrulama yapıldı: taze tekrarlar 35–42, birincil uçlar aynı.
- **Hesap ve kaynak.** Toplam 4.13 CPU-saat. Astra'nın işlerine ve payına dokunulmadı.

### Gerekçeli sonraki adım

- **Model.** PHR_NRMAP, SHQ_ATS_H'nin yerine varsayılan sınıflandırıcı olabilir: kararlar aynı, olasılıklar daha iyi (DEV).
- **Karar ve sorgu kazancı.** Bu, artık model değil seçici veya yeni bilgi sorusu. RC20'de margin seçicisi bütçenin yaklaşık %41'ini iç içe köşede harcadı. Köşede tekrar sorgulamayı azaltacak bir seçici sınanmaya değer bir aday; bu bir iddia değil.
- **Köşe.** Köşede fiziksel doğrulama ya da yeni simülasyon sahibin kararı.

---

## 1. What was done

The owner asked for an improvement of SHQ_ATS_H that uses the exact public inputs better:
- at most one new, justified combination — physical summaries + h trend + a regularised correction for the remaining input effects;
- the generic-input control (SHQ_ATS_X) run sequentially on its own queries;
- the model contribution isolated first on identical query paths, then a pre-registered sequential comparison;
- decisions (BA, both recalls, hard conditions) reported next to probabilities, and log-loss gains never sold as decision gains.

| stage | data | content |
|---|---|---|
| design diagnostics (disclosed, `diagnostics/DESIGN_DIAGNOSTICS.md`) | full pool, evaluator-side | the logistic boundary in log-input space points along h (cosine 0.9965; exponents P^1 VX^−0.59 LS^−1.34 ST^−0.08); linear transverse terms add nothing; oracle depth alone gives BA 0.978; the fast-scan corner is label-interleaved |
| numerical acceptance (`RC21_VALIDATION*.json`) | DEV tasks | Laplace = weight-space (3.6e−11); nesting to SHQ_ATS_H; RC20 reproduction ≤ 3e−8; H arm = RC20 CAND trajectory exactly; shadow tests 0.0 |
| Stage 1 (`stage1/STAGE1.md`) | 200 RC19B paths, B8–B60 | PHR and its decomposition on identical paid prefixes |
| RC21 sequential (`final_report/FINAL.md`) | fresh repeats 27–34, 240 trajectories | NEW = PHR_NR (A1), H, X, ATSAPPROX, E1S, G3 |
| RC21B confirmation (`b_final_report/FINAL.md`) | fresh repeats 35–42, 160 trajectories | NEW = PHR_NRMAP, H, ATSAPPROX, E1S |

## 2. The combination (equations: `MODEL_DEFINITIONS_RC21.md`)

The model has one discriminative layer:

η(x) = b0 + β_h z_h(x) + Σ_t w_t F̃_t(x) + r(U(x))

- **F̃** — the honest out-of-fold SHQ predictions of (log A, T, S); exactly the SHQ_ATS_H upstream.
- **z_h** — the exact standardised log h.
- **U** — the 3-D complement of the h direction in standardised log-input space, so r is constant along h and cannot duplicate the trend.
- **Priors** — b0 ~ N(0, 10²), β_h ~ N(0, τ_h²), w ~ N(0, τ_F²), r ~ GP(0, σ_r² SE(ℓ)).
- **Inference** — Laplace GP classification. The hyperparameters are averaged over a fixed 112-point grid by marginal likelihood; the no-residual model has prior mass ½.

h is a deterministic input function. It appears once, in the decision layer; the emulators stay on x without h, and no h-based and feature-based probabilities are multiplied.

How this differs from the earlier h attempts:

| attempt | what it did | what RC21 changes |
|---|---|---|
| M3 | frozen C = 1e6 h-logistic mean, capped residual over all inputs, no physical summaries | — |
| LT | learnable h basis inside the label GPC | — |
| SHQH | h as an extra emulator input | — |
| SHQT | h-mean emulators | — |
| SHQ_ATS_H | fixed C = 1 | PHR learns every strength from the paid labels and restricts the residual to h^⊥ |

By-products of the same fits:

| name | definition |
|---|---|
| PHR_FXMAP | the RC20 classifier (nesting, Δ ≈ 0) |
| PHR_FX | the same with integrated predictive |
| PHR_NR | learned strengths, no residual, integrated |
| PHR | full |
| PHR_NRMAP | learned strengths, plug-in; added by A1 as an exploratory by-product, then confirmed in RC21B |

## 3. Stage 1 — model contribution on identical queries (200 paths; all-path means, 8 repeats)

| construction | LL B8–B24 | BA B8–B24 | Keyhole recall | conduction recall | LL B8–B60 | BA B8–B60 |
|---|---|---|---|---|---|---|
| SHQ_ATS_H (RC20) | 0.2254 | 0.9165 | 0.9031 | 0.9299 | 0.1647 | 0.9384 |
| SHQ_ATS_X | 0.2291 | 0.9123 | 0.8954 | 0.9292 | 0.1696 | 0.9346 |
| PHR_FX (integrated, fixed) | 0.2677 | 0.9166 | 0.9032 | 0.9299 | 0.1897 | 0.9384 |
| PHR_NR | 0.2418 | 0.9268 | 0.9184 | 0.9351 | 0.1776 | 0.9421 |
| PHR | 0.2472 | 0.9261 | 0.9164 | 0.9358 | 0.1804 | 0.9416 |
| ATSAPPROX | 0.2169 | 0.9236 | 0.9094 | 0.9378 | 0.1645 | 0.9403 |
| E1CAL / E1RAW | 0.3170 / 0.3478 | 0.9011 / 0.9104 | – | – | 0.237 / 0.238 | 0.930 / 0.935 |

Decomposition (B8–B24, paired over 8 repeats):

| component | ΔLL | ΔBA |
|---|---|---|
| intercept prior | 0.0000 | 0.0001 |
| latent integration | **+0.042 (0/8)** | 0 (by construction) |
| learned regularisation | **−0.026 (8/8)** | **+0.010 (8/8)** |
| transverse residual | +0.005 (0/8) | −0.0006 |

Pre-registered rules:
- the residual rule chose PHR_NR;
- the gate returned NOT CARRIED (LL +0.016 MATERIAL HARM, next to BA +0.010 MATERIAL);
- amendment A1 carried PHR_NR into the sequential stage.

## 4. RC21 sequential (fresh repeats 27–34)

| arm | LL B8–B24 | BA B8–B24 | Keyhole rec. | cond. rec. | LL B8–B60 | BA B8–B60 | sims to BA ≥ 0.93 | sims to LL ≤ 0.20 |
|---|---|---|---|---|---|---|---|---|
| NEW = PHR_NR + margin | 0.2333 | 0.9296 | 0.9198 | 0.9395 | 0.1724 | 0.9442 | 16.4 (13–19) | 23.0 |
| H = SHQ_ATS_H + margin | 0.2130 | 0.9274 | 0.9105 | 0.9444 | 0.1616 | 0.9420 | 18.1 (13–33) | 19.75 |
| X = SHQ_ATS_X + margin | 0.2103 | 0.9208 | 0.9006 | 0.9409 | 0.1600 | 0.9387 | 20.1 | 18.6 |
| ATSAPPROX + margin | 0.2038 | 0.9254 | 0.9026 | 0.9481 | 0.1575 | 0.9414 | 18.6 | 19.0 |
| E1RAW / E1CAL + straddle | 0.369 / 0.306 | 0.913 / 0.901 | – | – | 0.232 / 0.202 | 0.938 / 0.931 | 23.6 / 25.25 | 31.4 / 27.25 |
| G3 + margin | 0.380 | 0.888 | – | – | 0.272 | 0.923 | 32.0 | 48.25 |

Verdicts:

| contrast | result | verdict |
|---|---|---|
| Q1 NEW − H, BA B8–B24 | +0.0022 (5/8) | NOT DIFFERENT |
| Q2 NEW − H, sims to BA ≥ 0.93 | −1.75 (4/1/3) | NO CLEAR DIFFERENCE |
| **Answer** | | **NO** |
| NEW − H, LL B8–B24 | +0.020 (1/8) | WORSE (declared in A1) |
| X − H, BA | −0.0067 (2/8) / −0.0033 (1/8) | NOT DIFFERENT |
| X − H, LL | −0.003 | NOT DIFFERENT |
| X − H, spend | +2.0 / −1.1 | NO CLEAR DIFFERENCE |

Matched-path decomposition on the fresh paths:
- the model on the same queries gives BA +0.005 to +0.0065 (7–8/8);
- NEW's own query path cost the H model −0.004 BA, which offsets the model gain.

## 5. RC21B confirmation (fresh repeats 35–42; NEW = PHR_NRMAP)

| arm | LL B8–B24 | BA B8–B24 | Keyhole rec. | cond. rec. | LL B8–B60 | BA B8–B60 | sims to BA ≥ 0.93 | sims to LL ≤ 0.20 |
|---|---|---|---|---|---|---|---|---|
| NEW = PHR_NRMAP + margin | **0.1912** | 0.9283 | 0.9170 | 0.9396 | **0.1459** | 0.9463 | 16.4 | **16.9** |
| H = SHQ_ATS_H + margin | 0.2211 | 0.9253 | 0.9087 | 0.9419 | 0.1582 | 0.9452 | 16.75 | 20.6 |
| ATSAPPROX + margin | 0.2152 | 0.9211 | 0.9037 | 0.9386 | 0.1597 | 0.9419 | 21.1 | 20.75 |
| E1RAW / E1CAL + straddle | 0.378 / 0.318 | 0.910 / 0.890 | – | – | 0.243 / 0.210 | 0.937 / 0.927 | 24.25 / 25.4 | 30.75 / 27.75 |

Verdicts:

| contrast | result | verdict |
|---|---|---|
| Q1 BA B8–B24 | +0.0030 (6/8) | NOT DIFFERENT |
| Q2 sims to BA ≥ 0.93 | −0.38 (4/1/3) | NO CLEAR DIFFERENCE |
| **Answer** | | **NO** |
| key secondary: LL B8–B24 | −0.0298 ± 0.0048 (8/8) | **BETTER** |
| LL B8–B60 | −0.0123 (8/8) | BETTER |
| Brier | −0.0025 (6/8) | NOT DIFFERENT |
| sims to LL ≤ 0.20 | −3.75 (7/0/1) | **FEWER** |
| NEW − ATSAPPROX, LL | −0.024 (7/8) / −0.014 (7/8) | BETTER |
| NEW − ATSAPPROX, BA | +0.007 | NOT DIFFERENT |
| NEW − ATSAPPROX, sims to BA ≥ 0.93 | −4.75 | FEWER (H − ATSAPPROX −4.4 as well, so not specific) |
| NEW vs E1RAW / E1CAL / G3 | | BETTER / FEWER |

Same queries: PHR_NRMAP − SHQ_ATS_H LL −0.029 / −0.034 (8/8), BA +0.003 / +0.007. The NEW model's own path is neutral for it.

## 6. Hard conditions (both stages)

**Fast-scan corner.** NEW-batch conduction runs predicted Keyhole, of 96, at B24 / B60:

| arm | RC21 B24 | RC21 B60 | RC21B B24 | RC21B B60 |
|---|---|---|---|---|
| NEW | 81 | 66 | 71 | 62 |
| H | 77 | 70 | 75 | 64 |
| X | 83 | 70 | – | – |
| ATSAPPROX | – | – | 73 | 64 |

Every arm is limited by the label interleaving (nearest-neighbour agreement 0.44 vs 0.91).

**Short-Keyhole capture** (of 176):

| arm | RC21 B24 / B60 | RC21B B24 / B60 |
|---|---|---|
| NEW | 136 / 135 | 140 / 143 |
| H | 135 / 141 | 140 / 148 |

**q20 BA (B8–B24):**

| arm | RC21 | RC21B |
|---|---|---|
| NEW | 0.733 | 0.739 |
| H | 0.730 | 0.739 |

## 7. Compute and records

**CPU** (`COMPUTE.md`), 4.13 CPU-h in total:

| job | CPU-h |
|---|---|
| d-replay | 0.61 |
| d-smoke | 0.09 |
| d-final | 1.99 |
| e-smoke | 0.06 |
| e-final | 1.38 |

Decision CPU is 0.88–0.90 s per step for the physical arms (all constructions computed), separate from the paid-simulation axis. No new physical simulation was run.

**Auditable records:**
- `final_export/` and `b_final_export/`: `predictions_f32.npz` holds every per-budget test prediction of every arm and every by-product on each physical arm's own path; `paths.csv.gz` holds every paid query with its rule (startup / path / margin / arm selector). Acceptance PASS on 2,968 and 2,120 metric cells.
- `stage1_export/`: the 200-path predictions, acceptance PASS, plus the posterior diagnostics per state.
- Single-learner boundary-evolution views: `viewer/rc21_boundary_view.html` (repeat 27, fold 1) and `viewer/rc21b_boundary_view.html` (repeat 35, fold 1). Refit vs recorded ≤ 3e−8.
- Figures: `figures/fig_rc21_stage1.png`, `fig_rc21_final.png`, `fig_rc21b_final.png`.

## 8. Deviations and process notes

**Queue.** The first runner counted Astra's declared non-numerical finisher as 4 slots. Before any unit ran, the runner was changed to count it at 0, exactly as her share declares it (RC21-QUEUE).

**A1.** The LL gate was overridden after Stage 1, before any sequential outcome (AMENDMENT_A1.md); the original rule outcome is kept.

**RC21B selection.** PHR_NRMAP was selected after seeing the RC21 by-products. Its confirmation used fresh repeats with unchanged endpoints and reused the frozen RC21 report code.

**Rules kept.** No label, exclusion, q20 or target was changed. OLD/NEW is used only for evaluator diagnostics. Every startup query is counted.
