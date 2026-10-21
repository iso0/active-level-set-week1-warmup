# RC23 — Tamamen sade h + derinlik sistemi ve tek model kararı (Opus, 2026-10-21)

**Kanıt etiketi: DEV.**
- Tüm sonuçlar aynı 541 incelenmiş simülasyonun yeni bölmeleridir; fiziksel doğrulama değildir.
- Hedef harcamaları test etiketlerinden hesaplanmıştır. Bunlar çevrimdışı değerlendirmedir, gerçek kullanımda bir durma kuralı değildir.

**Çalışma penceresi ve hesap:**
- Pencere 17:46 UTC'de başladı; işler 19:12 UTC'de bitti.
- 726 birim, hata yok, 2.35 CPU-saat; en fazla 2 tek iş parçacıklı işçi.
- Astra'nın payı serbest ve kullanılmadı.

**Kayıt ve donma:**
- Kurallar ve karar sonuçlardan önce donduruldu (`PROTOCOL_RC23.md`, `freeze/RC23_MANIFEST.json`, commit 8cef7a54).
- Hiçbir kapı sonradan aşılmadı.

## Türkçe sonuç

**Tek karar: Tamamen sade sistem yeterli. Önerilen tek model + seçici: tamamen sade h + derinlik sistemi + margin (HA_LEAN + margin).**

Önceden kaydedilen kurala göre:
- taze tekrarlarda RC22 referansına göre performans korundu;
- dört sağlamlık koşulunun hiçbirinde kötüleşme yok.

**1) Ne istedik, ne yaptım?**
- **Amaç:** Tek havuzda sıfırdan başlayıp her simülasyonu sayarak, mevcut güçlü adayın gerçekten sade bir biçimiyle aynı ya da daha iyi BA öğrenme eğrisini elde edip edemeyeceğimizi görmek.
  - BA: dengeli doğruluk.
  - BA-AULC: BA öğrenme eğrisi altındaki ortalama.
- **RC22 düzeltmeleri:** Tarihli bir ek yazdım (`opus_rc22/ADDENDUM_RC22_20261021.md`).
  - RC22 adayının (HA_LR) derinlik tahmini hâlâ sıcaklık ve akışla ortak eğitilen üst modelden geliyordu. Bunu ölçtüm: ödenmiş sıcaklık/akış değerleri değiştirilince olasılıkları 0.53'e kadar değişiyor.
  - "8 simülasyon tasarrufu" atanmış bir skordu. İkisinin de ulaştığı yedi çiftte gözlenen fark −8.14'tü. Ulaşamayan durum için atanabilecek en küçük harcama 64 değil 61.
- **Dört kurulum aynı başlangıç, bütçe, karar eşiği ve margin seçicisiyle karşılaştırıldı:**
  - RC22 referansı (PHR_NRMAP);
  - ortak üst modelli RC22 adayı (HA_LR);
  - tamamen sade h + derinlik (HA_LEAN): derinlik GP'si yalnız ödenmiş derinliklerden öğreniyor, sıcaklık ve akış hiçbir aşamaya girmiyor;
  - yalnız-h kontrolü (HONLY_LR).
- **Doğrulama:** Sade sistemin tahminleri ve sorgu yolu, sıcaklık/akış değerleri değiştirilince ya da silinince bit düzeyinde aynı kaldı.
- **Deney sırası:**
  1. önce kayıtlı sorgu yollarında mekanizma;
  2. sonra taze tekrarlar 51–58'de ileriye dönük karşılaştırma;
  3. son olarak dört sağlamlık koşulu: standart, rastgele ve kümelenmiş başlangıç, geometrik bloklar.

**2) Hangi bilgiler gerçekten gerekli?**
- **Sıcaklık ve akış gerekli değil.**
  - Aynı yollarda üst modeli bu kanallardan arındırmak ne BA'yı ne olasılığı değiştiriyor: BA +0.001, log-kayıp +0.001.
  - Kararlar adayların yalnız %0.5–3.7'sinde farklı.
  - Taze tekrarlarda sade sistem ile ortak üst modelli aday arasında fark yok: BA +0.002 / +0.001.
