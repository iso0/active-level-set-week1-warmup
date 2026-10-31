# IR sonuç raporu: Ioan'ın 30 Ekim istekleri

- **Kapsam:** 2026-10-31, 16:09–17:05 UTC.
- **Dal ve kayıt:** dal `ioan-requests-20261031`. Kayıt `0ecf9f70`, hiçbir sayı hesaplanmadan önce yapıldı.
- **Hesaplama:** 0 yeni simülasyon, en fazla 3 tek iş parçacıklı işçi, yaklaşık 1.5 işçi-saat.

**Karar: V-A CEVAPLANDI, KAZANÇ YOK.**
- İlişkiler ölçüldü. Diğer fiziksel çıktılar derinlikle güçlü ilişkili, genişlik ise orta düzeyde.
- Bu ilişkileri kullanmak simülasyon sayısını azaltmıyor.

## 1. Kısa cevap

1. **KE, sıcaklık, akış ve enerji derinlikle güçlü ilişkili** (Spearman ρ 0.71–0.93).
   - Bu ilişkinin neredeyse tamamı ortak bir sebepten geliyor: girdilerden, özellikle h = P/√(VX·LS³)'ten.
   - Girdiler bilindikten sonra kalan ilişki küçük. GP artık korelasyonu ≤ 0.27; tek istisna hız sıçraması oranı (0.43).
2. **Genişlik derinlikle orta düzeyde ilişkili** (ρ 0.50).
   - Conduction'da derinlik genişlikle neredeyse orantılı büyüyor: eğim 0.90, D/W ≈ 0.34.
   - Keyhole'da derinlik genişliğin yarısını aşıyor: D/W medyanı 0.89 (tavan altı) ile 1.46 (tümü) arasında.
   - Literatürdeki "W/D ≤ 2" kuralı parametresiz olarak BA 0.978 veriyor. Ama genişlik tek başına zayıf (AUC 0.64) ve derinliğe bilgi eklemiyor.
3. **Gerçek değerlerle bile hiçbir çıktı h + derinliğe etiket bilgisi eklemiyor.**
   - Derinlik, girdilerden etikete giden yolun aracı değişkeni.
   - Diğer çıktılar aynı sebebin kardeş sonuçları.
4. **Simülasyon tasarrufu yok.**
   - Altı aday denendi: çok çıktılı GP (LMC) ve Ioan'ın zinciri (CHAIN), genişlik / KE / sıcaklık ile. Hiçbiri C1'in açılmamış noktalardaki derinlik tahminini anlamlı biçimde iyileştirmedi. En iyisi +0.0001 BA; CHAIN zarar verdi.
   - Test noktalarındaki gerçek KE verilse bile kazanç +0.001 BA.
   - Kayıtlı kural gereği aşağı akış ve taze test koşulmadı.
5. **Zaman serisi:** Keyhole başlangıcından önce belirgin biçimde yükselen tek sinyal maksimum sıcaklık (ilk Keyhole karesinden yaklaşık 28 µs önce).
   - Tavana ulaşmayan Keyhole koşularında emilen lazer gücü ve genişlik de önceden yükseliyor.
   - KE önceden yükselmiyor.
6. **Önemli veri bulgusu:** Keyhole koşularının %68'i (134/197) yaklaşık 300 µm derinlik tavanında.
   - Bu muhtemelen alan veya altlık tabanı. Week 19'da da işaretlenmişti, doğrulanamadı.
   - Bu yüzden Keyhole içindeki derinlik ilişkileri sansürlü.

## 2. Ne yapıldı

| bölüm | içerik | etiket |
|---|---|---|
| P1 veri | genişlik W_A, W_T0, W_atA, uzunluk L_A ve 6 kanalın (KE, T, V, lazer, toplam enerji, parçacık) aktif pencere değerleri ile zaman serisi istatistikleri; derinlikle aynı monitör dosyası ve aynı denetlenmiş Week 19 kodu | DATA |
| A | korelasyon yapısı (bootstrap GA), girdiler bilinince kalan ilişki, genişlik–derinlik fiziği, gerçek değerlerle etiket bilgisi, aracı değişken analizi | DESCRIPTIVE |
| B | her çıktının küçük bütçede girdilerden öğrenilebilirliği (kayıtlı C1 yolları) | DEV-DESCRIPTIVE |
| C | yöntem taraması: 6 aday, 5 kontrol, 272 öğrenici-yolu × 8 bütçe, önceden kayıtlı taşıma kuralı S1–S4 | DEV |
| D, E | aşağı akış DEV ve taze test; yalnız C bir aday taşırsa koşacaktı | koşulmadı |
| F | koşu içi zaman bağı: korelasyon, öncülük-gecikme, Keyhole başlangıcına hizalı ortalamalar, erken pencere | DESCRIPTIVE |
| G | literatür: W/D kriterleri, normalize entalpi, çok çıktılı GP'de transfer teorisi | LITERATURE |
| X | kayıt sonrası ekler: W/D ≤ 2.75 ve ~300 µm tavanı | EXTRA |

