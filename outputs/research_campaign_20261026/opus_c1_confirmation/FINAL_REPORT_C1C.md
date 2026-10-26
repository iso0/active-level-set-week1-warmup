# C1 doğrulaması (C1C): sonuç raporu

**Tarih:** 2026-10-26. Görev 18:05 UTC'de başladı; iş bitince 21:45 UTC'de erken kapatıldı.
**Kayıt ve dondurma:** commit 63e9ae1d, hiçbir yeni sonuçtan önce push edildi.
**Ayrıntılı tablolar:** [evaluation/RESULTS_C1C.md](evaluation/RESULTS_C1C.md). **Karar:** [DECISION_C1C.md](DECISION_C1C.md). **Dış plan:** [EXTERNAL_VALIDATION_PLAN_C1C.md](EXTERNAL_VALIDATION_PLAN_C1C.md).

---

## Tek sayfalık sonuç

**Hüküm:** C1 + margin bu 541 koşuluk havuzda önerilen öğrenici. Erken öğrenme kazancı ve BA 0.95'e daha az simülasyonla ulaşma, yeni 80 tekrarda (400 öğrenici) yeniden gösterildi. HA_LEAN + margin donmuş referans olarak kalıyor; havuzun örneklemediği bölgelere taşımada da daha güvenli seçenek o.

**Ne gösterildi** (C1 + margin eksi HA_LEAN + margin; köşeli parantezde tek yönlü %95 sınırları, tekrar kümeleri üzerinden):

- **Erken öğrenme.** BA-AULC B8–B24 farkı +0.0053 [+0.0039, +0.0068]; 80 tekrarın 59'unda pozitif.
  - Yalnız 8 koşuyla (başlangıç) BA 0.918, referansta 0.899.
  - Bu, EA'nın tek testindeki +0.0056 ile aynı büyüklük.
- **Hedefe daha az simülasyon.** Kısıtlı-ortalama tasarruflar:
  - BA 0.90 için +0.38;
  - 0.93 için +1.09;
  - 0.95 için +1.81 [+0.53, +3.09].
  - Üçü de gösterildi. 0.95 tasarrufu tekrarlandı (EA: +2.00). EA'da gösterilmemiş olan 0.93 tasarrufu bu kez gösterildi.
- **0.95'te güvenilirlik.** Ulaşma oranı +0.040 [+0.011] daha yüksek; koruma oranı +0.015 [−0.016], yani kabul edilebilir kayıp sınırı içinde.
- **Geç dönem.** B28–B60 farkı −0.0006 [−0.0013, +0.0002]. Kayıp gösterilmedi ve olası kayıp 0.003'ten küçük, yani geç performans korundu. 60 koşuda BA eşit: 0.9568 ve 0.9569.
- **Sağlamlık.** Erken kazanç rastgele 8 noktalık başlangıçta (+0.0055) ve kümelenmiş 8 noktalık başlangıçta (+0.0087) de gösterildi. Önsel genişliği yarıya indirilince ya da iki katına çıkınca da korunuyor (+0.0055 / +0.0047).
- **Maliyet.** Karar adımı başına CPU 1.19 kat. Log loss sınırın çok altında (+0.0025).

**Ne anlama gelmiyor:**

- **"GÜVENİLİR" üstünlük ya da her koşu için garanti değil.** C1, 0.95'e daha sık ulaşıyor ama sonra hedefin altına daha sık da düşüyor: 400 öğrenicide 65'e karşı 55. 0.95'te sürdürme iyileşmedi (−0.007); EA'daki +0.055 tekrarlanmadı.
- **0.95 tasarrufu daha çok öğrenicinin hedefe ulaşmasından geliyor.** İkisinin de ulaştığı öğrenicilerde hız farkı gösterilmedi (+0.66 [−0.28]).
- **Alternatif başlangıçlarda 0.95'i koruma gösterilmedi.** Fark −0.03 / −0.04, 20 tekrarla geniş aralıklar. Bu yüzden 0.95 güvenilirliği standart başlangıç için geçerli.
- **Hepsi aynı 541 koşunun yeni bölünmeleri.** Dış doğrulama değil.
- **Yeni yöntem iddiası yok.** Bileşenler bilinen yöntemler.

