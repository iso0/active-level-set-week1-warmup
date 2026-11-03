# Tez öncesi kapanış özeti (2026-11-02)

Bu sayfa araştırmanın tamamını tek yerde özetler. Ayrıntı ve kaynaklar İngilizce belgelerdedir; numaralı başlıklar o belgelere karşılık gelir.

## 1. Sonuç tek paragrafta

**Problem.** LPBF SPH simülasyonlarında erime havuzu ya Keyhole rejimindedir ya da conduction rejiminde. Amaç, bu sınırı olabildiğince az simülasyonla öğrenmek.

**Cevap: C1 + margin.** 541 koşuluk tek havuzda en iyi öğrenici iki aşamalı bir model:
- **Birinci aşama:** maksimum erime derinliğini tahmin eden bir GP. Ortalamasında log h yönünde doğrusal bir fizik eğilimi var; hiperparametreleri sabit, zayıf bir öncülle MAP olarak kestiriliyor.
- **İkinci aşama:** [z_h, tahmini derinlik] üzerinde, düzenlileştirmesi öğrenilen bir lojistik sınıflandırıcı.
- **Sorgu kuralı:** düz margin.

**Dondurulmuş referansa (HA_LEAN + margin) göre, 80 taze tekrarda (C1C):**
- daha erken öğreniyor: erken BA-AULC +0.0053 [+0.0039, +0.0068];
- BA 0.95'e ortalama 1,8 daha az simülasyonla ulaşıyor;
- geç dönemde bir şey kaybetmiyor: −0.0006, 0.003 içinde korunuyor.

**Kazancın kaynağı model,** yani açılmamış girdilerde daha iyi derinlik tahmini. Sorgu kuralı değil: model sabitken denenen hiçbir kural margin'i geçmedi.

**Kalan açık bir bilgi sınırı.** Açılmamış bölgelerde ve etiketlerin iç içe geçtiği hızlı tarama köşesinde duruyor. Şunların hiçbiri bu açığı kapatmadı:
- diğer fiziksel çıktılar (sıcaklık, akış, KE, genişlik);
- geometrik oranlar;
- erken sıcaklık;
- dengeleyiciler ve güven kuralları.

**Kapsam.** Bütün sonuçlar aynı havuzun yeniden bölünmeleri. Dış veya fiziksel doğrulama yok (Hafta 11 denemesi durdu; C1C planı yazıldı, çalıştırılmadı).

## 2. Çalışmalar nasıl birbirine bağlandı (yedi dönüm noktası)

1. **Hafta 7.** Derinlik regresyonu Keyhole kuyruğunda bozuluyor. Hedef ikili Keyhole sınırı oldu.
2. **Hafta 8–10.**
   - Margin rastgele örneklemeyi yeniyor, ama "40 simülasyon tasarrufu" ve "2.33×" iddiaları dondurulmuş doğrulamada düştü.
   - h = P/√(VX·LS³) sınıfları ayırıyor.
   - Kazanç modelden geliyor, sorgu yolundan değil. Track A dondu.
3. **Hafta 11–17.**
   - NEW verisinde dış doğrulama tek sınıflı başlangıç yüzünden durdu.
   - Keşif ve metrik kuramı kuruldu.
   - Hiçbir model ya da sorgu değişikliği gerekçelenemedi.
4. **Hafta 18–20.**
   - OLD'da etiket bir derinlik eşiği; derinlik etiketin taşıyıcısı.
   - NEW'deki hızlı taramalar bunu bozuyor.
   - Aktif pencere derinliği daha iyi, ama G3'e karşı üstünlüğü C3'te doğrulanmadı.
5. **Ortak çalışma ve RC18–RC23.**
   - Ortak derinlik–etiket modelleri ön elemeyi geçemedi.
   - Tek havuz, yalnız ödenmiş sonuçlar kuralıyla gereksiz bileşenler tek tek çıktı.
   - Kalan: h + tahmini derinlik (HA_LEAN).
6. **RC24 → C1C.**
   - Fizik eğilimi erken kazanç veriyor, ama küçük örneklemde ML-II bunu bozuyor.
   - MAP öncülü düzeltiyor (C1).
   - 80 taze tekrarla doğrulandı.