**Kabul testleri (hepsi geçti):**

| test | ne doğrulandı |
|---|---|
| V1 | derinlik havuzdakiyle birebir aynı (540 koşu, en büyük fark 6e-14 µm) |
| V2 | gölge testi: açılmamış koşuların çıktıları karıştırılınca 16 modelin hiçbir tahmini değişmiyor |
| V3 | LMC analitik gradyanı sayısalla eşleşiyor (bağıl fark 1e-9); indirgeme birebir; gürültüsüz eş-noktalı ICM'de transfer iptal oluyor |
| V4 | CHAIN dürüstlüğü |
| V5 | C1 kayıtlı olasılıkları birebir yeniden üretiyor (fark 0) |
| V6 | değerlendirme haritası g* dondu (gerçek derinlikle BA 0.978) |
| bağımsız yeniden hesaplama | S1–S4 ayrı kodla aynı sonucu veriyor (fark 0.0) |

Bütün LMC, SUM2 ve ICM uydurmaları yakınsadı: her biri 2176/2176.

**Regresyon testleri** (12. hafta ve sonrası, 26 dosya; `REGRESSION_TESTS.log`): 199 geçti, 2 atlandı, 2 kaldı. İki başarısızlık da IR'den önce var. IR bu dosyalara dokunmuyor; IR dalında bu yollarda değişiklik yok.
1. `test_reports_use_full_simulation_ids`: `outputs/joint_depth_label_development/ATTEMPT_LEDGER.md` dosyasının 84. ve 93. satırlarında kısaltılmış H-kimlikleri var. Dosya en son e2cfd7bf'de (16 Ekim) değişti.
2. `test_t_tobit_truth_is_the_frozen_phase2_truth`: Week 18 T_TOBIT dondurulmuş hiperparametre kontrolünde sayısal sapma var. IR'nin hiçbir dosyasını okumuyor.

**Kayıt öncesi açıklama:** 31 Ekim'deki ilk bakış kayıttan önce yapılmıştı (`prelook/`, defterde IR-PRE). Bu bakış genişlik ve sıcaklığın da aday olmasına yol açtı. Hiçbir eşik ondan türetilmedi.

## 3. Q1: fiziksel çıktılar ve derinlik (Şekil 1)

Örneklem: 534 tam kayıt (T0 çıktılarında 479). Tablodaki sınıf sütunları yalnızca o sınıfın koşularını içeriyor.

| çıktı | ρ, tümü [%95 GA] | ρ, conduction | ρ, Keyhole | girdiler bilinince kalan (GP artığı) | girdilerden öğrenilebilirlik, tüm veri (R²) |
|---|---|---|---|---|---|
| log h (girdi formülü) | 0.945 [0.932, 0.955] | 0.83 | 0.83 | – | – |
| KE, aktif maksimum | 0.926 | 0.86 | 0.47 | 0.02 | 0.42 |
| KE, T0 | 0.898 [0.876, 0.914] | 0.86 | 0.29 | 0.15 | 0.98 |
| maks. sıcaklık, T0 | 0.848 [0.811, 0.878] | 0.42 | 0.77 | 0.20 | 0.97 |
| hız sıçraması oranı | 0.851 | 0.61 | 0.47 | 0.43 | 0.94 |
| emilen lazer gücü, T0 | 0.815 | 0.85 | 0.17 | 0.15 | 0.99 |
| toplam enerji, T0 | 0.801 | 0.83 | 0.37 | 0.24 | 0.98 |
| maks. hız, aktif maksimum | 0.710 | −0.07 | 0.57 | 0.27 | 0.80 |
| genişlik W_A | 0.498 [0.419, 0.570] | 0.61 | 0.49 | 0.06 | 0.85 |
| uzunluk L_A | 0.519 | 0.63 | −0.42 | 0.20 | 0.97 |

Aynı GP'nin derinlik için tüm veriyle verdiği R² 0.988. Sınır bölgesinde (q20) genişliğin derinlikle ilişkisi yalnızca 0.11.

