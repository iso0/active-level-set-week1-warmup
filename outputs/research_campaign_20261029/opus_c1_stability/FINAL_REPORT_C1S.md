# C1 istikrarı (C1S): sonuç raporu

**Tarih:** 2026-10-29. Pencere 00:10:41 UTC'de açıldı; iş bitince 02:13:11 UTC'de erken kapatıldı.
**Kayıt ve dondurma:** commit 9cad00ad, hiçbir taze sonuçtan önce push edildi.
**Ayrıntılı tablolar:** [evaluation/RESULTS_C1S.md](evaluation/RESULTS_C1S.md). **Karar:** [DECISION_C1S.md](DECISION_C1S.md). **Teşhis:** [diag/DIAGNOSIS_C1S.md](diag/DIAGNOSIS_C1S.md). **Protokol:** [PROTOCOL_C1S.md](PROTOCOL_C1S.md).

---

## Tek sayfalık sonuç

**Hüküm:** C1 + margin değişmeden kalıyor.
- Denenen tek geliştirme AVG4'tü: son 4 bütçenin olasılıklarının ortalaması.
- Taze 40 tekrarda (200 öğrenici) birincil istikrar ölçütünü değiştirmedi.
- 0.95 hedefinde simülasyon harcaması için konan zarar sınırını aştı.
- Önceden kayıtlı kurala göre benimsenmedi.

**1. Sorunun mekanizması neydi?**
- C1'in öğrenme sırasındaki gerilemeleri, sınıra çok yakın tek tek test noktalarının sınıf değiştirmesinden doğuyor.
- Bu noktaların çoğu Keyhole ve etiketlerin iç içe geçtiği hızlı tarama köşesinde ya da zor grupta. Her yeni margin etiketi yakınındaki noktaları çeviriyor.
- Çevrilmenin kaynakları:
  - sınıflandırıcının yeniden kurulması, %62;
  - hiperparametrelerin düzgün kayması, %28;
  - ağırlık değişimi, %12.
- Zararlı ve yararlı çevrilmeler dengeli. Bu yüzden gerilemeler BA düzeyini aşağı çekmiyor; yalnız eğriyi titretiyor.
- B24–B60 arasında 0.95'in altında kalma eksiğinin yaklaşık %81'i, zor katlarda kalıcı bir düzey açığı. Kalan %19 titreşim.
- DEV'de yazılan beş mekanizma öngörüsünün beşi de taze veride tuttu.

**2. Ne değişti?**
- C1'in kodu, etiketler, eşik ve hata ağırlıkları değişmedi.
- Yalnız karar katmanında bir aday sınandı: AVG4. b ≥ 25 için C1'in son dört bütçedeki olasılıklarının ortalaması.
- AVG4 C1'in kendi yolunu ve açtığı koşuları kullanıyor: ek simülasyon yok, ek CPU ihmal edilebilir.
- İki basit kontrol de sınandı:
  - EVERY4: daha seyrek güncelle;
  - FREEZE24: 24'te dondur.

