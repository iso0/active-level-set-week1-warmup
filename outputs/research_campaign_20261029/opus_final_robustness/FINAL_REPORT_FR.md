# FR: C1 ile HA_LEAN arasında ödenmiş veriden öğrenilen tek güven kuralı (son araştırma görevi)

Opus, 2026-10-29. **Kanıt etiketi: DEV.**
- Bütün sayılar aynı 541 koşuluk havuzdan, daha önce incelenmiş kayıtlı yollardan geliyor.
- Yeni simülasyon açılmadı; yeni fiziksel veri ya da dış doğrulama yok.
- **Pencere:** 13:31:37 UTC'de başladı, sınır 19:31:37 UTC (6 saat). İş bitince erken kapatıldı.
- **Hesap:** 392 DEV birimi, hata yok, 1.6 işçi-saat. En çok 3 tek iş parçacıklı işçi kullanıldı; Astra'nın ve sistemin payı kullanılmadı.

## Tek sayfalık sonuç

**Hüküm:** **C1 + margin değişmeden kalıyor.**
- Tek aday GATE, sonuçlardan önce kaydedilen DEV kuralını geçemedi:
  - geometrik bloklarda C1'e göre +0.0045, alt sınır −0.0016;
  - gereken: en az +0.010 ve alt sınır sıfırın üstünde.
- Kural gereği taze sınama başlatılmadı. GATE hiçbir kullanım için benimsenmedi.

**Ne denedik?**
- C1 ile HA_LEAN'in olasılıklarını noktaya bağlı bir ağırlıkla birleştiren tek, sade bir kural:
  - p(x) = w(x) · p_C1(x) + [1 − w(x)] · p_HA_LEAN(x);
  - w(x) = σ(a + c · u(x)); u(x), x'in ödenmiş koşulara uzaklığıdır.
- a ve c yalnız ödenmiş koşulardan öğrenildi. Her ödenmiş koşu için iki model, o koşu ve uzaysal grubu hiç görülmeden yeniden kuruldu.

**Neden denedik?** Önce iki modelin aynı ödenmiş veride nerede ayrıştığını ölçtük.
- Geometrik bloklarda, doğru modeli nokta nokta seçen (test etiketini bilen) bir oracle C1'i +0.049 iyileştirirdi.
- Test etiketlerini kullanan bir teşhis modeli bu payın +0.021'ini öngörülebilir buldu.
- Sonuçlardan önce yazdığım geçiş kuralı (G1, G2) bu yüzden geliştirmeye izin verdi.

**Ne kazandık?** Yalnız DEV'de ve aynı ödenmiş veride:
- K5 bloklarında +0.022: HA_LEAN'in üstünlüğünün yarısı.
- Standart bölmelerde (STD):
  - erken dönem korundu (+0.0002);
  - geç dönem biraz iyi (+0.0009);
  - log loss biraz iyi (−0.0011).

**Ne kaybettik?**
- K4 bloklarında −0.013. Bu kayıp gösterildi.
- Geometrik toplamda kazanç gösterilmedi.
- Sabit yarı yarıya ortalama (kontrol), bloklarda bu kuraldan iyiydi (+0.0055). Öğrenilen yerel kural gerekli çıkmadı.

**Neden olmadı?** Blok tasarımında test bölgesi öğreniciye hiç açılmaz.
- Ödenmiş dört bölgenin içinde ve arasında, C1'in fizik eğilimi HA_LEAN'den iyi genelliyor. Kural bu yüzden uzakta C1'e daha çok güveniyor.
- Bazı K5 bölgelerinde bu eğilim tutmuyor, K4'te tutuyor.
- "Burada HA_LEAN'e geç" bilgisini taşıyan koşular hiç açılmamış koşular. Ödenmiş veriden öğrenilen hiçbir kural bunu göremez.
- Bu, EA'nın bulduğu "darboğaz: sorgulanmamış girdilerin derinliği" sonucunun aynısı.

