# RC22 — robustness, necessary ingredients and one acquisition test for the current Keyhole learner (Opus, 2026-10-21)

**Evidence label: DEV.** These are new partitions of the 541 inspected simulations. They are stability and generalisation stress tests, not physical validation.

**Programme:** own 24-hour clock, started 13:48:07 UTC, cap 2026-10-22 13:48:07 UTC. Work finished 16:45 UTC and used 4.13 CPU-h on ≤ 2 single-thread workers. Astra's share was released and never used. Local commits only.

**Freezes and rules:**
- F1 before any outcome: `PROTOCOL_RC22.md`, `freeze/RC22_F1_MANIFEST.json`.
- Decision rules applied to the matched tables, then F2 before any acquisition outcome: `PROTOCOL_RC22_ACQ.md`, `freeze/RC22_F2_MANIFEST.json`.
- No gate was overridden.

---

## Türkçe kısa açıklama (önce)

**Tek hüküm: Model sadeleşti ve güçlendi; yeni sorgu seçicisi başarısız (DEV = aynı 541 simülasyonun yeni bölmeleri, fiziksel doğrulama değil).**

Kullandığım düz adlar:
- **referans:** öğrenilmiş düzenlileştirmeli fizik sınıflandırıcısı + margin (PHR_NRMAP + margin);
- **sabit cezalı kontrol:** fizik sınıflandırıcısı + margin (SHQ_ATS_H + margin);
- **derinlik Gauss-süreci modeli + straddle:** E1 + straddle;
- **yeni sadeleştirilmiş model:** yalnız log h ve tahmini derinlikle aynı öğrenilmiş düzenlileştirme (HA_LR).

Ölçütler:
- **Dengeli doğruluk:** iki sınıfın doğru tanınma oranlarının ortalaması.
- **Erken öğrenme:** 8–24 ödenmiş simülasyon aralığındaki ortalama.

**1) Mevcut model sağlam mı, hangi koşullarda?**

- **Başlangıç değişince:**
  - Rastgele 8 noktalı başlangıçta referans çalışmaya devam ediyor.
  - Sabit cezalı kontrole göre olasılık üstünlüğü küçülüyor (erken olasılık kaybı (log-loss) −0.018, 6/8; artık "daha iyi" sayılmıyor).
  - Dengeli doğruluk 0.95 hedefi için referans 5.75 daha fazla simülasyon istiyor.
- **Kümelenmiş (çoğu tek sınıflı) başlangıç:**
  - 40 öğrenicinin 30'u tek sınıfla başladı; sınıf keşfi ortalama 0.9, en fazla 6 sorgu sürdü.
  - Bütün modeller belirgin biçimde kötüleşiyor; referans en az kötüleşen.
  - Referans burada kontrolden olasılıkta açıkça iyi (−0.112, 8/8); dengeli doğrulukta +0.014 (7/8, marjın altında).
- **Eksik monitör kanalları (sıcaklık / hız-sıçrama değerlerinin %25 veya %50'si yok):**
  - Referans neredeyse etkilenmiyor (dengeli doğruluk −0.004).
  - Sabit cezalı kontrol belirgin kötüleşiyor (dengeli doğruluk −0.011, log-loss +0.038).
  - Böylece aradaki fark büyüyor: dengeli doğruluk +0.014, 8/8.
  - Kayıt-kalitesi işlemini kapatmak ya da kısa kayıtları çıkarmak hiçbir şeyi değiştirmiyor (≤ 0.001). Üstünlük birkaç tuhaf kayda dayanmıyor.
- **Geometrik dış-değerlendirme (girdi uzayında beş blok; her blok uydurmadan da sorgudan da çekildi):**
  - Bütün modeller ciddi düşüyor (referansın erken dengeli doğruluğu 0.899; standart bölmede 0.928).
  - Dengeli doğruluk 0.95'e hiçbir model ulaşmıyor.
  - Bloklardaki azınlık sınıfı (örneğin 4 iletim koşulu olan blok) kötü tanınıyor.
  - Referans ile kontrol arasındaki fark burada anlamlı değil. Derinlik Gauss-süreci modelinden ise yine iyi.
- **Kısacası:** olasılık üstünlüğü standart bölmede ve eksik kanallarda sağlam. Rastgele başlangıçta zayıflıyor; dış-değerlendirmede kayboluyor. Dengeli doğruluk üstünlüğü hiçbir koşulda kanıtlanmadı.

**2) Hangi bileşenler gerçekten yararlı?** (aynı kayıtlı sorgu yolları üzerinde)