**Yorum:**
- Conduction'da derinlik enerjiyle birlikte büyüyor: KE, lazer, toplam enerji ρ 0.83–0.86.
- Keyhole'da enerjiyle bağ zayıf, sıcaklıkla güçlü (ρ 0.77). Ama Keyhole sütunu tavan yüzünden sansürlü:
  - tavanın altındaki 63 koşuda derinlik en çok hız sıçraması (0.82), sıçrama süresi (0.81), maksimum hız (0.62) ve toplam enerji (0.61) ile ilişkili;
  - aynı koşularda genişlikle ilişki 0.08, KE ile 0.11 (EXTRA).
- Kritik nokta: ham korelasyonların büyük bölümü girdilerden geliyor. Girdiler bir kez bilindiğinde diğer çıktılar derinlik hakkında yeni bir şey söylemiyor.

## 4. Q2: genişlik ve derinlik (Şekil 2)

| ölçü | conduction | Keyhole |
|---|---|---|
| log D – log W eğimi (Theil–Sen) | 0.90 [0.79, 1.01] | tümü 0.03 [0.02, 0.05]; tavan altı (n 61) 0.16 [−0.40, 0.70] |
| D/W medyanı (IQR) | 0.34 (0.29–0.39) | tümü 1.46 (1.25–1.65); tavan altı 0.89 (0.68–1.23) |

**Parametresiz literatür kuralları ("W/D ≤ c ise Keyhole"):**

| c | BA | duyarlılık | özgüllük | kaynak |
|---|---|---|---|---|
| 1.5 | 0.960 | 0.938 | 0.982 | Johnson 2019 |
| 2.0 | **0.978** | 0.995 | 0.962 | Zhang 2021 |
| 2.5 | 0.886 | 1.000 | 0.771 | Sheikh 2023, Tablo 1 |
| 2.75 (ek) | 0.806 | 1.000 | 0.613 | Sheikh 2023, Denklem 8 |

**Eşik öğrenen sınıflandırıcılar** (10-katlı CV, 20 tekrar):

| özellik | BA | AUC |
|---|---|---|
| log D | 0.982 | 0.999 |
| log(D/W) | 0.976 | 0.998 |
| log W | 0.645 | 0.637 |

**Yorum:**
- Genişlik–derinlik oranı fiziksel olarak anlamlı bir rejim göstergesi. Klasik "derinlik > genişlik/2" sınırı simülasyonlarımızda çok iyi çalışıyor.
- Ama bu başarının kaynağı derinlik: genişlik tek başına neredeyse bilgisiz. Oran, derinliğin kendisinden biraz kötü.
- Keyhole'da "derinlik genişlikten kopuyor" görüntüsü (eğim 0.03) büyük ölçüde ~300 µm tavanından kaynaklanıyor. Tavanın altında eğim belirsiz.

## 5. Q3: Bu ilişkiler simülasyon sayısını azaltır mı?

**5a. Etiket bilgisi, gerçek değerlerle** (Şekil 3; 479 koşu, 20×10-katlı CV, L2 lojistik):
- **Taban:** [h, D] → log kayıp 0.0662, BA 0.976.
- **Her çıktı tek tek eklenince:** log kayıp −0.0013 ile +0.0148 arası değişiyor, BA +0.0001 ile −0.0096 arası.
  - Genişlik: +0.0004 / +0.0001.
  - KE: +0.0011 / −0.0038.
  - Sıcaklık: +0.0018 / −0.0017.
  - Bütün T0 çıktıları birlikte: +0.0036 [0.0029, 0.0043] / −0.0094.
- **Doğrusal olmayan kontrol** (gradient boosting): BA'da +0.003'e kadar, ama log kayıp iyileşmiyor. Pratik bir kazanç yok.
- **Aracı değişken analizi:**

  | özellikler | log kayıp |
  |---|---|
  | 4 log girdi | 0.126 |
  | 4 log girdi, kuadratik terimlerle | 0.109 |
  | yalnız derinlik | 0.065 |
  | h + derinlik | 0.061 |
  | girdiler + derinlik | 0.0625 |
  | girdiler + derinlik + genişlik | 0.0625 |

  Derinlik, girdilerin etiket hakkında söylediği her şeyi taşıyor.

**5b. Küçük bütçede öğrenilebilirlik** (Şekil 5; kayıtlı C1 yolları, STD 200 öğrenici-yolu, medyan test R²):

