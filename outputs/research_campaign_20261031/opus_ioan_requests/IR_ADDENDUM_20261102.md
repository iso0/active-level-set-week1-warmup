# IR addendum, dated 2026-11-02: corrections of interpretation

This addendum was written in the GT study (branch `geometry-temperature-20261102`, registration 9dcee41f) at the owner's request of 2026-11-02.
- **It changes no number.** Every frozen IR table and value (results commit 0a57d644) stays as it is.
- **It corrects how the numbers are worded.** Where the wording in `FINAL_REPORT_IR.md` or `IOAN_SUMMARY.md` differs from this addendum, this addendum applies.
- **Both reports now link to it** in a dated line at their top.

## Türkçe

1. **"Derinlik, girdilerin etiket hakkında söylediği her şeyi taşıyor" (rapor §1.3, §5a; özet "Answers 3")**
   - Bu nedensel ya da evrensel bir kanıt değil.
   - Ölçülen şu: bu havuzda (541 koşu), denenen sınıflandırıcı ailelerinde (L2-lojistik; 20 × 10 kat CV ve HGB), gerçek değerlerle [h, D]'ye girdiler ya da diğer çıktılar eklenince çapraz doğrulanmış log loss en fazla +0.015 / −0.001 değişti.
   - Etiketler elle yapılmış biçim (morfoloji) işaretlemeleri: Ioan'ın ifadesiyle "çoğunlukla eriyik havuzunun hemen altındaki boşluklar". Derinlik bu işaretlemenin güçlü bir izi, ama etiketin nedeni olduğu gösterilmedi.
   - Derinlik Keyhole koşularının %68'inde yaklaşık 300 µm'de sansürlü (madde 7).
   - "Aracı değişken" (mediator) sözcüğü, bu modeller ve bu veri içindeki istatistiksel yeterlilik anlamında okunmalı, nedensel aracılık anlamında değil.
2. **"Hiçbir çıktı h + derinliğe bilgi eklemiyor"**
   - Bu ifade şunlarla sınırlı:
     - denenen özellikler: T0-pencere özetleri (KE, maksimum sıcaklık, hız sıçraması oranı ve süresi, emilen lazer, toplam enerji, parçacık sayısı), aktif pencere maksimumları (KE_A, T_A, V_A), genişlik ve uzunluk;
     - denenen modeller: doğrusal lojistik ve HGB;
     - pratik etki: IR A4 tablosunda, gerçek değerlerle [h, D]'ye tek tek eklenen 16 özellik kümesi log loss'u −0.0013 ile +0.0148 arasında, BA'yı −0.0096 ile +0.0001 arasında değiştirdi. Hiçbiri log loss'u 0.002'den fazla düşürmedi, BA'yı da 0.001'den fazla artırmadı.
   - Erken, nedensel pencereler ve doğrusal olmayan etkileşimler bu kapsamda değildi. GT erken sıcaklığı ayrıca sınıyor.
   - Doğru ifade: "denenen özellik ve modellerde, pratik eşiğin üstünde ek bilgi görülmedi."
3. **"Simülasyon tasarrufu yok"**
   - Tam ardışık karşılaştırma (adayın kendi sorgularını seçtiği yol ve taze sınama) KOŞULMADI. Kayıtlı kural, kayıtlı C1 yolları üzerindeki eşleştirilmiş taramada durdu.
   - O tarama da gerçek etiket BA'sı yerine dondurulmuş değerlendirici haritası g\* ile vekil BA kullanıyordu.
   - Doğru ifade: "eşleştirilmiş DEV taramasında hiçbir eş-çıktı derinlik modeli kayıtlı eşiği geçmedi; ardışık tasarruf sınanmadı."
4. **Gerçek KE kontrolü bir üst sınır değil**
   - ORACLE_CHAIN_KE (+0.001), yalnızca o yapının (gerçek KE'yi temel fonksiyon olarak kullanan derinlik GP'si) en iyi durumudur.
   - Bütün olası yöntemler için teorik bir üst sınır değildir. Örneğin KE'nin doğrudan sınıflandırıcıda ya da doğrusal olmayan bir biçimde kullanımı ölçülmedi.
   - Doğru ifade: "bu zincir yapısı için, test noktasındaki gerçek KE bile +0.001'den fazla kazandırmadı."
5. **Çok çıktılı GP'de "transferin iptali"**
   - Bonilla vd. (2007) ve Wackernagel'in "autokrigeability" sonucunun koşulları şunlar:
     - tek bir ortak girdi çekirdeği (ICM: K = B ⊗ k);
     - izotopik veri (bütün çıktılar aynı girdilerde gözlenmiş);
     - gürültüsüz gözlem, ya da gürültü yapısının B ile uyumlu olması.
   - Bu koşullar altında bir çıktının tahmin ortalaması yalnız kendi gözlemlerine bağlıdır.
   - IR'nin LMC'si (R ≥ 2 çekirdek, çıktıya özgü bağımsız gürültü) bu koşulların tam olarak altında değildi. Bu yüzden transferin sıfır olması beklenmez, yalnızca küçük olması beklenir.
   - Ölçülen küçük etki teoriyle uyumlu, ama teorinin doğrudan bir sonucu değil.
   - Test noktasında öteki çıktılar da gözlenmediği için oradaki bilgi ancak öteki koşulardan gelebilir.
   - Özetteki "korelasyon yeni bilgi aktaramaz" ifadesi fazla genel. Doğrusu: "bu ayarda (eş-noktalı, küçük gürültü) aktarılabilecek bilgi azdır ve ölçülen etki de küçüktür."
