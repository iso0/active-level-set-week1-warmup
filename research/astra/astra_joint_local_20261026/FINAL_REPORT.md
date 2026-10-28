# Genel ve yerel yapıyı birlikte öğrenmek: sonuç

**Birlikte öğrenmek küçük bir fayda sağladı; önceki başarısızlığın tamamını açıklamadı.** Daha pahalı sorgu seçimi deneyine geçmek için önceden koyduğumuz ölçüt karşılanmadı. Eşiği değiştirmeden bu kampanyayı kapatıyoruz.

Önceki çalışmada güçlü genel model önce öğreniliyor, yerel düzeltme onun üzerine kuruluyordu. Şüphemiz şuydu: genel model yerel bir farklılığı zaten gürültüye veya geniş ölçekli yapıya katmış olabilir. Bu kez genel modelin uzunluk ölçeklerini, genliğini ve gürültüsünü, yerel açıklamayı da hesaba katarak birlikte öğrendik. Yerel şekiller, karar eşiği ve satın alınmış gözlemler aynı kaldı. Ayrıca yalnız daha fazla optimizasyon yapmanın etkisini ayıran güçlü kontrol kullandık.

Önce daha önce gördüğümüz 32 dünyada, 64 ortak sorgu yolunda geliştirme deneyi yaptık. Sonuç olumlu çıkınca modeli değiştirmeden **144 yeni sentetik dünyada, 288 ortak yolda** sınadık. Dairesel yapıların yanında döndürülmüş sırtlar, düz tepeler, çift adalar, halkalar; ayrıca düzgün sınır, dengesiz sınıf, farklı gürültü ve bozuk monitor kontrolleri vardı. Aynı dünyanın iki yolu iki bağımsız dünya sayılmadı.

Yerel yapı içeren 72 yeni dünyada, 8–24 gözlem arasındaki ortalama dengeli doğruluk kazancı:

|Birlikte öğrenme, hangi modele göre?|Kazanç: yüzde puanı|Betimleyici %95 aralık|
|---|---:|---:|
|Daha çok optimize edilmiş genel model|+0,736|+0,474 ile +1,035|
|Aynı yerel yapı, sabit genel model|+0,402|+0,188 ile +0,651|
|Aynı ortalama önsel ek varyans, yerelleştirmesiz kontrol|+0,759|+0,481 ile +1,069|

Üç karşılaştırmada da ortalama kazancın en az **0,50 yüzde puanı** olmasını önceden istemiştik. İkinci karşılaştırma bunu geçmedi. Dolayısıyla sonuç “hiçbir fayda yok” değil; **ek fayda tekrarlanıyor ama gözlenen ortalama seçtiğimiz pratik büyüklüğe ulaşmıyor**. Aralık 0,50 puanı da içeriyor; gerçek etkinin kesin olarak bu eşiğin altında olduğunu kanıtlamadık. Üç ana karşılaştırmanın çoklu karşılaştırmaya göre ayarlanmış alt sınırları sıfırın üzerindeydi; tablodaki aralıklar ise ayrı ayrı betimleyicidir.

Zor bölgeler çözülmedi. Halka biçiminde toplam doğruluk biraz yükselirken bölge içi hata kötüleşti. Çift adalarda daha belirgin iyileşme vardı, yine de 24 yolun hiçbiri teyitli BA 0,90'a ulaşmadı. Düzgün sınırda küçük zarar gördük. Birlikte öğrenme Brier puanını iyileştirirken, sabit yerel modele göre log loss'u kötüleştirdi. Tek bir başarı sayısı bu tabloyu anlatmıyor.

Toplam 288 yolda BA 0,90 / 0,93 / 0,95'e teyitli ulaşma sayıları birlikte öğrenmede **109 / 65 / 25**, güçlü genel kontrolde **107 / 64 / 24** oldu. Sorgu tasarrufu için güçlü bir sonuç değil. Birlikte öğrenmenin yol başına model hesap maliyeti yaklaşık **3,02 CPU saniyesi**, eski sabit yerel yaklaşımınki **1,05 saniye**. Fiziksel simülasyon süresi ölçmedik.

**Şimdi önerim:** bu modeli mevcut yöntemin yerine geçirmek yerine doğrulanmış araştırma bileşeni olarak saklayalım. Bir sonraki ayrı deney, “adayı yeterince görmedik” ile “gördüğümüz bilgiyi bu dar yerel model paylaşamıyor” açıklamalarını ayırmalı: aynı dünyalarda bilgi miktarı ile yerel şeklin yeterliliğini ayrı ayrı değiştiren küçük bir teşhis. Gerçek konumu bilen kontrol yalnız değerlendirme amacıyla kullanılmalı. Bu yeni deney burada başlatılmadı.

Bu çalışma gerçek Keyhole etiketini veya 541'lik havuzu doğrulamaz. Teze katkısı, birlikte öğrenmenin ölçülmüş ama sınırlı faydasını; toplam doğruluk, zor bölgeyi öğrenme ve sorgu tasarrufunun farklı şeyler olduğunu göstermesidir. Sayısal referanslar, ham tahminler, bütün aileler, maliyetler ve bağımsız taşınabilir kod [sonuç indeksinde](RESULTS_INDEX.md).