- **Tahmini derinlik gerekli, ama BA için değil olasılık kalitesi için.**
  - Yalnız-h kontrolüne göre log-kayıp belirgin iyi: −0.023 erken, −0.037 tüm bütçe; 8/8.
  - BA'da erken dönemde yalnız-h biraz önde (−0.006), tüm bütçede sade sistem önde (+0.003).
  - Yalnız-h, BA ≥ 0.95'i 8 tekrarın yalnız 3'ünde teyit etti; sade sistem 8'inde.
- **Öğrenilmiş düzenlileştirme:** her kurulumda korunmuş ortak bileşen; RC21–RC22'de gerekli olduğu gösterilmişti.

**3) Tek model + seçici önerim:** Tamamen sade h + derinlik sistemi + margin.

**4) BA-AULC, sabit bütçelerde BA ve hedef harcaması** (taze tekrarlar 51–58; 5 katın tahminleri birleştirilmiş tekrar eğrileri; 8 eşleşik tekrar)

BA-AULC:

| | B8–B24 | B8–B60 |
|---|---|---|
| sade sistem | 0.9352 | 0.9474 |
| referans | 0.9296 | 0.9436 |
| ortak üst modelli aday | 0.9332 | 0.9465 |
| yalnız-h | 0.9409 | 0.9440 |

Sabit bütçelerde BA (sade sistem / referans):

| bütçe | sade sistem | referans |
|---|---|---|
| B8 | 0.886 | 0.877 |
| B16 | 0.937 | 0.942 |
| B24 | 0.947 | 0.944 |
| B40 | 0.953 | 0.951 |
| B60 | 0.956 | 0.956 |