---

## 1. Sabit model: C1 + margin

EA'daki tarifin aynısı, değiştirilmedi. Kod `src/ea_cand.py` SYSTEMS["C1"]; dondurma commit 63e9ae1d ve `freeze/C1C_MANIFEST.json`.

**Girdiler**
- x = (P, VX, LS, ST); z = havuzun ortalaması ve standart sapmasıyla standartlaştırılmış log girdiler.
- h = standartlaştırılmış (log P − ½ log VX − 3/2 log LS); fiziksel ölçek değişkeni.

**1. Derinlik emülatörü.** Yalnız açılmış (ücretli) koşuların derinliğiyle kurulur:

  log A(z) = θ·h(z) + f(z) + ε

- θ ~ N(0, 3²); integralle dışarı alınır, kovaryansa 9·h hᵀ eklenir.
- f ~ GP(0, s_f² · Matérn-3/2(z, z′; ℓ₁..ℓ₄)).
- ε_i ~ N(0, s_n² w_i); kısa kayıtlarda w_i = 10⁴, diğerlerinde 1.

**2. Hiperparametreler** (C1'i HA_TREND'den ayıran tek fark). φ = (log s_f², log ℓ₁..₄, log s_n²) MAP ile seçilir:

  φ̂ = argmin_φ [ −log p(y | φ) + ½ Σ_k ((φ_k − m_k) / s_k)² ]

- m = (0, 0, 0, 0, 0, log 0.01).
- s = (1.5, 1, 1, 1, 1, 1.5).
- L-BFGS-B iki sabit başlangıçtan çalışır (HA_TREND'in başlangıcı ve m); düşük amaç değeri seçilir.

**3. Dürüst yığınlama.** Açılmış koşular 10 kata ayrılır.
- Her açılmış koşunun derinlik tahmini F, kendi katı dışarıda bırakılarak kurulan modelden gelir.
- Test ve aday koşuların F değeri, tüm açılmış koşularla kurulan modelden gelir.

**4. Sınıflandırıcı** (HA_LEAN ile aynı). Standartlaştırılmış [h, F] üzerinde Laplace lojistik.
- (τ_F, τ_h) ∈ {0.5, 1, 2, 4}² ızgarasının her noktasında bir model; ağırlıklar Laplace kanıtıyla orantılı.
- P(Keyhole | x) = Σ_g w_g σ(m_g(x)); karar eşiği 0.5.

**5. Tek sınıf kuralı.** Kullanılabilir derinliği olan açılmış koşularda iki sınıf da görülene kadar:
- tahmin, açılmış koşuların sınıf oranıdır;
- sonraki sorgu, etiketsiz yoldaki bir sonraki noktadır.

**6. Seçim (margin).** Sonraki sorgu = argmax_{açılmamış x} −|P(Keyhole | x) − 0.5|.

**Algoritma.** Her öğrenici için:
1. Etiketsiz 8 noktalık başlangıç açılır; sayılır.
2. b = 8, …, 60 için: emülatör (MAP) ve sınıflandırıcı yeniden kurulur, test kümesi tahmin edilir, margin ile bir koşu daha açılır.
3. Her bütçede yalnız o ana kadar açılmış koşular kullanılır.

**Referans A = HA_LEAN + margin.** Aynı yapı; yalnız eğilimsiz (sabit ortalamalı) derinlik GP'si, ML-II ve tek başlangıç kullanılır.

**Bilinen bileşenler:**
- eğilimli GP (universal kriging);
- hiperöncül altında MAP;
- yığınlama;
- Laplace lojistik;
- belirsizlik örneklemesi.

Katkı yöntemsel yenilik değil. Katkı, EA'da ölçülen hata kaynağı (küçük n'de ML-II kestirim artefaktı) için ucuz bir düzeltme ve bu düzeltmenin tekrarlı doğrulaması.