- **h tek başına** (öğrenilmiş düzenlileştirmeyle) erken dengeli doğrulukta en iyisi: 0.938'e karşı referans 0.921 (+0.017, 7/8). Ama olasılıkları tüm bütçede açıkça kötü (+0.029).
- **Tahmini derinlik eklemek** olasılığı belirgin iyileştiriyor (−0.020 erken, −0.038 tüm bütçe; 8/8).
- **Sıcaklık ve hız-sıçrama özetleri**, h + derinlik + öğrenilmiş düzenlileştirme varken artık katkı vermiyor; erken bütçede olasılığı bozuyor (+0.015).
- **Referansın kazancının niteliği:** büyük ölçüde güven ölçeği değişikliği.
  - Logitleri, sabit cezalı kontrolün logitlerinin neredeyse ortak bir katı: eğim 1.35 → 0.98, R² ≥ 0.99.
  - Karar farkı az: adayların %0–4'ünde.
  - Margin sıralaması neredeyse aynı (Spearman ≥ 0.99). Yalnız en iyi aday yakın-eşitliklerden dolayı sık değişiyor.
- **Basit yeniden kalibrasyon bu kazancı bulamıyor:** dürüst kat-dışı tahminlerden öğrenilen tek ölçekli düzeltme olasılığı kötüleştiriyor (+0.020, 0/8). Etiketlerden öğrenilen düzenlileştirme gerekli.

**3) Sorgu seçimi dengeli doğruluğu ya da ödenmiş sorguyu iyileştirdi mi?**

- **Hayır.** Aynı tahmin modeli, aynı karar eşiği ve aynı sabit kapsama takvimiyle (her 5. sorgu en uzak nokta) karşılaştırıldı.
- **Bilgi kazancı seçicisi** (sınıflandırıcı ağırlıkları üzerinden; Houlsby ve ark. 2011):
  - Denetimde anlamlı ve margin'den gerçekten farklıydı.
  - Ama dengeli doğrulukta erken −0.003 (2/8), tüm bütçede −0.008 (0/8).
  - Keyhole duyarlılığını düşürdü (−0.024).
  - Dengeli doğruluk 0.95 hedefini 8 tekrarın 5'inde 60 simülasyonda yakalayamadı (sansürlü).
  - Önceden tanımlı başarı ölçütü geçilmedi.
- **Kapsama takvimi:** margin'e etki etmedi (±0.002).
- **Etiketsiz en-uzak-nokta tasarımı:** daha kötü (log-loss +0.020).

**4) Hangi tek model + seçici kalsın, sınırları ne?**

- **Önerim: sadeleştirilmiş model (log h + tahmini derinlik, öğrenilmiş düzenlileştirme; HA_LR) + margin.**
- Taze tekrarlarda (43–50) referansa göre:
  - erken log-loss −0.013 (7/8, daha iyi);
  - dengeli doğruluk +0.006 / +0.003 (fark yok);
  - dengeli doğruluk 0.95'e −8 simülasyon (6/8, ikincil hedef);
  - 0.93 hedefinde fark yok (−2.0, 4/0/4).
- Sıcaklık ve hız-sıçrama emülatörlerine ihtiyacı yok; bu yüzden o kanalların eksikliğine doğal olarak bağışık.
- **Sınırlar:**
  - Dengeli doğrulukta pratik üstünlük gösterilmedi.
  - Başlangıç ve blok sağlamlığı yalnız referans için test edildi, sadeleştirilmiş model için değil.
  - Dış-değerlendirme ve kümelenmiş başlangıçta bütün modeller kötüleşiyor.
  - Hızlı-tarama köşesi hâlâ zayıf (iletim duyarlılığı ~0.3).
  - Kanıt DEV; fiziksel doğrulama değil.

---

## 1. Intake and corrections adopted

**Starting state:** commit 1eedff2f, reference PHR_NRMAP + margin from RC21B, no live jobs.