**Ne anlama gelmiyor?**
- C1'in K5 zayıflığının kanıtlanmış bir çözümü yok.
- HA_LEAN "her blokta daha güvenli" de değil: K4'te C1 açık farkla iyi.
- Taze kimlikler (STD 383+, K5 49+, K4 33+) kullanılmadı; sonraki çalışmalar için boş duruyor.

## 1. Kurulum ve bütünlük

**Kayıtlar (sonuçlardan önce commit ve push edildi):**

| commit | ne kaydedildi |
|---|---|
| 4dced919 | görev ve kazanç alanı geçiş kuralı (G1, G2, kaynak sınırı); hiçbir sayı hesaplanmadan önce |
| c4edc59a | kazanç alanı sonucu; tek aday GATE, kontrol AVG ve DEV kuralı (C-GEO, C-EARLY, C-LATE); hiçbir DEV kapı sonucundan önce |

**DEV değerlendirici:** `src/fr_dev_eval.py` DEV koşusu sürerken, sonuç görülmeden yazıldı. Kural eşikleri c4edc59a'daki protokolden alındı; dosya kapanış commit'inde eklendi.

**Taze sınama:** `PROTOCOL_FR_FRESH.md` DEV sonucundan önce taslak olarak yazıldı. Hiç dondurulmadı ve hiç çalıştırılmadı, çünkü DEV kuralı görevi kapattı.

**Veri ve kurallar**
- 541 koşu tek havuz. OLD/NEW yönlendirmesi ve ücretsiz arşiv yok. Etiketler, dışlamalar, eşik 0.5 ve hata ağırlıkları değişmedi.
- **Değerlendiriciye özel tanımlar:** test etiketleri, zor grup (kısa-Keyhole NEW ile NEW iletim) ve köşe (VX > 0.85, P > 330). Hiçbiri öğreniciye girmedi.

**Koordinasyon:**
- Yalnız `thesis_shared_runtime\campaign_20261029\opus_state.json` yazıldı.
- Astra'nın dosyası okundu: kampanyası CLOSED, işi yok.

**Graphify gerekmedi**
- Gereken çağrı zincirleri doğrudan kaynaktan okunup doğrulandı: C1 tahmini, HA_LEAN durumu, blok görevleri, değerlendirici.
- Paylaşılan grafik değişmedi (SHA-256 5d96e506…), global kurulum değişmedi.

## 2. Kazanç alanı: iki model aynı ödenmiş önekte ne zaman ayrışıyor?

**Kod ve sonuç:** `src/fr_gain.py`, `gain/GAIN_AREA.json`.

**Veri:**
- STD 163–282, iki yol (120 küme);
- K5 başlangıçları 33–48 ve K4 başlangıçları 17–32, her biri 16 küme.

**Ölçülenler**
- Her test noktası ve bütçe için dört durum:
  - C1 yanlış / HA_LEAN doğru (R);
  - ters durum (L);
  - ikisi aynı yönde yanlış (W);
  - ikisi doğru.
- **Kazanç alanı GA** = R noktalarının BA ağırlığı = oracle BA − C1 BA.
- Dışbükey bir birleşim yalnız iki modelin ayrıştığı noktaları düzeltebilir. W noktaları hiçbir ağırlıkla düzelmez.

| koşul (B8–B60) | C1 | HA_LEAN | oracle | sabit ortalama | META (teşhis) | GA | C1 hatasının düzeltilebilir payı |
|---|---|---|---|---|---|---|---|
| STD | 0.9491 | 0.9469 | 0.9559 | 0.9490 | 0.9501 | 0.0068 | %13 (geri kalan %87 ikisinin de yanlış olduğu yer) |
| K5 | 0.6768 | 0.7204 | 0.7512 | 0.7104 | 0.7258 | 0.0744 | %23 |
| K4 | 0.6882 | 0.6546 | 0.7114 | 0.6746 | 0.6813 | 0.0231 | %7 |
| geometrik (K5 + K4) | 0.6825 | 0.6875 | 0.7313 | 0.6925 | 0.7035 | 0.0487 | %15 |

**Dağılım**
- **Erken ve geç dönem:**
  - STD'de GA erken (B8–B24) 0.0099, geç 0.0053;
  - geometrikte GA erken 0.041, geç 0.053.
