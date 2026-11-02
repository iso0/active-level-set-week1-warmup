# Temsil ve iki adımlı planlama: tamamlanan çalışmanın sonucu

Yeni yöntemleri gerçekten çalıştırdım. 336 bağımsız sentetik dünyada 4.096
öğrenme yolundan 4.093'ü tamamlandı; ayrıca 352 saf arama yolu çalıştı. Üç
öğrenme yolu ortak kaynak dosyasını okuma hatasıyla durdu. Bunların satın
alınmış gözlemleri ve hata kayıtları korunuyor; sonuçları tamamlanmış gibi
doldurmadım. Önceki kampanya ve Opus'un dosyaları değişmedi.

Soru şuydu: Beklenmedik bir bölgeyi öğrenemememizin nedeni modelin yerel
yapıyı temsil edememesi mi, yoksa bir sorgu yerine iki sorgu sonrasını
hesaplamamızın gerekmesi mi? Aynı başlangıç verisi ve aynı keşif takvimiyle
bu iki etkiyi ayrı karşılaştırdım. Ayrıca olasılık karışımını daha doğru
kullanan tek adımlı bir kontrol çalıştırdım.

Eklediğim yerel bileşen genel bir iyileşme sağlamadı. Çoğu dünyada model,
bu bileşenin ağırlığını neredeyse sıfıra indirdi; aynı noktaları sorgulamaya
devam etti. İki adımlı planlama bazı sorgu yollarını değiştirdi fakat genel
hata veya ada öğrenmesinde güvenilir kazanç göstermedi. Karışımı daha doğru
hesaplayan kontrol de bunu çözmedi. Bu sonuç “yerel bilgi faydasızdır” ya da
“planlama hiçbir zaman işe yaramaz” demek değil; sınanan yapı ve bütçede
bu önerilerin yararını gösteremedik.

Olumlu ve daha sağlam bulgu, uzunluk ölçekleriyle birlikte genlik ve gürültüyü
veriden öğrenen GP oldu. Sorgular henüz ayrışmadan, aynı 32 satın alınmış
gözlemde genel hata yaklaşık **3,49 yüzde puanı** daha düşüktü. Bu model
iyileşmesi; yeni planlayıcının başarısı değil. Ancak güçlü GP de döndürülmüş
yapıda yaklaşık yazı-tura düzeyinde kaldı ve küçük adaları neredeyse hiç
öğrenemedi. Ortalama iyileşme bu başarısızlıkları gizlemiyor.

Büyük adalarda güçlü modelle tek adımlı risk seçimi yararlı bir ikincil sonuç
verdi: straddle'a göre ada içindeki noktaları doğru pozitif sınıflama oranı
ortalama 26,2 yüzde puanı arttı.
Fakat aynı karşılaştırma küçük adaların sınır hatasını yaklaşık 4,0 yüzde
puanı kötüleştirdi. Bu yüzden bütün problemlere tek bir seçici önermiyorum.
Bir bölgeye ilk kez rastlamak ile rastlandıktan sonra sınırını öğrenmek de
farklı: küçük adalarda rastgele arama 16 dünyanın dördünde adaya ulaşırken
güçlü GP'nin iki ucuz seçicisi bu panelde hiç ulaşamadı.

Maliyet önemli. Ortak başlangıç deneyinde mevcut modelin tek adımlı seçimi
ortalama 1,42 CPU saniyesi, iki adımlısı 8,37 saniye sürdü. Yerel modelde
bu değerler 4,66 ve 11,74 saniye. Aynı beş saniyelik seçim hesabı bütçesinde
iki adımlı yöntem daha kötü sonuç verdi. Hiçbir sistem genel sorgu tasarrufu
iddiası için önceden koyduğumuz %80 hedefe ulaşma şartını karşılamadı.
Fiziksel simülasyon süresi ölçülmediği için saat tasarrufu iddiası da yok.

Önerim: **pahalı iki adımlı yöntemi şimdi gerçek veri sistemine taşımayalım.**
Opus'un güçlü modelini ve ucuz seçim kontrollerini koruyalım. Bu çalışma,
modelin güçlü olmasının planlamayı derinleştirmekten daha somut bir kazanç
verdiğini gösteriyor; bütün yerel rejim sorununu çözdüğünü göstermiyor.

Bir sonraki ayırt edici deney için açıklamam şu: yerel bileşenin korelasyonu
yerel olsa da eklediği önsel varyans her yerde var. Tek bir yerel anomaliyi
açıklamak için bütün sıradan noktalarda karmaşıklık bedeli ödüyor olabilir.
Bunun sınırlı bir matematiksel örneğini türettim. Rakip açıklama ise küçük
bölgenin genel hata hedefinde çok az ağırlık taşıması. Yeni bir kampanyada
aynı satın alınmış başlangıçlar ve aynı ucuz seçiciyle önce yerel tahminin
iyileşip iyileşmediğini, sonra sorguların bu bilgiyi kullanıp kullanmadığını
ayırmak gerekir. Bu yeni deney yapılmadı; mevcut test sonuçlarına bakıp
önseli yeniden ayarlamadım.

Kod, matematik, bütün ailelerin sonuçları, maliyet tabloları, görsel olarak
incelenmiş şekiller ve Opus'un kullanabileceği arayüz yerel pakette hazır.
Bu bağımsız sentetik kanıt; yeni fiziksel simülasyon, Keyhole BA başarısı,
C4 veya Stage A sonucu değildir. Ana rapor: FINAL_REPORT.md.