**Astra's package** `astra_representation_planning_20261020` was read only; none of her files are copied into the bundle. RC22 adopts three corrections from her context audit (RC21 erratum `opus_rc21/ERRATUM_RC21_20261021.md`):
1. Low nearest-neighbour agreement in the corner is not an impossibility proof.
2. The h-transverse residual does not identify β_h against the physical-summary terms.
3. RC21 targets were applied to fold-pooled curves.

RC22 reports individual learners next to the fold-pooled curves, never calls the corner "irreducible", and blacklists no region.

## 2. Part 1 — robustness of REF (PHR_NRMAP + margin)

### (a) Lawful public-feature-only startups

Same RC21B splits, repeats 35–42. STD is the completed RC21B trajectories, reused; 240 new trajectories.

AULC B8–B24 / B8–B60, fold-pooled, 8 repeats:

| arm | startup | BA B8–B24 | BA B8–B60 | LL B8–B24 | LL B8–B60 | sims to BA ≥ 0.93 | learners attaining own BA ≥ 0.93 |
|---|---|---|---|---|---|---|---|
| REF | STD | 0.9283 | 0.9463 | 0.1912 | 0.1459 | 16.4 | 40/40 |
| H | STD | 0.9253 | 0.9452 | 0.2211 | 0.1582 | 16.75 | 39/40 |
| E1RAW / E1CAL | STD | 0.910 / 0.890 | 0.937 / 0.927 | 0.378 / 0.318 | 0.243 / 0.210 | 24.25 / 25.4 | 37 / 36 |
| REF | RAND8 | 0.9254 | 0.9448 | 0.1814 | 0.1398 | 17.6 | 38/40 |
| H | RAND8 | 0.9212 | 0.9443 | 0.1995 | 0.1461 | 19.0 | 37/40 |
| REF | LOCAL8 | 0.8918 | 0.9349 | 0.5449 | 0.2555 | 19.4 | 39/40 |
| H | LOCAL8 | 0.8781 | 0.9289 | 0.6566 | 0.2975 | 20.0 | 38/40 |
| E1RAW / E1CAL | LOCAL8 | 0.850 / 0.841 | 0.916 / 0.910 | 0.912 / 0.725 | 0.435 / 0.350 | 27.75 / 29.25 | 38 / 35 |

REF − H verdicts:

| startup | LL B8–B24 | BA B8–B24 | BA ≥ 0.95 spend | LL ≤ 0.20 spend |
|---|---|---|---|---|
| STD | −0.030 (8/8) BETTER | +0.003 ND | +0.9 ND | −3.75 FEWER |
| RAND8 | −0.018 (6/8) ND | +0.004 ND | **+5.75 (1/0/7) MORE** | −3.5 FEWER |
| LOCAL8 | −0.112 (8/8) BETTER | +0.014 (7/8, below margin) ND | | |

LOCAL8 notes:
- 30/40 starts were one-class; class discovery took 0.93 queries on average (max 6), counted in every budget.
- Every arm is WORSE than with STD (REF BA B8–B24 −0.037, 0/8).
- REF degrades least.
- REF − E1 is BETTER in LL in every startup, and in BA B8–B24 vs E1CAL in every startup.
- REF needs FEWER simulations than both E1 arms to BA ≥ 0.93 in every startup.

### (b) Geometry blocks (extrapolation)

k-means on the public log inputs, fixed before any outcome. Each block is withheld from fitting and querying in turn; 8 startup seeds; 120 trajectories.

| block | n | Keyhole / conduction | median P (W), VX (m/s), LS (µm) | share outside the pool's coordinate box |
|---|---|---|---|---|
| 1 | 149 | 1 / 148 | 203, 0.74, 75 | 0.00 |
| 2 | 88 | 84 / 4 | 390, 0.47, 45 | 0.73 |
| 3 | 91 | 0 / 91 | 131, 0.78, 53 | 0.06 |
| 4 | 118 | 101 / 17 | 378, 0.54, 44 | 0.00 |
| 5 | 95 | 11 / 84 | 168, 0.31, 65 | 0.04 |

Median distance to the pool is 0.82–1.16, against 0.33–0.37 between pool neighbours: every block is extrapolation. Block 2 is the strongest case (73 % outside the box).

Pooled over the 5 blocks per seed (all 541 runs predicted once):