- **Sınıf, köşe ve uzaklık:**
  - geometrik GA'nın %71'i Keyhole noktalarında, %25'i köşede;
  - %53'ü ödenmiş veriye orta uzaklıkta (ikinci çeyrek); en uzak çeyrekte yalnız %13.
- **Zor grup** (STD, B8–B60):

  | sistem | kısa-Keyhole NEW yakalama | NEW iletim özgüllüğü |
  |---|---|---|
  | C1 | 0.904 | 0.229 |
  | HA_LEAN | 0.929 | 0.216 |
  | oracle | 0.948 | 0.258 |

  Yanlışların çoğu iki modelde de aynı.

**Oracle neden uygulanamaz?**
- Oracle, ayrıştığı her noktada test etiketine bakarak doğru modeli seçer. Gerçek bir öğrenicide bu bilgi yoktur. Yalnız bir üst sınırdır, öğreniciye verilmedi.
- META, "ayrışmada hangisi haklı" sorusunu diğer öğrenicilerin test etiketleriyle öğrenen bir teşhis modelidir: grup dışı çapraz doğrulama, AUC 0.71.
- O etiketler aynı 541 koşudan geldiği için META hiçbir zaman yönteme dönüşemez; ancak "ayrışma girdilerden öngörülebilir mi?" sorusunu yanıtlar.
- META'nın kazancı bile tasarıma bağlı: K5'te +0.049, K4'te −0.007.

**Geçiş kuralı:**
- G1 (oda ≥ 0.030): 0.049, GEÇTİ.
- G2 (META ≥ +0.010 ve alt sınır > 0, STD erken ≥ −0.003): +0.021 [+0.012] ve +0.0005, GEÇTİ.

## 3. Aday GATE

**Formül:** p_GATE(x) = w(x) · p_C1(x) + [1 − w(x)] · p_HA_LEAN(x).
- w(x) = σ(a + c · u(x)).
- u(x) = kırp(log(d(x, L) / s_L), −2, 2), burada:
  - d(x, L): x'in en yakın ödenmiş koşuya uzaklığı, herkese açık standartlaştırılmış log girdilerde;
  - s_L: ödenmiş koşuların medyan komşu aralığı.

**(a, c) nasıl bulunuyor:** MAP kestirimi.
- **Öncül:** a ~ N(0, 1.5²), c ~ N(0, 1).
- **Olabilirlik:** ödenmiş etiketlerin q_i = w_i p1_i + (1 − w_i) p2_i altındaki Bernoulli olabilirliği.
- **İç içe uzaysal çapraz tahmin (p1_i, p2_i):**
  - Ödenmiş koşular k-means ile 4 uzaysal gruba ayrılıyor.
  - Her grup için iki boru hattı da, kendi iç K = 10 çapraz uyumlarıyla birlikte, yalnız öteki gruplarla yeniden kuruluyor.
  - Böylece bir koşunun tahmini, o koşunun etiketi, derinliği ya da başka çıktısı görülmeden üretiliyor.
- **Yenileme takvimi:** b = 16, 20, …, 60. Arada son uyum kullanılıyor.

**Tanımlı davranışlar**

| durum | davranış |
|---|---|
| b < 16 ya da sınıf başına 4'ten az kullanılabilir koşu | w = 1, yani C1 aynen |
| tek sınıflı başlangıç | iki boru hattı da ödenmiş ortalamayı verir; margin etiketsiz yola düşer (C1 gibi) |
| eksik derinlik | değişmemiş boru hatlarının kendi kuralı |

**Bilgi akışı**
- **Girer:** yalnız açılmış koşuların etiketleri ve çıktıları (değişmemiş boru hatlarının içinden) ve herkese açık girdiler (uzaklık).
- **Girmez:** test etiketi, açılmamış çıktı, kampanya kimliği, kısa-Keyhole ya da zor grup üyeliği, OLD/NEW, bölge ya da köşe bilgisi.
- "Burası köşe, öbür modeli seç" gibi sabit bir kısayol yok.

**EL-2 karışımından (E) farkı**

