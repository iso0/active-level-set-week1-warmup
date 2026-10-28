# Astra'nın tamamlanan araştırması: ne öğrendik?

Bu kez yalnız kod testi yapılmadı. Eski geliştirme sürümleriyle birlikte
**13.065 kontrollü deney yolu** tamamlandı. Ana bağımsız sentetik testte
14 farklı problem ailesi ve her ailede 24 gerçekleşme var. Aynı dünyadaki farklı
yöntemleri bağımsız deney diye saymıyorum. Gerçek SPH simülasyonu çalıştırılmadı;
Opus'un önceki pilotu tekrarlanmadı.

Yeni katkı, “beklenmedik bir nokta bulunca çevresini araştır” fikrini açık bir
amaçla bağlamak: bir sonraki simülasyonun, rejimin hangi tarafta olduğunu
yanlış tahmin ettiğimiz alanı ne kadar azaltacağını hesaplamak. Aynı simülasyondan
gelen birden fazla çıktı birlikte değerlendiriliyor. Ölçüm gürültüsü ile modelin
bilmediği şeylerden doğan belirsizlik ayrı tutuluyor. Sorgudan önceki tahmin ve
sorgu yolu kaydediliyor. Bu parçaların temel teorisi yeni değil; benim katkım,
çalışan uygulama ve hangi mekanizmanın işe yaradığını ayıran kontrollü deney.

**İlk açıklamamın bir kısmı çalışmadı.** Eski sürpriz eşiği neredeyse hiç
tetiklenmedi. Karar değişimine dayanan yeni eşik daha fazla çalıştı, ancak
yerel sorgulama genel hatayı veya hedefe ulaşmak için gereken sorgu sayısını
belirgin biçimde iyileştirmedi. Her beklenmedik noktanın komşularına gitmek de
iyi bir genel kural çıkmadı.

**Model değişikliği belirli bir sorunu çözdü.** Bir yönde çok hızlı değişen
sınırda hata yaklaşık %49'dan %2'ye indi. Fakat bu kazanç bütün dünyalara
yayılmadı. Küçük adalarda model, başlangıçta pozitif örnek görmüş olsa bile
bölgeyi iyi öğrenemedi. Başlangıçta görülmeyen küçük adalarda yeni sistem
24 dünyanın yalnız birinde adaya sorgu yaptı. Başlangıçta görülen küçük
adalarda ortalama yakalama oranı yalnız %9,3 oldu.

Bu yüzden “ortalama hata azaldı” demek, “ilginç bölgeleri daha az simülasyonla
keşfettik” demek değil. Yeni modelin bölgesel yöntemi ortak başarı hedefine
336 dünyanın 148'inde ulaştı; basit modelde aynı yöntem 164'ünde ulaştı.
Önceden belirlediğimiz sorgu tasarrufu koşulunu hiçbir kayıtlı karşılaştırma
geçmedi. Birbirinden farklı ölçütleri birleştirip olumlu sonuç çıkarmıyorum.

Büyük adalarda yerel tepkinin küçük bir yararı var; bunu da saklamıyorum.
Ancak bu, küçük ve henüz görülmemiş bölgeler sorununu çözmüyor. Ayrıca
mekânsal olarak tutarlı bir monitor hatası gerçek bir rejim adası gibi
görünebilir. Yalnız aynı monitoru daha fazla örneklemek bu ayrımı her zaman
yapamaz; gerekirse gerçekten farklı bir ölçüm gerekir.

**Sonraki en ayırt edici deney:** aynı ödenmiş ilk anomali örneklerinden
başlayıp iki şeyi ayrı ayrı değiştirmek: modelin yerel bir yapıyı temsil
edebilmesi ve sorgu kararının bir yerine iki adım sonrasını düşünmesi.
Yalnız model değişikliği işe yararsa sorun temsildir; aynı modelde iki adım
işe yararsa sorun kısa vadeli sorgu kararıdır. Bu yeni deney henüz yapılmadı.
Yeni gerçekleşmeler ve önceden sabitlenmiş küçük bir protokol gerekir.

Kod, tüm başarısızlık kayıtları, sayısal denetimler, görseller ve maliyet
tabloları korunuyor. Altı posterior kontrolünde sayısal integrasyon geçti;
yaklaşık edinim hesabının bir durumda farklı nokta seçtiği de açıkça yazıldı.
Sonuçları Opus'a dosya paketi olarak bıraktım; onun çalışma dosyalarını
değiştirmedim ve senin adına mesaj göndermedim. C3 kararı, q20, etiketler ve
dışlamalar korundu; C4 ve gerçek veri Stage A çalıştırılmadı.

Ana rapor: [FINAL_REPORT.md](FINAL_REPORT.md).
Tüm dosyalar: [RESULTS_INDEX.md](RESULTS_INDEX.md).