| arm | BA B8–B24 | BA B8–B60 | LL B8–B24 | LL B8–B60 |
|---|---|---|---|---|
| REF | 0.899 | 0.913 | 0.252 | 0.238 |
| H | 0.889 | 0.909 | 0.280 | 0.239 |
| E1RAW | 0.866 | 0.901 | 0.407 | 0.301 |
| E1CAL | 0.839 | 0.893 | 0.385 | 0.294 |

Verdicts:
- REF − H: BA +0.010 (5/8), LL −0.028 (6/8) and −0.001 (4/8); all NOT DIFFERENT.
- REF − E1: BETTER.

Target attainment:
- BA ≥ 0.93 was confirmed by REF in 6/8 seeds (mean 27 sims) and by H in 6/8 (47 sims).
- BA ≥ 0.95 was never reached.

Per block, individual learners (BA undefined for one-class blocks):
- **Minority-class recall is poor.** Block 2's 4 conduction runs: REF 0.16–0.28. Block 4's 17 conduction runs: REF 0.23–0.43, E1CAL 0.51–0.71, H 0.32–0.46. Block 1's single Keyhole: REF 0.13–0.63, H 0.38–1.0.
- **Majority classes are recognised.** Block 3 conduction 1.00; block 2 and 4 Keyhole ≥ 0.94.

This is a stated failure of extrapolation for every learner, not a tuning target.

### (c) Missing monitor channels and record quality

Matched RC21B REF paths; paid T / S channels only; labels and depth untouched. Δ vs the REAL condition, B8–B24:

| condition | REF ΔBA | REF ΔLL | H ΔBA | H ΔLL | REF − H BA | REF − H LL |
|---|---|---|---|---|---|---|
| REAL | – | – | – | – | +0.006 (6/8) | −0.032 (8/8) |
| MCAR25 | −0.004 | +0.006 | **−0.011** | **+0.038** | **+0.014 (8/8)** | −0.064 (8/8) |
| MCAR50 | −0.003 | +0.008 | **−0.010** | **+0.038** | **+0.014 (8/8)** | −0.062 (8/8) |
| QOFF | 0.000 | 0.000 | 0.000 | 0.000 | +0.006 | −0.032 |
| SHORTDROP | +0.001 | −0.001 | +0.002 | 0.000 | +0.006 | −0.033 |

- Over B8–B60, REF's LL rises +0.013 under MCAR50 (material, but small).
- The REAL condition reproduces RC21B within 3e−8.

## 3. Part 2 — necessary ingredients (identical saved paid prefixes; 80 RC21B paths × 8 budgets)

| construction | BA B8–B24 | LL B8–B24 | BA B8–B60 | LL B8–B60 |
|---|---|---|---|---|
| HONLY_LR (log h only, learned regularisation) | **0.9380** | 0.2096 | **0.9409** | 0.2034 |
| HA_LR (log h + predicted depth) | 0.9309 | **0.1898** | 0.9402 | **0.1653** |
| PHR_NRMAP (REF: + temperature + spike) | 0.9214 | 0.2050 | 0.9343 | 0.1746 |
| SHQ_ATS_H (fixed C = 1) | 0.9166 | 0.2352 | 0.9313 | 0.1946 |
| SHQ_ATS_H_RECAL (honest scalar recalibration) | 0.9139 | 0.2549 | 0.9290 | 0.2121 |

Matched contrasts (MATERIAL iff |Δ| ≥ 0.010 and ≥ 7/8):

| contrast | BA B8–B24 | LL B8–B24 | LL B8–B60 |
|---|---|---|---|
| HONLY_LR − REF | +0.017 (7/8) MATERIAL | +0.005 | +0.029 MATERIAL HARM |
| HA_LR − REF | +0.0095 (7/8) | −0.015 (7/8) MATERIAL | −0.009 |
| depth beyond h: HA_LR − HONLY_LR | −0.007 (1/8) | −0.020 (8/8) MATERIAL | −0.038 (8/8) MATERIAL |
| T, S beyond h + depth: REF − HA_LR | −0.0095 | +0.015 MATERIAL HARM | +0.009 |
| REF − SHQ_ATS_H | +0.005 (6/8) | −0.030 (8/8) MATERIAL | −0.020 (8/8) MATERIAL |
| RECAL − SHQ_ATS_H | −0.003 | +0.020 (0/8) MATERIAL HARM | +0.018 MATERIAL HARM |