| | E | GATE |
|---|---|---|
| birleştirilen modeller | iki ML-II öykünücü (HA_LEAN, HA_TREND) | iki tam boru hattı (MAP öncüllü C1 ve HA_LEAN) |
| ağırlığın kaynağı | örneklem içi Laplace evidence | iç içe, uzaysal, dürüst çapraz tahmin olabilirliği |
| girdiye bağlılık | tek, global ağırlık | ağırlık geometrik desteğe bağlı |
| az veride | özel davranış yok | C1'e açık geri dönüş |

AVG4/histerezis zaman içinde yumuşatmaydı. BA_RISK, JEER ve kapsama kuralları sorgu seçimini değiştiriyordu. GATE bunların hiçbiri değil; sorgu seçimi düz margin.

**Kontroller** (`dev/SMOKE.json`)
- **İndirgeme:** w ≡ 1 C1 + margin'i, w ≡ 0 HA_LEAN + margin'i birebir verdi; aynı yol, en büyük olasılık farkı 0.
- **Gölge testi:** hiç açılmamış koşuların etiketleri çevrildi ve çıktıları karıştırıldı. Yol, olasılıklar ve kapı parametreleri aynı kaldı.

## 4. DEV sonucu: aynı ödenmiş veride model etkisi

**Veri ve dosyalar**
- Veri: kayıtlı EA yolları. STD 163–182 (iki yol, 20 küme); K5 33–48 ve K4 17–32 (32 başlangıç kümesi; iki sınıflı test bölgeleri).
- Ayrıntı: `dev/DEV_RESULT.md`, `dev/DEV_GATE.json`, `dev/DEV_TABLES.json`.

**BA-AULC B8–B60:**

| koşul | C1 | HA_LEAN | güçlü alternatif D_on_A (yalnız HA_LEAN yolu) | GATE | sabit ortalama |
|---|---|---|---|---|---|
| STD | 0.9491 | 0.9474 | 0.9482 | **0.9498** | 0.9494 |
| K5 | 0.6768 | **0.7204** | 0.6838 | 0.6985 | 0.7104 |
| K4 | **0.6882** | 0.6546 | 0.6830 | 0.6755 | 0.6746 |
| geometrik | 0.6825 | 0.6875 | 0.6834 | 0.6870 | **0.6925** |

**Kayıtlı DEV kuralı (GATE − C1):**

| kural | değer | sonuç |
|---|---|---|
| C-GEO, geometrik B8–B60 | +0.0045 [−0.0016, +0.0106], 32 kümenin 18'inde pozitif | **GEÇMEDİ** |
| C-EARLY, STD B8–B24 | +0.0002 [−0.0003, +0.0006] | geçti |
| C-LATE, STD B25–B60 | +0.0009 [+0.0005, +0.0013] | geçti |

**Ayrı hükümler (DEV):**

| konu | hüküm |
|---|---|
| erken başarı | **korunuyor:** +0.0002 [−0.0003]; b < 16'da tanım gereği C1 |
| geometrik sağlamlık | **gösterilmedi:** +0.0045 [−0.0016]. K5 +0.022 [+0.017], K4 **−0.013** [−0.017, −0.008] (kayıp gösterildi) |
| zor örnekler (STD) | kısa-Keyhole NEW yakalama 0.906 → 0.925, NEW iletim özgüllüğü 0.211 → 0.206. Birini artırıp ötekini azaltan bir takas; çözüm sayılmaz |
| iki sınıf (STD) | Keyhole yakalama +0.0014 [+0.0007], iletim yakalama −0.0000. Geometrikte iletim yakalama −0.006 [−0.009] |
| hedef maliyeti (kayıtlı yollarda, uçtan uca değil) | 0.95'e ulaşma 172'ye 171; harcama 21.9'a 21.8 (8 başlangıç ve b + 4 teyidi dahil); kısıtlı ortalama tasarruf +0.07 [−1.01]. 0.93: −0.17 [−0.51]. 0.90: +0.04 [−0.05]. Fark yok |
| koruma | B60'ta 0.95'i koruyan 138'e 134 (+0.020 [−0.010]); ulaştıktan sonra her bütçede 0.95'in üstünde kalan 33'e 35 |
| kontrol: yerel kural gerekli mi? | **hayır.** Geometrikte sabit ortalama GATE'ten iyi (−0.0055 [−0.0086, −0.0023]). GATE yalnız STD erken dönemde iyi (+0.0013), o da b < 16'daki C1 geri dönüşü yüzünden |
| güçlü alternatif D_on_A | C1'e göre STD erken −0.0007, geometrik +0.0013 [−0.0017, +0.0043]. Bir şey değiştirmiyor |

