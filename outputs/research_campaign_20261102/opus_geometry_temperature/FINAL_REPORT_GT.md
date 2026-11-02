# GT sonuç raporu: geometrik Keyhole sınıflandırıcısı ve erken sıcaklık

> **Karar: C1 KORUNUYOR.**
> - Tahmin edilen derinlik ve genişlikten kurulan geometrik sınıflandırıcıların hiçbiri, aynı açılmış simülasyonlarda C1 + margin'e yaklaşamadı. En iyisi erken BA-AULC'de −0.017 geride kaldı.
> - Erken sıcaklık ne simülasyon sayısına ne de yürütme süresine ek katkı gösterdi.
> - Kayıtlı kurallar gereği kendi-yol (G3) ve taze doğrulama (G4) aşamaları koşulmadı. Taze kimlikler kullanılmadı.

- **Kapsam.** 2026-11-02, 17:45–20:00 UTC. 24 saatlik pencere (2026-11-03 17:45 UTC'ye kadar) erken kapandı.
- **Dal.** `geometry-temperature-20261102`, IR sonucu 0a57d644'ten açıldı. main'e merge yok.
- **Kayıt.** `9dcee41f`. Hiçbir öğrenici, sınıflandırıcı ya da etiket ilişkisi sayısından önce gönderildi.
- **Hesaplama.**
  - 0 yeni simülasyon.
  - 541 koşuluk tek havuz.
  - En çok 6 tek iş parçacıklı işçi, BLAS = 1.
  - Yaklaşık 7 işçi-saat: G2'de 272 birim, QT-B'de 0.15 işçi-saat.

## 1. Ne istedik?

Mevcut C1 + margin yöntemini gerçekten geliştirebilecek iki açık yolu adil biçimde sınamak:
1. **Geometri.** Tahmin edilen derinlik d ve genişlik w'den, fiziksel sınır d / w = 1/2 (W/D ≤ 2) ile kurulan bir Keyhole sınıflandırıcısı. Bu, az simülasyonla daha yüksek BA verir mi?
2. **Erken sıcaklık.** Bilgi, simülasyon sayısına mı (yeni ayarlarda önceden tahmin) yoksa yürütme süresine mi (başlamış koşuyu erken değerlendirmek) katkı sağlar?

Yanında IR'nin yorumları düzeltilecek, ~300 µm derinlik yığılması araştırılacak ve merkezi tez kayıtları tamamlanacaktı.

**IR ile fark.** IR, genişliği DERİNLİK tahminini iyileştirmek için kullandı (eş-çıktı GP). Burada geometri doğrudan SINIFLANDIRICI oluyor: sabit fiziksel eşik etiketsiz bir karar veriyor. Bu soru daha önce sınanmamıştı.

## 2. Kısa cevap

1. **Ölçüm tanımları denetlendi.**
   - Genişlik ışın çapı değil, eriyik havuzu genişliği: W_A / (2·LS) medyanı 1.54; log ilişki ρ yalnızca 0.26.
   - IR'nin oranı (A / W_A) eşzamanlı değil: iki maksimum medyan 0.35 ms arayla oluşuyor.
   - Gerçek değerlerle etikete uyum (betimsel; bir model başarısı ya da tavan değil): R1 maksimumlar 0.977, R2 en derin anda 0.974, R3 anlık oranın maksimumu 0.969.
2. **Geometrik sınıflandırıcılar C1'den belirgin biçimde kötü** (DEV; 200 STD öğrenicisi, kayıtlı C1 yolları, aynı açılmış simülasyonlar).
   - Erken BA-AULC (B8–B24) farkı: en iyisi GEO_B1 −0.017 [−0.020, −0.015], en kötüsü −0.048.
   - Hedefe ulaşma: 0.95'e C1'in 169/200'üne karşı GEO_B1'in 124/200 öğrenicisi ulaştı.
3. **Neden** (kayıt sonrası betimsel mekanizma). Sabit eşik g = log(2d/w) = 0, iki sınıf kümesinin ortasında değil, conduction kümesinin kıyısında duruyor.
   - Gerçek değerlerde conduction'ın %95'liği g = −0.03; Keyhole'un %5'liği +0.27.
   - GP iki küme arasındaki sıçramayı yumuşatınca sınıra yakın conduction koşuları eşiğin üstüne itiliyor.
   - Sonuç: Keyhole geri çağırması C1'den yüksek (0.985 / 0.935), conduction geri çağırması düşük (0.860 / 0.945).
4. **Doğrudan oran hedefi (B), iki büyüklüğü ayrı tahmin etmekten (A) kolay** (B1 − A1 = +0.009), ama yine C1'in gerisinde.
   - Anlık oran hedefleri daha da zor.
   - Etiketle kalibrasyon (CAL_B1) farkı −0.009'a indiriyor ama kapatmıyor.
   - Oranı C1'e eklemek (C1_G) hiçbir şey değiştirmiyor (−0.0008). Oran, derinlik ve genişliğin yeniden yazımı olduğundan bu beklenen bir sonuç; yeni bilgi bulunmadı.
5. **Erken sıcaklık A (simülasyon sayısı).**
   - Tahmin edilen erken sıcaklığı C1'e eklemek zarar veriyor: −0.0069 [−0.0082, −0.0056].
   - Test koşusunun GERÇEK erken sıcaklığı verilse bile C1'in gerisinde: −0.0037.
6. **Erken sıcaklık B (yürütme süresi).** Başlamış bir koşunun ilk 0.5–1.0 ms'sindeki sıcaklık, ayarlara ve aynı anda görülen erken derinliğe bilgi eklemiyor.
   - 0.75 ms'de log loss +0.0002 [−0.003, +0.003].
   - Alarm süresinde fark −0.0001 [−0.005, +0.006].
   - Kayıtlı yarar kuralı geçmedi. Doğrulama yarısı açılmadı, büyük zaman modeli kampanyası başlatılmadı.
7. **Tavan.** 134 Keyhole koşusu 300.2 µm'de çok dar bir platoda (SD 0.7 µm; plato düzeyi güç, ışın ve altlık sıcaklığından bağımsız). Bu, sert bir geometrik alt sınırla tutarlı.
   - Ancak alanın z boyutu hiçbir mevcut dosyada yok (`parameters.json` yalnız dört giriş anahtarı içeriyor). HİPOTEZ olarak kalıyor.
   - Geometrik modellerin kaybı tavandan değil, sınır yakınındaki conduction koşularından geliyor.
8. **IR yorumları tarihli bir ekle düzeltildi.** Sayılar değişmedi.

## 3. Varsayımlar: ne doğru, ne yanlış çıktı?

| varsayım | sonuç | kanıt düzeyi |
|---|---|---|
| Genişlik, eriyik havuzu genişliğidir (ışın değil) | **doğru** | betimsel (540 koşu) |
| A / W_A anlık bir geometrik orandır | **yanlış**: iki maksimum medyan 0.35 ms (IQR 0.16–0.62) arayla | betimsel |
| Gerçek oranın %97.8 uyumu, tahmin edilen oranla da iyi sınıflandırma verir | **yanlış**: tahmin edilen oranla −0.017 ile −0.048 | DEV |
| Sabit fiziksel eşik (W/D = 2) etiket öğrenmeyi gereksiz kılar | **yanlış**: eşik conduction kümesinin kıyısında; tahmin hatası asimetrik | DEV + POST-HOC betimsel |
| Doğrudan oran hedefi, d ve w'yi ayrı öğrenmekten kolaydır | **kısmen doğru**: B1 − A1 +0.009, B2 − A2 +0.010; ikisi de C1'in altında | DEV |
| Anlık oranın maksimumu "herhangi bir Keyhole olayı" etiketine daha uygundur | **yanlış**: gerçek değerle BA 0.969 (en düşük), öğrenilmesi de en zor (−0.048) | betimsel + DEV |
| Oran, C1'e yeni bilgi ekler | **yanlış**: C1_G −0.0008 [−0.0012, −0.0003] | DEV |
| Erken sıcaklık C1'e katkı verir (simülasyon sayısı) | **yanlış**: C1_T −0.0069, gerçek erken sıcaklıkla bile −0.0037 | DEV |
| Erken sıcaklık başlamış koşuyu erken değerlendirmeye katkı verir (süre) | **yanlış**: erken derinliğin üstüne bilgi ve süre kazancı yok | DEV (koşu düzeyinde) |
| "Keyhole'dan 28 µs önce sıcaklık yükseliyor" bir erken uyarıdır | **kullanılamaz**: etiket anına hizalı bir betimleme; nedensel pencerelerde gelecekteki olayı ayarlardan iyi öngörmüyor | DEV |
| ~300 µm yığılması alan tabanıdır | **doğrulanamadı** (iç kanıt tutarlı) | HİPOTEZ |

## 4. Ölçüm tanımları

`src/gt_data.py`, kayıtla donduruldu; `data/GT_RUNS.csv`, `data/DEFINITION_AUDIT_TRUE_VALUES.json`, Şekil 1.

| tanım | ne ölçüyor | kapsam | gerçek değerle uyum (BA / Keyhole / conduction) |
|---|---|---|---|
| R1 = A / W_A (IR'nin, referans) | aktif penceredeki maksimum derinlik / maksimum genişlik; eşzamanlı değil | 540 | 0.977 / 0.995 / 0.959 |
| R2 = A / W_atA | en derin satırdaki genişlikle oran (eşzamanlı) | 540 | 0.974 / 1.000 / 0.948 |
| R3 = maks d(t) / w(t) | anlık oranın aktif penceredeki maksimumu; w ≥ 12 µm koruması (Week 6, 3 parçacık aralığı) | 540 | 0.969 / 1.000 / 0.939 |

- **Kalite kuralları (denetlenmiş, sonuca göre seçilmedi):**
  - Geçerli sınır satırları; Week 19 aktif penceresi; iter.dat üzerinden zaman eşlemesi.
  - 12 µm koruması aktif satırların medyan %0.12'sini dışarıda bıraktı.
  - Bir koşuda sınır/zaman satırları uyuşmuyor; geometrisi yok, maliyeti sayılıyor.
  - Derinlik, havuzdaki A_um'u 540 koşuda birebir yeniden üretiyor.
- **Yorum.** Anlık orana dayanan tanım, "herhangi bir Keyhole olayı" etiketine daha uygun görünse de conduction'daki kısa ani yükselmelerde de eşiği aşıyor.
- **Uyarı.** %97.8 bir model başarısı ya da kesin bir tavan değil. Bu sayı, ölçülmüş değerlerin elle yapılmış etiketle uyumudur.

## 5. Geometrik sınıflandırıcı

**Sistemler** (hepsi C1'in GP motoruyla; yalnız hedef değişiyor):
- **GP motoru.** h eğilimi, zayıf MAP öncülü, iki başlangıç ve RC18 kalite ağırlıkları.
- **A (ayrı tahmin).** log d (C1'in derinlik GP'si) ve log w için ayrı GP'ler kullanıldı. P = Φ((m_d − m_w + log 2) / √(v_d + v_w)); iki tahminin bağımsız olduğu açıkça varsayıldı.
  - 0.5 kararı çapraz kovaryanstan bağımsızdır; kovaryans yalnız olasılık ölçeğini ve margin sıralamasını değiştirir.
- **B (doğrudan hedef).** g = log(2d/w) üzerinde tek bir GP; P = Φ(m_g / √v_g).
  - Sabit hiperparametrelerde B'nin ortalaması A'nınkine eşittir. Doğrusallık özdeşliği 2.9e-14 ile doğrulandı.
  - Bu yüzden A ile B arasındaki fark yalnız ayrı öğrenilen hiperparametrelerden gelebilir.
- **A ve B etiket kullanmaz.** Kalibrasyon kontrolü CAL_B1 ve "oranı C1'e ekle" kontrolü C1_G, dürüst kat-dışı özelliklerle eğitildi.

**Kabul (G1, hepsi geçti):**
- **Gölge testi.** Açılmamış ve test koşularının bütün etiket, derinlik, genişlik, oran ve sıcaklıkları bozulduğunda her yöntemin tahmini ve sorgu yolu bit düzeyinde aynı kaldı. Yalnız test gerçeğini okumak üzere tasarlanmış ORACLE_T değişti (pozitif kontrol).
- **Yeniden üretim.** C1, 272 öğrenicinin her bütçesinde kayıtlı tahminlerle 0.0 farkla yeniden üretildi.
- **GP uyumları.** 86,496 GP uyumu başarılı, hiç geri dönüş (fallback) yok.
- **Bağımsız yeniden hesaplama.** Dışa aktarılan dosyalardan en büyük fark 8e-17.

**En önemli karşılaştırma** (G2, DEV; STD 163–202 × 5 kat = 200 öğrenici; aynı açılmış simülasyonlar ve başlangıçlar; köşeli parantez: kümeler üzerinden tek yönlü %95 alt / üst sınır):

| sistem | BA-AULC B8–B24 | Δ (− C1) | BA-AULC B8–B60 | BA B8 / B12 / B16 / B24 / B40 / B60 | Keyhole / conduction geri çağırma (B8–B24) | log loss B8–B60 | 0.95'e ulaşan | 0.95 harcama ort. / medyan (ulaşanlar) |
|---|---|---|---|---|---|---|---|---|
| **C1 (kayıtlı)** | **0.9400** | – | **0.9493** | 0.921 / 0.939 / 0.943 / 0.948 / 0.953 / 0.957 | 0.935 / 0.945 | **0.146** | **169/200** | 22.4 / 17 |
| GEO_A1 (ayrı, R1) | 0.9134 | −0.0265 [−0.0289, −0.0241] | 0.9192 | 0.917 / 0.910 / 0.914 / 0.915 / 0.921 / 0.928 | 0.981 / 0.846 | 0.326 | 79/200 | 28.8 / 25 |
| GEO_A2 (ayrı, R2) | 0.8922 | −0.0478 [−0.0504, −0.0452] | 0.9046 | 0.891 / 0.890 / 0.893 / 0.896 / 0.910 / 0.920 | 0.986 / 0.798 | 0.415 | 40/200 | 34.2 / 37.5 |
| **GEO_B1** (doğrudan, R1; seçilen GEO\*) | 0.9225 | −0.0174 [−0.0196, −0.0153] | 0.9338 | 0.921 / 0.917 / 0.924 / 0.929 / 0.939 / 0.947 | 0.985 / 0.860 | 0.309 | 124/200 | 28.0 / 25 |
| GEO_B2 (doğrudan, R2) | 0.9019 | −0.0381 [−0.0410, −0.0352] | 0.9242 | 0.894 / 0.895 / 0.902 / 0.914 / 0.936 / 0.945 | 0.990 / 0.814 | 0.394 | 102/200 | 34.7 / 35.5 |
| GEO_B3 (doğrudan, R3) | 0.8915 | −0.0485 [−0.0517, −0.0453] | 0.9183 | 0.874 / 0.881 / 0.894 / 0.907 / 0.932 / 0.943 | 0.991 / 0.792 | 0.418 | 91/200 | 37.4 / 40 |
| CAL_B1 (etiketle kalibre) | 0.9307 | −0.0093 [−0.0119, −0.0067] | 0.9353 | 0.925 / 0.933 / 0.933 / 0.934 / 0.938 / 0.938 | 0.923 / 0.938 | 0.315 | 138/200 | 21.8 / 15 |
| C1_G (C1 + oran) | 0.9392 | −0.0008 [−0.0012, −0.0003] | 0.9484 | 0.921 / 0.938 / 0.942 / 0.948 / 0.952 / 0.956 | 0.934 / 0.945 | 0.146 | 167/200 | 21.9 / 16 |
| C1_T (C1 + tahmini erken sıcaklık) | 0.9330 | −0.0069 [−0.0082, −0.0056] | 0.9446 | 0.921 / 0.926 / 0.936 / 0.944 / 0.948 / 0.954 | 0.927 / 0.939 | 0.155 | 160/200 | 23.7 / 18.5 |
| ORACLE_T (tanı: gerçek erken sıcaklık) | 0.9363 | −0.0037 [−0.0047, −0.0026] | 0.9473 | 0.899 / 0.936 / 0.941 / 0.947 / 0.951 / 0.955 | 0.931 / 0.941 | 0.170 | 161/200 | 21.6 / 17 |

**Hedefler** (STD, C1 karşısında; `REPORT_TABLES.md` tam tabloyu veriyor):
- **Sayım kuralı.** Harcama, doğrulanmış b + 4'tür: 8 başlangıç ve 4 doğrulama simülasyonu dahildir. Ulaşamayan öğreniciler medyanda ∞ sayılır; 61 ile sınırlı ortalama gerçek maliyet değildir.
- **C1:**
  - 0.80: 200/200, harcama 12.0;
  - 0.90: 200/200, 12.7 (medyan 12);
  - 0.93: 194/200, 16.4 (13);
  - 0.95: 169/200 (31 ulaşamadı), ulaşanlarda 22.4 (17), herkeste medyan 21.
- **GEO_B1:**
  - 0.90: 199/200, 14.9 (12);
  - 0.93: 180/200, 20.6 (16);
  - 0.95: 124/200 (76 ulaşamadı), 28.0 (25), herkeste medyan 43.5.
- **0.95'te sınırlı ortalama tasarruf.** GEO_B1 −12.1 [−14.4, −9.8], CAL_B1 −5.5, C1_G +0.04 [−1.06, +1.14], C1_T −2.7.
- **Erken bütçe.** B8'de tek başına CAL_B1 C1'den yüksek (0.925 / 0.921). B10'dan sonra C1 öne geçiyor ve fark kapanmıyor (Şekil 2).

**Sınıra yakın karar** (q20: her test katının sınıra en yakın %20'si; B8–B24 BA):
- C1 0.748;
- GEO_B1 0.682 (−0.066);
- CAL_B1 0.738 (−0.010);
- C1_G 0.747 (−0.001);
- C1_T 0.739 (−0.010).

Geometrik modeller en çok tam sınırda kaybediyor; düşük küresel R² burada eleme gerekçesi olarak kullanılmadı.

**Alt gruplar** (STD, B8–B24; değer / C1):

| grup | GEO_B1 | C1 |
|---|---|---|
| kısa-Keyhole (havuz kuralı) | 0.972 | 0.808 |
| tavan altı Keyhole | 0.954 | 0.803 |
| tavandaki Keyhole | 1.000 | 0.998 |
| conduction | 0.860 | 0.945 |
| zor conduction (NEW) | 0.009 | 0.146 |
| köşe conduction (VX > 0.85, P > 330) | yaklaşık 0.16 | 0.33 |

Geometri Keyhole'u, kısa olanlar dahil, çok iyi yakalıyor ama conduction'ı feda ederek. BA iki sınıfı eşit tarttığı için net sonuç kayıp.

**Mekanizma** (POST-HOC, betimsel; `dev/G2_MECHANISM_POSTHOC.json`):
- **Gerçek g1.** Conduction medyanı −0.38, %95'liği −0.03. Keyhole %5'liği +0.27, medyanı +1.07.
- **Tahmin edilen g.** Sınıra yakın conduction koşularının (gerçek g > −0.35) b = 12'de %28'i, b = 60'ta %18'i g ≥ 0 tahmin ediliyor. Gerçekte bu oran %4.
- **Keyhole koşuları** aşağı çekiliyor (sapma −0.25), ama eşiğin çok üstünde oldukları için yalnızca %1–2'si yanlış sınıflanıyor.
- **Sonuç.** Sabit eşik sınıf boşluğunun ortasında değil. C1 sınırı etiketlerden öğreniyor ve bu asimetriden etkilenmiyor.

**Bloklar** (dış bölgeye uzanım, bölge başına B8–B60):
- GEO_B1: K5'te +0.001 [−0.023, +0.025], K4'te −0.034 [−0.057, −0.011].
- K5'te geometri C1'den kötü değil, ama alt sınırlar EA uyarı eşiğini (−0.02) aşıyor.
- Blok BA düzeyleri düşük (yaklaşık 0.65–0.70). Hedeflere ulaşma farkları birkaç öğreniciye dayanıyor.

**Tavan açısından:**
- Tavandaki Keyhole koşularında bütün sistemler kusursuz (yaklaşık 1.000).
- C1 yolunda ödenmiş koşuların yalnızca medyan %3.3'ü tavanda. Öğrenici başına kayıpla ilişkisi zayıf (Spearman −0.08 ile −0.23).
- Geometrik kayıp tavandan değil, sınır yakınındaki conduction koşularından geliyor. Ana örneklem değiştirilmedi.

**CPU** (karar başına, test satırları, işlem saniyesi):
- C1 0.28 s;
- GEO_B1 0.025 s (yaklaşık 11 kat ucuz);
- CAL_B1 0.26 s;
- C1_G 0.61 s;
- C1_T 0.64 s.

Ucuzluk, BA kaybını telafi etmiyor.

**Seçim ve durdurma (kayıtlı kurallar):**
- GEO\* = GEO_B1 (en iyi erken fark −0.0174).
- "Umut verici" kuralı ≥ −0.003 istiyordu: **geçmedi → GEOMETRİ DURDUR.**
- G3 (kendi-yol; margin / straddle / alanı dolduran) ve G4 (taze doğrulama: STD 383–462, K5 49–56, K4 33–40) koşulmadı; taze kimlikler boş kaldı.
- C1_G taşıma kuralı (≥ +0.005 ve alt sınır > 0): geçmedi.
- Kod G3 ve G4 için hazırdı ve kod yolları DEV görevlerinde denendi.

**Kazanç modelden mi, yoldan mı?**
- Kazanç yok. Eşleştirilmiş karşılaştırma modeli yalıtıyor: aynı ödenmiş veride geometrik model kayıp veriyor.
- Önceki çalışmalarda yol etkileri küçüktü (EL: erken kazanç bir tahmin etkisiydi). −0.017'lik bir model açığını kendi yolun kapatması beklenmez.
- Yol etkisi ayrıca ölçülmedi (kayıtlı durdurma).

## 6. Erken sıcaklık A: simülasyon başlamadan tahmin (simülasyon sayısı iddiası)

- **C1_T.** Erken sıcaklık özeti Tmax(0.75 ms): simülasyon başlangıcından 0.75 ms'ye kadar maksimum sıcaklığın koşan maksimumu. Yalnız açılmış koşulardan C1'in GP motoruyla öğrenildi ve C1 sınıflandırıcısına ayrı çekilebilen bir özellik olarak eklendi. Eğitim özellikleri dürüst kat-dışı.
  - STD erken −0.0069 [−0.0082, −0.0056], B8–B60 −0.0047, 0.95 tasarrufu −2.7.
  - K5 −0.018, K4 −0.003.
- **ORACLE_T (tanı).** Test koşularında GERÇEK Tmax(0.75) verildiğinde bile −0.0037 [−0.0047, −0.0026]. Bu ayarda gerçek erken sıcaklık bile h + tahmini derinliğe yararlı bilgi eklemiyor; fazladan özellik küçük örneklemde zarar veriyor.
- **Zaman tanımı.** Önceki "T0 sıcaklık" sonucu (RC20 / RC22: h + derinlikten sonra işe yaramaz) aktif pencerenin son %20'sini kullanıyordu. Buradaki pencere nedensel ve erken; sonuç ayrı olarak sınandı.
- **Karar (kayıtlı):** SICAKLIK-A DURDUR. Kendi-yol testi ve zaman modeli kampanyası yok.

## 7. Erken sıcaklık B: başlamış bir koşuyu erkenden değerlendirmek (yürütme süresi iddiası)

**Kurulum** (kayıtlı; `src/gt_tb.py`):
- **Popülasyon.** Sınır kutusu ve maksimum sıcaklık kanalı olan 485 koşu. 56 koşu dışarıda: 55'inde sıcaklık dosyası yok (52 OLD conduction, 3 OLD Keyhole), 1'inde sınır/zaman satırları uyuşmuyor (NEW conduction).
- **Bölme.** Etikete göre tabakalı, tohumlanmış ikiye bölme. DEV yarısı 242 koşu (97 Keyhole) ve 5 × 10 katlı, koşu düzeyinde çapraz doğrulama kullanıldı. Aynı koşunun kareleri iki tarafa dağıtılmadı. VAL yarısı (243 koşu) kayıtlı kural gereği açılmadı.
- **Özellikler.** Yalnızca o ana kadar görülen satırlar: koşan maksimum ve son 10 µs medyanı. Zaman, simülasyon başlangıcından ölçüldü (t = 0, önceden bilinir).
- **Karar zamanları.** 0.50, 0.75 ve 1.00 ms; alarm için 25 µs'lik bir ızgara.
- **Kullanılmayanlar.** Koşunun tümüne ait ortalama, gelecekteki maksimum, aktif pencerenin sonu, ilk K karesi ve etiket hiçbir özelliğe girmedi.

**Bilgi** (DEV, dışarıda tutulan log loss; köşeli parantez: koşu düzeyinde %95 bootstrap aralığı):

| model | 0.50 ms | 0.75 ms | 1.00 ms |
|---|---|---|---|
| S (ayarlar, z_h) | 0.153 | 0.154 | 0.154 |
| S + sıcaklık | 0.154 | 0.155 | 0.153 |
| S + erken derinlik | 0.155 | 0.143 | **0.116** |
| S + erken derinlik + sıcaklık | 0.154 | 0.144 | 0.166 |
| C1p (simülasyon öncesi; C1'in derinlik GP'si, büyük eğitim kümesi) | **0.108** | **0.109** | **0.109** |
| **sıcaklığın erken derinliğe katkısı** (S+D+T − S+D) | −0.0007 [−0.0047, +0.0034] | +0.0002 [−0.0026, +0.0029] | +0.050 [+0.001, +0.144] |
| sıcaklığın ayarlara katkısı (S+T − S) | +0.0006 | +0.0013 | −0.0009 |

- Sıcaklık, ne bilinen ayarlara ne de aynı anda görülen erken derinliğe bilgi ekliyor. 1.00 ms'de erken derinliğe eklenince log loss'u bozuyor: derinlik ve sıcaklık sınıfları neredeyse tamamen ayırdığında birkaç aşırı emin hata oluşuyor.
- Erken derinlik 1.00 ms'de ayarları belirgin biçimde geçiyor (−0.038 [−0.060, −0.018]). Ama büyük eğitim kümesiyle C1'in simülasyon öncesi tahmini (C1p) hâlâ daha iyi (0.109).
- **Gelecekteki Keyhole olayı** (ilk K karesi karar anından sonra gelenler). Erken sinyaller ayarlara göre daha kötü:
  - 0.75 ms'de 32 koşu: geri çağırma S 0.875, S+D 0.787, S+D+T 0.794.
  - 1.00 ms'de 11 koşu: geri çağırma 0.73, 0.45 ve 0.45.
  - Sinyaller, olmuş olanı görüyor; olacak olanı öngörmüyor.

**Alarm** (DEV; her koşu, karar ızgarasının her noktasında alarm verebilir; eşik, eğitim katlarının içinde iç içe 5 katlı çapraz doğrulamayla seçildi; hedef: conduction koşularının en çok %5'i HİÇ alarm vermesin):

| model | Keyhole yakalama | yanlış alarm (gerçekleşen) | okunan fiziksel süre payı (tüm koşular) | okunan süre (Keyhole) | uyarı süresi medyanı (ilk K karesinden önce) | kısa-Keyhole yakalama | NEW conduction yanlış alarmı |
|---|---|---|---|---|---|---|---|
| S (simülasyonsuz karar) | 0.907 | 0.055 | 0.603 | 0.093 | 0.65 ms | 0.58 | 0.96 |
| S + sıcaklık | 0.930 | 0.055 | 0.660 | 0.219 | 0.34 ms | 0.72 | 0.96 |
| S + erken derinlik | 0.973 | 0.055 | 0.651 | 0.199 | 0.29 ms | 0.78 | 0.92 |
| S + erken derinlik + sıcaklık | 0.973 | 0.055 | 0.651 | 0.198 | 0.30 ms | 0.76 | 0.92 |

- Sıcaklığın süreye katkısı (S+D+T − S+D): −0.0001 [−0.005, +0.006].
- Kayıtlı yarar kuralı en az −0.03 istiyordu: **geçmedi**. Bilgi kuralı da geçmedi.
- **Maliyet.** Gerçek yürütme süresi kaydı yok. Okunan pay fiziksel simülasyon süresidir (t / TE). Çözücü yineleme payı aynı çıkıyor (0.653 / 0.651), yani zaman adımı fiilen sabit. Hesap, maliyetin yineleme sayısıyla orantılı olduğunu varsayar; CPU tasarrufu iddia edilmiyor.
- **Uyarılar.**
  - Yanlış alarm gerçekleşmesi 0.055, hedef 0.05'in biraz üstünde.
  - Zor conduction (NEW conduction) koşularının %92–96'sında yanlış alarm var.
  - Erken durdurma bu koşulara yanlış etiket verirdi.

**Karar (kayıtlı):** SICAKLIK-B: EK YARAR YOK. VAL yarısı açılmadı, büyük zaman modeli kampanyası başlatılmadı.
- Erken derinlikle durdurmanın süre kazancı (Keyhole koşularında okunan pay yaklaşık 0.20) yalnız DEV düzeyinde betimseldir. Doğrulanmadı ve sıcaklıkla ilgili değildir.

## 8. ~300 µm derinlik yığılması

**Aranan kaynaklar:**
- yerel ham kopya: koşu klasörlerinde yalnızca `frames.csv` ve izleme dosyaları var;
- Week 11 varış denetimi: koşu başına `parameters.json` yalnız dört anahtar içeriyor (güç, tarama hızı, ışın boyu, altlık sıcaklığı);
- Week 7 dosya envanteri: yalnız .png, .dat, .gif, .csv ve .json dosyaları;
- koşu adları;
- Week 19 raporunun hipotezi.

Alanın z boyutu hiçbir mevcut dosyada yok.

**İç kanıt** (`ceiling/CEILING_EVIDENCE.json`, Şekil 5):
- 134 koşunun aktif penceresinde ≥ 295 µm satır var. Hepsi Keyhole: NEW 100, OLD 34.
- Bu satırlardaki derinliğin medyanı 300.2 µm; %5–95 aralığı 299.6–300.6 µm, SD 0.72 µm.
- Plato düzeyi güç, ışın boyu ve altlık sıcaklığından bağımsız (\|ρ\| ≤ 0.09). Hızla zayıf bir ilişki var (ρ −0.43).
- Keyhole derinlik histogramı:
  - 300–310 µm aralığında 131 koşu;
  - 290–300 µm aralığında 4 koşu;
  - 280–290 µm aralığında 1 koşu.
- Genişlikte böyle bir yığılma yok: yalnızca 1 koşu ≥ 295 µm.
- Tavan koşuları aktif satırlarının medyan %42'sini platoda geçiriyor. Platoya ilk ulaşma medyanı 0.72 ms.

**Sonuç:** Bu tablo sert bir geometrik alt sınırla (altlık ya da alan tabanı) tutarlı, ama doğrulanmadı. HİPOTEZ olarak kalıyor. Doğrulamak için simülasyon kurulumunun veri sağlayıcıdan öğrenilmesi gerekir.

Tavanın öğrenmeye etkisi için §5'e bakın: geometrik kayıp tavandan gelmiyor.

## 9. IR yorumlarının düzeltilmesi

Tarihli ek: `outputs/research_campaign_20261031/opus_ioan_requests/IR_ADDENDUM_20261102.md`, Türkçe ve İngilizce. IR'nin Türkçe raporuna ve İngilizce özetine tarihli bir bağlantı satırı eklendi. Hiçbir sayı değişmedi. Düzeltilen yedi nokta:
1. **Derinlik–etiket bağı nedensel ya da evrensel değil.** Etiketler elle yapılmış biçim işaretlemeleri ve derinlik sansürlü.
2. **"Hiçbir çıktı bilgi eklemiyor".** Denenen özellik ve modellerle sınırlı. Ölçülen aralık: Δ log loss −0.0013 ile +0.0148, ΔBA −0.0096 ile +0.0001.
3. **"Tasarruf yok".** Tam ardışık karşılaştırma koşulmadı; eşleştirilmiş tarama vekil BA kullanıyordu.
4. **Gerçek-KE kontrolü (+0.001).** Yalnızca o zincir yapısının sınırı.
5. **Transfer iptali.** ICM (tek ortak çekirdek), izotopik veri ve gürültüsüz ya da uyumlu gürültü gerektirir. IR'nin LMC'si bu koşulların tam olarak altında değildi; küçük transfer beklenir, sıfır değil.
6. **Kayıt öncesi ilk bakış.** İngilizce özetteki "all rules were registered before any result" cümlesi düzeltildi.
7. **Tavan.** Tavandaki koşuların hepsinin Keyhole olması, tavanın öğrenmeye etkisizliğini kanıtlamaz.

## 10. Sonuçların kanıt düzeyleri

| sonuç | düzey |
|---|---|
| Ölçüm denetimi, gerçek değerle uyum, tavan, eşzamansızlık | BETİMSEL (bütün havuz; etiket kullanan uyum sayıları kayıt öncesi açıklandı) |
| Geometrik sınıflandırıcılar, kontroller, C1_T (G2) | DEV (kayıtlı eşleştirilmiş karşılaştırma; 272 öğrenici; aynı havuzun daha önce kullanılmış bölmeleri) |
| Mekanizma (eşik asimetrisi) | POST-HOC betimsel (G2 sonucundan sonra) |
| Erken sıcaklık B | DEV (koşu düzeyinde çapraz doğrulama; VAL açılmadı) |
| Yeni bölmelerde doğrulama | YOK: kayıtlı durdurma; taze kimlikler kullanılmadı |

**Dış fiziksel doğrulama iddia edilmiyor.** Her şey aynı 541 koşudan geliyor.

## 11. Ana yöntem değişmeli mi?

**Hayır. C1 + margin havuz içi önerilen öğrenici olarak kalıyor; HA_LEAN + margin donmuş referans.**
- Geometrik sınıflandırıcı, oranı C1'e eklemek ve erken sıcaklığın iki kullanımı benimsenmedi.
- **Tez için yararlı olumsuz sonuç.** Sabit fiziksel W/D eşiği, gerçek değerlerde iyi uyum gösterse bile, ÖĞRENİLEN geometriyle kullanıldığında asimetrik hata üretiyor. Sınırın konumunu etiketlerden öğrenmek gerekli.
- **Yayın / yenilik iddiası.** Bu bir olumsuz DEV sonucu ve tek havuzla sınırlı. Yeni bir yöntem iddia edilmiyor.

## 12. Denenenler, denenmeyenler ve gerekçeleri

**Denenenler:**
- üç oran tanımının denetimi;
- GEO_A1/A2, GEO_B1/B2/B3, CAL_B1, C1_G, C1_T, ORACLE_T (G2, her bütçe 8–60);
- QT-B'de S, S+T, S+D, S+D+T, C1p ve alarm.

**Gerekçeyle denenmeyenler:**

| ne | gerekçe |
|---|---|
| G3 kendi-yol, straddle ve alanı dolduran seçim | kayıtlı "umut verici" kuralı geçmedi; seçici, model açığını kapatamaz |
| G4 taze doğrulama | kayıtlı durdurma |
| Çapraz kovaryanslı ortak d–w modeli | 0.5 kararı kovaryanstan bağımsız; IR'nin LMC'si derinlikte kazanç vermemişti |
| Kalıcı (50 µm hareketli medyan) en-boy oranı | Week 7'de gerçek değerle sınanmıştı (R3 AUC 0.9986, G3 1.000); kullanıcının üç tanımı dışında; yeni hedef araması yapılmadı |
| Büyük zaman serisi modelleri | küçük DEV deneyi yarar göstermedi |
| Eşiği öğrenme varyantları | CAL_B1 bunu temsil ediyor (yalnız açılmış etiketlerle) |

## 13. Testler, kayıtlar, dosyalar

**Testler:**
- **12. hafta ve sonrası regresyon takımı** (27 dosya): 217 geçti, 2 atlandı, 2 başarısız.
- **İki başarısızlık eski taban b0e9569f'de de aynı değerlerle tekrarlandı** (`regression/OLD_BASE_b0e9569f_two_tests.log`). Önceden var oldukları doğrulandı.
  1. `test_t_tobit_truth_is_the_frozen_phase2_truth`: Week 18 T_TOBIT dondurulmuş θ'dan sayısal sapma (θ₁ −0.2257, dondurulmuş −0.2518). Kod değişmedi; muhtemelen kütüphane sürümü kayması. Dondurulmuş referans değiştirilmedi.
  2. `test_reports_use_full_simulation_ids`: merkezi defterin 84. ve 93. satırlarındaki kısaltılmış H kimlikleri (599f1025, 2026-10-16). Bu çalışmayla ilgisiz; tarihsel kayıt yeniden yazılmadı.
- **Tam takım** (59 dosya; önceki çalışmaların koşmadığı 8.5–11. hafta testleri dahil): 719 geçti, 2 atlandı, 40 başarısız (`regression/FULL_SUITE_all59files.log`).
  - 40'ın 2'si yukarıdaki bilinen başarısızlıklar.
  - Kalan 38'i 8.5–9. hafta testleri: Week 9 başlangıç SHA'sına göre `git diff` ile "tarihsel çıktılar değişmedi" kontrolleri (binlerce sonraki dosya), eski `tests/` klasör düzeni, defter özetleri ve yeniden çalıştırma, atlanan checkpoint'ler.
  - Bu çalışmadan bağımsız oldukları, IR taban commit'i `0a57d644` (GT'den önce) üzerinde yeniden koşularak sınandı. Sonuç `regression/FULL_SUITE_NOTE.md` dosyasında.

**Kayıtlar:**
- bu çalışmanın defteri `ATTEMPT_LEDGER.md`;
- `docs/thesis_progress_log.md` (IR ve GT bölümleri);
- `outputs/joint_depth_label_development/CLAIMS_MATRIX.md` §9–10;
- `docs/alse/claims.md` (IR için C145–C150, GT için C151–C158), `decisions.md`, `experiments.md`;
- merkezi `ATTEMPT_LEDGER.md` (IR-* ve GT-* satırları).

**Dosyalar:**

| dosya | içerik |
|---|---|
| `PROTOCOL_GT.md` | kayıtlı kurallar |
| `REPORT_TABLES.md` | bütün tablolar, sonuç dosyalarından otomatik üretildi |
| `dev/G2_RESULT.json`, `dev/G2_SELECTION.json`, `dev/G2_summary_*.csv`, `dev/G2_MECHANISM_POSTHOC.json` | G2 sonuçları |
| `temporal/TB_DEV_RESULT.json` | QT-B sonuçları |
| `ceiling/CEILING_EVIDENCE.json` | tavan kanıtı |
| `acceptance/ACCEPTANCE_G1.json` | kabul testleri |
| `exports/g2/` | tahminler ve sorgu kimlikleri, bağımsız yeniden hesaplama PASS |
| `figures/fig1`–`fig5` | şekiller |
| `src/gt_*.py`, `src/gt_runner.ps1` | kod |