**Scale analysis** of logit(PHR_NRMAP) on logit(SHQ_ATS_H), over the candidates of every state (median by budget, B8 → B60):

| quantity | B8 → B60 |
|---|---|
| slope | 1.35 → 0.98 |
| intercept | −0.09 to +0.02 |
| R² | 0.991 → 0.999 |
| candidates with a different decision | 3.6 % → 0.0 % |
| Spearman of the margin scores | 0.988 → 0.996 |
| same top-1 margin choice | 5 % → 71 % (near-ties) |
| top-5 overlap | 0.17 → 0.84 |

The recalibration coefficient c is 0.90–1.02 (median a ≈ 0). Honest out-of-fold predictions of the complete pipeline are noisier than its deployed predictions, so the recalibration shrinks the probabilities instead of sharpening them.

Conclusions:
- The RC21B gain is close to a confidence rescaling with an almost unchanged decision boundary.
- Learned regularisation recovers that rescaling; honest scalar recalibration cannot.
- These are predictive attributions, not causal laser physics.

## 4. Part 3 — acquisition

### Audit (matched states)

PHR_NRMAP exposes:
- 16 posterior weights;
- per configuration, a Laplace latent mean and variance given the PLUG-IN emulator features.

Upstream emulator uncertainty is not propagated.

| criterion | BALD_LAP (classifier-weight + grid information) | BALD_GRID (grid disagreement only, coherent with the mixture) |
|---|---|---|
| information / entropy ratio (median) | 0.25 | 0.06 |
| collapse (states below 1e−6) | none | none |
| top-1 differs from margin | 97.5 % of states | 97.7 % |
| median Spearman with margin | 0.25 | 0.65 |
| top-1 differs from SHQ_ATS_H eta-straddle (RC20) | 95 % | 93 % |
| Monte Carlo reference / direct formula | within MC error | 1e−15 |
| extra CPU per step | 0.03 s | – |

- Both passed; BALD_LAP was first in the registered order.
- BALD_LAP's choices sat at a median p of 0.35–0.54 at small budgets and 0.10 at B60, and it picked far fewer evaluator-defined corner runs than margin.

### Sequential comparison

Fresh repeats 43–50; predictive model PHR_NRMAP and cutoff 0.5 fixed; 200 trajectories.

| arm | BA B8–B24 | BA B8–B60 | Keyhole recall B8–B60 | conduction recall B8–B60 | LL B8–B24 | sims to BA ≥ 0.93 | sims to BA ≥ 0.95 (confirmed) | learners attaining own BA ≥ 0.93 |
|---|---|---|---|---|---|---|---|---|
| A1 margin (REF) | 0.9289 | 0.9434 | 0.936 | 0.951 | 0.1909 | 17.75 | 39.1 (7/8) | 40/40 |
| A2 margin + coverage | 0.9267 | 0.9430 | 0.936 | 0.950 | 0.1915 | 18.75 | 39.25 (8/8) | 39/40 |
| A3 BALD_LAP + coverage | 0.9234 | 0.9348 | **0.912** | **0.958** | 0.1902 | 19.25 | 51.7 (**3/8**) | 35/40 |
| A4 maximin (label-free) | 0.9225 | 0.9374 | 0.929 | 0.946 | 0.1971 | 20.75 | 38.7 (3/8) | 38/40 |
| A5 HA_LR + margin | **0.9350** | **0.9465** | 0.941 | 0.952 | **0.1781** | **15.75** | **34.25 (8/8)** | 40/40 |

**Primary A3 − A2:**

| endpoint | result | verdict |
|---|---|---|
| BA-AULC B8–B24 | −0.0033 (2/8) | NOT DIFFERENT |
| sims to BA ≥ 0.93 | +0.5 (3/3/2) | NO CLEAR DIFFERENCE |
| BA-AULC B8–B60 | −0.0082 (0/8) | NOT DIFFERENT at margin 0.010 |
| **SUCCESS** | | **false** |
| secondary: BA ≥ 0.95 | +20.1, 5 of 8 censored | MORE SIMULATIONS |

**Secondary contrasts:**

