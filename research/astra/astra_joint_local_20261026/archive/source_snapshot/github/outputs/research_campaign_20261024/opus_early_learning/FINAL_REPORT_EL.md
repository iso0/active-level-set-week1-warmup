# EL çalışması: erken öğrenme avantajı tek öğrenicide simülasyon tasarrufuna dönüşüyor mu?

Opus, 2026-10-25. **Kanıt etiketi: DEV.**
- Bütün sayılar aynı 541 koşuluk havuzdan geliyor. Taze tekrarlar bağımsız fiziksel doğrulama değildir.
- **Pencere:** 2026-10-25 20:07:51 UTC'de açıldı, bitişi 2026-10-27 20:07:51 UTC olacaktı. İş bitince 23:18 UTC'de kapatıldı.
- **Hesap:** 1827 birim, hata yok, 6.1 işçi-saat. En çok 3 tek iş parçacıklı işçi kullanıldı; Astra'nın payı kullanılmadı.
- Simülatör, bulut, C4 ya da korunan dış değerlendirme kullanılmadı.

## Sade özet (bir sayfa)

**Ne sorduk?** HA_TREND, ilk 8–24 simülasyonda HA_LEAN'den daha yüksek BA veriyordu. Bu avantaj tek bir öğrenicide BA 0.93 ve 0.95'e daha az simülasyonla ulaşmaya dönüşüyor mu? Bunu anlamak için "seçen" modeli (margin ile sonraki simülasyonu belirleyen) "tahmin eden" modelden ayırdık:

| sistem | seçer | tahmin eder |
|---|---|---|
| A | HA_LEAN | HA_LEAN |
| B | HA_TREND | HA_TREND |
| C | HA_TREND | HA_LEAN |
| D | HA_LEAN | HA_TREND |

İkinci aşamada tek bir mekanizma denendi:

| sistem | seçer | tahmin eder |
|---|---|---|
| E | HA_LEAN | iki modelin, açılmış etiketlerin kanıtıyla ağırlıklandırılmış karışımı |

