# RC19B — RC19 continuation: improving the pooled learner and locating the gain (Opus, 2026-10-19/20)

**Evidence label: DEV.** All 541 simulations were inspected earlier. The final arms ran on fresh splits (repeats 11–18) of the same runs, frozen before any final run: protocol `PROTOCOL_RC19B.md`, manifest `final/RC19B_FINAL_MANIFEST.json`, commit 8299437f.

Every budget counts total revealed simulations, startup included. Ledger rows: RC19B-REPAIR, -DEV-REPLAY, -SELECT-RULES, -DESIGN, -FREEZE, -RESULTS.

---

## Türkçe açıklama (önce)

**Tek hüküm: KISMİ İYİLEŞME (DEV).**
- Dürüst çapraz-uyumlu fiziksel sınıflandırıcı, kalibre edilmiş E1'den daha iyi Keyhole olasılığı verir. Önceden ilan edilen birincil karşılaştırma BETTER: log-loss −0.030, 8 tekrarın 7'sinde.
- Kazancın büyük ve sağlam kısmı sıcaklık ve hız-sıçrama tahminlerinden gelir; olasılık eşlemesi daha küçük ve yola bağlı bir paydır.
- Karar düzeyinde (BA) fark yoktur.
- Süre darboğazı çözülmedi: hurdle modeli daha kötü, darboğaz-farkında sorgu etkisiz.

**1. Ne onarıldı, herhangi bir sonuç değişti mi?**
- **A.** "Hedefe kaç simülasyonda ulaşıldı" sütunu teyit çiftinin ilk bütçesini gösteriyordu; gerçek harcama b + 4'tür. Düzeltilmiş değerler:
  - bölge SHQ + straddle 27.1 (25–30);
  - etiket PHYSCF 17.9, E1 23.8, G3 28.3.
  
  İlk-ulaşma bütçesi artık ayrı raporlanıyor. Eşleştirilmiş farklar değişmedi (−5.875).
- **B.** float16 dışa aktarımlar kayıplıydı: etiket BA'da 2.968 hücrenin 44'ü, en çok 0.035. Rapor CSV'leri bundan etkilenmemişti. float32 yeniden dışa aktarıldı; her metrik hücresi dışa aktarımdan yeniden hesaplandı, PASS.
- **C.** RC19'daki "çapraz uyum" aslında tam-veri hiperparametreli, yaklaşık bir LOO'ydu. Adı ATSAPPROX oldu; dürüst K-katlı ATSCF eklendi.
- **D.** Ortak 8-çıktı tamamlanması artık her kol için verildi: SHQ + RANDOM 7/8, M0Q + MOIVR 5/8, M0Q + RANDOM 2/8, SHQ + MOIVR 1/8, MAXIMIN kolları 0/8.
- **E.** RC19'da rapor kodu sonuçlardan önce commit edilmişti ama çalışma anında hash ile denetlenmiyordu. RC19B'de değerlendirme, rapor ve dışa aktarım kodu da donduruldu.
- **F.** RC19'un 3B görünümü beş farklı katlama öğrenicisini karıştırıyordu. Aynı bağlantıda yeniden etiketlendi; ayrıca tek-öğrenici görünümü eklendi.
- **Sonuç:** hiçbir RC19 hükmü değişmedi. Mutlak harcama sayıları +4 kaydı ve "çapraz uyum" iddiası geri çekildi.

**2. Görev başına pratik model ve sorgu stratejisi** (hepsi DEV):