## 2. Ana doğrulama: yeni STD tekrarları 203–282

Hüküm kümesi: 80 küme, 400 öğrenici, kendi yolları. Kayıtlı 1.400 birimin hepsi bitmeden hiçbir sonuca bakılmadı; başarısız birim yok.

### 2.1 Kayıtlı hükümler

| hüküm | sonuç | durum |
|---|---|---|
| V-EARLY (BA-AULC B8–B24) | +0.0053 [+0.0039, +0.0068] | ERKEN KAZANÇ GÖSTERİLDİ + PRATİK |
| V-0.90 (kısıtlı-ortalama tasarruf) | +0.38 [+0.15, +0.60] | TASARRUF GÖSTERİLDİ |
| V-0.93 | +1.09 [+0.42, +1.75] | TASARRUF GÖSTERİLDİ + PRATİK |
| V-0.95 güvenilirlik | Δulaşma +0.040 [+0.011]; Δkoruma +0.015 [−0.016] | GÜVENİLİR |
| 0.95 tasarrufu | +1.81 [+0.53, +3.09] | TASARRUF GÖSTERİLDİ + PRATİK (tekrarlandı) |
| geç dönem (B28–B60) | −0.0006 [−0.0013, +0.0002] | KAYIP GÖSTERİLMEDİ; 0.003 içinde KORUNDU |
| zarar sınırları | ΔLL +0.0025 (≤ 0.030); ΔBrier −0.0001 (≤ 0.010); CPU 1.19× (≤ 3×) | geçti |

**Bootstrap kontrolü** (10.000 küme yeniden örneklemesi):

| ölçüt | aralık |
|---|---|
| erken | (+0.0040, +0.0068) |
| 0.95 tasarrufu | (+0.56, +3.08) |

İkisi de t sınırlarıyla aynı yönde.

**Havuzlanmış değerler** (bir tekrarın katları birleştirilerek; bilgi amaçlı):

| ölçüt | fark |
|---|---|
| erken | +0.0050 [+0.0035] |
| 0.95 tasarrufu | +3.01 [+0.93] |

### 2.2 Pencereler ve iki geri çağırma

| büyüklük (C1 − A) | fark | pozitif küme |
|---|---|---|
| BA-AULC B8–B24 | +0.0053 [+0.0039, +0.0068] | 59/80 |
| BA-AULC B8–B60 | +0.0015 [+0.0007, +0.0022] | 49/80 |
| BA-AULC B28–B60 | −0.0006 [−0.0013, +0.0002] | 34/80 |
| Keyhole geri çağırma B8–B24 | +0.0074 [+0.0044, +0.0104] | 54/80 |
| iletim geri çağırma B8–B24 | +0.0033 [+0.0014, +0.0052] | 52/80 |
| Keyhole geri çağırma B8–B60 | +0.0023 [+0.0007, +0.0039] | 47/80 |
| iletim geri çağırma B8–B60 | +0.0006 [−0.0003, +0.0016] | 46/80 |
| log loss B8–B24 | −0.0040 [−0.0065, −0.0016] | 31/80 |
| log loss B8–B60 | +0.0025 [+0.0010, +0.0040] | 48/80 |
| Brier B8–B60 | −0.0001 [−0.0005, +0.0003] | 36/80 |

### 2.3 Sabit bütçelerde BA

Hücrelerde BA, parantez içinde (Keyhole / iletim) geri çağırma.