**1. Erken kazanç nereden geliyor?** **Tahminden, seçimden değil.**
- Aynı simülasyonlarla eğitilen HA_TREND tahmini, HA_LEAN tahmininden daha iyi. Taze 40 tekrarda erken BA-AULC farkı:
  - HA_LEAN yolunda +0.0040 (tekrarların 30/40'ında);
  - HA_TREND yolunda +0.0062 (37/40).
- HA_TREND'in seçtiği simülasyonlar erken dönemde ek bir şey kazandırmıyor: +0.0003.
- Kazanç çok erken: b = 8'de +0.015 BA, b = 16'da +0.003. b ≥ 24'ten sonra HA_TREND tahmini hafifçe geride kalıyor.

**2. Tasarrufa dönüşüyor mu?** **Yalnız BA 0.93 hedefinde, küçük ölçüde.** BA 0.95'te dönüşmüyor.
- **BA 0.93:** D'nin (HA_LEAN seçer, HA_TREND tahmin eder) kısıtlı ortalama tasarrufu:
  - ilk taze testte +0.8 simülasyon, gösterilemedi;
  - ikinci taze testte +2.0 simülasyon, alt sınır +1.3.
  - E'nin tasarrufu +1.1 simülasyon (alt sınır +0.3).
- **BA 0.95:** tasarruf ≈0 (−1.1 ile +0.7 arası). Ayrıca 0.95'e ulaşıp B60'ta hâlâ tutan öğrenici payı A'dan 4–5 puan düşük.
- **Kayıtlı karar kuralı ne D'yi ne E'yi kabul etti (NOT_ADOPTED).** İkisi de 0.95 için güvenilirlik koşulunu (alt sınır ≥ −0.05) geçemedi:
  - D ilk testte 0.95'e ulaşmada da (−0.045, alt sınır −0.088) korumada da kaldı;
  - D ikinci testte yalnız korumada kaldı (alt sınır −0.097);
  - E korumada kaldı (alt sınır −0.081).
  - B ve C de kabul edilmedi.

**3. Modelimiz ve seçicimiz ne olmalı?** Koşulsuz bir kazanan yok. Kullanıma göre:

| kullanım | önerilen sistem | neden |
|---|---|---|
| sabit küçük bütçe (8–16 simülasyon) | D | en büyük erken kazanç (b = 8'de +0.015 BA) |
| BA 0.93'e hızlı ulaşmak | D ya da E | 1–2 simülasyon tasarruf |
| BA 0.95'e ulaşıp korumak, güvenilir olasılık | A | tez öğrenicisi olarak kalıyor |

E dengeli bir uzlaşma, ama kuralı geçemedi. Güçlü yanları:
- erken kazancın %60–65'ini koruyor;
- 0.93 tasarrufu gösterildi;
- log loss ve Brier A ile aynı (D ve B'de log loss +0.006 daha kötü);
- eski beş bölgede kayıp yok (D'de −0.04).

Eksik yanı: 0.95'i B60'ta koruma payı −5 puan, alt sınır −0.081. Kayıtlı sınır −0.05 olduğu için kural onu reddetti.

**4. BA-AULC kazancı ile hedef kazancı neden farklı?** BA-AULC kazancı ilk 8–16 simülasyonda toplanıyor; 0.95 hedefine ise genellikle 20–25 simülasyonda ulaşılıyor. O bölgede iki tahminci eşit ya da HA_TREND biraz geride. Bu yüzden erken kazanç 0.93'e küçük bir tasarruf olarak yansıyor, 0.95'e yansımıyor.

**5. Hangi iddia kanıtlanmadı?**
- BA 0.95 hedefinde tek öğrenici tasarrufu.
- D ya da E'nin kayıtlı kurala göre A'nın yerini alması.
- DEV'de görülen "HA_TREND'in seçtiği yol 0.95'i zorlaştırır" bulgusu. Taze veride tekrarlanmadı.
- Fiziksel ya da başka bir simülatörde dış doğrulama.

**6. Katkımızın sınırı.**
- Yeni bir yöntem değil. Bilinen fikirler kullanıldı:
  - seçen ile tahmin eden modeli ayırmak (Lowell ve diğerleri 2019; Coleman ve diğerleri 2020);
  - kanıtla model ortalaması almak (Hoeting ve diğerleri 1999; MacKay 1992).
- Bizim katkımız iki şey:
  - bu fizik-destekli aktif sınıflamada erken kazancın kaynağını aynı başlangıçlarla 2×2 ayrıştırıp ölçmek;
  - bu kazancın tek öğrenicide hangi hedefe kadar tasarrufa dönüştüğünü, önceden kaydedilmiş kurallarla göstermek.

## 1. Dört sistem, taze tekrarlar 83–122

EL-1 ileriye dönük testinde 200 tek öğrenici, 40 tekrar kümesi vardı. Havuzlanmış değerler parantez içinde.

| sistem | BA-AULC B8–B24 | B8–B60 | BA b8 / 12 / 16 / 24 / 40 / 60 | log loss | Brier | CPU/adım |
|---|---|---|---|---|---|---|
| A: HA_LEAN seçer / HA_LEAN tahmin eder | 0.9328 (0.9329) | 0.9469 (0.9468) | 0.895 / 0.931 / 0.937 / 0.946 / 0.954 / 0.957 | 0.1463 | 0.0403 | 0.14 s |
| B: HA_TREND seçer / HA_TREND tahmin eder | 0.9371 (0.9372) | 0.9477 (0.9476) | 0.911 / 0.936 / 0.940 / 0.947 / 0.953 / 0.956 | 0.1525 | 0.0413 | 0.14 s |
| C: HA_TREND seçer / HA_LEAN tahmin eder | 0.9308 (0.9309) | 0.9461 (0.9460) | 0.895 / 0.929 / 0.932 / 0.945 / 0.954 / 0.957 | 0.1510 | 0.0416 | 0.28 s |
| D: HA_LEAN seçer / HA_TREND tahmin eder | 0.9368 (0.9370) | 0.9470 (0.9469) | 0.911 / 0.937 / 0.940 / 0.945 / 0.951 / 0.956 | 0.1519 | 0.0412 | 0.28 s |

**Hedefler.**
- Ulaşma: b ve b+4'te teyitli.
- Harcama: b+4, 8 başlangıç simülasyonu dahil.
- Kısıtlı ortalama (ufuk 60): ulaşamayan 61 sayılır. Gerçek maliyet ya da sınır değildir; iki ulaşma eğrisi arasındaki alandır.

| sistem | 0.90 ulaşan / kısıtlı ort. | 0.93 ulaşan / kısıtlı ort. / B60'ta tutan | 0.95 ulaşan / kısıtlı ort. / B60'ta tutan / sürdürme payı | 0.95 medyan harcama |
|---|---|---|---|---|
| A | 200 / 13.22 | 196 / 18.17 / 187 | 168 / 29.52 / 134 / 0.766 | 23 |
| B | 200 / 12.94 | 197 / 17.48 / 181 | 161 / 30.36 / 129 / 0.766 | 23 |
| C | 200 / 13.01 | 197 / 17.91 / 186 | 168 / 30.50 / 133 / 0.767 | 24.5 |
| D | 200 / 13.11 | 198 / 17.38 / 183 | 159 / 30.64 / 126 / 0.747 | 24 |

**Kayıtlı karar:** D, B ve C'nin üçü de NOT_ADOPTED.

## 2. Model etkisi ve yol etkisi (2×2, aynı başlangıçlar)

| etki | DEV (24 küme) erken ΔBA-AULC | taze (40 küme) erken ΔBA-AULC | taze, 0.95 kısıtlı tasarruf |
|---|---|---|---|
| HA_LEAN yolunda tahminci (D − A) | +0.0053 [+0.0040, +0.0067] | +0.0040 [+0.0026, +0.0055] | −1.11 |
| HA_TREND yolunda tahminci (B − C) | +0.0069 | +0.0062 [+0.0048, +0.0077] | +0.13 |
| HA_LEAN tahmincisi için yol (C − A) | −0.0011 | −0.0020 | −0.97 |
| HA_TREND tahmincisi için yol (B − D) | +0.0004 | +0.0003 | +0.28 (DEV'de −2.38; tekrarlanmadı) |
| etkileşim | +0.0015 | +0.0022 [+0.0008] | +1.24 |

**Yollar:**
- İki seçici her öğrenicide ilk sorgudan (9. simülasyon) itibaren farklı seçiyor.
- B24'te 24 koşudan ≈12.8'i ortak, B60'ta 60'tan ≈51.5'i.
- İkisi de sorguların ≈%42–45'ini havuzun %7'lik etiket-karışık köşesine harcıyor.

## 3. Tek öğrenicide sorgu tasarrufu

Aynı öğrenici ve aynı başlangıç eşleştirildi; belirsizlik tekrar kümeleri üzerinden. "+", A'dan az simülasyon demek.

| test | sistem − A | 0.90 | 0.93 | 0.95 | 0.95 ulaşma tablosu (ikisi / yalnız X / yalnız A / hiçbiri) | ikisi de ulaştıysa 0.95 farkı (koşullu) |
|---|---|---|---|---|---|---|
| EL-1, taze 83–122 | B | +0.29 | +0.69 [−0.33] | −0.84 [−2.39] | 149 / 12 / 19 / 20 | −0.28 |
| | C | +0.21 | +0.26 [−0.70] | −0.97 [−2.63] | 154 / 14 / 14 / 18 | −1.27 |
| | D | +0.11 | +0.79 [−0.20] | −1.11 [−2.73] | 150 / 9 / 18 / 23 | +0.49 |
| EL-2, taze 123–162 | D | −0.19 | **+2.04 [+1.32]** | +0.69 [−0.63] | 151 / 6 / 8 / 35 | +0.64 |
| | E | +0.11 | **+1.09 [+0.33]** | +0.45 [−0.77] | 154 / 6 / 5 / 35 | −0.15 |

**0.95'e ulaşmış öğrenici payı**, b = 16 / 24 / 40 / 60 simülasyonda:

| test | sistem | 16 | 24 | 40 | 60 |
|---|---|---|---|---|---|
| EL-1 | A | 0.37 | 0.53 | 0.74 | 0.84 |
| EL-1 | D | 0.39 | 0.51 | 0.70 | 0.80 |
| EL-2 | A | 0.36 | 0.57 | 0.73 | 0.80 |
| EL-2 | D | 0.43 | 0.58 | 0.73 | 0.79 |
| EL-2 | E | 0.38 | 0.55 | 0.75 | 0.80 |

**0.95'i B60'ta tutma, sistem − A:**
- EL-1: D −0.040 [−0.080].
- EL-2: D −0.040 [−0.097], E −0.050 [−0.081].

İki testte de tekrarlanan tek kayıp bu.

## 4. Aşama 2: tek mekanizma, E

**Neden:** EL-1'de D'nin taze testte kabul edilmemesi; bu kayıtlı bir yön değişikliği (`PROTOCOL_EL2_MECHANISM.md`). Ölçülmüş sorun: HA_TREND tahmini yalnız b ≤ 16'da iyi, sonra hafif geride.

**Tanım:**
- Emülatör seçimi (eğilimli ya da eğilimsiz), HA_LEAN'in τ ızgarası için zaten kullandığı Laplace kanıt kuralına bir ayar parametresi daha olarak eklendi.
- Tahmin: p_E = W_L·p_L + W_T·p_T. Ağırlıklar yalnız açılmış etiketlerin marjinal olabilirliğinden gelir.
- Bütçe kuralı, OLD/NEW ve test etiketi yok. Serbest ayar yok.

**Ağırlıklar.** HA_TREND ağırlığı (ortalama W_T, taze 123–162):

| b | 8 | 16 | 24 | 32 | 40 | 60 |
|---|---|---|---|---|---|---|
| W_T | 0.52 | 0.54 | 0.53 | 0.50 | 0.44 | 0.33 |

Veri arttıkça ağırlık kendiliğinden HA_LEAN'e kayıyor.

**Sonuçlar, A'ya göre:**

| | erken | 0.93 | 0.95 | 0.95'i tutma | log loss |
|---|---|---|---|---|---|
| DEV (64 küme) | +0.0029 | +0.68 | +0.57 | +0.003 | −0.0004 |
| taze doğrulama (40 küme) | +0.0028 [+0.0020] | +1.09 [+0.33] | +0.45 [−0.77] | −0.050 [−0.081] | −0.0001 |

**Karar:** NOT_ADOPTED.

## 5. Sağlamlık

Bu bölüm kararın parçası değil.

**Bölge başına BA-AULC B8–B60, A'ya göre:**

| test | bölüntü | sistemler |
|---|---|---|
| EL-1 | eski beş bölge | B −0.031, D −0.051 (uyarı); C +0.004 |
| EL-1 | k = 4 | B +0.044, C +0.011, D +0.028 |
| EL-2 | eski beş bölge | D −0.039 (uyarı), E −0.006 (uyarı yok) |
| EL-2 | k = 4 | D +0.037, E +0.024 |

Havuzlanmış blok ölçütünde B ve D her bölüntüde A'dan yüksek. Bu, RC24P'deki bölüntüye bağlı tablonun aynısı.

**Kısa-Keyhole sert grubu.** B60'ta sert-grup BA'sı:

| test | A | B | C | D | E |
|---|---|---|---|---|---|
| EL-1 | 0.615 | 0.610 | 0.629 | 0.609 | – |
| EL-2 | 0.636 | – | – | 0.625 | 0.633 |

Hiçbir sistem sert grubu çözmüyor.

## 6. Dışa aktarımlar ve bağımsız yeniden hesap

Konum: `exports/`. 12 set var:
- `dev_*` ve `final_*`: A, B, C, D, iki seçim yolu;
- `el2_dev_*` ve `el2_final_*`: A, D, E ve öğrenici-bütçe başına kanıt ağırlığı W_T.

Her setin içeriği:
- `predictions_f32.npz`: her bütçede test tahminleri;
- `paths.csv.gz`: her yolun ödenmiş bütün simülasyon kimlikleri, sırayla ve seçen kuralla.

`src/el_export.py`, değerlendirici kodunu kullanmadan, yalnız bu dosyalardan ve etiket manifestinden BA, BA-AULC ve hedef harcamasını yeniden hesaplıyor. 12/12 set PASS: BA-AULC farkı ≤ 6e-16, harcama farkı 0 (`exports/EXPORTS_ACCEPTANCE.json`).

**Kod kontrolleri:** her birimde b = 8'de C(8) = A(8) ve D(8) = B(8) tam olarak tuttu. Ayrıca:
- yeniden hesaplanan D, mevcut kayıtlarla bit düzeyinde aynı;
- E'nin bileşenleri p_L = A ve p_T = D bit düzeyinde aynı;
- iki ileriye dönük yolun uçtan uca yeniden koşusu kayıtlarla bit düzeyinde aynı.

## 7. En yakın literatür ve katkı sınırı

Ayrıntı `LITERATURE_EL.md` dosyasında.

| çalışma | ne gösterdi | bizim düzenekle farkı |
|---|---|---|
| Lowell, Lipton & Wallace 2019 (EMNLP-IJCNLP), tam metin | bir modelin seçtiği veri başka bir "ardıl" modele çoğu zaman yaramıyor; sınıflamada aktarımların yalnız %37.5'i rastgele örneklemeyi geçti | C ve D bunun iki yönü; bizde modeller yalnız tek bir eğilim tabanında farklı |
| Coleman ve diğerleri 2020 (ICLR, SVP), tam metin | küçük bir vekil modelin seçtiği veriler büyük modelde neredeyse aynı hata veriyor ve seçimi 3.8–51 kat hızlandırıyor | D'de seçici daha ucuz değil; amaç hız değil, hangi modelin seçtiği |
| Tomanek ve diğerleri 2007; Baldridge & Osborne 2004, özet düzeyinde | AL verisinin başka modellerce yeniden kullanımı bazen işe yarıyor, bazen yaramıyor | bizde HA_TREND yolu HA_LEAN'e erken fayda sağlamıyor |
| Hoeting ve diğerleri 1999; MacKay 1992, özet düzeyinde | model belirsizliğinde Bayesçi ortalama; sınıflandırıcıların kanıtla karşılaştırılması | E tam olarak bunun emülatör seçimine uygulanması |

**Sonuç:**
- Yeni bir istatistiksel yöntem iddia etmiyoruz.
- "Literatürü geçtik" demiyoruz; yayımlanmış yöntemler yeniden uygulanmadı ve düzenekler farklı.
- Katkımız, bilinen bileşenlerin bu fizik-destekli aktif sınıflamada ölçülmüş bir ayrıştırması ve tasarrufa dönüşme sınırının dürüst bir gösterimi.

## 8. Kayıt, sıra ve kurallar

| commit | aşama | içerik |
|---|---|---|
| d13b70d5 | EL-1 kayıt | plan, hedef sırası ve kurallar, sonuçlardan önce |
| 1751fd3b | EL-1 dondurma | DEV çapraz analiz ve ileriye dönük dondurma |
| 2dee796e | EL-1 sonuç | ileriye dönük sonuç (NOT_ADOPTED) ve dışa aktarımlar |
| dcdb8234 | EL-2 kayıt | mekanizma, değerlendirmeden önce |
| a839ef1c | EL-2 dondurma | EL-2 DEV ve doğrulama dondurması |
| son commit | EL-2 sonuç | doğrulama sonucu, rapor ve kayıtlar |

Kurallara uyuldu:
- Sonuç görüldükten sonra kural, eşik ya da kimlik değiştirilmedi.
- Önceki donmuş kararlar değişmedi. RC24P kararı "HA_LEAN + margin" bu çalışmayla da destekleniyor.
- Açılmamış koşulardan bilgi kullanılmadı. Test etiketleri yalnız değerlendiricide.
- Hard-group üyeliği ve dışlamalar değişmedi.
- Koordinasyon yalnız `opus_state.json` üzerinden yapıldı; Astra'nın dosyaları okundu, hiç yazılmadı.

## 9. Dosyalar

| konu | dosya |
|---|---|
| plan ve hedef sırası | `PLAN.md`, `PROTOCOL_EL_OBJECTIVES.md` |
| DEV çapraz analiz | `dev/DEV_CROSS.md` |
| EL-1 protokolü ve sonucu | `PROTOCOL_EL_FINAL.md`, `final/FINAL_COMPARISON.md` |
| EL-2 protokolleri, DEV ve doğrulama | `PROTOCOL_EL2_MECHANISM.md`, `PROTOCOL_EL2_FINAL.md`, `el2_dev/EL2_DEV.md`, `el2_final/EL2_CONFIRMATION.md` |
| sert grup | `el2_final/HARD_GROUP_ROBUSTNESS.json` |
| literatür | `LITERATURE_EL.md` |
| dışa aktarımlar | `exports/` |
| kod | `src/el_*.py`, `src/el2_freeze.py`, runner `src/el_runner.ps1` |