**Hedefler, kayıtlı yollar, STD (200 öğrenici-yol):**

| sistem | 0.95: ulaşan / ulaşamayan | teyit b ort. | harcama ort. (medyan) | B60'ta koruyan | kaybeden | her bütçede üstünde kalan |
|---|---|---|---|---|---|---|
| C1 | 171 / 29 | 17.8 | 21.8 (17) | 134 | 37 | 35 |
| GATE | 172 / 28 | 17.9 | 21.9 (18) | 138 | 34 | 33 |
| HA_LEAN | 169 / 31 | 20.0 | 24.0 (21) | 136 | 33 | 31 |
| sabit ortalama | 170 / 30 | 17.8 | 21.8 (17) | 138 | 32 | 29 |
| D_on_A (100 yol) | 84 / 16 | 17.9 | 21.9 (19) | 66 | 18 | 12 |

0.90 ve 0.93 satırları `dev/dev_targets_std.csv` dosyasında. 61 ile sınırlanmış skor gerçek simülasyon maliyeti değildir.

**Bloklarda bağımlılık:**
- K5 ve K4 test bölgeleri bütün başlangıçlarda aynı sabit k-means bölgeleridir. Yeni bir başlangıç yalnız ödenmiş yolu değiştirir.
- Belirsizlik bu yüzden yol değişkenliğidir, yeni bölge değil.
- STD'de bir tekrarın beş katı aynı bölmeyi paylaşır. Küme, tekrardır.

## 5. Neden olmadı?

4,704 kapı uyumunun hepsinde yeterli veri vardı.

| | STD | K5 | K4 |
|---|---|---|---|
| ödenmiş koşularda uzaysal çapraz log loss, C1 − HA_LEAN | −0.069 | −0.073 | −0.052 |
| ortalama a / c | 0.39 / 0.18 | 0.46 / 0.22 | 0.34 / 0.13 |
| test noktalarında ortalama w, B25–B60 | 0.61 | 0.66 | 0.60 |

**Neden yanlış yöne bakıyor?**
- Ödenmiş veride C1, tutulmuş uzaysal grupları her tasarımda HA_LEAN'den iyi tahmin ediyor.
- c pozitif: kural uzaklaştıkça C1'e daha çok güveniyor.
- K5 test bölgelerinde ise doğrusu tam tersi: HA_LEAN +0.044 iyi.
- Ağırlık her tasarımda 0.6 / 0.4 civarında bir sabite oturuyor. Bu sabit K5'te yardım ediyor, K4'te zarar veriyor.

**Neden ödenmiş veriden çözülemez?**
- Blok tasarımında test bölgesi uyum ve sorgudan tümüyle saklı.
- Bölgeye özgü doğru seçimi belirleyecek bilgi hiç açılmayan koşularda.
- Bu bir bilgi sınırı, kural ayarıyla çözülmez.

## 6. Bağımsız yeniden hesap

`exports/dev/` içinde:
- her bütçede C1, HA_LEAN, GATE ve D_on_A tahminleri (float32);
- kayıtlı yolların sorgu sırasındaki ödenmiş koşu kimlikleri.

Sabit ortalama bu bileşenlerden yeniden üretiliyor.

Değerlendirici kodu kullanılmadan, yalnız bu dosyalar ve etiket manifesti ile yeniden hesaplananlar:
- C-GEO, C-EARLY, C-LATE;
- sabit ortalama − C1;
- kazanç alanı G1.