| b | C1 + margin | HA_LEAN + margin | fark |
|---|---|---|---|
| 8 | 0.9184 (0.910 / 0.926) | 0.8987 (0.882 / 0.916) | +0.0197 [+0.0143] |
| 12 | 0.9373 (0.931 / 0.944) | 0.9318 (0.924 / 0.940) | +0.0055 [+0.0023] |
| 16 | 0.9416 (0.935 / 0.948) | 0.9406 (0.933 / 0.948) | +0.0010 [−0.0008] |
| 24 | 0.9483 (0.943 / 0.954) | 0.9460 (0.939 / 0.953) | +0.0023 [+0.0005] |
| 40 | 0.9531 (0.948 / 0.958) | 0.9541 (0.949 / 0.959) | −0.0011 [−0.0023] |
| 60 | 0.9568 (0.951 / 0.962) | 0.9569 (0.951 / 0.963) | −0.0002 [−0.0013] |

### 2.4 Her hedef için sorgu, ulaşma ve sürdürme

400 öğrenici; paydalar gösteriliyor.

| sistem | τ | ulaştı | korudu | kaybetti | B60'ta ≥ τ | sürdürdü | ilk b (ulaşanlar) | doğrulanmış b (ulaşanlar) | harcama ort. / medyan (ulaşanlar) | medyan harcama (hepsi; ∞ = ulaşamadı) | KO (61 sınırlı) | birikimli ulaşma b16/24/40/60 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C1 | 0.90 | 400/400 | 398 | 2 | 398 | 279 | 8.36 | 8.80 | 12.80 / 12 | 12 | 12.80 | 0.950 / 0.988 / 1 / 1 |
| A | 0.90 | 400/400 | 397 | 3 | 397 | 224 | 8.72 | 9.18 | 13.18 / 12 | 12 | 13.18 | 0.938 / 0.978 / 1 / 1 |
| C1 | 0.93 | 392/400 | 365 | 27 | 365 | 130 | 9.89 | 12.03 | 16.03 / 13 | 13 | 16.93 | 0.730 / 0.882 / 0.958 / 0.980 |
| A | 0.93 | 389/400 | 360 | 29 | 361 | 117 | 10.63 | 12.80 | 16.80 / 13 | 13.5 | 18.02 | 0.718 / 0.853 / 0.945 / 0.973 |
| C1 | 0.95 | 335/400 | 270 | 65 | 273 | 52 | 13.51 | 18.30 | 22.30 / 18 | 22 | 28.59 | 0.390 / 0.575 / 0.752 / 0.838 |
| A | 0.95 | 319/400 | 264 | 55 | 271 | 55 | 13.69 | 18.63 | 22.63 / 19 | 22.5 | 30.40 | 0.335 / 0.532 / 0.728 / 0.797 |

**Tanımlar**
- **İlk:** BA ≥ τ olan ilk bütçe.
- **Doğrulanmış b:** BA(b) ≥ τ ve BA(b + 4) ≥ τ olan ilk b ≤ 56.
- **Harcama:** b + 4. Sekiz başlangıç koşusu ve dört doğrulama sorgusu dahildir.
- **Korudu:** ulaştı ve BA(60) ≥ τ.
- **Sürdürdü:** ulaştı ve doğrulanmış b'den (başlangıç noktası) 60'a kadar her bütçede BA ≥ τ.
- **KO** (61 ile sınırlı kısıtlı-ortalama harcama): ulaşamayan öğrenici 61 sayılır. Bu, gerçek maliyet ya da gerçek farkın alt sınırı değildir.

**Eşleştirilmiş ulaşma** (C1 / A):

| τ | ikisi | yalnız C1 | yalnız A | hiçbiri | ikisinin de ulaştığı öğrenicilerde tasarruf (koşullu) |
|---|---|---|---|---|---|
| 0.90 | 400 | 0 | 0 | 0 | +0.38 [+0.15] |
| 0.93 | 387 | 5 | 2 | 6 | +0.88 [+0.20] |
| 0.95 | 300 | 35 | 19 | 46 | +0.66 [−0.28] (gösterilmedi) |

### 2.5 İkincil sistemler ve ayrıştırma