**3. Erken başarı, istikrar, iki sınıf ve harcamada ne oldu?** (AVG4 − C1; köşeli parantezde tek yönlü %95 sınırları, tekrar kümeleri üzerinden)
- **Erken başarı:** birebir aynı (b ≤ 24'te fark 0). C1'in HA_LEAN'e göre erken üstünlüğü bu taze kümede de görüldü: B8–B24 +0.0059 [+0.0041]. Bu, EA ve C1C'den sonra üçüncü bağımsız tekrar.
- **İstikrar (birincil ölçüt S95):** değişmedi, −0.000001 [−0.00010, +0.00010].
  - Eğri belirgin biçimde düzleşti:
    - toplam dalgalanma %43 azaldı;
    - öğrenici başına gerileme adımı 2.6 azaldı;
    - çevrilme sayısı yarıya indi.
  - 0.95'i ulaşıldığı yerden sona kadar sürdüren öğrenici sayısı 31'den 45'e çıktı (+0.070 [+0.037]).
  - Ama BA düzeyi aynı kaldı. Yalnız ufak titreşimler silindi.
- **İki sınıf:** Keyhole duyarlılığı +0.0001, iletim (conduction) duyarlılığı −0.0001. İki sınıfta da zarar yok; FN ve FP farkları gürültü düzeyinde.
- **Harcama:** 0.90 ve 0.93'te daha kötü değil. 0.95'te ortalama ortalaması geride kaldığı için hedef geç onaylanıyor:
  - kısıtlı-ortalama harcama farkı −0.64 [−1.06];
  - sınır −1.0'dı, aşıldı.

**4. C1 kalıyor mu? Geliştirme hangi kullanımda benimsendi?**
- C1 + margin değişmeden kalıyor. Havuz içinde erken ve hedefte durma kullanımları için önerilen öğrenici olmaya devam ediyor; C1C kararı kapalı ve değişmedi.
- AVG4 hiçbir kullanımda benimsenmedi; "hedefi tutma" kullanımında bile, çünkü 0.95 harcama sınırı aşıldı.
- HA_LEAN + margin donmuş referans ve havuz dışına taşımada güvenli seçenek olarak kalıyor.

**Ne anlama gelmiyor:**
- **AVG4 işe yaramaz değil.** Eğriyi düzleştiriyor ve sürdürmeyi artırıyor. Ama aynı sürdürme kazancını "daha seyrek güncelle" kontrolü de veriyor. Bu genel bir yumuşatma etkisi, AVG4'e özgü değil.
- **Kalan geç açık titreşim değil, düzey açığı.** Onu bir karar katmanı kapatamaz. Zor katlardaki iç içe etiketler için daha çok bilgi gerekiyor (EA'nın bilgi sınırı bulgusu).
- **Hepsi aynı 541 koşunun yeni bölünmeleri;** dış doğrulama değil.

---

## 1. Kurulum ve bütünlük

| öğe | değer |
|---|---|
| depo, dal | iso0/active-level-set-week1-warmup, araştırma dalı `c1-stability-20261029` (3caf7c4e'den; main'e merge yok) |
| başlangıç | C1/C1C taban 3caf7c4e; Research Hub main 4fc9b5d (`src/` ikisinde aynı, doğrulandı) |
| Graphify | 0.9.96; yalnız açık sabit grafik (`thesis-graphify-sync-2026-10-29\source\graphify-out\graph.json`, SHA-256 5D96E506…, değişmedi); 2 dar sorgu; eksik dosyalar arası çağrılar kaynakta doğrulandı; [graphify/GRAPHIFY_USAGE.md](graphify/GRAPHIFY_USAGE.md), [graphify/C1_CODE_MAP.md](graphify/C1_CODE_MAP.md) |
| pencere | tek 48 saat (00:10:41 – 2026-10-31 00:10:41 UTC); 02:13:11 UTC'de erken kapandı |
| kapasite | en çok 3 tek iş parçacıklı Opus işçisi; Astra'nın payı hiç kullanılmadı; BLAS/OpenMP = 1 |
| dondurma | `freeze/C1S_MANIFEST.json`; her işçi ilk biriminden önce, değerlendirme de başlamadan önce manifesti doğruladı ("C1S manifest check: True") |
| ara bakış | yok; 600 birimin hepsi bittikten sonra değerlendirildi |
| hata | 651 birim (DEV izleme 51 + taze 600), 0 hata |
| bağımsız yeniden hesaplama | 3 kümenin 3'ünde GEÇTİ (en büyük fark ≤ 6·10⁻¹⁶; varyant yeniden hesabı 0; S95 ve erken başlık sayıları kararla birebir aynı) |

## 2. Mekanizma (DEV teşhisi ve taze doğrulama)

**DEV teşhisi.** C1C'nin zaten değerlendirilmiş verisinde yapıldı (STD 203–282, RAND8 283–302, LOCAL8 303–322). 50 öğrenici, kimliğe göre seçilerek bit düzeyinde aynı biçimde yeniden oynatıldı (`c1s-trace`). Yeni kimlik kullanılmadı.

**Bulgular**
- **Gerileme adımları tek noktalık.** Gerileyen test noktalarında |p − 0.5| medyanı 0.023.
- **Kaybedilen sınıf çoğunlukla Keyhole.** Kaybedilen BA'nın %68'i Keyhole noktalarından geliyor.
- **Yer.** İç içe etiketli köşe 5.7 kat, zor grup 7 kat fazla temsil ediliyor.
- **Tetikleyici yeni etiket.** Çevrilmelerin %55'i yeni etiketin en yakın çeyreğinde; %80'i yeni etiket yönünde.
- **Bileşenler** (aynı ücretli veriyle yapılan ayrıştırma):

  | bileşen | pay |
  |---|---|
  | sınıflandırıcının yeniden kurulması | %62 |
  | MAP hiperparametre kayması | %28 |
  | yapılandırma ağırlığı değişimi | %12 |
  | yanıt standartlaştırması | ≈ %0 |

  İkinci bir hiperparametre modu yok: iki başlangıç aynı optimuma gidiyor. Bu yüzden mod ortalaması aday bile yapılmadı.
- **Model etkisi mi, yol etkisi mi?** Aynı yolda C1 ile HA_LEAN'in çevrilme oranları benzer: HA_LEAN'in yolunda C1 0.540, HA_LEAN 0.493 / adım. Eski eğilimli ML-II modeli (HA_TREND) 0.658 ile en dalgalısı. MAP düzeltmesi dalgalanmayı zaten azaltmış.

**Taze veride kayıtlı öngörüler** (STD 323–362; RAND8 ve LOCAL8 de aynı yönde)

| öngörü (koşudan önce yazıldı) | taze değer | tuttu mu |
|---|---|---|
| C1'in gerileme adımlarının ≥ %90'ında ≤ 2 zararlı çevrilme | %96.8 | evet |
| çevrilmelerin ≥ %30'u köşede | %40.4 | evet |
| zararlı / yararlı çevrilme oranı 0.8–1.0 arası | 0.235 / 0.263 = 0.89 | evet |
| düzey payı ≥ S95'in %70'i | %81 | evet |
| AVG4 çevrilmeleri yaklaşık yarıya indirir | 0.497 → 0.256 (0.52) | evet |

## 3. Aday ve kontroller

**Seçim.** DEV'de en çok iki aday elendi:
- **HYST05** (±0.05 karar histerezisi) DEV'de harcama sınırını geçemedi: 0.95 tasarruf alt sınırı −1.27.
- **AVG4** taşındı.

**AVG4'ün tanımı:**
- p̃_b = p_b, b ≤ 24 için;
- p̃_b = (p_{b−3} + p_{b−2} + p_{b−1} + p_b) / 4, b ≥ 25 için;
- karar eşiği 0.5.
- Her p_b, C1'in o bütçede o ana kadar açılmış koşularla verdiği olasılık.
- Sorgu yolu, seçici (C1'in güncel p'si üzerinde margin) ve açılan koşular C1'inkiyle aynı.

**Kontroller** (aynı yol, aynı koşular):
- EVERY4: b ≥ 24 için son 4'ün katı olan bütçenin olasılıkları;
- FREEZE24: b ≥ 24 için p_24.

**Referanslar:**
- değişmemiş C1 + margin;
- HA_LEAN + margin (kendi yolu);
- HA_LEAN'in yolunda C1 (ayrıştırma için).

## 4. Taze sınama sonuçları (STD 323–362, 40 küme, 200 öğrenici)

**Kayıtlı kararlar** (AVG4 − C1)

| karar | sonuç | durum |
|---|---|---|
| İSTİKRAR (birincil) ΔS95 | −0.000001 [−0.00010, +0.00010]; 21/40 küme pozitif | GÖSTERİLMEDİ |
| ERKEN ΔBA-AULC B8–B24 | tam 0 | EŞDEĞER (yapı gereği aynı) |
| DAHA AZ SİMÜLASYON 0.90 / 0.93 / 0.95 | −0.01 / −0.17 / −0.64 [−1.06] | daha kötü değil / daha kötü değil / GÖSTERİLMEDİ |
| SÜRDÜRME 0.93 / 0.95 | +0.065 [+0.032] / +0.070 [+0.037] | KAZANÇ GÖSTERİLDİ / KAZANÇ GÖSTERİLDİ |
| zarar sınırları | iki sınıfın duyarlılıkları, geç BA, 0.90 / 0.93 harcama, 0.95 ulaşma ve koruma: sağlandı; **0.95 harcama: aşıldı** | hepsi sağlanmadı |
| kullanım kararı | | **KEEP_C1_UNCHANGED** |

**Ortalamalar**

| sistem | S95 | düzey payı | titreşim payı | BA-AULC B8–B24 | B24–B60 | toplam dalgalanma |
|---|---|---|---|---|---|---|
| C1 | 0.00698 | 0.00563 | 0.00135 | 0.9396 | 0.9526 | 0.149 |
| AVG4 | 0.00698 | 0.00566 | 0.00131 | 0.9396 | 0.9526 | 0.085 |
| EVERY4 | 0.00723 | 0.00583 | 0.00140 | 0.9396 | 0.9522 | 0.065 |
| FREEZE24 | 0.01058 | 0.01058 | 0 | 0.9396 | 0.9478 | 0 |
| HA_LEAN | 0.00625 | 0.00534 | 0.00091 | 0.9337 | 0.9539 | 0.146 |

**Hedef başına (0.95; 200 öğrenici)**

| sistem | ulaşan | B60'ta koruyan | sonra düşen | sürdüren | onaylanan b (ulaşanlar) | harcama ort. / medyan (ulaşanlar) | kısıtlı-ortalama skor (61 sınırlı) |
|---|---|---|---|---|---|---|---|
| C1 | 163 | 134 | 29 | 31 | 18.02 | 22.02 / 17 | 29.23 |
| AVG4 | 163 | 131 | 32 | 45 | 18.80 | 22.80 / 17 | 29.86 |
| EVERY4 | 157 | 133 | 24 | 46 | 18.17 | 22.17 / 17 | 30.52 |
| FREEZE24 | 124 | 105 | 19 | 37 | 12.17 | 16.17 / 14 | 33.20 |
| HA_LEAN | 160 | 140 | 20 | 35 | 19.54 | 23.54 / 20 | 31.03 |

**Tanımlar:**
- **Onaylanan b:** BA(b) ≥ τ ve BA(b + 4) ≥ τ olan ilk b ≤ 56.
- **Harcama:** onaylanan b + 4. 8 başlangıç koşusu ve 4 onay sorgusu dahil.
- **Sürdüren:** onaylanan b'den 60'a kadar her bütçede ≥ τ.
- **61 sınırlı skor:** maliyet ya da sınır değil.
- **Ulaşanların ortalaması:** genel tasarruf değil.

0.90 ve 0.93 tabloları [RESULTS_C1S.md](evaluation/RESULTS_C1S.md)'de.

**Eşleştirilmiş ulaşma (0.95):**
- ikisi de ulaşan 161; yalnız AVG4 2; yalnız C1 2; hiçbiri 35.
- İkisinin de ulaştığı öğrenicilerde AVG4 daha geç onaylıyor: −0.55 [−0.91, −0.19] (koşullu).
- Harcama kaybı ulaşma kaybından değil, gecikmeden geliyor.

**Kontroller**
- **EVERY4 − C1:**
  - ΔS95 +0.00026 [+0.00010], yani kayıp gösterildi;
  - 0.95 harcama −1.29 [−1.81];
  - sürdürme(0.95) +0.075 [+0.039], AVG4 ile aynı.
- **AVG4 − EVERY4:**
  - ΔS95 −0.00026 [üst sınır −0.00011]; ortalama almak "seyrek güncellemekten" iyi;
  - ama ikisi de C1'i geçmiyor.
- **FREEZE24 − C1:**
  - ΔS95 +0.0036 [+0.0024];
  - 0.95 ulaşma −0.195.
  - 24'ten sonra öğrenmek gerçekten işe yarıyor. Gerilemeler yükselen bir düzeyin etrafındaki gürültü.

**İki sınıf ve ek ölçütler** (AVG4 − C1, B24–B60)

| ölçüt | fark |
|---|---|
| Keyhole duyarlılığı | +0.0001 [−0.0001] |
| iletim duyarlılığı | −0.0001 [−0.0003] |
| FN, bütçe başına | −0.004 [−0.015, +0.006] |
| FP, bütçe başına | +0.008 [−0.003, +0.019] |
| kesinlik (ek) | −0.0002 |
| F2 (ek) | +0.0000 |
| log loss (ek) | +0.0006 [+0.0004] |
| Brier (ek) | +0.0001 [+0.0001] |

Ortalama almak olasılıkları biraz bulanıklaştırıyor. Ek ölçütler kazananı değiştirmez.

**Zor grup** (yalnız değerlendirmede tanımlı; B24–B60 ortalamaları)
- **Kısa-Keyhole NEW duyarlılığı:**
  - C1 0.921, AVG4 0.925, HA_LEAN 0.953;
  - AVG4 − C1 +0.0039 [+0.0016];
  - C1 − HA_LEAN −0.033 [üst sınır −0.014]. EA'daki yönle aynı (B60: 0.915 / 0.955).
- **NEW iletim özgüllüğü:**
  - C1 0.251, AVG4 0.243, HA_LEAN 0.254;
  - AVG4 − C1 −0.0080 [−0.0112, −0.0047].
- Hiçbir sistem zor grubu çözmüyor.

## 5. C1 − HA_LEAN bu üçüncü taze kümede (betimsel)

Bu karşılaştırma C1S'nin kayıtlı kararı değil; protokol gereği yanında raporlanıyor. C1C kapalı.

| ölçüt | C1S (40 küme) | C1C (80 küme) | EA (40 küme) |
|---|---|---|---|
| erken BA-AULC B8–B24 | +0.0059 [+0.0041] | +0.0053 [+0.0039] | +0.0056 [+0.0038] |
| 0.95 kısıtlı-ortalama tasarruf | +1.80 [+0.11] | +1.81 [+0.53] | +2.00 [+0.21] |
| 0.95 ulaşma | +0.015 [−0.026] | +0.040 [+0.011] | – |
| 0.95 koruma (B60) | **−0.030 [−0.071]** | +0.015 [−0.016] | +0.020 |
| 0.95 sürdürme | −0.020 [−0.076] | −0.007 [−0.044] | +0.055 [+0.001] |
| geç BA-AULC B28–B60 | −0.0013 [−0.0027] | −0.0006 [−0.0013] | – |

- **Erken üstünlük ve 0.95 tasarrufu yeniden görüldü.**
- **Koruma bu kümede zayıf.** C1C'deki "0.05 içinde koruma" eşdeğerliği burada sağlanmıyor (alt sınır −0.071). Ulaşıp sonra düşen: C1 29, HA_LEAN 20.
- C1C kararı değişmiyor. Ama 0.95'i koruma iddiasına ek bir çekince düşülüyor (iddia C137).

## 6. Başlangıç kontrolleri (betimsel, 10'ar küme)

| | RAND8 363–372 | LOCAL8 373–382 |
|---|---|---|
| ΔS95 (AVG4 − C1) | +0.00003 [−0.00009, +0.00015] | −0.00002 [−0.00023, +0.00019] |
| 0.95 harcama | −1.00 [−1.89] | −0.58 [−1.28] |
| sürdürme(0.95) | +0.040 [−0.009] | +0.140 [+0.062] |
| zarar sınırları | sağlanmadı (0.95 harcama, ulaşma, koruma) | sağlanmadı (0.95 harcama) |
| C1 − HA_LEAN erken | +0.0086 [+0.0040] | +0.0075 [+0.0024] |
| tek sınıflı başlangıç | 3/50 (ek sorgu ort. 0.08) | 41/50 (ek sorgu ort. 1.00, en çok 3; harcamaya dahil) |

**Başlangıç kuralı:** RAND8'de ΔS95 ortalaması > 0 ve iki kümede de zarar sınırı aşılıyor. AVG4 benimsenmiş olsaydı öneri standart maximin başlangıçla sınırlanacaktı. Benimsenmediği için kural uygulanmıyor.

## 7. DEV beklentisi ve taze sonuç

| ölçüt | DEV (C1C verisi) | taze | yorum |
|---|---|---|---|
| ΔS95 | −0.0001 [üst −0.0000] | −0.000001 [üst +0.0001] | DEV'deki küçük kazanç tekrarlanmadı |
| sürdürme(0.95) | +0.058 [+0.037] | +0.070 [+0.037] | tekrarlandı |
| 0.95 tasarruf | −0.52 [−0.91] | −0.64 [−1.06] | aynı yön; sınır bu kez aşıldı |
| 0.95 ulaşma | ≈ −0.02 | 0.000 [−0.017] | sınır içinde |
| erken | aynı | aynı | yapı gereği |

## 8. Maliyet

| iş | birim | hata | birim duvar saati | kayıtlı CPU saati |
|---|---|---|---|---|
| c1s-trace-smoke (DEV) | 1 | 0 | 0.003 | 0.002 |
| c1s-trace (DEV yeniden oynatma) | 50 | 0 | 0.137 | 0.136 |
| c1s-main (STD) | 400 | 0 | 2.568 | 2.935 |
| c1s-start (RAND8 + LOCAL8) | 200 | 0 | 1.300 | 1.493 |
| **toplam** | **651** | **0** | **4.01** | **4.57** |

**Süre ve CPU**
- Taze sınama duvar saati: 00:46 – 02:05 UTC, 3 işçiyle yaklaşık 1.3 saat.
- Değerlendirme 29 s, dışa aktarım 23 s sürdü; ikisi de tek işlem.
- Karar adımı başına CPU: HA_LEAN 0.135 s, C1 0.163 s (1.2 kat). AVG4, EVERY4 ve FREEZE24 yalnız saklı vektörleri ortalıyor ya da kopyalıyor.

**Simülasyonlar**
- Her öğrenici yolu 60 koşu açar: 8 ortak başlangıç + 52 sorgu.
- STD: HA_LEAN yolu 12.000, C1 yolu 12.000 koşu-ücreti. Bir öğrenicinin iki yolundaki farklı koşu sayısı ortalama 68.1.
- RAND8 + LOCAL8: 6.000 + 6.000.
- AVG4, EVERY4, FREEZE24 ve çapraz tahminler: 0 ek koşu.
- DEV yeniden oynatma 0 yeni koşu açtı; hiçbir koşu iki kez ücretlendirilmedi.
- Bütün koşular mevcut 541 koşuluk havuzdan. Yeni fiziksel simülasyon ya da ücretli hizmet yok.
- Ayrıntı: [COST_BREAKDOWN.json](COST_BREAKDOWN.json).

## 9. Teslim edilenler

| içerik | yol (görev klasörüne göre) |
|---|---|
| tahminler (her öğrenici, her bütçe, 6 sistem) | `exports/main/predictions_f32.npz`, `exports/start_rand8/…`, `exports/start_local8/…` |
| sorgu kimlikleri ve yollar | `exports/*/paths.csv.gz` |
| kararlar ve bütün karşılaştırmalar | `evaluation/C1S_DECISION.json`, `evaluation/RESULTS_C1S.md`, `evaluation/*_stability.csv.gz`, `*_supplementary.csv.gz` |
| bağımsız yeniden hesaplama | `exports/EXPORTS_ACCEPTANCE.json` (3 küme × 2 kontrol: 6/6 GEÇTİ) |
| maliyet | `COST_BREAKDOWN.json` |
| dondurma | `freeze/C1S_MANIFEST.json`, `PROTOCOL_C1S.md` |
| DEV teşhisi ve eleme | `diag/`, `dev/`, `c1s-trace/units` |
| Graphify notu, kod haritası ve yerel harita | `graphify/` |
| Research Hub ilişkisi ve Astra kaydı | `hub/RESEARCH_HUB_RELATION.md`, `hub/ASTRA_CENTRAL_RECORD.md` |

**Hatalar ve düzeltmeler.** Hiçbiri sonucu etkilemedi:
- `c1s_trace` ilk denemede `KeyError: 8` verdi (b < 10'da 10'dan az kat). DEV koşusundan önce `dict.get` ile düzeltildi.
- `c1s_eval` iki hata ile yazılmıştı. Dondurmadan önce düzeltildi ve kuru koşuyla doğrulandı:
  - anatomi BA'sı yanlış yoldan hesaplanıyordu;
  - havuzlanmış istikrar tablosunda öğrenici sütunu eksikti.
- Yerel harita betiği Graphify sürüm niteliğinde hata verdi; `importlib.metadata` ile düzeltildi.
- Taze birimlerin hiçbiri başarısız olmadı.

## 10. Değişen Python dosyaları ve sürümleri

**Mevcut hiçbir dosya değişmedi.** `src/` 3caf7c4e'ye göre yalnız yeni dosyalar içeriyor. Hepsi 9cad00ad'de donduruldu; SHA-256 değerleri:

| dosya | SHA-256 | görev |
|---|---|---|
| `src/c1s_diag.py` | 92b2f2b43904ad19678558fec57f05af3eee8cffda1c364bfa903482ae1683fd | DEV anatomi (C1C dışa aktarımlarından) |
| `src/c1s_trace.py` | a3797fd96df65162bc2592b313d66f7c293b9fb65bbe9d88de8eed9e8713b208 | bit düzeyinde yeniden oynatma ve bileşen ayrıştırması |
| `src/c1s_dev.py` | d397754379c93c6021943547d715a0ba8740a841269f5c7a1d6ad78af5c78b09 | karar katmanı varyantları, S95, DEV elemesi |
| `src/c1s_fwd.py` | 655f77c6fe3249e658194dd234e2a714a9685451e81ecaa3c024571d79e40d72 | taze birimler (`ea_fwd` ve `c1c_fwd` değişmeden çağrılır) |
| `src/c1s_eval.py` | 0b1ccf18b69fcc0283d08a141effbdbdc494ee8695dc607e24e5c1cb366fc39b | kayıtlı değerlendirme ve karar |
| `src/c1s_export.py` | e465174e5af4f090c60a02ae23937e714b07266231423cad708b00ce2063c043 | dışa aktarım ve bağımsız yeniden hesaplama |
| `src/c1s_freeze.py` | e8e74e3ffaf1cf4d7e99bdc4bf6e64677a6aa9d5adc7c3dd7074ba3a689c9f11 | manifest ve kontrol |

Çalıştırıcılar: `src/c1s_runner.ps1` (79cc4dd2…), `src/c1s_supervisor.ps1` (3fca6fed…), `src/c1s_start_runner.ps1` (d80f3e50…).

**Yerel Graphify haritası** (yalnız bu dosyalar, yalnız AST): [graphify/local_map/LOCAL_MAP_MANIFEST.json](graphify/local_map/LOCAL_MAP_MANIFEST.json), 92 düğüm, 233 kenar. Paylaşılan grafik değişmedi; bütün depo yeniden taranmadı.

## 11. Research Hub ve Astra

**Research Hub.**
- C1S, Hub'daki **C1C-002**'nin açık sorusuna bağlanıyor: sürdürme iyileşmedi.
- C1C-001, C1C-003 ve C1C-004 olduğu gibi kalıyor.
- Ayrıntı ve kaynak yollar: [hub/RESEARCH_HUB_RELATION.md](hub/RESEARCH_HUB_RELATION.md).
- Main'de birleştirme yapılmadı.

**Astra.**
- Dört Astra kampanyasının (AD18, RP20, LC24, JL26) eksik merkezi kayıtları, Hub'ın yayımlanmış raporlarından **KAYNAKTAN AKTARILMIŞ** olarak tamamlandı: [hub/ASTRA_CENTRAL_RECORD.md](hub/ASTRA_CENTRAL_RECORD.md).
- Opus hiçbirini yeniden hesaplamadı.
- Astra'nın canlı klasörüne, ortamına, Git'ine ve süreçlerine dokunulmadı.
- Yeni bağımsız modülü beklenmedi ve entegre edilmedi.

## 12. Sınırlar

- **Yalnız havuz içi.** Bütün kimlikler aynı 541 koşunun yeni bölünmeleri ya da başlangıçları.
- **Yenilik iddiası yok.** Tahmin olasılıklarını zamanda yumuşatmak bilinen bir karar katmanı yöntemi.
- **Katkı:** C1'in geç gerilemelerinin ölçülmüş mekanizması, bunun ileriye dönük doğrulanması ve en basit dengeleyicinin kayıtlı olumsuz testi.
- **Sonraki mantıklı adım** (yalnız öneri): kalan düzey açığı bir bilgi sorunu. Zor katlardaki iç içe Keyhole / iletim koşularını ayıracak yeni bir girdi ya da etiket bilgisi olmadan, havuz içi dengeleyiciler bu açığı kapatamaz. Bu görevde başka varyant koşulmadı.
