# RC24 — Fizik bağlantılı istifleme: güçlü karşılaştırmalar, yeni yöntem ve taze veride doğrulama (Opus, 2026-10-21/22)

**Kanıt etiketi: DEV.**
- Bütün sonuçlar aynı 541'lik havuzun yeni bölmeleri, yeni geometri blokları ve sentetik dünyalardır. Fiziksel doğrulama değildir.
- Hedef harcamaları test etiketlerinden hesaplanmıştır. Bunlar çevrimdışı değerlendirmedir; durma kuralı değildir.

**Pencere ve kaynak:**
- Tek 48 saatlik pencere 2026-10-21 20:32:31Z'de başladı. Aşamalar arasında yeniden başlatılmadı. İş 23:28Z'de bitti (≈ 3 saat).
- Kalan süreyi doldurmak için iş üretilmedi; kuyruk `stop_runner` ile kapatıldı.
- Bütün yerel çekirdekler kullanıldı; yetki koordinasyon kaydına işlendi.
- Zamanlama denemesi: 6 × 1 iş parçacığı dakikada 63.7 iş yükü, 8 × 1 ise 61.4 verdi. Bu yüzden 6 işçi seçildi; kısa süreli olarak 7–8 işçiye çıkıldı.
- Toplam 9.0 CPU-saat, 2,062 kuyruk birimi, hata yok (`COMPUTE_RC24.csv`). Ayrıca kabul testleri, tanılar ve ön kontroller etkileşimli çalıştırıldı.

**Donmalar (hepsi sonuçlardan önce commit edildi):**
- Stage A: e69c726c.
- Stage C: e82d2845.
- Sentetik test: b3b54f75.

## Türkçe sonuç

**Tek karar:** Tezin öğrenicisi **HA_TREND + margin** (fizik bağlantılı istifleme).
- RC23'ün HA_LEAN sınıflandırıcısı aynen korunuyor.
- Tek değişiklik, derinlik emülatörünün ortalamasının log h'ye bağlanması: log A = μ + θ·z_h + g + e, θ ~ N(0, 3²) integre ediliyor.

Taze veride önceden kaydedilen kuralın sonucu **CONFIRMED (DEV-confirm)**:
- standart bölmelerde HA_LEAN'e göre non-inferior;
- geometri bloklarında HA_LEAN'den daha iyi: BA-AULC +0.0112, 8/8 tohum, tek yönlü %95 alt sınır +0.0080.

Kazanç şu kontrollerden geçti:
- **Model kaynaklı:** aynı yollarda +0.0101, 8/8.
- **Önsele duyarsız:** b = 1 ile +0.0095, b = 10 ile +0.0102.
- **Fiziğe özgü:** genel doğrusal trend −0.013 kaybettiriyor.

Sınır: yalnız-h öğrenicisi, standart koşulun erken bütçesinde (−0.006) ve bloklarda (−0.008) hâlâ biraz daha iyi. Hiçbir model sert köşeyi çözmüyor.

### 1) Anlatı

**Hata düzeltmesi (§2).**
- RC23 karar kuralındaki `startswith("NON-INFERIOR")` hatası tarihli bir düzeltmeyle giderildi. Kural artık açık PASS / FAIL / INCOMPLETE durumları kullanıyor.
- D1, kaydedilmiş tablolardan GP fit'i yapılmadan yeniden hesaplandı: 26 sayı birebir üretildi, en büyük fark 4e-17.
- Olumsuz kontroller: eski kural dört başarısız ya da eksik girdiyi D1'e geçiriyor; yeni kural hiçbirini geçirmiyor.
- PHR_NRMAP için doğrudan tanık eklendi: bir kanal bütün ödenmiş koşularda yoksa `ValueError` veriyor. HA_LR bu durumda sonlu kalıyor ve ayrıca kaydedildi.

**Stage A: güçlü karşılaştırmalar** (taze tekrarlar 59–66). İlgili satırlar Bölüm 3'te.
- **Q1 – yalnız-h yeterli mi?** Hayır.
  - BA-AULC'de non-inferior; erken pencerede +0.006.
  - Ama BA ≥ 0.95'e 8 tekrarın 5'inde ulaşıyor (HA_LEAN 7/8).
  - Olasılık kalitesi kötü: log loss +0.023.
- **Q2 – tarihsel M3 ve E1:**
  - M3 BA'da benzer (non-inferior), ama olasılıkları çok kötü (LL +0.30 / +0.12). Bunun nedeni C = 1e6 ile doymuş h ortalaması.
  - E1 + straddle daha kötü (−0.025 / −0.012) ve BA ≥ 0.93'e 8 simülasyon fazla harcıyor.
  - G3 daha kötü.
