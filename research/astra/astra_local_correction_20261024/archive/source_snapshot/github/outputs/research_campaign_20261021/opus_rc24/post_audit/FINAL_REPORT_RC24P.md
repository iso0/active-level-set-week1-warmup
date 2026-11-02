# RC24 sonrası denetim ve son karar (Opus, 2026-10-22)

**Kanıt etiketi: DEV.**
- Bütün sayılar aynı 541'lik havuzdan geliyor. Taze bölmeler ve yeni başlangıçlar bağımsız fiziksel doğrulama değildir.
- Aynı beş bölgede yeni başlangıçlar yeni geometri değildir.
- RC24'ün 48 saatlik penceresi yeniden başlatılmadı. İş 12:27–13:10 UTC arasında, 6 tek iş parçacıklı işçiyle yapıldı: 765 birim, hata yok, 2.3 CPU-saat.
- Son karşılaştırma sonuçlardan önce donduruldu (commit 0c8fe09c).

## Sade özet (bir sayfa)

**1. Ne istedik?**
- 541 koşuluk havuzda sıfırdan başlayıp, az simülasyonla yüksek ve güvenilir sınıflama.
- Önceki sistem (HA_LEAN), fizik eğilimli sistem (HA_TREND) ve yalnız-h kontrolü (HONLY) adil biçimde karşılaştırıldı.
- Fiziğe özgülüğü sınamak için bir genel eğilim kontrolü eklendi.

**2. Hangi önceki ifadeler düzeltildi?**
- "h boyutsuz" yanlıştı. h'nin birimi W·s^½·m⁻². Boyutsuz olan, standartlaştırılmış log koordinatı z_h.
- "Taze geometri blokları" yanlıştı. Bunlar aynı beş bölgede yeni başlangıçlardı.
- RC24'teki blok kazancı yalnız havuzlanmış ölçüttür. Bölge başına HA_TREND daha kötüydü (0.689'a karşı 0.723). Kazancın %78'i tek bölgenin çoğunluk sınıfından geliyordu.
- "Harcama PASS" yalnız "daha fazla simülasyon kararı çıkmadı" demekti; "daha kötü değil" gösterilmemişti (üst sınır +9.3).
- P2'nin genel garantisi geri çekildi (karşı örnek: q = n/(1+n), varyans 0.81'de kalıyor). P1, P3, P4 ve P5 koşullu hâle getirildi.
- "Kısa-K forming bitince oluşan geçici olaydır" ifadesi mekanizma olarak geri çekildi. Etiket sırası doğru (her koşuda ilk Keyhole, ilk forming bölümünden hemen sonra), ama fiziksel mi yoksa etiketleme kalıbı mı olduğu belli değil.

**3. Hangi kazanım korundu?**
- Taze standart testte HA_TREND, HA_LEAN'e göre erken BA'da daha iyi: +0.0088, alt sınır +0.004.
- BA ≥ 0.93 ve 0.95'e havuzlanmış eğride daha az simülasyonla ulaşıyor: −3.3 ve −6.5.
- Aynı kazancı genel bir log-girdi eğilimi de veriyor. Standart koşulda fiziğe özgü değil (+0.0018, alt sınır −0.0003).

**4. Hangi koşulda kayıp var?**
- **Olasılıklar:** HA_TREND daha kötü. Log loss +0.0073, alt sınır +0.0023, üst sınır +0.0123, yani kayıtlı 0.010 marjını aşıyor.
- **BA ≥ 0.95'i koruma:** daha zayıf (pay 0.75'e karşı 0.92).
- **Sert grup:** daha kötü. B60'ta yerel BA standart koşulda 0.607'ye karşı 0.636, eski bloklarda 0.524'e karşı 0.615.
- **Eski beş bölge:** bölge başına −0.038. Kayıp, Keyhole ağırlıklı bölgelerdeki az sayıdaki iletim koşusunda.