En büyük fark 4·10⁻¹⁷, G1 farkı 0: **PASS** (`exports/EXPORTS_ACCEPTANCE.json`). Öğrenici başına AULC ve hedef karşılaştırması da PASS.

## 7. Nihai kullanım kararı

| | karar |
|---|---|
| C1 + margin | **değişmeden kalıyor**: havuz içi erken ve hedefte durma kullanımı için önerilen öğrenici (C1C) |
| GATE | **hiçbir kullanım için yeterli kanıt yok.** K5'teki model etkisi DEV'de pozitif, ama K4'te negatif; ödenmiş veriden hangi durumda olunduğu ayırt edilemiyor. Taze sınama yapılmadı |
| HA_LEAN + margin | donmuş referans. C1C-003'teki "uzanımda daha temkinli" ifadesi bu verilerde yalnız K5 tipi bölgeler için doğru: K4'te C1 iyi, iki tasarım birlikte fark göstermiyor (+0.005 [−0.008]) |
| sabit ortalama | yalnız kontrol; benimsenmedi. STD'de erken kayıp −0.0011 [−0.0020] |

Bu görevden sonra yeni araştırma otomatik başlamıyor.

## 8. Maliyet

| iş | birim | hata | işçi-saat | CPU-saat | yeni simülasyon |
|---|---|---|---|---|---|
| kazanç alanı analizi | 1 | 0 | 14 s | 14 s | 0 |
| duman testi (indirgeme, gölge, maliyet) | 6 koşu | 0 | 0.03 | 0.03 | 0 |
| DEV tekrar oynatması (kayıtlı yollar, kapı uyumları) | 392 | 0 | 1.54 | 1.52 | 0 |

**Simülasyon sayımı**
- Kayıtlı yolların 60 simülasyonu (8 başlangıç + 52 sorgu) EA'da ödenmişti. Burada yeniden ücretlendirilmedi.
- Kapının uyumları yalnız zaten açılmış koşuları kullanır.

**İşlem süresi:** kapı uyumu başına 1.1–1.2 s CPU. Bir GATE + margin yolu, öğrenici başına 31 s CPU.

**Sürüm sabitleri:** başlangıç commit'i c8437907; bilimsel taban 3caf7c4e. Görev 13:31:37 UTC'de açıldı, 14:32:46 UTC'de kapandı (yaklaşık 61 dakika); 6 saat sınırının çok içinde.

## 9. Teslim edilenler ve Python dosyaları

**Yeni Python dosyaları** (mevcut hiçbir dosya değişmedi):

| dosya | SHA-256 | rol |
|---|---|---|
| `src/fr_gain.py` | 82fbb41d346bba3470f39c1ce9528389cf7190f783747890983d84bf8ca7607e | kazanç alanı teşhisi (değerlendirici) |
| `src/fr_gate.py` | 50bd1f3273b20ff772070f3b64dc17df98103810012db7ab4f4573dbe0f8f4d1 | aday GATE, DEV tekrar oynatması, duman testi. Aday fonksiyonları c4edc59a ile birebir; sonradan yalnız çalıştırılmamış taze sınama birimleri eklendi |
| `src/fr_dev_eval.py` | 9fc2d2d366124e2385e8ba7454334cc2e353a67049586fe222e01634ed5d70c0 | DEV değerlendirmesi ve kural |
| `src/fr_dev_export.py` | 26dc5bb632aa03385642e3b6e5cef3cc2160eacb35b5697d715b13635349cd1e | DEV tabloları, dışa aktarım, bağımsız yeniden hesap |
| `src/fr_inventory.py` | 3990b29aa29cf24f7dbcf7ec055fa9b33e91f94b524a0370e631924a7f5210d8 | kullanılmış kimlik envanteri |
| `src/fr_eval.py` | eec9aacadc9836c57ec5e53887d6f41fa02380991ca6bf70454eb087c3fd064b | taze sınama için hazırlandı; **çalıştırılmadı** |
| `src/fr_export.py` | d66b7b80a7bedd3fd73f786b9857d95f2b7c0cc6045d832b6179d2771764913a | taze sınama için hazırlandı; **çalıştırılmadı** |
| `src/fr_freeze.py` | cbf5250a73b6eba8bff0d4bb18191c4bf7a4d7a54d8dc46299ac9baf59ba5108 | taze sınama için hazırlandı; **çalıştırılmadı** |