- **Q3 – HA_LEAN üzerinde straddle:**
  - Belirsizliği üç kaynaktan kuruldu ve Monte Carlo ile doğrulandı.
  - Seçimlerin %86'sı margin'den farklı ve sayısal olarak ayırt edilebilir.
  - Yine de daha kötü (−0.011 / −0.009). Kaybın tamamı yoldan geliyor.
- **Q4 – ayrıştırma (eşleştirilmiş matris):**
  - E1 ve G3'ün kaybı model kaynaklı.
  - Yalnız-h'nin erken kazancı yarı model, yarı yol.
  - Yalnız-h'nin margin yolu HA_LEAN modeli için de daha iyi (+0.003).
  - Kalibrasyon modelleri ayırmıyor: eşik açığı her modelde 0.006–0.012.

**Sert bölge (§4).**
- Kullanıcının B60 sayıları RC23 kayıtlarında birebir doğrulandı. HA_LEAN için:
  - 10 NEW kısa-K duyarlılığı 0.95;
  - 12 NEW iletim özgüllüğü 0.33;
  - bölgesel BA 0.64;
  - havuzlanmış 22 kısa-K duyarlılığı 0.80.
- Yalnız-h bu grupta 1.0 / 0.0 / 0.5 veriyor.
- **Mekanizma sorusu (zamanlama):** Kısa-Keyhole olayı bir başlangıç geçici olayı. 10 koşunun hepsinde keyhole kareleri, açılış (forming) evresinin bittiği anda ortaya çıkıyor (kaydın 0.17–0.27'si).
- **Açılış sonrası açıklama:** ölçülen derinlik zayıf ayırıyor (LOO AUC 0.745); T0 penceresi özetleri buna bir şey eklemiyor.
- **Açılış öncesi kullanım:** tahmin edilen özet de bir şey eklemiyor (0.755).

**Stage B: iki prototip ve bir kazanan ablasyon** (kullanılmış DEV verisi).
- **P1 (PAC):** yapısal model, yani ölçülmüş derinlikle eğitim ve tahminde hata-değişkenli integrasyon.
  - Standart koşulda HA_LEAN'i geçmedi. Önerme P3 nedenini açıklıyor: integrasyon tek bir yapılandırmanın 0.5 kararını değiştiremez.
  - **Kapatıldı.**
  - Ama ablasyonları asıl mekanizmayı buldu: bloklarda fizik bağlantısı gerekli. Trendsiz yapısal model −0.023, genel trend −0.006, **HA_TREND** +0.011 (8/8).
- **P2 (JEER):** iki gözlemli beklenen hata azaltımı; derinlik ve etiket fantezisi, sorgunun kendi etiketi hariç.
  - 16 öğrenicide BA −0.004 / −0.001.
  - Köşe sorgu payı değişmedi (0.349'a karşı 0.352).
  - Maliyeti 30 kat.
  - Pilot ölçütleriyle **durduruldu**; BA_RISK benzeri bir devam yapılmadı.
- **HT_PHYS:** sorgular fizik margin'iyle (yalnız-h), tahminler HA_TREND ile. İkincil aday olarak yazıldı.

**Stage C: taze veride doğrulama.**
- Koşullar: tekrarlar 67–74 ve blok tohumları 9–16. 240 kendi-sorgu ve 160 eşleştirilmiş birim.
- **Birincil aday HA_TREND + margin: CONFIRMED.**
- **İkincil aday HT_PHYS: o da CONFIRMED.** Standart koşulda HA_LEAN'e göre erken pencerede +0.0078 (alt sınır +0.0014), bloklarda +0.0051.
- Ama HT_PHYS bloklarda HA_TREND + margin'den 0.006 geride. Sert grupta kısa-K duyarlılığını 0.96'dan 0.75'e düşürüyor.

**Sentetik ölçüt (§8).**
- Geliştirme ve test aileleri ayrı tutuldu; test ailesi başına 10 tohum kullanıldı.
- S2 ve S3 destekleniyor:
  - bağlantı yanlış ya da işe yaramazken kayıp ≤ 0.006;
  - yardımcı çıktı değersizken karmaşıklık kazandırmıyor.
- S1 kayıtlı biçimiyle desteklenmedi: iki ailede de ortalama pozitif (+0.025, +0.015), ama ikinci ailede yalnız 6/10 tohum.
- S4 desteklenmedi: gürültülü dengeli ailede HA_TREND beklenenden fazla kazandı (+0.012).
- S5: margin, karar sınırında durmayan rastgele etiketli bir kutuyu aşırı örneklemiyor. Gerçek köşedeki %45, köşenin sınırın tam üstünde durmasından kaynaklanıyor.

### 2) Tek model + edinim ve nedeni

**HA_TREND + margin**, çünkü:
- önceden seçilen birincil aday taze veride tam olarak doğrulandı;
- tek bileşenli, mekanizması açık bir değişiklik: Önerme P1, sabit ortalamalı istiflemenin dış değerlemede h boyunca eğim hatası verdiğini gösteriyor;
- maliyeti HA_LEAN ile aynı: adım başına 0.25 s;
- HT_PHYS standart koşulda biraz daha iyi, ama bloklarda ve kısa-K duyarlılığında daha kötü. Önceden kayıtlı birincil seçim değiştirilmedi.

### 3) BA-AULC ve sorgu sonuçları (kontrollerle)

| koşul | sistem | BA-AULC B8–B24 | B8–B60 | log loss B8–B60 | BA ≥ 0.93: ulaşılan / ortalama harcama | BA ≥ 0.95: ulaşılan / ortalama harcama |
|---|---|---|---|---|---|---|
| Stage A (59–66) | HA_LEAN + margin | 0.9360 | 0.9467 | 0.142 | 8/8 · 14.5 | 7/8 · 35.6 |
| | yalnız-h + margin | 0.9422 | 0.9451 | 0.165 | 8/8 · 13.5 | 5/8 · 35.2 |
| | M3 + margin | 0.9391 | 0.9443 | 0.266 | 8/8 · 15.8 | 7/8 · 30.6 |
| | E1 + straddle | 0.9115 | 0.9344 | 0.202 | 8/8 · 22.8 | 7/8 · 40.4 |
| | G3 + margin | 0.9002 | 0.9289 | 0.269 | 8/8 · 29.6 | 6/8 · 43.2 |
| | HA_LEAN + straddle | 0.9235 | 0.9372 | 0.171 | 8/8 · 20.1 | 5/8 · 43.8 |
| **Stage C STD (67–74)** | HA_LEAN + margin | 0.9322 | 0.9464 | 0.147 | 8/8 · 15.0 | 8/8 · 31.4 |
| | **HA_TREND + margin** | **0.9356** | **0.9472** | 0.149 | 8/8 · 14.3 | 7/8 · 31.9 |
| | HT_PHYS | 0.9400 | 0.9479 | 0.151 | 8/8 · 13.4 | 8/8 · 30.1 |
| | yalnız-h + margin | 0.9416 | 0.9451 | 0.177 | 8/8 · 13.1 | 5/8 · 28.4 |
| **Stage C BLOCK (9–16)** | HA_LEAN + margin | 0.9268 | 0.9274 | 0.200 | 8/8 · 23.0 | 0/8 |
| | **HA_TREND + margin** | **0.9375** | **0.9386** | 0.182 | 8/8 · 13.6 | 3/8 · 24.7 |
| | HT_PHYS | 0.9334 | 0.9325 | 0.207 | 8/8 · 14.6 | 0/8 |
| | yalnız-h + margin | 0.9401 | 0.9468 | 0.185 | 8/8 · 13.6 | 8/8 · 33.3 |

Okuma notları:
- Değerler havuzlanmış tekrar eğrileridir; bireysel öğrenici tabloları `stage_a/STAGE_A.md` ve `stage_c/STAGE_C.md` içinde.
- Stage C'de iki pencerede de duyarlılık ve özgüllük raporlandı. Bloklarda HA_TREND özgüllüğü 0.898'den 0.913'e yükseltiyor; duyarlılık 0.957'den 0.964'e çıkıyor.

### 4) Kısa pozitifler ve yerel negatifler (B60; değerlendirici üyeliği)

| koşul | sistem | 10 NEW kısa-K duyarlılığı | 12 NEW iletim özgüllüğü | bölgesel BA | 22 havuz kısa-K duyarlılığı |
|---|---|---|---|---|---|
| RC23 (51–58) | HA_LEAN | 0.950 | 0.333 | 0.642 | 0.801 |
| Stage A | HA_LEAN | 0.900 | 0.333 | 0.617 | 0.790 |
| | E1RAW | 0.825 | 0.385 | 0.605 | 0.801 |
| | yalnız-h | 1.000 | 0.000 | 0.500 | 0.864 |
| Stage C STD | HA_LEAN | 0.975 | 0.323 | 0.649 | 0.835 |
| | HA_TREND | 0.963 | 0.344 | 0.653 | 0.835 |
| | HT_PHYS | 0.750 | 0.396 | 0.573 | 0.744 |
| Stage C BLOCK | HA_LEAN | 0.988 | 0.260 | 0.624 | 0.938 |
| | HA_TREND | 1.000 | 0.135 | 0.568 | 0.920 |

- Hiçbir model iki sınıfı bu bölgede ayırmıyor; yerel BA en iyi durumda 0.65.
- Bloklarda HA_TREND burada yerel bir kayıp veriyor (iletim özgüllüğü 0.26 → 0.14). Global BA bunu gizliyor; açıkça raporlanıyor.

### 5) Literatür matrisi

`literature/LITERATURE_MATRIX.md`, 21 çalışma. Kolonlar: görev; sorgudan önce bilinen; sorgu başına çıktı; fiziğin yeri; belirsizlik aktarımı; edinimin azalttığı kayıp; farkımız; özel durum mu; uygulama.
- **En yakın çalışmalar:**
  - Bryan & Schneider 2008: bileşik seviye kümesi, bilinen bağlantı, sorgu başına tek gözlenebilir.
  - Astudillo & Frazier 2019/2021: bileşik ve ağ BO'su.
  - Ziatdinov 2021: GP ortalaması olarak fizik modeli.
  - Hardcastle 2025: GPC'de sabit fizik önseli.
- **Hiçbirinde birlikte yok:**
  - her sorguda doğrudan gözlenen etiket ve aynı kayıttan gelen yardımcı yanıt;
  - hem etiket modeline hem de yardımcı emülatörün ortalamasına giren bilinen boyutsuz sayı;
  - küçük bütçeli havuz sınıflaması.

### 6) Bilinen bileşen / değişikliğimiz / ölçülen fayda / kanıt sınırı

| bilinen bileşen (kaynak) | değişikliğimiz | ölçülen fayda | kanıt sınırı |
|---|---|---|---|
| yardımcı çıktının GP emülatörü + istifleme (kriging; Wolpert 1992; van der Laan 2007; RC20–23) | yalnız derinlik, kayıt kalitesi gürültüsü, dürüst K = 10 | HA_LEAN = D1 (RC23) | DEV |
| GP ortalaması olarak fizik (Ziatdinov 2021; Hardcastle 2025; Week-9 M3) | bağlantı YARDIMCI emülatörde, θ integre, istifleme içinde (HA_TREND) | bloklarda +0.0112 (8/8; alt sınır +0.008); BA ≥ 0.93 harcaması 23.0 → 13.6; standart non-inferior | bloklarda ve erken standartta yalnız-h altında; tek dış değerleme tasarımı; sert bölgede yerel kayıp |
| öğrenilmiş düzenlileştirme (RC21) | değişmedi | olasılık kalitesi | – |
| hata-değişkenli regresyon kalibrasyonu (Carroll 2006) | GP kovaryatlı yapısal kompozit (PAC) | yok (P3) | DEV pilotu; kapatıldı |
| SUR / EER / EPIG (Bect 2012; Roy & McCallum 2001; Bickford Smith 2023) | iki gözlemli ileri bakış, kendi etiketi hariç (JEER) | yok; maliyet 30× | 16 öğrenicilik pilot; kapatıldı |
| straddle / LSE (Bryan 2005; Gotovos 2013) | HA_LEAN üzerinde üç kaynaklı moment | −0.011 / −0.009 | Stage A taze veri |
| vekil model ile seçim (selection via proxy) | yalnız-h margin'i + HA_TREND tahmini (HT_PHYS) | standart erken pencerede +0.0078 (CONFIRMED) | bloklarda ve kısa-K duyarlılığında daha kötü |

### 7) İngilizce yöntem makalesi taslağı

`paper/PAPER_DRAFT.md`. Bölüm 6, Stage C sonuçlarıyla dolduruldu.

### 8) Denklemler, algoritma, kaynaklar ve yeniden üretim

- Denklemler, algoritma ve yeniden üretim komutları: `paper/EQUATIONS_AND_ALGORITHM.md`.
- Önermeler ve kanıtları: `analysis/PROPOSITIONS.md`.
- Dışa aktarımlar kabul testini geçti: Stage A 2968 hücre; Stage C STD ve BLOCK 1272'şer hücre; |Δ| = 0.

### 9) Araştırma kararı

**Gösterildi (DEV-confirm):**
- Bilinen bir boyutsuz fizik sayısı varken, yardımcı yanıtın emülatörünü bu sayıya bağlamak istiflenmiş sınıflandırıcının dış değerleme kaybını büyük ölçüde gideriyor; standart performansı da koruyor.
- Bunu genel bir trend sağlamıyor; önseli değiştirmek de değiştirmiyor.

**Hipotez olarak kalanlar:**
- Kazancın başka bir simülatöre ya da fiziksel deneylere taşınması. Sentetik destek kısmi.
- Sert köşenin aleatorik olduğu. Başlangıç geçici olayına dayanan bir yorum; henüz test edilmedi.
- HT_PHYS'in fizik yolu avantajının genelliği.

**Yayın iddiasını en çok güçlendirecek eksik:** dış fiziksel doğrulama.
- `PHYSICAL_DATA_PROPOSAL.md`'deki R3: havuz dışı LS'de 16 koşu; öğrenicilerin tahminleri koşulardan önce dondurulur.
- Aynı yerdeki R1: köşe tekrar koşuları; sert bölgenin deterministik olup olmadığını gösterir.
- Bu öneri yalnız yazıldı; hiçbir simülatör işi başlatılmadı.