6. **Kayıt öncesi ilk bakış**
   - 31 Ekim'deki betimleyici ilk bakış (korelasyonlar, gerçek değerlerle lojistik; `prelook/`, defterde IR-PRE) kayıttan ÖNCE yapıldı.
   - Rapor (§2) bunu söylüyor. İngilizce özetteki "All rules were registered before any result" cümlesi ise eksik: o ilk bakış kurallardan önceydi ve genişlik ile sıcaklığın aday olmasına yol açtı.
   - Bu açıklama bundan sonra her özette korunacak.
7. **~300 µm tavanı ve "sınıflandırmayı etkilemiyor"**
   - Tavandaki 134 koşunun hepsinin Keyhole olması, tavanın öğrenmeyi etkilemediğini kanıtlamaz.
   - Tavan, derinlik GP'sinin hedefini Keyhole bölgesinde sansürlüyor ve derinlik–genişlik ilişkisini düzleştiriyor.
   - Doğru ifade: "tavandaki koşuların gerçek-değer sınıfını değiştirmez; öğrenmeye etkisi IR'de sınanmadı."
   - Neden hâlâ bir HİPOTEZ:
     - Veri setinin koşu başına `parameters.json` dosyası yalnız dört anahtar içeriyor (güç, hız, ışın boyu, altlık sıcaklığı; Week 11 denetimi). Alanın z boyutu hiçbir mevcut dosyada yok.
     - İç kanıt sert bir alt sınırla tutarlı (GT `ceiling/CEILING_EVIDENCE.json`):
       - plato düzeyinin medyanı 300.2 µm, %5–95 aralığı 299.6–300.6 µm, SD 0.7 µm;
       - plato düzeyi P, LS ve ST'den bağımsız (\|ρ\| ≤ 0.09);
       - Keyhole derinlik histogramında 300–310 µm aralığında 131 koşu, 290–300 µm aralığında 4 koşu var.
   - Doğrulama, simülasyon kurulumunun (alan boyutu) veri sağlayıcıdan öğrenilmesini gerektirir.
8. **Öteki genel cümleler.** "Kalan erken hata, simüle edilmemiş girdilerde derinlik hakkında bilinebileceklerin sınırı" cümlesi, denenen modeller için geçerlidir.

## English (for `IOAN_SUMMARY.md`)

1. **"Depth carries everything the inputs say about the label" is not a causal or universal result.**
   - What was measured: with the tried classifiers (L2 logistic, HGB) on this pool, adding the inputs or any other output to the TRUE [h, depth] changed the cross-validated log loss by at most +0.015 / −0.001.
   - The labels are manual morphology annotations, mostly guided by cavities below the melt pool.
   - Depth is censored at about 300 µm in 68 % of the Keyhole runs.
   - Read "mediator" as statistical sufficiency within these models, not as causal mediation.
2. **"No output adds label information"** holds only for:
   - the tried features: late-window T0 summaries, active-window maxima, width and length;
   - the tried models;
   - the measured range: 16 additions to the true [h, D] changed log loss by −0.0013 to +0.0148 and BA by −0.0096 to +0.0001.

   Early, causal time windows were not part of it.
3. **"No saving":** the full sequential comparison was not run. The registered rule stopped at a matched screen on recorded C1 paths, which used a proxy BA.
4. **The true-KE control (+0.001)** bounds only that chain construction, not every possible method.
5. **Transfer cancellation.** The cancellation result needs:
   - an intrinsic coregionalisation (one shared kernel);
   - isotopic data;
   - noise-free or matched-noise observations.

   IR's LMC was close to, but not exactly in, that setting. Small transfer was therefore expected, not zero. The sentence "their correlation cannot transfer new information" is too strong.
6. **First look.** A descriptive first look (correlations, true-value logistic) was computed BEFORE the IR registration and is disclosed in `prelook/` (ledger row IR-PRE). "All rules were registered before any result" should read: "all rules were registered before any result, after a disclosed descriptive first look."
7. **The ceiling.** That every ceiling run is Keyhole does not show that the ceiling leaves learning unaffected. It censors the depth target. The domain floor remains a hypothesis:
   - the per-run parameters.json holds only four input keys;
   - the internal evidence is a tight plateau at 300.2 µm, independent of P, LS and ST.

The GT study (2026-11-02) tests a geometric classifier and early temperature directly. See `outputs/research_campaign_20261102/opus_geometry_temperature/FINAL_REPORT_GT.md`.
