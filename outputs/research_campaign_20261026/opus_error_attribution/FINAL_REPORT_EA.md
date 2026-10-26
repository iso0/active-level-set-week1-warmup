# EA çalışması: hata nereden geliyor, ve ona dayanan geliştirme işe yarıyor mu?

Opus, 2026-10-26. **Kanıt etiketi: DEV.**
- Bütün sayılar aynı 541 koşuluk havuzdan geliyor. Yeni bölmeler ve başlangıçlar dış fiziksel doğrulama değildir.
- **Pencere:** 2026-10-26 13:33:01 UTC'de açıldı, bitişi 2026-10-28 13:33:01 UTC olacaktı. İş bitince 17:17 UTC'de kapatıldı.
- **Hesap:** 1495 birim, hata yok, 6.6 işçi-saat. En çok 3 tek iş parçacıklı işçi kullanıldı; Astra'nın payı kullanılmadı.
- Simülatör, bulut, C4 ya da korunan değerlendirme kullanılmadı.

## Sade özet

**1. Darboğaz neymiş?** **Sorgulanmamış koşuların derinliği.**
- Sınıflandırıcı, etiket sayısı ve seçici darboğaz değil. Gerçek derinlik bilinseydi, aynı sınıflandırıcı:
  - 8 simülasyonla BA 0.957, 12 simülasyonla 0.972 verirdi;
  - bugünkü sistem aynı bütçelerde 0.897 ve 0.933 veriyor.
- Erken dönemdeki bu açığın çoğu bir bilgi sınırı: 8–24 ödenmiş derinlikten öteki koşuların derinliği ancak bu kadar iyi kestirilebiliyor.
- Açığın daha küçük ama giderilebilir bir parçası bir **kestirim hatası**:
  - fizik eğilimli derinlik modelinin (HA_TREND) hiperparametreleri küçük örneklemde ML-II ile kestirilince aşırı uyuyor;
  - b ≤ 16'da uyumların hemen hepsinde bir hiperparametre sınıra dayanıyor;
  - gürültü sıfıra çöküyor.
- Geç dönemde mevcut sistem, girdilerden ulaşılabilecek tavana zaten çok yakın.

**2. Hangi değişiklik neden işe yaradı, hangisi yaramadı?**
- **İşe yarayan (C1):** HA_TREND'in derinlik modeline sabit, zayıf bilgilendirici hiperöncüller koyup ML-II yerine MAP kestirimi kullanmak. Öncül:
  - gürültünün çökmesini ve uzunluk ölçeklerinin uçlara kaçmasını engelliyor;
  - fizik eğiliminin erken kazancını koruyor, biraz da artırıyor;
  - olasılık kalitesini eski düzeye getiriyor;
  - geç dönemdeki kaybı büyük ölçüde gideriyor.
- **İşe yaramayanlar:**
  - **Aynı öncülü eğilimsiz modele (HA_LEAN) koymak** erken BA'yı 0.038 düşürdü. Eğilim olmadan, veriden uzakta tahmin sabit ortalamaya dönüyor.
  - **Öncülsüz, daha çok başlangıç noktalı optimizasyon** C1'in kazancını vermedi. Kazanç öncülden geliyor, hesap bütçesinden değil.
  - **Sınıflandırıcıyı ölçülmüş derinlikle eğitmek** kötüleştirdi (−0.009).
  - **Margin'in köşeye harcadığı sorguları kısmak** küçük bir pay verdi: +0.002.

**3. En güçlü kontrole karşı ne kazandık?** Taze doğrulama: tekrar 163–202, 200 tek öğrenici.

| C1 + margin, karşılaştırılan sistem | sonuç |
|---|---|
| tez öğrenicisi HA_LEAN + margin | erken BA-AULC (B8–B24) **+0.0056** [alt sınır +0.0038]; bütün aralık +0.0016; geç dönemde kayıp gösterilmedi |
| en iyi erken kontrol D (HA_LEAN seçer / HA_TREND tahmin eder) | erken +0.0013 (gösterilemedi); olasılık kalitesi daha iyi (log loss −0.005); BA 0.95'in üstünde sürekli kalma +0.085 [+0.024]; geç dönem kaybı yok, D'de var |
| evidence karışımı E | erken +0.0029 [+0.0013] |

**4. Kaç sorguda hangi başarıya ulaşılıyor?** Taze test, 200 öğrenici, 8 başlangıç simülasyonu dahil.