7. **C1S, FR, IR, GT.** Kalan açık bir bilgi sınırı. Dengeleyici, güven kuralı, eş-çıktılar, geometri ve erken sıcaklık işe yaramadı.

## 3. Kapanışta yapılanlar

1. **GitHub.**
   - Bütün çalışma tek doğrusal zincirde; `main` 4 çalışma gerideydi.
   - Kapanış dalı `main`'le birleştirildi, `main` güncellendi.
   - Her çalışmanın dondurulmuş hali için etiket (tag) eklendi.
   - Research Hub dosyaları SHA-256 ile kilitli olduğu için hiç değiştirilmedi. Kök README yeni giriş noktasını gösteriyor.
2. **Ham çıktılar.** Yaklaşık 3 GB ham birim çıktısı yalnız bu worktree'deydi. Hepsi `Documents\thesis_archive\` altına SHA-256 doğrulamasıyla kopyalandı: 18.972 dosya, 0 çakışma.
3. **Testler.** Bilinen iki hata çözüldü; hiçbir dondurulmuş referans değişmedi.
   - `T_TOBIT`: dondurulmuş değer yalnız 8 BLAS iş parçacığıyla birebir üretiliyor; GT koşuları 1 iş parçacığıylaydı. Test artık bu ayarı kendisi sabitliyor.
   - H soneki: 10 tarihsel satır, tarihli bir düzeltme satırıyla tam kimliklere bağlandı.
   - Weeks 12+ takımı: 219 geçti, 2 atlandı, 0 başarısız.
4. **Merkezi kayıtlar.**
   - Karar, deney ve ilerleme kayıtlarında Hafta 10'dan RC18'e kadar eksik olan satırlar eklendi.
   - İddia defterine ve CLAIMS_MATRIX'e kapanış notları eklendi.
5. **Tez için yeni katman (`docs/final/`).**
   - sentez, çalışma indeksi, iddia haritası, açık madde kaydı, sözlük, depo haritası;
   - ana sonuç için 3 şekil, dondurulmuş verilerden, sayılarla doğrulanmış.

## 4. Senin yapman gereken tek şey

Ana klasör `Documents\thesis` hâlâ 13 Ekim'deki eski dalda. Bu oturum izole bir worktree'de çalıştığı için o klasöre git işlemi yapamadı.

Klasörü güncel `main`'e geçirmek için şu komut yeterli. Hiçbir şey silmez, kayıt tutar; önce `-DryRun` ile deneyebilirsin:

```
powershell -NoProfile -ExecutionPolicy Bypass -File "%USERPROFILE%\Documents\thesis\.claude\worktrees\joint-depth-label-dev\tools\finalize_local_workspace_20261102.ps1"
```

İstersen `-Archive` ekle. Bu, kodun başvurmadığı Hub ve staging klasörlerini `thesis_archive`'a taşır. Eski analizlerin mutlak yolla okuduğu Hafta 4, 5 ve 9 klasörlerine dokunmaz.

## 5. Ioan'a sorulacak üç şey

Hiçbiri yazmayı engellemiyor.

**Tezde nereye girecek?** 2026-11-03 kararıyla dış doğrulama soruları tezin "Further studies" bölümüne girecek; yazımdan önce çalıştırılmayacaklar. Liste `THESIS_SYNTHESIS.md` §8'de:
- yeni koşularda genelleme;
- aralık dışı güvenlik;
- köşedeki etiketin belirlenimli olup olmadığı;
- 49 bekletilen koşu;
- 300 µm tabanı.

1. SPH alanının z derinliği nedir; 300 µm alanın tabanı mı? Bu, Keyhole koşularının 300 µm'de birikmesini hipotezden olguya çevirir.
2. Tezden sonra küçük bir dış doğrulama koşusu mümkün mü? Plan `EXTERNAL_VALIDATION_PLAN_C1C.md`'de: 152–176 koşu.
3. Bug nedeniyle bekletilen 49 NEW koşusunun fiziği bozuk mu, yoksa yalnız kayıtları mı? Geçerliyse, hiç dokunulmamış tek küçük dış set bunlar.