**Küçük yerel harita: hangi dosya neyi çağırıyor**
- **fr_gain:** kayıtlı EA ve C1C dışa aktarımları ile etiket manifestini okur; `el_eval.tstats` kullanır.
- **fr_gate:**
  - C1 tahmini için `ea_cand.predict` → `ea_diag2.cf_generic` → `ea_diag.lin` → `rc22_common.phr_family`;
  - HA_LEAN için `rc23_common.state` → `rc20_attr.cf` → `phr_family`;
  - görevler ve başlangıç için `rc19b_keyhole._rev_with`, `rc22_common.startup`, `el_cross.tasks_for`.
- **fr_dev_eval ve fr_dev_export:** kayıtlı tahminler ile fr-dev ağırlıklarını birleştirir; `el_eval`, `el_export`, `ea_cand_eval.sustained` kullanır.

**Dosyalar**

| konu | dosya |
|---|---|
| görev, durum, sonraki adım | `TASK.md`, `STATE.json`, `NEXT_ACTION.md` |
| protokoller | `GAIN_AREA_PROTOCOL.md`, `PROTOCOL_FR_DEV.md`, `PROTOCOL_FR_FRESH.md` (çalıştırılmadı) |
| kazanç alanı | `gain/` |
| DEV | `dev/` |
| dışa aktarımlar | `exports/` |
| kimlik envanteri | `freeze/ID_INVENTORY.json` |
| maliyet | `COST_BREAKDOWN.json` |
| Hub ve Astra | `hub/` |
| toplantı özeti | `MEETING_SUMMARY_IOAN.md` |

## 10. Research Hub ve Astra

**Research Hub** (main 4fc9b5d, yalnız okundu): bkz. `hub/RESEARCH_HUB_RELATION.md`.
- FR, **C1C-003**'e bağlanıyor: "HA_LEAN, uzanım için daha temkinli referans".
- C1C kararı ve kodu değişmedi.

**Astra'nın finite-pool assurance çalışması:** `hub/ASTRA_FINITE_POOL_ASSURANCE_RECORD.md`. Kaynaktan aktarıldı, Opus yeniden hesaplamadı, Astra dosyaları depoya kopyalanmadı.
- **Özet:**
  - Sabit bir C1'i az ek etiketle denetlemenin asıl pratik kapısı geçmedi: 32 etikette kararların %5.6'sı çözüldü.
  - Hedef üstündeki hiçbir hücre onaylanamadı.
  - Yalnız betimsel nokta tahmini onarıldı.
  - İki sürümün sıralamasını çözmek ileride ayrı kaydedilecek bir çalışma için bir ipucu.
- **FR ile ilişkisi:** iki çalışma bağımsız. FR, Astra'nın kodunu ya da çıktısını kullanmadı. Active testing çalışması yeniden açılmadı.

## 11. Sınırlar

- Bütün sonuç DEV. Aynı havuz ve kayıtlı yollar; uçtan uca GATE + margin sınanmadı. Model etkisi kuralı geçmediği için bu adım hiç atılmadı.
- GATE'in STD'deki küçük olumlu farkları (geç +0.0009, log loss −0.0011) kural dışı DEV gözlemleri. Hiçbir iddiaya genişletilmez.
- %95'i kesintisiz koruma ya da güvenli durma garantisi iddia edilmiyor.

## 12. Tez için çıkarım

**Tek cümleyle:** iki modelin ölçülmüş tamamlayıcılığı gerçek, ama yalnız açılmış simülasyonlardan öğrenilen sade bir güven kuralı onu geometrik uzanımda kullanılabilir kılmıyor.
- Görülmemiş bölgede hangi modelin doğru olduğunu belirleyen bilgi, açılmamış koşularda.
- C1 + margin havuz içi önerilen öğrenici olarak kalıyor.