| hedef | sonuç |
|---|---|
| BA 0.90 | C1 200/200 öğrenicide ulaşıyor (A 199/200). 16 simülasyonda ulaşan pay %96.5'e karşı %92. Medyan 12 simülasyon. |
| BA 0.93 | C1 194/200, A 193/200. Medyan ikisinde de 13. Kısıtlı ortalama tasarruf +0.6 simülasyon, gösterilemedi; kural "daha kötü değil" dedi. |
| BA 0.95 | C1 169/200, A 161/200. Ulaşamayan 31'e karşı 39 öğrenici. Medyan 21'e karşı 22.5 simülasyon. Kısıtlı ortalama tasarruf **+2.0 simülasyon** [alt sınır +0.21]. Kural "güvenilir" dedi. Hedefi 60. simülasyona kadar hiç kaybetmeden tutan öğrenici 41'e karşı 30. |

**5. Hangi iddia DEV, hangisi hâlâ hipotez?**
- **İkisi de DEV:**
  - Bütün sonuçlar aynı havuzdan.
  - C1'in erken kazancı iki bağımsız 40 tekrarlık sette tekrarlandı: +0.0053 ve +0.0056.
- **Tek testte gösterildi, tekrarı gerekiyor:**
  - 0.95 tasarrufu ve güvenilirliği bu testte gösterildi.
  - Ama önceki DEV setinde 0.95'i koruma payı tersine işaret vermişti (−0.055).
- **Hipotez:** geç dönemdeki kalan farkın, hiperparametrelerin margin'in sınıra yığılmış örnekleminden kestirilmesinden geldiği.
- **Hiçbiri gösterilmedi:**
  - dış veride geçerlilik;
  - eski beş bölgeye geometrik uzanımda iyileşme. C1 bölge başına −0.049; uyarı tetiklendi.

**6. Sonraki tek gerekçeli adım ne?** C1 + margin'in BA 0.95 hükmünü, daha büyük (en az 80 tekrar) ve önceden kaydedilmiş, hiç kullanılmamış kimliklerle bir kez daha sınamak.
- Erken kazanç zaten tekrarlandı.
- Belirsiz olan 0.95 tarafı; tez öğrenicisi bu sonuç olmadan değiştirilmemeli.

**Hüküm:**
- **Erken öğrenme için C1 + margin daha iyi** ve olasılık kalitesini koruyor.
- **0.93'te** daha kötü değil.
- **0.95'te** bu testte daha az simülasyonla ve güvenilir biçimde ulaşıyor, ama setler arası kararlılık gösterilmedi.
- Koşulsuz kazanan değil: eski beş bölgeye uzanımda zayıf.
- Eski donmuş karar (tez öğrenicisi HA_LEAN + margin) değiştirilmedi.

## 1. Hata ayrıştırması (teşhis)

**Kapsam:**
- **Yollar:** STD tekrar 83–122, 200 öğrenici, kayıtlı HA_LEAN yolları.
- **Basamaklar:** her biri aynı ödenmiş veride yalnız bir şeyi değiştiriyor.
- **Oracle basamakları yalnız değerlendirici teşhisi:**
  - yöntem değil;
  - sorgu tasarrufu sayılmaz;
  - evrensel tavan değil.

| basamak | erken BA-AULC | geç |
|---|---|---|
| mevcut HA_LEAN | 0.934 | 0.955 |
| HA_TREND | 0.938 | 0.954 |
| ideal hiperparametreli HA_TREND (oracle) | 0.941 | 0.957 |
| sınırsız veriyle derinlik emülatörü (oracle) | 0.956 | 0.961 |
| gerçek test derinliği (oracle) | 0.948 | 0.974 |
| gerçek derinlik, iki tarafta (oracle) | **0.974** | **0.982** |
| + h'ye dik girdiler (oracle) | 0.968 | 0.981 |
| + esnek (h, derinlik) artığı (oracle) | 0.974 | 0.982 |

**Hipotezlerin durumu:**

| hipotez | sonuç | neden |
|---|---|---|
| H-A, derinlik emülatörü | **baskın** | erken açığın çoğu bilgi sınırı; küçük bir parçası hiperparametre kestirimi |
| H-B, sınıflandırıcı | reddedildi | |
| H-C, sıkıştırma | reddedildi | |
| H-D, etiket ve zaman penceresi | küçük artık pay | yalnız 15 koşu, (h, gerçek derinlik) bakımından zıt etiketli komşuya sahip: %87'si hızlı-tarama köşesinde, %40'ı kısa-Keyhole. Gerçek derinliğin de düzeltemediği geç hataların %76'sı bunlardan geliyor. |

