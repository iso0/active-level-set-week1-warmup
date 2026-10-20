# RC20 — what actually makes the pooled Keyhole learner better, the log-h combination, and the paid-query test (Opus, 2026-10-20)

**Evidence label: DEV.** All 541 simulations were inspected earlier; new partitions are not physical validation.

**Programme:** the owner's NEW bounded programme, started 2026-10-20 11:52:22 UTC; cap 24 h; 2 threads. Local commits only.

**Rules and freezes:**
- Stage 1 rules: ledger RC20-RULES, commit 47242600.
- Sequential freeze: commit 6f41d4fd, manifest `final/RC20_FINAL_MANIFEST.json`.

---

## Türkçe açıklama (önce)

**Tek hüküm: İYİLEŞME (DEV).**
- Fiziksel-yanıt sınıflandırıcısına kesin log h koordinatını eklemek (SHQ_ATS_H, dürüst çapraz uyum), aynı seçiciyle (margin) ATSCF'den daha iyi olasılık verir. Önceden ilan edilen birincil sonuç: küçük bütçe log-kayıp AULC'si −0.038, 8 tekrarın 8'inde (BETTER).
- Ödenmiş simülasyon sayısında da kazanç var: ATSCF'ye göre 4 civarı, E1 + straddle'a göre 6–10 daha az simülasyon.
- Karar doğruluğu (BA) pratik marjı geçmiyor. Hızlı-tarama köşesi ve süre darboğazı açık kalıyor.

**1. Hangi güçlü kontrole göre ne iyileşti?**

Taze tekrarlar 19–26'da (aynı başlangıç, aynı bütçe, eşleştirilmiş tekrar) SHQ_ATS_H + margin'in sonuçları:
- **ATSCF + margin'e göre (aynı seçici, yalnız model değişti):**
  - log-kayıp AULC: B8–B24 −0.038 ± 0.007 (8/8, **BETTER**); B8–B60 −0.026 (8/8, BETTER);
  - Brier −0.006 (8/8, BETTER);
  - BA +0.008 (8/8 tekrarda olumlu, ama 0.02 marjının altında, NOT DIFFERENT). Küçük bütçede BA +0.020, tam marj sınırında; bu yüzden yine NOT DIFFERENT.
- **Kalibre E1 + straddle'a göre:** log-kayıp −0.051 (8/8, BETTER).
- **G3'e göre:** log-kayıp −0.114 (8/8).
- **RC19'un yaklaşık ATSAPPROX'una göre:** fark yok (−0.006 / −0.009, 5/8). Yani dürüst model artık en güçlü kontrolle aynı düzeyde.

**2. Neden?** (Önce aynı ödenmiş yollar üzerinde, 200 RC19B yolu, Stage 1.)

- **Kazanç nereden geliyor:**
  - RC19B'deki "ATSCF − derinlik-tek" kazancı (−0.037), aynı SHQ üst modeliyle eklenen sıcaklık ve hız-sıçrama özelliklerinden geliyor. Karar verici H1 sonucu: −0.029 (8/8), MADDİ.
  - Üst modelin paylaşılan uzunluk ölçekleri (SHQ) maddi değil: ana etki −0.003.
  - İki ayrıştırma sırası 0.005'ten fazla farklı olduğu için yüzde ayrımı verilmiyor. Eski "%45 kalibrasyon / %55 fizik" ifadesi geri çekildi: E1'in olasılık haritası bütün yollarda −0.001.
- **log h'nin rolü:**
  - h = P/√(VX·LS³) kamusal bir ölçekleme koordinatı. LS, metre cinsinden Gauss spot yarıçapı; birim W s^½ m⁻².
  - Aynı sınıflandırıcıya, büzülebilir bir terim olarak kesin değeriyle girdiğinde log-kaybı −0.020 (8/8) düşürüyor; küçük bütçede −0.036 (8/8). Tahmin edilen özellikler küçük n'de gürültülü, kesin bir girdi bu açığı kapatıyor.
  - h'yi emülatör ortalamasına koymak (öğrenilen güçlü, belirsizliği taşınan trend, SHQT) maddi değil. Eski M3'ün C = 1e6 doymuş trendi tekrar kurulmadı.