| çıktı | b = 8 | b = 16 | b = 24 | b = 60 | R² ≥ 0.8'e ulaşan |
|---|---|---|---|---|---|
| derinlik (C1 modeli) | **0.87** | **0.91** | **0.92** | **0.93** | 200/200, medyan b = 8 |
| maks. sıcaklık | 0.85 | 0.90 | 0.90 | 0.90 | 200/200, medyan b = 8 |
| KE | 0.76 | 0.90 | 0.90 | 0.92 | 200/200, medyan b = 12 |
| genişlik | 0.50 | 0.75 | 0.73 | 0.64 | 98/200; 102 yol 60'a kadar hiç ulaşmıyor |
| toplam enerji / parçacık | 0.37 | 0.70 | 0.81–0.82 | 0.88 | 185 / 187 |
| lazer gücü | 0.55 | 0.70 | 0.75 | 0.86 | 153 |
| hız sıçraması | 0.68 | 0.72 | 0.73 | 0.77 | 83 |

Derinlik en kolay öğrenilen çıktı. Ioan'ın zincirinde ara büyüklük derinlikten kolay öğrenilmiyor, bu yüzden zincirin kazandıracağı bir şey yok.

**5c. Yöntem taraması** (Şekil 4):
- **Ne karşılaştırıldı:** C1'in derinlik modeli R0 ile adaylar, aynı açılmış simülasyonlar üzerinde.
- **Vekil BA:** derinlik tahmini dondurulmuş g*(h, â) haritasından geçirilip etikete çevriliyor.
- **R0 düzeyleri:**

  | küme | R0 | gerçek derinlik tavanı |
  |---|---|---|
  | STD, erken bütçe | 0.948 | 0.978 |
  | geometrik bloklar | 0.680 | 0.888 |

**Sonuçlar** (fark = aday − R0, küme ortalaması [tek yönlü %95 sınır]):

| model | S1: STD erken BA (eşik ≥ +0.005, LCB > 0) | S2: sınırda (q20) derinlik hatası, erken | S3: STD geç BA (LCB) | S4: geometrik BA (LCB) | geçti mi |
|---|---|---|---|---|---|
| LMC_W | −0.0009 [−0.0015] | +%1.8 | −0.0007 | −0.0062 | hayır |
| LMC_KE | +0.0001 [−0.0006] | +%1.5 | −0.0006 | −0.0206 | hayır |
| LMC_T | −0.0007 [−0.0013] | −%0.3 | −0.0012 | −0.0112 | hayır |
| CHAIN_W | −0.0041 [−0.0053] | +%11.5 | −0.0009 | −0.0042 | hayır |
| CHAIN_KE | −0.0021 [−0.0031] | +%7.6 | −0.0006 | −0.0100 | hayır |
| CHAIN_T | −0.0034 [−0.0042] | +%6.3 | −0.0009 | −0.0099 | hayır |
| kontrol SUM2 | −0.0001 | 0.0 | – | −0.0034 | kontrol |
| kontrol ICM_W | −0.0013 | +%2.1 | +0.0010 | **+0.0069** (ortalama +0.017) | kontrol |
| kontrol ORACLE_CHAIN_KE (gerçek KE her yerde) | **+0.0011 [+0.0002]** | −%2.7 | – | – | kontrol |
| kontrol ORACLE_CHAIN_W (gerçek genişlik her yerde) | +0.0003 | +%1.6 | – | – | kontrol |

**Yorum:**
- **LMC etkisiz.** Gürültü küçük ve bütün çıktılar aynı noktalarda ölçülüyor. Teorinin öngördüğü gibi transfer neredeyse sıfır (Bonilla vd. 2007; Wackernagel, "autokrigeability").
- **CHAIN zararlı.** Ara büyüklüğün tahmin hatasını derinliğe taşıyor.
- **"Kehanet" kontrolü belirleyici.** Test noktasındaki gerçek KE bile yalnızca +0.001 BA kazandırıyor. Bu yol en iyi durumda bile sınırlı.
- **Karar:** taşınan aday yok, D ve E koşulmadı. Taze kimlikler kullanılmadı: STD 383+, K5 49+, K4 33+.
- **İpucu, sonuç değil:** ICM_W kontrolü geometrik bloklarda +0.017 veriyor, ama STD'de erken bütçede zarar ediyor. Protokol kontrolleri taşımaya izin vermiyor. Ancak ayrı ve kayıtlı bir testle anlam kazanır.

## 6. Q4: Koşu içi zaman bağı (Şekil 6)

**F1, koşu içi ρ medyanı:**
- Conduction: KE 0.71, toplam enerji 0.66, parçacık 0.64, uzunluk 0.63; genişlik 0.24; sıcaklık −0.12.
- Keyhole: **emilen lazer 0.73**, KE 0.61, hız 0.49, genişlik 0.44, sıcaklık 0.42.
- Yorum: Keyhole'da derinlik dalgalanması emilen lazer gücüyle birlikte hareket ediyor. Bu, kavitenin emilimi artırmasıyla tutarlı.