H-D satırındaki 15 koşu "öğrenilemez" ya da "etiket hatası" diye okunmuyor.

**Hata türleri:**
- Erken dönemde mevcut sistem daha çok Keyhole kaçırıyor: recall 0.922, iletim 0.946.
- Sert gruptaki NEW iletim koşularını hem mevcut sistem hem gerçek derinlik çoğunlukla Keyhole sanıyor (%77 ve %61).

Ayrıntı: `diagnosis/DIAGNOSIS.md`.

## 2. Geliştirme (C1) ve DEV seçimi

- **Aday ve kontroller:** `PROTOCOL_EA_CANDIDATES.md`, değerlendirmeden önce kaydedildi.
- **DEV verisi:** kayıtlı HA_LEAN yolları, tekrar 123–162 (`cand_dev/CAND_DEV.md`).
- **DEV sonucu:** C1 erken +0.0053, geç −0.0015. Kayıtlı taşıma kuralının "geç kayıp yok" koşulu sağlanmadı; **taşınmadı**.

**Kayıtlı yön değişikliği (açık sapma):**
- Talimat erken, 0.93 ve 0.95 için ayrı hükümler istiyordu ve birindeki başarısızlığın ötekindeki kazancı silmemesini söylüyordu.
- Taşıma kuralının geç-dönem koşulu benim eklememdi ve bu talimata uymuyordu.
- Bu nedenle C1, sonuçlardan önce kaydedilen tek bir taze doğrulamayla, üç ayrı hükümle sınandı (`PROTOCOL_EA_VALIDATION.md`).
- DEV'e göre 0.95 ve geç-dönem hükümlerinin başarısız olmasını önceden yazmıştım; olmadılar.

## 3. Taze doğrulama

Kimlikler: STD 163–202, K5 41–48, K4 25–32. Ayrıntı: `validation/VALIDATION.md`.

| hüküm | sonuç |
|---|---|
| V-ERKEN | **gösterildi, pratik**: +0.0056 [+0.0038] |
| V-0.93 | daha kötü değil: +0.61 [−0.29] |
| V-0.95 | **güvenilir**: ulaşma +0.040, koruma +0.020; tasarruf **gösterildi, pratik**: +2.00 [+0.21] |
| geç pencere | kayıp gösterilmedi: −0.0005 [−0.0017, +0.0007] |
| zarar sınırları | log loss +0.0013, Brier −0.0004, CPU 1.19×; hepsi sınır içinde |
| geometri (bildirilir) | K5 bölge başına −0.049, **uyarı**; K4 +0.043 |

**Model ve yol ayrıştırması:**
- C1'in kazancı bir **model** etkisi. Aynı ödenmiş veride C1 tahmini, HA_LEAN tahmininden erken dönemde +0.0098 iyi; 40 tekrarın 40'ında.
- C1'in kendi margin yolu, C1 için HA_LEAN'in yolu kadar iyi.

## 4. Kullanım koşulları (koşulsuz kazanan yok)

| kullanım | öneri |
|---|---|
| sabit küçük bütçe (8–24 simülasyon) | **C1 + margin**: en yüksek erken BA, A düzeyinde olasılık kalitesi, 1.2× CPU |
| BA 0.93'te durmak | C1 + margin ya da A + margin; fark gösterilmedi |
| BA 0.95'e ulaşıp korumak | bu testte C1 + margin daha iyi; tekrarlanana kadar genel iddia yok |
| görülmemiş bölgeye uzanım (eski beş bölge, bölge başına) | eğilimli modellerden kaçının; E ya da A daha güvenli |

## 5. Kanıt düzeyleri

| iddia | düzey |
|---|---|
| darboğaz: derinlik bilgisi; sınıflandırıcı, temsil, seçici değil | DEV, oracle teşhisi |
| HA_TREND'in geç kaybı hiperparametre kestirim artefaktı | DEV, oracle (D2T) ve mekanizma kontrolleri |
| C1 erken kazancı | DEV, iki bağımsız sette tekrarlandı |
| C1 0.95 tasarrufu ve güvenilirliği | DEV, tek taze testte gösterildi; önceki sette koruma payı tersti |
| C1 0.93 tasarrufu | gösterilmedi (daha kötü değil) |
| geç farkın örneklem yanlılığından gelmesi | hipotez |
| dış geçerlilik, geometrik uzanım | gösterilmedi |