**5. Modelimiz ve seçicimiz ne olmalı?**
- Dondurulmuş kural **HA_LEAN + margin** dedi. Nedeni, HA_TREND'in log loss non-inferiority koşulunu geçememesi.
- Koşulsuz tek bir kazanan yok. Koşullu tercih:
  - amaç yalnız erken BA ve hedefe az simülasyonsa, eğilimli emülatör (HA_TREND ya da aynı işi gören genel eğilim) daha iyi;
  - güvenilir olasılık, hedefi koruma ve azınlık davranışı önemliyse HA_LEAN daha iyi.
- Tezin hedefi olasılık güvenilirliğini de içeriyor. Bu yüzden ana sistem HA_LEAN + margin.

**6. Neden yalnız h ya da önceki model değil?**
- **Yalnız-h:**
  - BA ≥ 0.95'e 8 tekrarın 6'sında ulaşıyor ve hedefi B60'a kadar yalnız 3'ünde koruyor;
  - log loss +0.037 daha kötü;
  - bölge içi azınlığı neredeyse hiç bulmuyor (bölge başına −0.12).
  - Havuzlanmış blok ölçütünde en iyisi, ama yalnız çoğunluk sınıfını tahmin ederek.
- **HA_LEAN:** önceki modeldir ve bu denetim onu korudu. HA_TREND onu koşulsuz geçemedi.

**7. BA-AULC, BA ve %80/%90/%93/%95 harcaması.** Taze standart test, tekrarlar 75–82; havuzlanmış / bireysel değerler.

| sistem | BA-AULC B8–B24 | BA-AULC B8–B60 | log loss | 0.80 | 0.90 | 0.93 | 0.95 (havuzlanmış) | 0.95 (bireysel) |
|---|---|---|---|---|---|---|---|---|
| HA_LEAN | 0.9327 / 0.9329 | 0.9478 / 0.9481 | 0.145 | 12.0 | 13.0 | 16.8 | 8/8 · 30.9 | 34/40 · 22.4 |
| HA_TREND | 0.9414 / 0.9422 | 0.9499 / 0.9504 | 0.152 | 12.0 | 12.3 | 13.5 | 8/8 · 24.4 | 33/40 · 21.2 |
| yalnız-h | 0.9393 / 0.9405 | 0.9439 / 0.9447 | 0.182 | 12.0 | 12.4 | 13.8 | 6/8 · 34.2 | 26/40 · 15.0 |
| genel eğilim | 0.9396 / 0.9398 | 0.9502 / 0.9505 | 0.151 | 12.0 | 12.8 | 14.0 | 8/8 · 28.9 | 34/40 · 21.4 |

Okuma notları:
- Harcamalar, ulaşanlarda ortalama "b + 4" teyit simülasyonudur; 8 başlangıç koşusu dahil.
- 0.80, 0.90 ve 0.93 hedeflerine her sistem havuzlanmış eğride 8/8 tekrarda ulaştı.

**8. Özgün katkımızı tek cümleyle nasıl savunabiliriz?**
"Bilinen bileşenlerin (fizik-temelli tek taban fonksiyonlu GP eğilimi, dürüst istifleme, margin) ölçülmüş bir birleşimini ve bunun iki değerlendirme hatasını ortaya çıkaran bir teşhisini sunuyoruz." İki hata: havuzlanmış ve bölge başına dış değerlemenin modelleri ters sıralaması, ve harcama non-inferiority'sinin yanlış okunması. Bu yeni bir istatistiksel yöntem değil.

**9. Hangi iddia hâlâ kanıtlanmadı?**
- Fiziksel ya da başka bir simülatörde dış doğrulama.
- Bölge içi azınlık tespitinde eğilimin üstünlüğü: bölüntüye bağlı (eski bölgelerde −0.038, yeni bölüntüde +0.031).
- Fiziğe özgü dağılım-içi fayda.
- Yayımlanmış en yakın yöntemlere karşı üstünlük: doğrudan yeniden uygulanmadı.
- Sert köşenin ayrılabilirliği ya da aleatorik olduğu.