| contrast | result |
|---|---|
| A2 − A1 (coverage) | BA −0.002 / −0.0004, spend +1.0: no effect |
| A4 − A1 (label-free maximin) | BA −0.006, LL B8–B60 +0.020: WORSE |
| A5 − A1, LL B8–B24 | −0.0128 (7/8): BETTER |
| A5 − A1, BA | +0.0061 (5/8) / +0.0031 (6/8): NOT DIFFERENT |
| A5 − A1, sims to BA ≥ 0.93 | −2.0 (4/0/4): no clear difference |
| A5 − A1, sims to BA ≥ 0.95 | −8.0 (6/2/0; A1 censored once): FEWER (secondary target) |

**Discovery vs learning (evaluator-side):**

| arm | first corner query | first corner conduction hit | corner share of B60 |
|---|---|---|---|
| all arms | 3.5 (startup) | 8.5–11 | – |
| margin | | | 0.40 |
| coverage | | | 0.30 |
| BALD + coverage | | | 0.20 |
| maximin | | | 0.07 |

Fewer corner queries did not buy accuracy elsewhere: BALD lost Keyhole recall on the rest of the boundary.

**CPU:** decision CPU 0.43–0.50 s per step in every arm.

## 5. What is positive, null, incomplete, proposed

**Positive (DEV):**
- PHR_NRMAP is robust to missing T / S channels while SHQ_ATS_H is not (BA gap +0.014, 8/8, under MCAR).
- PHR_NRMAP's probability advantage holds under STD and LOCAL8 startups.
- PHR_NRMAP beats E1 + straddle under every startup and blocks: LL, BA vs E1CAL early, fewer sims.
- Depth adds probability information beyond h (8/8).
- HA_LR is at least as good as PHR_NRMAP, matched and prospective (LL −0.013 B8–B24, 7/8; fewer sims to BA ≥ 0.95).
- The REF gain is close to a logit rescaling that learned regularisation finds and honest recalibration does not.

**Null:**
- BALD_LAP + coverage vs margin + coverage: no BA or query gain; harm to Keyhole recall and BA ≥ 0.95.
- The coverage schedule had no effect.
- Maximin was worse.
- Temperature and spike summaries are not useful after h + depth + learned regularisation.
- Honest scalar recalibration is harmful.
- REF − H in blocks: no difference.
- REF's probability gain under RAND8 is below the margin, and REF needs MORE simulations to BA ≥ 0.95 there.

**Qualified:**
- HONLY_LR has the best early BA on matched paths (+0.017) but materially worse probabilities.
- The HA_LR BA gain is not significant.

**Incomplete / not tested:**
- Startup and block robustness of HA_LR itself.
- Any selector using upstream emulator uncertainty, which would need its joint law (Astra).
- Physical validation (owner decision).

**Proposed (not run):**
- A prospective HA_LR robustness check (RAND8 / LOCAL8 / blocks).
- Before any further selector work, a study of whether minority-class errors in extrapolated regions can be reduced by new information (simulations) rather than by selection.

## 6. Files

**Protocols and freezes:**
- `PROTOCOL_RC22.md`, `PROTOCOL_RC22_ACQ.md`
- `freeze/RC22_F1_MANIFEST.json`, `freeze/RC22_F2_MANIFEST.json`
- `RC22_VALIDATION.json`, `ingr/DECISIONS.json`

**Equations appendix:** `MODEL_DEFINITIONS_RC22.md`.

**Part reports:**
- `ingr/INGREDIENTS.md`
- `miss/MISSING_CHANNELS.md`
- `start/STARTUPS.md`
- `block/BLOCKS.md`
- `acq/ACQUISITION.md`
- Each has CSVs for every metric, contrast, endpoint and individual learner.

**Exports:**
- `{start,block,acq}/export/predictions_f32.npz`: per budget and learner.
- `{start,block,acq}/export/paths.csv.gz`: every paid ID with its rule (startup / path / margin / coverage / BALD_LAP / maximin).
- `{ingr,miss}/export/matched_states_f32.npz`: test predictions and candidate probabilities / selector scores.
- Acceptance PASS (bit-identical metric recomputation).

**Other:**
- Figures: `figures/fig_rc22_{robustness,ingredients,scale,acquisition}.png`.
- Compute: `COMPUTE.md`.
- Portable bundle: `review_bundle/RC22_REVIEW_BUNDLE.zip` with `BUNDLE_MANIFEST.json`. It contains source, protocols, manifests, tables, exports and figures; no Astra files.