## 6. Literatür ve katkı sınırı

Ayrıntı: `LITERATURE_EA.md`.
- **Bilinen bileşenler:**
  - eğilimli GP / universal kriging;
  - GP hiperparametrelerinde öncül ya da integrasyon (Snoek ve diğerleri 2012; Hvarfner ve diğerleri 2024; Stan kılavuzu);
  - ML-II'nin kötü tanımlı olabilmesi (Karvonen ve Oates 2023).
- **Katkımız:**
  - aynı yollar üzerinde ölçülmüş bir hata ayrıştırması;
  - fizik eğilimli modelin geç kaybının bir kestirim artefaktı olduğunu gösteren mekanizma;
  - bunun basit, ucuz ve taze veride erken kazancı doğrulanmış bir düzeltmesi.
- Yeni bir yöntem değil; literatüre üstünlük iddiası yok.

## 7. Kayıt, sapma ve olaylar

| commit | aşama |
|---|---|
| d4dc329d | hipotezler |
| 3a5595ed | teşhis kodu |
| fb7e361f | 1. ek |
| 613c9c7b | 2. ek |
| 0020b07e | aday |
| 04fc468a | doğrulama dondurması |
| son commit | sonuçlar |

Kural ve kimliklerin hepsi sonuçlardan önce commit edildi.

**Sapmalar ve olaylar:**
- **Taşıma kuralının sonucuna rağmen yapılan doğrulama.** Gerekçesiyle, sonuçtan önce kaydedildi.
- **Kapalı EL kampanyasının plan dosyası yanlışlıkla değişti.** Yanlış yardımcı betikle "x" notu eklendi; hemen `git checkout` ile geri alındı, içerik değişikliği commit edilmedi.
- **Bir bekleyici yanlış klasörü izledi.** Durduruldu; hesaba etkisi olmadı.

**Bilgi kuralları:**
- Açılmamış koşulardan bilgi kullanılmadı. Oracle, test etiketi ve sert-grup üyeliği hiçbir adaya girmedi.
- OLD/NEW yalnız kaynak kaydı.
- Etiketler, dışlamalar ve sert-grup tanımı değişmedi.

**Koordinasyon:**
- Yalnız `thesis_shared_runtime\campaign_20261026\opus_state.json` yazıldı.
- Astra'nın dosyaları okundu, hiç yazılmadı.
- Mühürlü teslim paketi scratchpad'e SHA-256 ile kopyalanıp okundu; kodu çalıştırılmadı ve import edilmedi.

## 8. Dosyalar

| konu | dosya |
|---|---|
| görev, durum, sonraki adım | `TASK.md`, `STATE.json`, `NEXT_ACTION.md` |
| protokoller | `PROTOCOL_EA_HYPOTHESES.md` (+ AMENDMENT1, AMENDMENT2), `PROTOCOL_EA_CANDIDATES.md`, `PROTOCOL_EA_VALIDATION.md`, `freeze/EA_VALIDATION_MANIFEST.json` |
| teşhis | `diagnosis/` (DIAGNOSIS.md, JSON ve CSV tabloları) |
| aday DEV | `cand_dev/` |
| doğrulama | `validation/` (VALIDATION.md, EA_VALIDATION_DECISION.json, tablolar) |
| dışa aktarımlar | `exports/` |
| literatür | `LITERATURE_EA.md` |
| maliyet | `COST_BREAKDOWN.json` |
| kod | `src/ea_*.py`, runner `src/ea_runner.ps1` |

`exports/` 10 set içeriyor:
- teşhis basamakları;
- köşe-sınırlı margin;
- aday DEV;
- doğrulama.

Her sette bütün sistemlerin her bütçedeki tahminleri ve her yolun ödenmiş bütün simülasyon kimlikleri var. Metrikler değerlendirici kodunu kullanmadan yalnız bu dosyalardan yeniden hesaplandı: **10/10 PASS** (`exports/EXPORTS_ACCEPTANCE.json`).

**Maliyet dökümü:**

| iş | birim | işçi-saat |
|---|---|---|
| teşhis basamakları | 272 | 1.59 |
| 1. ek teşhisler | 200 | 0.51 |
| 2. ek teşhis | 200 | 0.04 |
| aday DEV | 272 | 2.49 |
| taze doğrulama | 544 | 1.92 |

Duman testleri ve tek seferlik uyumlarla toplam 1495 birim, 6.6 işçi-saat.