- **h'ye özgüllük (keşifsel kontrol, 200 yolda eşleştirilmiş):**
  - Sınıflandırıcıya log h yerine 4 kesin log-girdi vermek, log-h kazancının yaklaşık dörtte üçünü yine sağlıyor: −0.015'e karşı −0.020 (8/8).
  - log h genel girdilerden tutarlı ama küçük farkla daha iyi: +0.005, 7/8 tekrarda; sadece derinlikle +0.008, 8/8 tekrarda.
  - Yani asıl mekanizma "sınıflandırıcıya kesin kamusal girdi vermek". h bunun daha az parametreli, fizik biçimli ve biraz daha iyi bir yolu.

**3. Gerçek bir ödenmiş-sorgu yararı var mı?**

Evet, DEV kanıtı olarak (çevrimdışı hedefler; ikinci kontrol noktası b + 4; sansür yok):

| hedef | SHQ_ATS_H + margin | ATSCF + margin | E1 + straddle (ham / kalibre) | ATSAPPROX |
|---|---|---|---|---|
| BA ≥ 0.93 | 15.1 | 19.5 | 22.6 / 23.1 | 16.6 |
| log-kayıp ≤ 0.20 | 18.75 | 22.5 | 28.5 / 24.75 | 20.5 |

- **ATSCF'ye göre** (önceden ilan edilen kural: FEWER SIMULATIONS):
  - BA ≥ 0.93: −4.4 simülasyon (6 tekrarda az, 2'de fazla);
  - log-kayıp ≤ 0.20: −3.75 (6 az, 1 eşit, 1 fazla).
- **E1'e göre:** 6–10 daha az (8/8).
- **ATSAPPROX'a göre:** açık fark yok (−1.5 / −1.75).
- Bir simülasyon bütün çıktıları tek maliyetle verdiği için tasarruf çıktı sayısıyla çarpılmaz.
- Karar CPU'su adım başına 0.56 s; yörünge başına 30 s. Simülasyon maliyeti yanında ihmal edilebilir.

**4. Ne hâlâ başarısız?**
- **BA:** hiçbir yapı 0.02 marjını geçmiyor.
- **η-straddle seçicisi** (aynı posterior, belirsizlik-farkında) margin'den kötü: küçük bütçe log-kaybı +0.015 (WORSE); log-kayıp hedefi için +4.1 simülasyon.
- **Dürüst çapraz uyumun küçük-bütçe açığı** için iki çare de ön-kayıtlı eşikte başarısız: kat-dağıtımı (FD) ve MAP uzunluk ölçeği.
- **h-ortalamalı emülatörler** (SHQT) maddi değil.
- **Hızlı-tarama köşesi** (12 iletim koşusu): adayın iletim duyarlılığı B60'ta 0.31; E1 tabanlı kollar 0.40–0.43. Fiziksel sınıflandırıcılar burada daha kötü.
- **Süre darboğazı** (RC19B): tekrar çalıştırılmadı, açık.

**5. Hangi sonraki adım gerekçeli?**
1. SHQ_ATS_H + margin'i DEV dışı bir doğrulamada denemek (yeni fiziksel simülasyonlar ya da C4). Bu sahibin kararıdır; bu programda yapılmadı.
2. Yorum için: genel kesin girdiler ile log h arasındaki fark küçük olduğundan tez metninde "kesin kamusal girdiler, özellikle fizik biçimli h" ifadesi kullanılmalı (Bölüm 4.4).
3. Köşe için ayrı, ön-kayıtlı bir yerel model.
4. Tez yazımı: bu sonuçlar artık temiz ayrıştırılmış durumda.

---

## 1. What ran

| stage | units | failures | wall (UTC) | output |
|---|---|---|---|---|
| intake, coordination, numerical acceptance | – | – | 11:52–12:05 | `RC20_VALIDATION.json` PASS; `src/rc20_gp.py validate` PASS |
| Stage 1 registration | – | – | 12:08 | `PROTOCOL_RC20_STAGE1.md` (commit 47242600) |
| remedy pilot | 20 | 0 | 12:09–12:13 | `pilot/PILOT.md` (rule → NONE) |
| Stage 1 matched replay (200 RC19B paths) | 200 | 0 | 12:14–12:49 | `stage1/STAGE1.md`, `stage1_export/` (acceptance PASS, 5,040 cells) |
| final-stage acceptance and smoke | 12 + validation | 0 | 12:52–12:56 | `RC20_VALIDATION_FINAL.json` PASS; `smoke_report/` |
| sequential freeze | – | – | 12:56 | `PROTOCOL_RC20_FINAL.md`, manifest (commit 6f41d4fd) |
| sequential stage (fresh r19–26) | 240 | 0 | 12:57–13:39 | `final_report/FINAL.md`, `final_export/` (acceptance PASS, 2,968 cells) |
| exploratory h-specificity replay | 200 | 0 code failures (1 deliberate worker stop to free a slot for the report) | 13:39–13:54 | `stage1_x/STAGE1_X.md` |

## 2. Contract and acceptance

**Contract (unchanged RC19):**
- One 541-run pool; OLD/NEW is provenance only.
- Matched 8-point label-free startups; every paid simulation counted.
- Learners use public inputs and paid outcomes only.

**Acceptance before any comparison:**
- recomputed SHQ_ATS / M0Q_A reproduce the cached RC19B ATSCF / DEPTHCF (≤ 3e-8, 5,600 checks);
- honesty for every new cross-fit (own outcomes never change own out-of-fold features or own fold model);
- shadow tests (13 constructions; both candidate arms);
- log h equals the week-18 definition;
- the learned-strength h-trend GP validated (gradient 2.7e-9; shrinks to its bound and equals the plain GP when h is useless);
- eta variance vs Monte Carlo (median relative error 1.6 %).

Definitions: `MODEL_DEFINITIONS_RC20.md`.

## 3. Stage 1 — matched paths (200 RC19B final paths, budgets 8–60 every 4; all-path means over 5 path types and 8 repeats)

| construction | LL B8–B60 | LL B8–B24 | BA B8–B60 | BA B8–B24 |
|---|---|---|---|---|
| ATSAPPROX (RC19 approximation) | 0.1645 | 0.2169 | 0.9403 | 0.9236 |
| **SHQ_ATS_H** (candidate) | 0.1647 | 0.2254 | 0.9384 | 0.9165 |
| SHQ_A_H | 0.1674 | 0.2318 | 0.9452 | 0.9302 |
| M0Q_ATS | 0.1835 | 0.2501 | 0.9340 | 0.9077 |
| SHQ_ATS (= ATSCF) | 0.1844 | 0.2610 | 0.9303 | 0.8973 |
| SHQT_ATS | 0.1871 | 0.2458 | 0.9379 | 0.9243 |
| SHQ_A | 0.2132 | 0.3078 | 0.9280 | 0.8955 |
| M0Q_A (= DEPTHCF) | 0.2209 | 0.3220 | 0.9254 | 0.8910 |
| SHQT_A | 0.2252 | 0.3081 | 0.9326 | 0.9139 |
| HONLY (log h only) | 0.2342 | 0.2909 | 0.9394 | 0.9343 |
| E1CAL | 0.2373 | 0.3170 | 0.9295 | 0.9011 |
| E1RAW | 0.2382 | 0.3478 | 0.9349 | 0.9104 |
| G3 | 0.3679 | 0.4233 | 0.8738 | 0.8458 |

**Pre-registered contrasts** (LL-AULC; MATERIAL iff mean ≤ −0.010 and ≥ 7/8 repeats):

| ID | contrast | B8–B60 | B8–B24 | label |
|---|---|---|---|---|
| **H1 (decisive)** | SHQ_ATS − SHQ_A (identical SHQ upstream) | −0.0288 (8/8) | −0.0468 (8/8) | **MATERIAL** |
| H1b | M0Q_ATS − M0Q_A | −0.0375 (8/8) | −0.0719 (8/8) | MATERIAL |
| H2a | SHQ_A − M0Q_A | −0.0078 (6/8) | −0.0142 (6/8) | not material |
| H2b | SHQ_ATS − M0Q_ATS | +0.0009 (4/8) | +0.0108 (4/8) | not material |
| H3 | E1CAL − E1RAW | −0.0009 (4/8) | −0.0308 (6/8) | not material |
| H4 | M0Q_A − E1CAL | −0.0164 (8/8) | +0.0051 (3/8) | material over B8–B60 only |
| H5 | ATSAPPROX − SHQ_ATS | −0.0199 (8/8) | −0.0441 (8/8) | material |
| **H6 (h, V1)** | SHQ_ATS_H − SHQ_ATS | −0.0197 (8/8) | −0.0356 (8/8) | **MATERIAL** |
| H6 (A only) | SHQ_A_H − SHQ_A | −0.0457 (8/8) | −0.0760 (8/8) | MATERIAL |
| H7 (h, V2) | SHQT_ATS − SHQ_ATS | +0.0027 (4/8) | −0.0152 (5/8) | not material |
| H7 (A only) | SHQT_A − SHQ_A | +0.0120 (2/8) | +0.0003 (3/8) | not material |

- BA differences are small throughout. H1 BA +0.002; H6 BA +0.008 / +0.019. SHQ_A_H has the best BA of all honest constructions (0.945).
- **2×2 decomposition of ATSCF − DEPTHCF (−0.0366):**

  | term | estimate |
  |---|---|
  | features main effect | −0.033 (order 1: −0.029; order 2: −0.038), 8/8 |
  | upstream main effect | −0.003 (order 1: −0.008; order 2: +0.001) |
  | interaction | +0.009 |

  Because the two orders disagree by more than 0.005, no percentage split is claimed.
- **Remedy pilot (null):** fold-deployment +0.010 and MAP lengthscales +0.002 in mean test LL at B12–B24.
  - Diagnostics: honest out-of-fold features differ from the approximation's by 0.54 / 0.42 / 0.22 feature-SD at B12 / B16 / B24, and the honest classifier's coefficients are attenuated (norm 1.18 vs 1.34 at B12).
  - This is consistent with noisier training features. Neither tested remedy fixes it.

## 4. Sequential stage — fresh DEV repeats 19–26, frozen (240 trajectories)

### 4.1 Pre-declared verdicts

| role | contrast | metric, window | mean Δ (SE) | good | verdict |
|---|---|---|---|---|---|
| **PRIMARY** | CAND_MARGIN − ATSCF_MARGIN | LL, B8–B24 | **−0.0383 (0.0067)** | 8/8 | **BETTER** |
| model, same selector | CAND_MARGIN − ATSCF_MARGIN | LL, B8–B60 | −0.0262 (0.0039) | 8/8 | BETTER |
| model, same selector | CAND_MARGIN − ATSCF_MARGIN | Brier, B8–B60 | −0.0062 | 8/8 | BETTER |
| model, same selector | CAND_MARGIN − ATSCF_MARGIN | BA, B8–B60 / B8–B24 | +0.0077 / +0.0200 | 8/8 / 8/8 | NOT DIFFERENT (margin 0.020) |
| selector, same posterior | CAND_ETASTRADDLE − CAND_MARGIN | LL, B8–B24 | +0.0145 | 1/8 | WORSE |
| selector, same posterior | CAND_ETASTRADDLE − CAND_MARGIN | BA, B8–B60 | +0.0006 | 6/8 | NOT DIFFERENT |
| control | CAND_MARGIN − ATSAPPROX_MARGIN | LL, B8–B24 / B8–B60 | −0.0057 / −0.0087 | 5/8 / 5/8 | NOT DIFFERENT |
| control | CAND_MARGIN − E1CAL+straddle | LL, B8–B60 | −0.0508 | 8/8 | BETTER |
| control | CAND_MARGIN − E1RAW+straddle | BA, B8–B60 | +0.0068 | 8/8 | NOT DIFFERENT |
| control | CAND_MARGIN − G3_MARGIN | LL, B8–B60 | −0.1139 | 8/8 | BETTER |

- **Loss and reference distribution are unchanged:** every arm is scored on the same held-out test fold with the same metrics at the same total paid budgets.
- **Separation of effects:**
  - the model change (same margin selector) is the primary;
  - the selector change (same posterior) is CAND_ETASTRADDLE − CAND_MARGIN.

### 4.2 Learning curves at matched budgets (mean of 8 repeats)

| arm | BA B16 | BA B24 | BA B60 | LL B16 | LL B24 | LL B60 | Keyhole / conduction recall B24 |
|---|---|---|---|---|---|---|---|
| CAND_MARGIN | 0.935 | 0.949 | 0.959 | 0.190 | 0.155 | 0.118 | 0.947 / 0.951 |
| CAND_ETASTRADDLE | 0.940 | 0.943 | 0.958 | 0.215 | 0.169 | 0.110 | 0.941 / 0.944 |
| ATSCF_MARGIN | 0.929 | 0.942 | 0.956 | 0.222 | 0.180 | 0.127 | 0.930 / 0.955 |
| ATSAPPROX_MARGIN | 0.934 | 0.945 | 0.955 | 0.205 | 0.157 | 0.122 | 0.934 / 0.957 |
| E1RAW+straddle | 0.911 | 0.949 | 0.958 | 0.355 | 0.205 | 0.147 | 0.963 / 0.935 |
| E1CAL+straddle | 0.908 | 0.944 | 0.954 | 0.297 | 0.182 | 0.133 | 0.939 / 0.949 |
| G3_MARGIN | 0.909 | 0.929 | 0.950 | 0.363 | 0.290 | 0.172 | 0.915 / 0.944 |

### 4.3 Target attainment and confirmation spend

All targets are confirmed at b and at the second checkpoint b + 4; spend counts total paid simulations, startup included.

| arm | BA ≥ 0.93: confirmed; mean (range) | LL ≤ 0.20: confirmed; mean (range) |
|---|---|---|
| CAND_MARGIN | 8/8; 15.1 (12–19) | 8/8; 18.75 (17–20) |
| CAND_ETASTRADDLE | 8/8; 16.5 (12–26) | 8/8; 22.9 (19–28) |
| ATSCF_MARGIN | 8/8; 19.5 (13–25) | 8/8; 22.5 (18–27) |
| ATSAPPROX_MARGIN | 8/8; 16.6 (13–20) | 8/8; 20.5 (17–24) |
| E1RAW+straddle | 8/8; 22.6 (17–26) | 8/8; 28.5 (21–38) |
| E1CAL+straddle | 8/8; 23.1 (20–27) | 8/8; 24.75 (20–29) |
| G3_MARGIN | 8/8; 28.9 (20–36) | 6/8 (2 censored); 49.3 (40–60) |

**Paired spend** (rule: restricted mean ≤ −2, fewer in ≥ 6/8, no extra censoring):

| contrast | BA ≥ 0.93 (fewer / equal / more) | LL ≤ 0.20 (fewer / equal / more) |
|---|---|---|
| CAND_MARGIN vs ATSCF_MARGIN | −4.38 (6/0/2), **FEWER** | −3.75 (6/1/1), **FEWER** |
| CAND_MARGIN vs E1RAW+straddle | −7.5 (8/8), FEWER | −9.75 (8/8), FEWER |
| CAND_MARGIN vs E1CAL+straddle | −8.0 (8/8), FEWER | −6.0 (8/8), FEWER |
| CAND_MARGIN vs G3_MARGIN | −13.75, FEWER | −34.25, FEWER (G3 censored twice, restricted) |
| CAND_MARGIN vs ATSAPPROX_MARGIN | −1.5, no clear difference | −1.75, no clear difference |
| CAND_ETASTRADDLE vs CAND_MARGIN | +1.4, no clear difference | +4.1, MORE SIMULATIONS |

- The held-out targets are offline benchmarks, not implementable stopping rules.
- A simulation's outputs arrive together, so nothing is multiplied by outputs.

**Reliability** (logistic recalibration slope, 1 = calibrated):

| arm | slope B16 → B60 | ECE B16 → B60 |
|---|---|---|
| CAND_MARGIN | 1.79 → 1.16 | 0.069 → 0.023 |
| ATSCF_MARGIN | 2.07 → 1.32 | – |
| ATSAPPROX_MARGIN | 1.66 → 1.17 | – |
| E1RAW+straddle (over-confident) | 0.47 → 0.61 | – |
| E1CAL+straddle | 0.82 → 1.29 | – |

**Fast-scan corner** (12 NEW conduction runs; evaluator-only):

| arm | conduction recall B60 (errors / 96) |
|---|---|
| CAND_MARGIN | 0.31 (66) |
| E1CAL+straddle | 0.43 (55) |
| E1RAW+straddle | 0.40 (58) |
| G3_MARGIN | 0.38 (60) |
| ATSCF_MARGIN | 0.29 (68) |

Unresolved, and the physical classifiers remain the weakest there.

**Compute** (single-thread seconds; separate from the paid-simulation count, which is 60 for every trajectory):

| arm | per trajectory | per decision step |
|---|---|---|
| CAND_MARGIN | 29.7 s | 0.56 s |
| CAND_ETASTRADDLE | 32.5 s | 0.61 s |
| ATSCF_MARGIN | 28.3 s | – |
| E1S | 24.3 s | – |
| G3_MARGIN | 7.0 s | – |
| ATSAPPROX_MARGIN | 3.3 s | – |

### 4.4 Exploratory: is it h, or exact inputs in general?

**On the candidate's own paths** (fresh repeats, the same paid prefixes, every 4 budgets), mean LL / BA:

| construction | LL | BA |
|---|---|---|
| SHQ_ATS_H | 0.1589 | 0.9436 |
| SHQ_ATS_X (4 exact log inputs) | 0.1664 | 0.9379 |
| SHQ_ATS (no exact input) | 0.1905 | 0.9309 |
| SHQ_A_H | 0.1640 | 0.9477 |
| HONLY | 0.2458 | 0.9401 |

**On the 200 Stage 1 paths, paired by repeat** (`stage1_x/STAGE1_X.md`):

| contrast | LL B8–B60 | LL B8–B24 | BA B8–B60 | BA B8–B24 |
|---|---|---|---|---|
| exact inputs vs none (SHQ_ATS_X − SHQ_ATS) | −0.0148 (8/8) | −0.0319 (8/8) | +0.0044 (6/8) | +0.0150 (7/8) |
| log h vs none (SHQ_ATS_H − SHQ_ATS) | −0.0197 (8/8) | −0.0356 (8/8) | +0.0081 (8/8) | +0.0192 (8/8) |
| log h vs exact inputs, ATS (SHQ_ATS_H − SHQ_ATS_X) | −0.0049 (h better 7/8) | −0.0036 (6/8) | +0.0038 (7/8) | +0.0042 (6/8) |
| log h vs exact inputs, A only (SHQ_A_H − SHQ_A_X) | −0.0079 (8/8) | −0.0082 (8/8) | +0.0084 (8/8) | +0.0132 (7/8) |

**Interpretation (exploratory, registered after Stage 1):**
- About three quarters of the log-h gain in log loss comes from giving the classifier exact public inputs at all. Without them it relies on noisy predicted summaries.
- log h, a single physics-shaped coordinate, is consistently but modestly better than the four generic log inputs: 7/8 repeats with A, T, S and 8/8 with depth only, at |Δ| below the 0.010 materiality gate with A, T, S.

## 5. Documentary repairs (RC19B addendum, no frozen outcome rewritten)

`opus_rc19b/ADDENDUM_RC19B_20261020.md`, `repairs/REPAIRS.md`:
1. The 23.5-query regression figure is a restricted score with non-completers at 84. It was observed in only 4/8 repeats; attainment is 12/16 vs 11/16 and unstable.
2. The filename DT is not the monitor cadence (0.018 µs). 7 positives, not 46, last ≤ 2 monitor rows; the "resolution-limited" remark is withdrawn.
3. The isotonic duration reference is not a theoretical ceiling.

## 6. Claims (positive / null / incomplete)

**Positive (DEV, pre-registered):**
- H1: T/S beyond depth with identical upstream.
- H6: log h in the classifier.
- Sequential PRIMARY BETTER, with FEWER simulations vs ATSCF and E1 on both targets.

**Null:**
- the SHQ upstream as the source of the gain (H2);
- the E1 probability map over all paths (H3);
- the log-h emulator mean (H7);
- both cross-fit remedies;
- the η-straddle selector (WORSE);
- the BA margin;
- no difference vs ATSAPPROX;
- the corner;
- duration (RC19B, not rerun).

**Incomplete / not claimed:**
- physical validation;
- h-specificity beyond the exploratory control;
- a deployable stopping rule;
- SUR with validated joint cross-covariances (not attempted; no joint label + output model).

The claims matrix rows C41–C56 are in `docs/alse/claims.md`.

## 7. Computational accounting

See the table in section 4.3 and `final_report/FINAL.md`. RC20 total CPU is summed in `COMPUTE.md`.

## Files

**Protocols, definitions and decisions:** `PROTOCOL_RC20_STAGE1.md`, `PROTOCOL_RC20_FINAL.md`, `MODEL_DEFINITIONS_RC20.md`, `src/rc20_decisions.py`.

**Stage 1 and pilot:**
- `stage1/` (STAGE1.md, metrics, AULC, contrasts, factorial, reliability);
- `stage1_export/` (float32 per-budget predictions + acceptance; the paid paths are those of `opus_rc19b/export_final/paths_final.csv.gz`);
- `pilot/`.

**Sequential stage:**
- `final_report/` (FINAL.md, verdicts, metrics, endpoints, reliability, matched by-products);
- `final_export/` (float32 predictions, `paths.csv.gz`, acceptance PASS).

**Figures and viewer:**
- figures: `figures/fig_rc20_stage1.png`, `figures/fig_rc20_final.png`;
- viewer: `viewer/rc20_boundary_view.html`. One learner per view (repeat 19, fold 1): the candidate and SHQ_ATS on the SAME paid path, the controls on their own paths; refit vs recorded ≤ 3e-8.

**Repairs:** `repairs/`.