## 1. Denetim sonuçları (Stage C, dışa aktarılan tahminlerden bağımsız yeniden hesap)

`ADDENDUM_RC24_DECISION.md`, `BLOCK_AUDIT.json`, `stagec_*` CSV'leri.

| BLOCK, B8–B60 | HA_LEAN | HA_TREND | yalnız-h |
|---|---|---|---|
| havuzlanmış | 0.9274 | 0.9386 | 0.9468 |
| bölge başına (4 iki-sınıflı blok) | 0.7225 | 0.6893 | 0.6268 |

- Sınıf sayıları (Keyhole / iletim): 1/148, 84/4, 0/91, 101/17, 11/84.
- Blok 3 tek sınıflı: BA tanımsız, iletim recall'u ≈ 1.0.
- Blok 1'deki tek Keyhole ve blok 2'deki 4 iletim koşusu üzerine sonuçlar anekdot düzeyinde. Bunlar aynı koşuların farklı başlangıçlarla tahmini.

## 2. Temiz eğilim kontrolü (eşleştirilmiş DEV; `TREND_CONTROL.md`)

Yalnız eğilim değişti. Kontrol, sıfır ve fizik eğilimli kollarla bit düzeyinde aynı kod yolundan geçiyor: TR_NONE ≡ HA_LEAN, TR_PHYS ≡ HA_TREND.
- **Standart koşul:** fizik − genel ≤ +0.003. Prior ölçeği (b = 3 ile 1.5) fark yaratmıyor.
- **Bloklar:** fizik doğrultusu havuzlanmış BA'yı artırıyor, bölge başına BA'yı düşürüyor; modeli yalnız-h davranışına itiyor.
- log h, log girdilerin doğrusal bir birleşimidir. Fizik eğilimi yeni bilgi getirmiyor; tek katsayılı bir yapısal kısıtlama.

## 3. Son karşılaştırma (dondurulmuş; `final/FINAL_COMPARISON.md`)

HA_TREND − HA_LEAN:

| bileşen | sonuç | durum |
|---|---|---|
| STD BA B8–B24 | +0.0088 (alt sınır +0.0040) | PASS |
| STD BA B8–B60 | +0.0022 (alt sınır −0.0008) | PASS |
| STD log loss | +0.0073 (üst sınır +0.0123) | **FAIL** |
| harcama 0.93 | −3.25 (üst sınır −0.96) | PASS |
| harcama 0.95 | −6.5 (üst sınır −1.32) | PASS |
| BLOCK_A (aynı 5 bölge, başlangıç 17–24), havuzlanmış | +0.0145 | PASS |
| BLOCK_A, bölge başına | −0.0377 (alt sınır −0.0605) | FAIL |
| BLOCK_B (yeni k = 4 bölüntü; 88/6, 96/13, 1/222, 12/103), havuzlanmış | +0.0251 | PASS |
| BLOCK_B, bölge başına | +0.0311 (alt sınır +0.0104) | PASS |

- **Fiziğe özgülük** (genel eğilime karşı): standart koşulda gösterilmedi. Havuzlanmış blok metriğinde iki bölüntüde de gösterildi (+0.008, +0.017). Bölge başına yalnız yeni bölüntüde gösterildi (+0.045).
- **Kural sonucu:** HA_LEAN + margin.
- **Yalnız-h, HA_LEAN'e karşı:** log loss FAIL, 0.95 harcaması FAIL.

## 4. Dosyalar

| dosya | içerik |
|---|---|
| `ADDENDUM_RC24_DECISION.md` | RC24 kararına tarihli ek |
| `analysis/PROPOSITIONS_v2_20261022.md` | düzeltilmiş önermeler |
| `TIMING_CORRECTION.md` | kısa-K zamanlama düzeltmesi |
| `ORIGINALITY_AND_LITERATURE.md` | literatür ve özgünlük |
| `PROTOCOL_RC24P_FINAL.md`, `final/` | son karşılaştırma |
| `exports/` | 14 set, bağımsız yeniden hesap PASS, 26,144 hücre |