| karşılaştırma | erken | geç | 0.95 tasarrufu | log loss B8–B60 |
|---|---|---|---|---|
| D (HA_LEAN seçer / eski HA_TREND tahmin eder) − A | +0.0042 [+0.0033] | −0.0014 [−0.0019, −0.0010] (KAYIP GÖSTERİLDİ) | +0.66 [−0.19] | +0.0060 |
| HA_LEAN seçer / C1 tahmin eder − A | +0.0057 [+0.0047] | −0.0006 [−0.0011, −0.0002] | +2.12 [+1.23] | −0.0009 |
| MAP düzeltmesi: aynı ücretli veride C1 − D | +0.0015 [+0.0010] | +0.0008 [+0.0005] | +1.46 [+0.58] | −0.0070 (80/80 kümede daha düşük) |
| C1 + margin − D | +0.0011 [−0.0002] | +0.0009 [+0.0002] | +1.15 [−0.17] | −0.0035 |
| model etkisi, C1'in yolunda (C1 − A) | +0.0077 [+0.0065] (75/80) | +0.0003 | +2.28 [+1.48] | −0.0051 |
| yol etkisi, HA_LEAN için (A, C1'in yolunda − A kendi yolunda) | −0.0024 [−0.0039] | −0.0009 | −0.47 | +0.0076 |
| yol etkisi, C1 için | −0.0004 | +0.0001 | −0.31 | +0.0035 |

**Okuma:**
- MAP düzeltmesi, eski eğilimli modelin (D) erken kazancını koruyor; geç kaybını ve log loss cezasını kaldırıyor. Bu, EA'daki teşhisle tutarlı.
- Kazanç seçiciden değil, modelden geliyor.

### 2.6 Önceden tanımlı alt gruplar

Bilgi amaçlı; 80 tekrarlık hükmü değiştirmez.

| alt grup | erken | 0.90 | 0.93 | 0.95 | Δulaşma 0.95 | Δkoruma 0.95 | Δsürdürme 0.95 |
|---|---|---|---|---|---|---|---|
| S1 (203–242) | +0.0055 [+0.0035] | +0.38 [+0.10] | +1.19 [+0.30] | +1.25 [−0.31] (DAHA KÖTÜ DEĞİL) | +0.030 | +0.025 | −0.015 |
| S2 (243–282) | +0.0052 [+0.0031] | +0.38 [−0.00] | +0.99 [−0.04] | +2.37 [+0.30] (GÖSTERİLDİ) | +0.050 | +0.005 | +0.000 |

## 3. Başlangıç sağlamlığı

Her koşul ayrı raporlanıyor; 20'şer yeni tekrar, ana doğrulamayla birleştirilmedi. Başlangıç kuralları RC22'den aynen alındı ve etiketsiz; yeniden üretimi 80/80.

| ölçüt | RAND8 (rastgele 8; 283–302) | LOCAL8 (kümelenmiş 8; 303–322) |
|---|---|---|
| erken | +0.0055 [+0.0025] GÖSTERİLDİ + PRATİK | +0.0087 [+0.0041] GÖSTERİLDİ + PRATİK |
| geç | −0.0004 [−0.0016] | +0.0029 [+0.0011] |
| 0.90 / 0.93 / 0.95 tasarrufu | +0.53 [−0.17] / +1.43 [+0.26] / +2.12 [−0.57] | +0.22 [−0.27] / +1.71 [−0.20] / +3.33 [+0.50] |
| Δulaşma / Δkoruma 0.95 | +0.020 [−0.041] / −0.030 [−0.098] | +0.060 [−0.016] / −0.040 [−0.099] |
| V-0.95 (bilgi amaçlı) | GÜVENİLİR DEĞİL (koruma sınırı aşıldı) | GÜVENİLİR DEĞİL (koruma sınırı aşıldı) |
| 0.95: ulaştı / korudu / kaybetti (C1; A) | 83 / 70 / 13; 81 / 73 / 8 | 83 / 66 / 17; 77 / 70 / 7 |
| log loss B8–B60 | −0.0043 | −0.0214 |
| tek sınıfla başlayan | 3/100; ikinci sınıf için 1'er ek sorgu | 83/100; ortalama 1.16 ek sorgu (en çok 2); iki sınıf ortalama b = 8.96'da |

**Kayıtlı başlangıç kuralı:**
- erken: BAŞLANGIÇTAN BAĞIMSIZ;
- 0.95 tasarrufu: ÇELİŞKİ YOK;
- geç kayıp: yok;
- zarar sınırı: aşılmadı.

Tek sınıfla başlayan öğreniciler dışlanmadı; ikinci sınıfı bulma maliyeti her iki kolda da harcamaya dahil. İki kol, iki sınıf görülene kadar aynı etiketsiz yolu izledi (kontrol edildi).

## 4. Önsel genişliği kontrolü

Bir kontrol, aday seçimi değil. DEV yolları 123–162, 40 küme. Bu yollar çapraz yol, yani A'nın kaydedilmiş yolu; yeni bağımsız doğrulama değil.

| (A'ya göre) | C1 | SD × 0.5 | SD × 2 |
|---|---|---|---|
| erken | +0.0053 [+0.0041] | +0.0055 [+0.0042] | +0.0047 [+0.0035] |
| geç | −0.0015 | −0.0017 | −0.0017 |
| 0.93 / 0.95 tasarrufu (çapraz yol) | +1.64 / +0.68 | +2.41 / +1.71 | +1.91 / +0.55 |
| Δkoruma 0.95 | −0.055 [−0.095] | −0.080 [−0.126] | −0.035 [−0.083] |
| log loss B8–B60 | −0.0007 | −0.0026 | +0.0031 |
| C1'e göre erken fark | – | +0.0002 | −0.0006 |

**Kural:** ÖNSELE KARŞI SAĞLAM (erken). İki kontrol de C1 ile pratikte aynı (|fark| < 0.003).

**Açıklama:**
- Önsel, EA'da tüm havuzun ML-II değerleri görüldükten sonra seçildi. Aynı havuzun yeni bölünmeleri bu tasarım etkisini ortadan kaldırmaz.
- Dar önsel (× 0.5) DEV'de log loss ve 0.95'te daha iyi görünüyor; protokol gereği aday yapılmadı.
- DEV kümesindeki bilinen 0.95 koruma sorunu (−0.055) önsel genişliğinden bağımsız sürüyor.

## 5. Eski ve yeni sonuçlar yan yana

Aynı kodla hesaplandı; hiçbir küme birleştirilmedi.

| küme | tekrarlar | erken | geç | 0.90 | 0.93 | 0.95 | Δulaşma 0.95 | Δkoruma 0.95 | Δsürdürme 0.95 | ΔLL |
|---|---|---|---|---|---|---|---|---|---|---|
| EA DEV (A'nın yolunda C1) | 123–162 | +0.0053 [+0.0041] | −0.0015 [−0.0022] | −0.06 [−0.42] | +1.64 [+0.80] | +0.68 [−0.58] | −0.015 | −0.055 [−0.095] | −0.010 | −0.0007 |
| EA taze doğrulama | 163–202 | +0.0056 [+0.0038] | −0.0005 [−0.0017] | +0.77 [+0.26] | +0.61 [−0.29] | +2.00 [+0.21] | +0.040 | +0.020 [−0.031] | +0.055 [+0.001] | +0.0013 |
| **C1C ana (hüküm)** | **203–282** | **+0.0053 [+0.0039]** | **−0.0006 [−0.0013]** | **+0.38 [+0.15]** | **+1.09 [+0.42]** | **+1.81 [+0.53]** | **+0.040 [+0.011]** | **+0.015 [−0.016]** | **−0.007 [−0.044]** | **+0.0025** |
| C1C S1 | 203–242 | +0.0055 [+0.0035] | −0.0006 | +0.38 | +1.19 [+0.30] | +1.25 [−0.31] | +0.030 | +0.025 | −0.015 | +0.0030 |
| C1C S2 | 243–282 | +0.0052 [+0.0031] | −0.0005 | +0.38 | +0.99 [−0.04] | +2.37 [+0.30] | +0.050 | +0.005 | +0.000 | +0.0020 |

**Yanında tutulan eski başarısızlıklar:**
- DEV taşıma kuralının başarısızlığı (geç −0.0015);
- EA K5 bölge başına uyarısı (−0.049, alt sınır −0.072);
- EL'de D ve E: BENİMSENMEDİ.

**Tekrarlanan:**
- erken kazanç (üç kümede de +0.005 civarı);
- 0.95 tasarrufu;
- 0.95 ulaşma.

**Tekrarlanmayan:**
- EA'nın 0.95 sürdürme kazancı (+0.055 → −0.007).

## 6. Tahminler, sorgu kimlikleri ve maliyet

**Dışa aktarımlar** (`exports/`):
- Her sistemin her bütçedeki test tahmini (float32).
- Her yolun açılan simülasyon kimlikleri, sorgu sırasıyla ve seçen kuralla (`paths.csv.gz`).
- Setler: main_s1 34.9 MB, main_s2 34.9 MB, start_rand8 17.5 MB, start_local8 17.3 MB, prior_dev 11.8 MB.

**Maliyet** (`COST_BREAKDOWN.json`):

| iş | birim | birim-saat |
|---|---|---|
| ana | 800 | 5.2 |
| başlangıç | 400 | 2.6 |
| önsel | 200 | 1.0 |
| yeniden üretim (eski kimlikler) | 6 | 0.03 CPU-saat |

- Toplam 1.406 birim, 8.8 işçi-saat, sıfır hata.
- Duvar saati 18:34–21:34 UTC; 3 işçi; Astra'nın payı kullanılmadı.

**Simülasyon muhasebesi**
- Yeni fiziksel simülasyon yok; "açılan koşu", havuzdaki bir koşunun sonucunun öğreniciye gösterilmesi.
- Her kol, öğrenici başına 60 koşu açar: 8 ortak başlangıç + 52 sorgu.
- İki kolun yolları birlikte öğrenici başına ortalama 67.8 farklı koşu açtı (başlangıç koşullarında 68.5).
- Çapraz tahminler açılmış koşuları yeniden kullanır; ek simülasyon sayılmaz.

## 7. Bağımsız yeniden hesaplama ve dondurma kontrolü

**Dondurma:**
- `python -m src.c1c_freeze check` değerlendirmeden önce ve dışa aktarımdan sonra geçti; EA manifesti de değişmedi.
- Dondurma öncesi yeniden üretim (yalnız eski kimlikler):
  - EA birimleri 4/4 bit düzeyinde aynı;
  - RC22 başlangıçları 80/80 (37 yol sorgusu dahil);
  - önsel ölçeği 1 kayıtlı C1 ile 2/2 bit düzeyinde aynı.
- Değerlendirme kodu eski EA verisinde EA kararını birebir üretti.

**Yeniden hesaplama:**
- Beş dışa aktarım setinden, kendi koduyla, öğrenici başına BA, BA-AULC ve harcama yeniden hesaplandı: 5/5 GEÇTİ (en büyük fark 2.2e-16; harcama farkı 0).
- Ana, RAND8 ve LOCAL8 başlık tahminleri (erken ve 0.90 / 0.93 / 0.95 tasarrufları, sınırlarıyla) dışa aktarımlardan yeniden hesaplandı: 3/3 GEÇTİ (en büyük fark 1.7e-17).

## 8. Kullanım kararı

Önceden kayıtlı eşleme uygulandı.

**Önerilenler** (bu havuzda):
1. **Erken, küçük sabit bütçe (B8–B24):** C1 + margin. Standart, rastgele ve kümelenmiş başlangıçta geçerli; önsel genişliğine bağlı değil.
2. **BA 0.95'te durma:** C1 + margin. Daha az simülasyon gerekiyor; ulaşmada ve korumada eşdeğerlikten kötü değil. Güvenilirlik standart başlangıç için geçerli.
3. **0.90 / 0.93:** C1 + margin; daha az simülasyon, gösterildi.
4. **Tüm bütçe / geç dönem:** iki öğrenici pratikte eşit; geç performans 0.003 içinde korunuyor.

**HA_LEAN + margin'in daha güvenli olduğu durumlar:**
- havuzun örneklemediği bölgelere taşıma (K5 uyarısı);
- 0.95'in bütçe sonuna kadar sürdürülmesi;
- standart dışı başlangıçta 0.95'in korunması;
- tez karşılaştırmalarının donmuş referans kolu.

**Yalnız bu havuza ait iddialar:** bu belgedeki tüm sayısal iddialar. Hepsi aynı 541 koşunun yeni bölünmeleri.

**Doğrulama dalı tamamlandı.** Yeni tohum ya da varyant çalıştırılmayacak; sıradaki adım dış veri.

## 9. Dış doğrulama planı (Ioan için)

Ayrıntı: [EXTERNAL_VALIDATION_PLAN_C1C.md](EXTERNAL_VALIDATION_PLAN_C1C.md). RC24 önerisi yeniden yazılmadı, genişletildi.

**İstenen koşular:**

| blok | koşu | sınadığı |
|---|---|---|
| V1 | 136 yeni etiketsiz LHS koşusu, havuz aralığında | erken kazanç |
| R3 | 16 koşu, LS aralık dışında | havuz dışına taşıma güvenliği |
| R1 | 24 tekrar koşusu | köşe etiketinin belirlenimciliği |
| R2 | 12 koşu (isteğe bağlı) | mekanizma |

Toplam 176 (R2 ile 188).

**Süreç:**
- Koşular istenmeden önce modeller (63e9ae1d), tasarım noktaları, R3 tahminleri ve karar kuralları commit edilir.
- Sonuçlar mühürlü etiket dosyası olarak gelir; deponun etiketsiz kabul süreciyle ve kilitli `execute` komutuyla yalnız bir kez açılır.

**Karşılaştırmalar:**
- V1'de C1 + margin ile HA_LEAN + margin karşılaştırılır (erken kazanç; geç dönemde −0.01'den kötü olmama). 0.95 bu boyutta yalnız tanımlayıcı.
- R3'te havuzun tamamıyla eğitilmiş donmuş tahminler karşılaştırılır (C1, 16 koşunun en az 3'ünde daha fazla hata yaparsa uyarı).
- R1'de etiket değişme oranı ölçülür (≥ 0.2 ise köşe rastlantısal).

## 10. Kurallar ve süreklilik

**Bilgi kuralları:**
- Kehanet (oracle) derinliği, tüm havuz hiperparametreleri, test etiketleri ve zor grup üyeliği hiçbir kola girmedi.
- Etiket, dışlama ve eşik değişmedi.
- Fiziksel simülatör, ücretli API, bulut ya da C4 kullanılmadı; mesaj gönderilmedi.

**Astra:** canlı klasörüne, Git'ine ve süreçlerine dokunulmadı; yalnız `astra_state.json` okundu.

**Paylaşılan dosyalar:** ortak klasörde yalnız `opus_state.json` (kampanya kimliği `opus_c1_confirmation_20261026`) ve kendi geçici dosyaları yazıldı. EA kapanış kaydı korundu.

**Çalıştırıcı:** sohbetten bağımsızdı ve kontrol noktalıydı; kullanım sınırı nedeniyle verilen arada hiçbir şey kaybolmadı.
