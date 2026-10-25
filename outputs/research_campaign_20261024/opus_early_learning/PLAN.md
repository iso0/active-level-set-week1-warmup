# EL çalışması — erken öğrenme avantajını tek öğrenicide simülasyon tasarrufuna dönüştürmek

**Görev planı.**
- Opus. Sahip talimatı 2026-10-24; başlangıç 2026-10-25 20:07:51 UTC.
- Tek pencere: 48 saat, bitiş en geç **2026-10-27 20:07:51 UTC**. Kota beklemeleri ve yeniden başlatmalar bu saati sıfırlamaz. İş erken biterse kampanya kapatılır.

## Sade özet
- HA_LEAN ve HA_TREND, hem "seçen" (margin ile sonraki simülasyonu belirleyen) hem "tahmin eden" rolünde çaprazlanır. Dört sistem: A = L/L, B = T/T, C = T seçer / L tahmin eder, D = L seçer / T tahmin eder.
- Önce mevcut kayıtlı yollarda (DEV) erken kazancın kaynağı ayrıştırılır: tahmin mi, simülasyon seçimi mi?
- Sonra en anlamlı sistem, dondurulmuş kod ve ölçütlerle, hiç kullanılmamış tekrarlarda tek öğrenici düzeyinde sınanır.

## Kaynak ve ayrılık
- **Çalışma ağacı:** `C:\Users\ozgur\Documents\thesis\.claude\worktrees\joint-depth-label-dev`, dal `joint-depth-label-dev`, başlangıç HEAD = origin = b3fd5620.
- **Çıktılar:** yalnız `outputs/research_campaign_20261024/opus_early_learning/`. Kod `src/el_*`.
- **Koordinasyon:** yalnız `C:\Users\ozgur\Documents\thesis_shared_runtime\campaign_20261024\`.
  - Ben yalnız `opus_state.json` yazarım; `astra_state.json` yalnız okunur.
  - Ortak dosyada iki tarafın aynı alanı değiştirmesi yok.
  - `POOL_PLAN.json` koordinasyon kaydı bu çalışmada kullanılmaz.
- **Kapasite:** 8 mantıksal çekirdek (4 fiziksel), 31.8 GB.
  - Opus en çok **3** sayısal işçi; Astra'nın 3'lük payı kullanılmaz, boş görünse de.
  - Her işçide BLAS/OpenMP 1 iş parçacığı. Elle başlattığım ağır analiz süreçleri de bu 3'e sayılır.
  - Boş bellek 3 GB'ın altındaysa yeni işçi başlamaz.
  - Daha küçük makinede pay = min(3, ⌊3 × mantıksal / 8⌋).
- **Astra:** başlangıçta durum SETUP, iş yok, bitiş 2026-10-27 20:05 UTC. Onun klasörlerine, indeksine, süreçlerine ve otomasyonlarına dokunulmaz.
- **Runner:** `src/el_runner.ps1`. RC24 runner'ının kopyası; koordinasyon yalnız kendi durum dosyası üzerinden.
  - Birimler tek tek ve atomik kaydedilir; biten birim tekrar çalışmaz, ölü kilitler bırakılır. Yeniden başlatma güvenlidir.
  - Sağlıklı kuyruk sürekli mesajla izlenmez; tek bir arka plan bekleyicisi iş bitince haber verir.

## Aşamalar
1. **Hedef sırası ve tanımlar:** `PROTOCOL_EL_OBJECTIVES.md`. Sonuçlardan önce commit ve push edilir.
2. **DEV çapraz analiz** (mevcut yollar, mekanizma ve aday seçimi; iddia değil):
   - C eksiksiz hesaplanır (HA_LEAN, HA_TREND yollarında, her bütçe).
   - D'nin yalnız eksik bütçeleri hesaplanır; birim başına bir denetim bütçesi eklenir.
   - 2×2 ayrıştırma: model etkisi, yol etkisi, etkileşim.
3. **Gerekirse tek bir sınırlı mekanizma:** yalnız açılmış gözlemlerden öğrenilir. Önce ölçülmüş sorun yazılır. Varyant taraması yok.
4. **Son karşılaştırma:**
   - Kod SHA-256 manifesti ve ölçütler sonuçlardan önce dondurulur.
   - Taze STD tekrarları 83–122, BLOCK_A başlangıçları 25–32, BLOCK_B başlangıçları 9–16.
   - Her iki seçim yolu ve her iki tahminci (A–D), varsa aşama 3 sistemi.
5. **Teslim:**
   - dışa aktarımlar (tüm kolların tahminleri ve ödenmiş sorgu kimlikleri) ve bağımsız yeniden hesap;
   - tek sayfa Türkçe özet, tablolar, literatür ve katkı sınırı;
   - tez kayıtları; commit ve push (main'e birleştirme ve force push yok).

## Yasaklar
- Simülatör, ücretli bulut/API, C4 veya korunan dış değerlendirme başlatılmaz.
- Açılmamış koşunun etiketi, derinliği veya başka çıktısı öğreniciye verilmez.
- OLD/NEW yalnız kaynak kaydıdır.
- Test etiketleri yalnız değerlendiricide kullanılır.
- Önceki donmuş kararlar değişmez.