| görev | öneri | kanıt |
|---|---|---|
| hız-sıçrama bölgesi | **SHQ + straddle** (RC19, değişmedi) | BA ≥ 0.95, 8/8 tekrarda ortalama 27 simülasyonda teyit |
| Keyhole, olasılık gerekiyorsa | **ATSCF + margin** (dürüst, K = 10) | kalibre E1'e göre log-loss −0.030 (7/8); BA ≥ 0.93 ortalama 20.4 simülasyonda (E1: 24.5) |
| Keyhole, yalnızca karar (p = 0.5) | **E1 + straddle** | BA aynı (0.937'ye karşı 0.937); daha basit |
| 8 fiziksel çıktı, sabit hedeflerle birlikte | **M0Q + MOIVR**, kendi GP süre tahminiyle | ortak hedef 7/8 tekrarda ortalama 49.7 simülasyonda; SHQ + RANDOM'a göre −23.5 simülasyon (7/8; önceden ilan edilmiş D3, BETTER) |
| spike süresi | hurdle **kullanılmamalı**; doğrudan GP kalmalı | hurdle 4 kolun 3'ünde WORSE |

- Yaklaşık ATSAPPROX + margin olasılıkta en iyisidir (log-loss 0.157) ve en hızlı teyit edendir (18.0 simülasyon). Ancak bir çapraz uyum değildir (bkz. 3).
- Ortak tamamlanma kırılgandır. RC19'da (tekrar 3–10) sıra tersti: SHQ + RANDOM 7/8, M0Q + MOIVR 5/8. 16 tekrar birlikte 12/16'ya karşı 11/16 (keşifsel). Sebep: ortak hedef her kolda tamamen süreye bağlıdır, süre de hedefinin (0.60) hemen çevresinde dolaşır.

**3. Fiziksel sınıflandırıcı mı, kalibre E1 mi, yoksa esas olarak olasılık eşlemesi mi?**

**Cevap:** iki etki birlikte var, ama büyük ve sağlam olan fiziksel bilgidir.
- Önceden ilan edilen birincil karşılaştırma **BETTER (DEV)** çıktı: dürüst ATSCF, kalibre E1'den daha iyi olasılık verir. Log-loss AULC −0.030 ± 0.007; 8 tekrarın 7'sinde daha düşük.
- **Ayrıştırma** (taze yollarda, aynı ödenmiş önekler üzerinde, keşifsel):
  - **Sadece eşleme:** E1'i dürüst bir küçük-örnek haritasıyla düzeltmek log-loss'u yaklaşık 0.024 düşürür. Bu etki yalnızca E1'in kendi straddle yolunda tutarlıdır; margin yollarında kaybolur ya da tersine döner. Bedeli de vardır: BA 8/8 tekrarda biraz düşer (−0.007).
  - **Derinlik + lojistik eşleme** (DEPTHCF), kalibre E1 ile aynıdır (her metrikte fark ≈ 0).
  - **Sıcaklık ve hız-sıçrama tahminlerini eklemek** (ATSCF − DEPTHCF), beş yol tipinin hepsinde log-loss'u 0.029–0.043 düşürür (8/8). Bu etki ne yola ne eşlemeye bağlıdır.
  - Ham E1'e göre toplam log-loss kazancı −0.055'tir. Kabaca %45'i eşleme, %55'i fiziksel özetlerdir.
- **Karar düzeyi:** BA farkı hiçbir yapıda pratik eşiği (0.02) geçmez. Kazanç olasılık kalitesindedir.
- **Yaklaşık sürüm dürüst sürümden hâlâ iyidir:**
  - Brier +0.005, 0/8 → WORSE; log-loss +0.019, 1/8, marjın hemen içinde.
  - Fark küçük bütçelerde yoğunlaşır: B16'da BA 0.914'e karşı 0.936. B24'te kapanır.
  - **Mekanizma (tek-faktör testi):** katlama boyutu farkın üçte birini açıklar (K = 5 → 10 → LOO). Kalan kısım, her katlamada hiperparametre ve normalizasyonun yeniden kestirilmesinden gelir; yaklaşık sürüm bunu yapmaz.
  - İkisi de yalnızca ödenmiş veriyi kullanır, ikisi de uygulanabilir. Dürüst olan savunulabilir kurulumdur; yaklaşık olanın avantajı gerçektir ama "çapraz uyum" değildir.

**4. Eşit maliyette iyileşmeler ve çözülmeyenler**
- **İyileşmeler** (eşit toplam simülasyonda):
  - Keyhole olasılık kalitesi: kalibre E1'e göre −0.030 (BETTER), ham E1'e göre −0.055 (8/8, BETTER), derinlik-tek sınıflandırıcıya göre −0.030 (7/8, BETTER).
  - BA ≥ 0.93 teyidi daha erken: ATSCF 20.4, E1 24.5–25.3 simülasyon (5 tekrarda daha az, 1'de eşit, 2'de fazla; keşifsel).
  - Fiziksel çıktılar: M0Q + MOIVR, ortak hedefe SHQ + RANDOM'dan 23.5 simülasyon daha az harcamayla ulaşır (BETTER).
- **Çözülmeyenler:**
  - **(a) Hızlı-tarama köşesi** (12 NEW iletim koşusu): her kolda iletim duyarlılığı B60'ta ≤ 0.49. Fiziksel sınıflandırıcılar burada en kötü: 0.33–0.35. Margin kolları bu koşuların ~10 adayından ~8'ini satın aldığı halde bu böyle; yani sorun keşif eksikliği değil, Keyhole komşuları arasında yalıtılmış istisnalar.
  - **(b) Spike süresi** (aşağıda 5).
  - **(c) Dürüst çapraz uyumun küçük-n açığı.**
  - **(d)** BA düzeyinde hiçbir yapı E1 + straddle'ı pratik marjla geçmiyor.

**5. Süre modeli ortak tamamlanmayı iyileştirdi mi?**

**Hayır.**
- **D1** (aynı yollar, süre R²-AULC'si, hurdle − kendi GP):

  | kol | fark (iyi yönde tekrar) | hüküm |
  |---|---|---|
  | SHQ + RANDOM | −0.077 (0/8) | WORSE |
  | SHQ + MOIVR | −0.074 (1/8) | WORSE |
  | SHQ + MOIVRB | −0.097 (0/8) | WORSE |
  | M0Q + MOIVR | −0.013 (4/8) | NOT DIFFERENT |

- **D2** (ortak tamamlanma, hurdle'a karşı kendi GP):

  | kol | hurdle | kendi GP | hüküm |
  |---|---|---|---|
  | SHQ + RANDOM | 2/8 | 4/8 | WORSE |
  | M0Q + MOIVR | 5/8 | 7/8 | WORSE |
  | SHQ + MOIVRB | 0/8 | 3/8 | WORSE |
  | SHQ + MOIVR | 2/8 | 1/8 | açık değişim yok |

- **D3** (darboğaz-farkında sorgu): MOIVRB süreye en yüksek ağırlığı verdi (≈ 0.45; diğer çıktılar 0.05–0.2), ama süre R²'sini yükseltmedi (B80'de 0.586). Ortak tamamlanma 3/8; SHQ + RANDOM'a göre harcama farkı yok (NOT DIFFERENT).
- Sıfırlar ölçüm hatası değil, gerçek "eşik üstü satır yok" sonuçlarıdır (denetim: 484 geçerli değerin 234'ü). İki-parçalı model, pozitif kısmı verinin yarısıyla öğrendiği için bu veri boyutunda gürültü ekliyor; doğrudan GP sıfır/pozitif karışımını zaten düzgün ortalıyor. Bu bir yorumdur.
- Gerçek sıçrama oranı bilinse bile süre R² tavanı 0.59–0.75'tir (betimsel). 0.60 hedefi B60–B80 civarında sınırdadır.

**6. Önceden belirlenmiş, keşifsel ve mevcut olmayan iddialar**
- **Önceden belirlenmiş** (dondurma 8299437f, taze tekrarlar 11–18, DEV):
  - Keyhole PRIMARY: BETTER.
  - İkinciller: ATSCF − ham E1 (log-loss) BETTER; ATSCF − DEPTHCF (log-loss, Brier) BETTER; E1CAL − E1RAW (log-loss) BETTER; ATSCF − G3 (log-loss, Brier) BETTER; ATSAPPROX − E1RAW (log-loss, Brier) BETTER; ATSCF − ATSAPPROX (Brier) WORSE. Bütün BA karşılaştırmaları NOT DIFFERENT.
  - Süre: D1–D3 yukarıda.
- **Keşifsel** (hüküm yok, çoklu-test düzeltmesi yok):
  - aynı-yol ayrıştırması;
  - harcama farkları;
  - güvenilirlik kutuları;
  - yol tanısı ve köşe analizi;
  - geliştirme tekrar oynatmaları ve K mekanizması;
  - süre tavanı;
  - RC19 + RC19B birleşik tamamlanma.
- **Mevcut değil / iddia edilmiyor:**
  - yeni fiziksel simülasyon, gerçek-veri Stage A, C4;
  - uygulanabilir bir durdurma kuralı (hedefler çevrimdışı ölçütlerdir);
  - ATSAPPROX için "çapraz uyum";
  - RC19 görüntüsünün katlama-başı okuması;
  - Astra'nın TEST sonucu (incelenmedi).

**7. Ne çalışıyor, neye dokunulmadı, sırada ne var**
- **Çalışan:** Opus tarafında hiçbir şey.
  - Kuyruk boşta (çalıştırıcı PID 17384) ve son tarihte (2026-10-20 08:41:20 UTC) kendiliğinden durur.
  - Bütün RC19B işleri tamam, 0 hata: geliştirme 120 + 40 + 120; duman 45; final 200 + 160.
  - Toplam 5.97 CPU-saat.
- **Dokunulmayan:**
  - Astra'nın çalışması, çalışma alanı, kodu ve 2 iş parçacığı (TEST: 22:01 UTC'de 9.529 tamam, 694 bekliyor);
  - ana dal, simülatör, bulut, dış mesajlar, C4, gerçek-veri Stage A; BA_RISK iptal.
- **Sırada:** kuyrukta bekleyen iş yok. Öneriler (her biri ayrı bir ön-kayıt gerektirir):
  - köşe için hedefli bir yerel model ya da özellik;
  - dürüst çapraz uyumda katlamalar arası hiperparametre paylaşımı;
  - süre için tek-çıktı lengthscale'li (M0Q) bir model ile SHQ'nun erken avantajını birleştiren karma.

---

## 1. What ran

| stage | units | failures | output |
|---|---|---|---|
| repairs from caches (no refit) | – | – | `repair/`, `export/`, erratum `../opus_pooled/ERRATUM_RC19_20261019.md` |
| matched-path replay K = 5 (RC19 final paths r3–10) | 120 | 0 | `KEYHOLE_REPLAY.md` |
| fold-size factor K = 10 / LOO | 40 | 0 | `KEYHOLE_REPLAY_K.md` |
| duration hurdle replay | 120 | 0 | `DURATION_REPLAY.md`, `DURATION_ZERO_AUDIT.json` |
| acceptance (K = 5, final configuration) | 9 runs | 0 | `RC19B_VALIDATION.json`, `RC19B_VALIDATION_FINAL.json` (PASS) |
| smoke test (seen repeat 1) | 45 | 0 | `report_smoke/`, `export_smoke/` |
| **final Keyhole (r11–18)** | 200 | 0 | `report/KEYHOLE_FINAL.md`, `KEYHOLE_FINAL_DECOMPOSITION.md` |
| **final physical outputs (r11–18)** | 160 | 0 | `report/DURATION_FINAL.md` |

## 2. Repairs (no learner refitted)

| finding | what was wrong | corrected | did a conclusion change? |
|---|---|---|---|
| A | "queries to the level" printed the first budget b of the confirmed pair | spend = b + 4: region SHQ + STRADDLE 27.125 (25–30); label PHYSCF_ATS 17.875, E1 + straddle 23.750, G3 28.250; first-qualifying budgets reported separately | no: paired differences unchanged |
| B | float16 label/region exports (label BA 44/2968 cells changed, max 0.0349; log loss up to 0.0659; region 37/3392, max 0.0022) | float32 at every recorded budget; every metric cell recomputed from the export equals the CSVs (max \|Δ\| ≤ 4e-15) | no: the CSVs came from float32 caches |
| C | "cross-fitted (LOO)" PHYSCF used full-fit hyperparameters and normalisation | renamed ATSAPPROX; honest K-fold ATSCF added | the RC19 label numbers stand but belong to an approximation |
| D | joint completion named only two arms | SHQ + RANDOM 7/8, M0Q + MOIVR 5/8, M0Q + RANDOM 2/8, SHQ + MOIVR 1/8, MAXIMIN 0/8 | no |
| E | "the report generator is part of the freeze" | committed before results, never hash-checked at run time; export, figures, viewer and AX report written after the runs | no; RC19B's freeze hashes eval, report and export code |
| F | the RC19 3D view mixes five fold learners | relabelled in place (same link, version 2); new single-learner view | no |

## 3. Development (seen RC19 final repeats 3–10; chooses the design, supports no final claim)

**Every construction on the same paid prefixes** (K = 5; AULC B8–B60):

| construction | BA, E1-straddle paths | LL, E1-straddle | BA, approximate-margin paths | LL, approximate-margin | BA, label-free paths | LL, label-free |
|---|---|---|---|---|---|---|
| E1RAW | 0.935 | 0.254 | 0.938 | 0.231 | 0.926 | 0.313 |
| E1CAL | 0.922 | 0.224 | 0.929 | 0.279 | 0.922 | 0.221 |
| DEPTHCF | 0.913 | 0.231 | 0.927 | 0.236 | 0.907 | 0.244 |
| ATSCF (K = 5) | 0.926 | 0.193 | 0.926 | 0.206 | 0.923 | 0.191 |
| ATSAPPROX | 0.939 | 0.168 | 0.939 | 0.167 | 0.931 | 0.177 |
| G3 | 0.906 | 0.285 | 0.830 | 0.470 | 0.917 | 0.275 |

**Fold-size factor** (mechanism-led, one factor; label-free paths), ATSCF LL-AULC:

| K | LL-AULC |
|---|---|
| 5 | 0.1911 |
| 10 | 0.1870 |
| exact refit-LOO | 0.1863 |
| ATSAPPROX | 0.1772 |

- The pre-registered rule K chose K = 10.
- Larger folds remove about a third of the gap. The rest (+0.009, 0/8) is the per-fold re-estimation of hyperparameters and normalisation.

**Spike duration:**
- 234 of 484 valid values are 0. No zero has spike ratio ≥ 2, so the zeros are genuine "no active row above 2 × median" outcomes; 57 NaN stay missing.
- No hurdle variant beat the arm's own duration GP (−0.04 to −0.085 R²-AULC). Rule V chose QS_RAW.
- Ceiling: an isotonic map from the TRUE spike ratio reaches duration R² of only 0.59 (20 runs) to 0.75 (400).

## 4. Keyhole: final paired adaptive comparison (fresh r11–18; 200 trajectories)

**PRIMARY: ATSCF_MARGIN − E1CAL+straddle, LL-AULC = −0.030 ± 0.007.** Lower in 7/8 repeats; range −0.052 to +0.013. **BETTER (DEV).**

**AULC B8–B60** (mean ± SE over 8 repeats; each arm on its own path):

| arm | BA | Keyhole recall | conduction recall | log loss | Brier | AUC |
|---|---|---|---|---|---|---|
| ATSAPPROX_MARGIN (RC19 approximation) | 0.943 ± 0.001 | 0.935 | 0.952 | **0.157** ± 0.003 | 0.042 | 0.986 |
| ATSCF_MARGIN (honest, K = 10) | 0.937 ± 0.002 | 0.924 | 0.949 | 0.176 ± 0.005 | 0.048 | 0.980 |
| DEPTHCF_MARGIN | 0.931 ± 0.002 | 0.916 | 0.945 | 0.206 ± 0.005 | 0.055 | 0.978 |
| E1CAL+straddle | 0.930 ± 0.004 | 0.919 | 0.941 | 0.206 ± 0.004 | 0.053 | 0.975 |
| E1RAW+straddle | 0.937 ± 0.002 | 0.947 | 0.928 | 0.231 ± 0.007 | 0.051 | 0.981 |
| G3_MARGIN | 0.924 ± 0.004 | 0.911 | 0.938 | 0.264 ± 0.006 | 0.071 | 0.965 |

**Pre-declared secondary verdicts** (margins BA 0.02, LL 0.02, Brier 0.005; ≥ 7/8):
- **BETTER:**
  - ATSCF − E1RAW (LL −0.055, 8/8);
  - ATSCF − DEPTHCF (LL −0.030, 7/8; Brier −0.008, 7/8);
  - E1CAL − E1RAW (LL −0.024, 8/8);
  - ATSCF − G3 (LL −0.088; Brier −0.023; 8/8);
  - ATSAPPROX − E1RAW (LL −0.074; Brier −0.009; 8/8).
- **WORSE:** ATSCF − ATSAPPROX (Brier +0.005, 0/8).
- **NOT DIFFERENT:**
  - every BA contrast;
  - ATSCF − E1CAL Brier (−0.005, 6/8);
  - DEPTHCF − E1CAL (all metrics ≈ 0);
  - ATSCF − ATSAPPROX LL (+0.019, 1/8);
  - E1CAL − E1RAW BA (−0.007, lower in 8/8 but below the margin).
- **RC19 primary C reproduced on fresh repeats:** ATSAPPROX − E1RAW BA +0.006 (7/8), NOT DIFFERENT.

**Matched budgets:**

| arm | BA B16 | BA B24 | BA B40 | BA B60 | LL B16 | LL B24 | LL B60 |
|---|---|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 0.936 | 0.944 | 0.950 | 0.951 | 0.191 | 0.158 | 0.123 |
| ATSCF_MARGIN | 0.914 | 0.944 | 0.948 | 0.952 | 0.244 | 0.166 | 0.129 |
| DEPTHCF_MARGIN | 0.908 | 0.931 | 0.942 | 0.946 | 0.269 | 0.212 | 0.143 |
| E1CAL+straddle | 0.902 | 0.932 | 0.943 | 0.947 | 0.282 | 0.216 | 0.137 |
| E1RAW+straddle | 0.914 | 0.938 | 0.949 | 0.952 | 0.346 | 0.229 | 0.154 |
| G3_MARGIN | 0.890 | 0.926 | 0.940 | 0.952 | 0.381 | 0.301 | 0.157 |

**BA ≥ 0.93, confirmation spend** (b + 4; every arm 8/8 confirmed, none censored):

| arm | mean (median; range) | per repeat |
|---|---|---|
| ATSAPPROX_MARGIN | 18.0 (18; 13–24) | 15, 20, 24, 22, 13, 14, 19, 17 |
| ATSCF_MARGIN | 20.4 (20; 15–27) | 15, 21, 22, 19, 19, 21, 19, 27 |
| E1RAW+straddle | 24.5 (21.5; 19–39) | 20, 26, 39, 19, 23, 20, 29, 20 |
| E1CAL+straddle | 25.3 (23; 19–39) | 19, 26, 39, 19, 33, 19, 27, 20 |
| DEPTHCF_MARGIN | 25.5 (26; 16–35) | 27, 23, 35, 16, 25, 24, 27, 27 |
| G3_MARGIN | 29.5 (26; 21–42) | 27, 25, 42, 35, 21, 21, 25, 40 |

Paired spend (exploratory):

| contrast | mean difference | fewer / equal / more |
|---|---|---|
| ATSCF − E1CAL | −4.9 | 5 / 1 / 2 |
| ATSCF − E1RAW | −4.1 | 5 / 1 / 2 |
| ATSCF − ATSAPPROX | +2.4 | 2 / 2 / 4 |
| ATSAPPROX − E1RAW | −6.5 | 7 / 0 / 1 |

A held-out BA target is an offline benchmark, not a deployable stopping rule.

**Reliability** (slope of the logistic recalibration, mean ± SE; 1 = calibrated):
- E1RAW over-confident: 0.47 ± 0.04 at B16, 0.57 ± 0.02 at B60.
- E1CAL: 0.82 → 1.23.
- ATSCF: 1.67 → 1.16 (ECE 0.079 → 0.024).
- ATSAPPROX: 1.63 → 1.10.
- G3: 2.16 → 1.56.
- Wilson-95 bins containing the mean prediction at B60: ATSAPPROX 8/10, ATSCF 7/10, E1RAW, E1CAL and G3 6/10, DEPTHCF 5/10.

**Fast-scan corner** (12 NEW-batch conduction runs, evaluator-only), conduction recall at B60 with errors out of 96 test cases in brackets:

| arm | conduction recall at B60 (errors / 96) |
|---|---|
| DEPTHCF | 0.49 (49) |
| E1CAL | 0.42 (56) |
| E1RAW | 0.40 (58) |
| G3 | 0.40 (58) |
| ATSCF | 0.35 (62) |
| ATSAPPROX | 0.33 (64) |

- The path diagnostic (`report/PATHS_DIAGNOSTIC.md`): the margin arms pay for about 8 of the roughly 10 corner candidates by B60 (E1S about 4). The failure is therefore not a lack of exploration.

**Secondary at B60:**
- q20 boundary BA 0.77–0.78 for every arm.
- Short-Keyhole capture (of 22): ATSCF 17.5, E1RAW 17.3, ATSAPPROX 16.6, G3 15.9, E1CAL 15.1, DEPTHCF 14.6.

**Matched-path decomposition on the fresh paths** (exploratory; every construction on every arm's own paid prefixes, every 4 budgets), LL-AULC differences:

| on the paths of | ATSCF − E1CAL | ATSCF − DEPTHCF | DEPTHCF − E1CAL | E1CAL − E1RAW | ATSCF − ATSAPPROX |
|---|---|---|---|---|---|
| E1S (straddle) | −0.026 (8/8) | −0.041 (8/8) | +0.015 (2/8) | −0.024 (8/8) | +0.020 (0/8) |
| ATSCF_MARGIN | −0.067 (8/8) | −0.035 (8/8) | −0.032 (8/8) | +0.013 (2/8) | +0.021 (0/8) |
| DEPTHCF_MARGIN | −0.062 (8/8) | −0.029 (8/8) | −0.033 (8/8) | +0.001 (3/8) | +0.019 (0/8) |
| G3_MARGIN | −0.036 (8/8) | −0.035 (8/8) | −0.001 (4/8) | −0.019 (6/8) | +0.017 (0/8) |
| ATSAPPROX_MARGIN | −0.073 (8/8) | −0.043 (8/8) | −0.031 (8/8) | +0.026 (1/8) | +0.022 (0/8) |

On every path type, BA differences between constructions are at most 0.011.

## 5. Physical outputs and the duration bottleneck (fresh r11–18; 160 trajectories)

Fixed RC19 targets: log A, KE, laser, temperature 0.85; spike ratio, etot, npart 0.80; spike duration 0.60. Horizon B80. Consistency of the joint endpoint with the evaluator: 0 mismatches.

| arm | joint by B80, own GP duration | joint spend per repeat | joint with hurdle | duration R²-AULC own / hurdle | duration R² at B80 own / hurdle |
|---|---|---|---|---|---|
| SHQ + RANDOM | 4/8 | 56, 76, –, –, –, 80, 72, – | 2/8 | 0.53 / 0.45 | 0.610 / 0.544 |
| **M0Q + MOIVR** | **7/8** | 44, 40, –, 60, 48, 48, 56, 52 | 5/8 | 0.54 / 0.52 | 0.623 / 0.587 |
| SHQ + MOIVR | 1/8 | –, –, –, 72, –, –, –, – | 2/8 | 0.54 / 0.47 | 0.593 / 0.574 |
| SHQ + MOIVRB | 3/8 | 80, –, –, –, 72, 80, –, – | 0/8 | 0.54 / 0.44 | 0.586 / 0.521 |

**Every one of the 7 other outputs** is confirmed 8/8 in every arm by B40. Joint completion is therefore exactly duration completion.

**Pre-declared verdicts:**
- **D1** (duration R²-AULC, hurdle − own GP, same paths): SHQ + RANDOM −0.077 (0/8) WORSE; SHQ + MOIVR −0.074 (1/8) WORSE; SHQ + MOIVRB −0.097 (0/8) WORSE; M0Q + MOIVR −0.013 (4/8) NOT DIFFERENT.
- **D2** (joint completion): WORSE for SHQ + RANDOM, M0Q + MOIVR and SHQ + MOIVRB; NO CLEAR CHANGE for SHQ + MOIVR.
- **D3** (joint spend with own GP duration vs SHQ + RANDOM; censored = 84 as a lower bound):
  - M0Q + MOIVR −23.5 (7/8) **BETTER**;
  - SHQ + MOIVR +5.0 and SHQ + MOIVRB +4.0, both NOT DIFFERENT.
  - With the hurdle duration (secondary): all NOT DIFFERENT.

**Mechanism notes (exploratory):**
- Bottleneck-aware MOIVRB put the largest weight on duration (≈ 0.45 against 0.05–0.2 for the others) yet did not raise duration R². This is consistent with a duration surface that is noisy given the inputs (the ceiling above), not under-sampled.
- SHQ's shared lengthscales help duration early: R² 0.51 vs 0.39 for M0Q at B16. Duration's own lengthscales (M0Q) reach the 0.60 level more often late: B80 0.623 vs 0.593. This is a hypothesis.
- Across RC19 (r3–10) and RC19B (r11–18), 16 repeats in all, joint completion is SHQ + RANDOM 11/16, M0Q + MOIVR 12/16, SHQ + MOIVR 2/16. The ranking between the first two is not stable.

## 6. Compute cost (single-thread seconds recorded by the units)

**Total RC19B 5.97 CPU-h:** development 1.60, smoke 0.46, final 3.91.

**Per trajectory:**
- Keyhole: ATSCF 48 s; E1S 46 s (both include the all-construction recording); G3 30 s; DEPTHCF 28 s; ATSAPPROX 25 s.
- Outputs: SHQ + MOIVR(B) 66 s; M0Q + MOIVR 32 s; SHQ + RANDOM 11 s.

Full table: `report/COMPUTE_COST.md`.

## 7. Thesis-ready explanation

**Setting.** Every learner starts from the same eight label-free simulations and pays for each further one.

**Two families.**
- **E1** regresses the log melt-pool depth with a Gaussian process. A depth threshold learned from the paid (depth, label) pairs turns the predicted depth into a Keyhole probability.
- **The physical-response classifier (ATS)** learns a logistic decision function on three predicted physical summaries (depth, peak temperature in the T0 window, velocity-spike ratio). Each summary is predicted from the process parameters by a Gaussian process.

**Cross-fitting.**
- Because ATS is trained on predicted rather than measured summaries, its training inputs must be produced as they will be at deployment: by a model that has not seen the run it predicts.
- RC19 used the closed-form leave-one-out predictions of a single full-data fit. That is an approximation: the held-out run still informs the hyperparameters and normalisation.
- RC19B implements honest K-fold cross-fitting, excluding the held-out paid runs from every upstream estimate.
- The same rule gives an honest small-sample calibration map for E1, so the physical classifier is compared with a probability-mapped E1, not only with raw E1.

**Results.**
- In a pre-registered comparison on eight fresh splits, the honest physical classifier with margin sampling gave better probabilities than calibrated E1 with straddle sampling: log-loss AULC −0.030, lower in 7 of 8 repeats.
- Re-evaluating every construction on the same paid prefixes separates the sources:
  - probability mapping alone accounts for roughly 45 % of the gain over raw E1, and only on E1's own straddle path;
  - a depth-only classifier with the same mapping equals calibrated E1;
  - adding predicted temperature and spike ratio lowers log loss on every path type, in 8 of 8 repeats.
- The physical summaries therefore carry Keyhole information beyond depth. Their benefit is in probability quality and in earlier confirmation of a BA target; balanced accuracy at p = 0.5 does not improve, and E1 with straddle remains as good for hard decisions.

**The approximation versus the honest construction.**
- The honest construction trails RC19's approximation when few runs are paid (0.022 BA and 0.053 log loss behind at B16) and converges in BA by B24.
- A one-factor development test assigns about a third of that gap to the training-fold size and the rest to re-estimating hyperparameters per fold.

**Duration.**
- For the eight physical outputs, the joint target is limited entirely by spike duration.
- A two-part (hurdle) duration model and a bottleneck-weighted acquisition both failed to improve it.
- Duration appears to be noisy given the process parameters: even its own spike ratio predicts it only to R² ≈ 0.6–0.75.

**Open failure.** A small corner of fast-scan, high-power conduction runs stays misclassified by every learner, although the margin learners pay for most of those runs.

## 8. Claims register

- **Pre-specified** (frozen 8299437f; DEV): the Keyhole primary and secondary verdicts in section 4, and D1–D3 in section 5.
- **Exploratory** (no verdict; no multiplicity control):
  - the matched-path decomposition;
  - paired spends;
  - reliability bins;
  - the path diagnostic and corner analysis;
  - the development replays and fold-size mechanism;
  - the duration ceiling;
  - pooled RC19 + RC19B completion;
  - the SHQ/M0Q lengthscale hypothesis.
- **Not available / not claimed:**
  - new physical simulations, real-data Stage A, C4;
  - a deployable stopping rule;
  - a cross-fit claim for ATSAPPROX;
  - the per-fold reading of the RC19 view;
  - Astra's TEST outcome (not inspected).

## 9. State at 2026-10-19 22:05 UTC

- **Opus queue:** idle; all RC19B jobs complete, 0 failures. The runner (PID 17384) stops by itself at the deadline 2026-10-20 08:41:20 UTC.
- **Astra:** her study, workspace, code and 2 threads were never touched (TEST 9,529 complete, 694 pending at 22:01 UTC).
- **Not used:** main branch, simulator, cloud, external messages, C4, real-data Stage A; BA_RISK stays cancelled.
- **Process note:** one sub-second verification process (comparing the live RC19 page with its local file) ran while both regression workers were active. It is logged in RC19B-RESULTS.

## Files

**Protocol and definitions:** `PROTOCOL_RC19B.md`, `MODEL_DEFINITIONS_RC19B.md`, `final/RC19B_FINAL_MANIFEST.json`.

**Final tables:**
- `report/KEYHOLE_FINAL.md`, `report/KEYHOLE_FINAL_DECOMPOSITION.md`
- `report/DURATION_FINAL.md`, `report/COMPUTE_COST.md`, `report/PATHS_DIAGNOSTIC.md`
- the CSVs beside them.

**Exports:** `export_final/predictions_label_f32.npz` and `predictions_reg_f32.npz` (8 outputs + hurdle), `export_final/paths_final.csv.gz`. `export_final/EXPORT_ACCEPTANCE.json` is PASS: label 2544, regression 4864 and duration 1216 cells; max |Δ| ≤ 7e-15.

**Figures:** `report/fig_rc19b_keyhole_curves.png`, `fig_rc19b_keyhole_decomposition.png`, `fig_rc19b_duration.png`, `fig_rc19b_boundary_evolution.png`.

**Viewers (private claude.ai pages):**
- single learner (repeat 11, fold 1; grid over log P × log VX at a chosen LS slice with ST fixed; refit vs recorded ≤ 6e-8): https://claude.ai/artifact/U4rvRPvxnQft8X4XRQTn76 (`viewer/single_learner_view.html`);
- RC19 view relabelled (same link as before): https://claude.ai/artifact/KpF6bE47rnzTWr2tmPfRow.

**Code:** `src/rc19b_*.py`. The viewer, figures and path diagnostic are presentation only and not frozen.