BA hedeflerine harcama (b ve b + 4'te teyit; toplam ödenmiş simülasyon):

| hedef | sade sistem: ulaşan / ortalama harcama | referans: ulaşan / ortalama harcama | eşleşik gözlenen fark |
|---|---|---|---|
| BA ≥ 0.80 | 8/8, 12.1 (7'si başlangıçta geçti) | 8/8, 12.25 | −0.1 |
| BA ≥ 0.90 | 8/8, 12.4 | 8/8, 12.75 | −0.4 |
| BA ≥ 0.93 | 8/8, 15.4 | 8/8, 16.6 | −1.25 (5 az / 1 eşit / 2 fazla; açık fark yok) |
| BA ≥ 0.95 | 8/8, 32.1 | 8/8, 40.75 | −8.6 (6/0/2; daha az simülasyon, sansür yok) |

- Bireysel öğreniciler (40'ar), BA ≥ 0.93 için: sade 40/40, referans 38/40.
- Bireysel öğreniciler (40'ar), BA ≥ 0.95 için: sade 32/40, referans 30/40.

**5) Hangi güçlü kontrole göre ne kazandı?**
- **Referansa göre (taze tekrarlar):**
  - BA-AULC +0.006 / +0.004. Pratik üstünlük marjı (0.020) geçilmedi, ama alt güven sınırı +0.0006 / +0.0005: performans korundu.
  - Erken log-kayıp −0.012 (7/8).
  - BA ≥ 0.95'e 8.6 daha az simülasyon.
  - Karar/eğitim işlemi adım başına 0.14 s, referansta 0.48 s: yaklaşık 3.3 kat daha hızlı.
  - Bir kanal tümden eksik olsa da çalışıyor. Referans bu durumda sayısal olarak çöküyor; kabul testinde bulundu.
- **Ortak üst modelli adaya göre:** BA ve olasılıkta fark yok; işlem süresi yaklaşık 3.2 kat daha az.

**6) Hangi koşullarda düşüyor?**
- **Kümelenmiş, çoğu tek sınıflı başlangıç:** bütün modeller belirgin düşüyor (erken BA 0.89–0.91). Sade sistem referansla aynı düzeyde. Burada yalnız-h erken dönemde olasılıkta daha iyi.
- **Geometrik bloklar (bir bölge hem eğitimden hem sorgudan ayrıldığında):**
  - Sade sistem referanstan erken BA'da iyi (+0.024, 8/8).
  - Ama BA ≥ 0.95'e hiçbir tohumda ulaşamıyor.
  - Az temsil edilen sınıfta kötü: 4 iletim koşulu olan blokta iletim duyarlılığı 0.22–0.25; 17 iletim koşulu olan blokta 0.31–0.51.
  - Bloklarda yalnız-h birleştirilmiş BA'da daha yüksek (B8–B60 0.945; BA ≥ 0.95 8/8). Ama az temsil edilen sınıfları tanımıyor: 1 Keyhole'lu blokta Keyhole ve 4 iletimli blokta iletim duyarlılığı 0.
  - Tek sınıflı blokta BA tanımsız; tanımlı duyarlılık ayrıca verildi.
- **Hızlı-tarama köşesi:** zayıf kalmaya devam ediyor; NEW-iletim duyarlılığı B60'ta ~0.33.

**7) Kanıtlanmış DEV sonucu ile sınanmamış iddia**
- **Kanıtlanmış (DEV):**
  - Sade sistem, referansa göre performansı koruyor (önceden belirlenen −0.010 sınırıyla).
  - Dört sağlamlık koşulunda kötüleşmiyor.
  - Sıcaklık/akış değerlerinden bit düzeyinde bağımsız.
  - Yaklaşık 3 kat daha hızlı.
  - BA ≥ 0.95'e daha az simülasyonla ulaşıyor (ikincil hedef).
- **Kanıtlanmamış:**
  - BA'da pratik üstünlük;
  - "eşdeğerlik" (yalnız "kayıp −0.010'dan küçük" gösterildi);
  - fiziksel doğrulama;
  - köşenin çözülmesi.
- **Sınanmamış:**
  - yeni fiziksel simülasyonlarla dış geçerlilik;
  - margin dışı seçicilerle sade sistemin davranışı.

---

## 1. Stage 1 — mechanism on identical saved paid prefixes (RC22 acquisition paths, repeats 43–50; fixed paths)

`match/MATCH.md`:

| construction | BA B8–B24 | LL B8–B24 | BA B8–B60 | LL B8–B60 |
|---|---|---|---|---|
| PHR_NRMAP | 0.9229 | 0.1994 | 0.9412 | 0.1542 |
| HA_LR | 0.9313 | 0.1877 | 0.9446 | 0.1493 |
| HA_LEAN | 0.9326 | 0.1885 | 0.9448 | 0.1508 |
| HONLY_LR | 0.9337 | 0.2084 | 0.9393 | 0.2019 |

Contrasts:
- HA_LEAN − HA_LR: BA +0.0013 / +0.0002, LL +0.0009 / +0.0015; NOT MATERIAL.
- HA_LEAN − HONLY_LR: LL −0.020 / −0.051 (8/8, MATERIAL).

Same-path agreement HA_LEAN vs HA_LR:
- decisions differ on 3.7 % (B8) → 0–0.7 % of the candidates and tests;
- margin-score Spearman 0.97–0.99;
- logit slope ≈ 1.

## 2. Stage 2 — prospective, fresh repeats 51–58

`std/STD.md`; 160 trajectories.

**Non-inferiority vs PHR_NRMAP** (one-sided 95 % lower bound vs −0.010):

| contrast | B8–B24 | B8–B60 |
|---|---|---|
| HA_LEAN − PHR_NRMAP | +0.0056, LCB +0.0006 | +0.0038, LCB +0.0005 |
| HA_LR − PHR_NRMAP | +0.0036, LCB −0.0015 | +0.0030, LCB −0.0000 |

All four are NON-INFERIOR.

**Superiority verdicts** (margin 0.020): all NOT DIFFERENT in BA.

**Probability, LL B8–B24:**
- HA_LEAN − PHR_NRMAP −0.012 (7/8) BETTER;
- HA_LEAN − HONLY_LR −0.023 (7/8) BETTER;
- HONLY_LR − PHR_NRMAP over B8–B60 +0.031 WORSE.

**Spend** (restricted score with censored = 61; the observed both-attained difference is reported apart):

| contrast | BA ≥ 0.93 | BA ≥ 0.95 |
|---|---|---|
| HA_LEAN − PHR_NRMAP | −1.25 | −8.6, FEWER (no censoring) |
| HA_LR − PHR_NRMAP | −2.0, FEWER | observed −7.1 on 7 pairs; restricted −4.0, no clear difference |

**CPU per step:** HA_LEAN 0.143 s, HA_LR 0.463 s, PHR_NRMAP 0.478 s, HONLY_LR 0.005 s.

## 3. Stage 3 — robustness

PHR_NRMAP was reused from RC21B / RC22; the three new arms were run (480 trajectories).

| condition | BA-AULC B8–B24 (HA_LEAN / HA_LR / PHR_NRMAP / HONLY_LR) | HA_LEAN − PHR_NRMAP, BA small / all | LL small |
|---|---|---|---|
| STD (35–42) | 0.933 / 0.937 / 0.928 / 0.942 | +0.004 / +0.002 (ND) | −0.006 |
| RAND8 | 0.939 / 0.933 / 0.925 / 0.938 | +0.013 (8/8) / +0.006 (ND) | −0.022 BETTER |
| LOCAL8 | 0.895 / 0.891 / 0.892 / 0.908 | +0.003 / +0.001 (ND) | +0.002 |
| blocks (pooled) | 0.923 / 0.921 / 0.899 / 0.936 | **+0.024 (8/8) BETTER** / +0.012 (ND) | −0.041 BETTER |

Additional spend observations:
- RAND8: HA_LEAN reached BA ≥ 0.93 with 4.0 fewer simulations (FEWER).
- Blocks: BA ≥ 0.93 was attained 7/8 by HA_LEAN vs 6/8 by PHR_NRMAP; observed −11.3 on the both-attained pairs (FEWER on the restricted score). BA ≥ 0.95 was never attained by HA_LEAN or PHR_NRMAP.

Per-block recalls are in `block/BLOCK.md`. Undefined BA is never set to 0 or 1.

**Decision rule** (`DECISION.json`):
- HA_LEAN: non-inferior in both windows, spend not MORE, robust in all 4 conditions (no WORSE verdict; mean B8–B60 Δ ≥ −0.010) → **D1**.
- HA_LR also passed.

## 4. Files

**Protocol and decision:**
- `PROTOCOL_RC23.md`, `freeze/RC23_MANIFEST.json`
- `RC23_VALIDATION.json`, `DECISION.json`, `COMPUTE.md`

**Part reports:**
- `match/MATCH.md`, `std/STD.md`
- `rob_std/ROB_STD.md`, `rob_rand8/ROB_RAND8.md`, `rob_local8/ROB_LOCAL8.md`, `block/BLOCK.md`
- Each has CSVs: metrics, contrasts, non-inferiority, pooled and individual-learner endpoints, spend.

**Exports:**
- `*/export/predictions_f32.npz` (per-budget probabilities) and `*/export/paths.csv.gz` (paid IDs with rule).
- Acceptance PASS: bit-identical metric recomputation, 1,696 cells per part.

**Figures:** `figures/fig_rc23_std.png`, `figures/fig_rc23_robustness.png`.

**Code:** `src/rc23_common.py`, `rc23_jobs.py`, `rc23_eval.py`, `rc23_validate.py`, `rc23_report.py`, `rc23_figures.py`, `rc23_freeze.py`.

**Related:** `opus_rc22/ADDENDUM_RC22_20261021.md`.