**F2, öncülük-gecikme:** sonuçsuz.
- Birinci farklarda en iyi gecikme her sinyal için 0 µs.
- Düzey korelasyonları eğilim tarafından domine ediliyor: koşuların bir kısmında ±100 µs sınırına dayanıyor.

**F3, ilk Keyhole karesine hizalı ortalamalar:**
- Tüm 197 Keyhole koşusu: ilk kareden önce kontrol düzeyinin üstüne sürekli çıkan **tek sinyal maksimum sıcaklık** (−28 µs'den itibaren).
  - [−50, −1] µs aralığında fark +0.10 z [0.003, 0.19].
  - Hız ve lazer gücü başlangıçtan sonra yükseliyor: [0, 50] µs aralığında +0.58 ve +0.31.
  - Derinlik kontrol düzeyini yaklaşık +28 µs'de geçiyor.
- Tavan altındaki 63 koşu (EXTRA): [−50, −1] µs aralığında farklar:
  - sıcaklık +0.58 [0.43, 0.73];
  - lazer +0.42 [0.25, 0.57];
  - genişlik +0.37 [0.27, 0.47];
  - hız +0.15 (anlamlı değil);
  - KE −0.50.
- Fiziksel okuma: yüzey sıcaklığı buharlaşmaya yaklaşırken kavite açılıyor. Uyarı: ilk Keyhole karesi el ile verilmiş bir etiket ve kareler yaklaşık 8 µs aralıklı. Öncülük etikete göre ölçülüyor.

**F4, keşif amaçlı:** aktif pencerenin ilk %25'indeki maksimum sıcaklık nihai derinlikle ρ 0.84 ilişkili ve etiket için AUC 0.97 veriyor (aynı penceredeki derinlik: 0.77 / 0.92). Ama h tek başına zaten AUC 0.99 veriyor. Kısa simülasyonla erken tahmin ancak simülasyon süresi maliyeti açısından ilginç olur; bu gelecek çalışma.

## 7. Sınırlar

1. A ve F bölümleri tüm koşuların gerçek değerlerini kullanıyor (değerlendirici görünümü). Öğrenici sonucu değiller.
2. C bölümü vekil BA kullanıyor: dondurulmuş g* haritası. C1'in gerçek sınıflandırıcısıyla aşağı akış testi kayıtlı kural gereği koşulmadı.
3. Yalnızca 3 ara çıktı (W, KE, T) ve 2 model ailesi tarandı. Özellik yolu ise gerçek değerlerle zaten kapandı (5a); paylaşılan uzunluk ölçeği yolu RC19 ve RC23'te denenmişti.
4. **~300 µm tavanı:** 134/197 Keyhole koşusu; alan tabanı olduğu doğrulanmadı (parametre dosyası yerelde yok). Keyhole içi derinlik ilişkileri sansürlü. Sınıflandırmaya zararı yok: tavandaki koşuların hepsi Keyhole.
5. Sıcaklık, hız, lazer, enerji ve parçacık kanalları 55–56 eski koşuda yok.
6. Johnson 2019 eşiğinin yönü (W/D ≤ 1.5) ikincil kaynaktan alındı. Tezde alıntılamadan önce orijinal makalede kontrol edilmeli.

## 8. Tez için anlamı

- C1 (derinlik + log h) yeterli. Ek fiziksel çıktılar simülasyon sayısını azaltmıyor.
- Kalan erken hata, açılmamış noktalardaki derinlik bilgisinin sınırı. Bu, EA ve FR bulgularıyla tutarlı.
- Tezde kullanılabilecek cümle: "Diğer fiziksel çıktılar derinlikle güçlü ilişkili; ama bu ilişki aynı süreç girdilerinin ortak etkisi. Girdiler bilindiğinde derinliğe ek bilgi taşımıyorlar. Ne gerçek değerleriyle sınıflandırıcıya, ne çok çıktılı ya da zincirleme GP'lerle derinlik tahminine katkı veriyorlar."

## 9. Dosyalar

- `PROTOCOL_IR.md`, `TASK.md`, `ATTEMPT_LEDGER.md`, `STATE.json`, `README.md`.
- `descriptive/`, `screen/`, `temporal/`, `extras/`, `figures/` (Şekil 1–6).
- `exports/screen/`: tahminler ve yollar; `EXPORTS_ACCEPTANCE.json`.
- `LITERATURE.md`.
- İngilizce özet: `IOAN_SUMMARY.md`.

**Karar: V-A CEVAPLANDI, KAZANÇ YOK.**
