# Yerel düzeltme araştırması — bağımsız sonuç

26 Ekim 2026. **Yeni yöntem, güçlü GP'nin yerine önerilmiyor.** Yalnız yazılım
kontrolü yapılmadı: 32 bağımsız sentetik dünyada 64 gerçek sorgu yolu çalıştırıldı.
İlk modelin başarısızlığından sonra, aynı gözlemler üzerinde farklı bir paylaşım
mekanizması da geliştirildi ve sınandı. İki sürüm de önceden konan genişletme
ölçütünü geçmedi. Olasılık tahminleri düzeldi; bunun daha iyi sınır öğrenmeye veya
daha az sorguya dönüştüğü gösterilemedi. Güçlü GP ve ucuz margin kontrolü korunmalı.

## Yapılan iş ve kapsam

Sekiz aile kullanıldı: düzgün ilişki, yerel sapma, küçük ada, döndürülmüş yerel
yapı, seyrek negatifler, değişen gözlem gürültüsü, aykırı değerler ve mekânsal
ilişkili monitor bozukluğu. Her ailede dört bağımsız dünya var. İki yol paneli
aynı dünyanın tekrarıdır; 64 yol, 64 bağımsız dünya değildir. Başlangıçta sekiz
maximin gözlemi satın alındı. Sonraki yollar maximin veya güçlü GP'nin margin
kuralıyla B24'e kadar devam etti. B8,10,…,24'te karşılaştırılan bütün modeller
tam olarak aynı satın alınmış gözlemleri kullandı.

Ölçülen hedef, gürültülü sürekli bir monitorun **latent sıfır eşiği**. Tahmin
p>=0.5 ile sınıflandırıldı; ana değerlendirme BA-AULC B8–B24. BA,
(pozitif recall + negatif recall)/2'dir. Bu sabit karar, farklı sınıf dengelerinde
BA-optimal karar olmak zorunda değildir; model etkisini ayırmak için ortak
tutuldu. Gerçek kaydedilmiş Keyhole etiketi, bu monitor eşiği ve fiziksel rejim
sınırı birbirine eşit varsayılmadı. Hiçbir gerçek SPH/541-havuz deneyi tekrarlanmadı.

İlk aşamada dört model vardı: güçlü öğrenilmiş ARD GP; eski sabit varyanslı kompakt
ek bileşen; varyansı da yerelleştiren kapılı bileşen; aynı toplam ek önsel varyansa
sahip sabit-varyans kontrolü. Konumlar gizli bölgeden seçilmedi: kamuya açık
aday özelliklerinden sabit 32 merkez kullanıldı. Merkez/ölçek olasılıkları yalnız
satın alınmış gözlemlerin olabilirliğiyle güncellendi. Yarısı düzeltmesiz modele
ayrılmış önsel, bilinmeyen konumun maliyetini korudu. Gözlem iki kez sayılmadı.

    f = g + delta;  z = f + epsilon
    k_delta(x,x') = 0.36 a(x)a(x') W_r(x,x')

Burada W eski kompakt korelasyon, a yerel etkinlik fonksiyonudur. Kontrolün
k_delta'sı 0.36 mean_reference(a^2) W_r'dir. İkinci sürüm yalnız kapı içindeki
korelasyonu değiştirdi: delta(x)=a(x) beta, beta~N(0,0.36). Aynı marjinal varyans,
konum önseli, gözlemler ve öğrenilmiş arka plan parametreleri korundu; ona da
eşit toplam varyanslı bir kontrol eklendi. Böylece tutarlı bir yerel sapmayı
paylaşmanın faydası ayrı sınandı. Woodbury güncellemesi yoğun matris hesabıyla
doğrulandı. Bu, bilinen yerel baz/GP bileşenlerinin birleşimidir.

## Sonuçlar

Yerel yapı içeren 12 dünyada, iki yolun etkisi önce dünya içinde ortalandı:

| Dondurulmuş tarama ölçütü | V1 kapılı | V2 ortak katsayılı | Gerekli koşul |
|---|---:|---:|---:|
| Güçlü modele göre erken BA farkı | −0.00030 | +0.00173 | >=+0.005 |
| Eşit varyans kontrolüne göre BA farkı | −0.00049 | +0.00172 | >=+0.005 |
| Güçlü modele göre bölgesel hata farkı | +0.00726 | −0.00018 | <0 |
| Düzgün/gürültü/bozukluk kontrollerinde BA farkı | +0.00195 | +0.00100 | >−0.01 |
| Genişletme kararı | Geçmedi | Geçmedi | Bütün koşullar |

V2'nin yerel BA farkı için tanımlayıcı noktasal %95 aralık [+0.00040,+0.00322];
bölgesel hata farkı için [−0.00214,+0.00208]. Küçük olumlu BA farkı, önceden konan
pratik büyüklüğü karşılamıyor. Aralıklar aile içinde dünya örneklemesine dayalı
bootstrap'tır; çoklu karşılaştırma düzeltmesi veya bağımsız doğrulama değildir.
V2 aynı incelenmiş DEV dünyalarını kullandı. Son test dünyaları oluşturulmadı;
başarısız tarama ölçütü sonradan gevşetilmedi.

Tüm 32 dünyada V1'in erken BA farkı +0.00071, log-loss farkı −0.20501 oldu; pozitif
recall 0.00226 azalırken negatif recall 0.00368 arttı. V2'de erken BA +0.00115,
log loss −0.11718; pozitif/negatif recall farkları +0.00018/+0.00211. Dolayısıyla
log-loss iyileşmesi, kalibrasyonun tek başına düzeldiğini veya zor bölgenin
çözüldüğünü göstermiyor.
Küçük adalarda V2'nin pozitif recall'u 0.320; güçlü modelde 0.327. Bu zarar genel
ortalamada gizlenmedi. Bütün aile ve iki recall tabloları ALL_FAMILIES.md'dedir.

%90/%93/%95 hedefleri, tek öğrenicide iki ardışık bütçede doğrulandı; doğrulamanın
ikinci bütçesi ödendi. Güçlü model ve V2 için toplam ulaşım sayıları aynı:
26/64, 19/64, 8/64. Küçük adalarda hiçbir model %90'a ulaşmadı: 0/8 yol. Ulaşamayanlar
B24'te sansürlü kaldı; 25'lik sınırlı yük bir gerçek başarı zamanı değildir.
Ortak yollar üzerinde hedefe erken ulaşma, yeni edinim kuralının sorgu tasarrufu
değildir. SAME_TARGET_QUERY_COST.md bütün sayıları ve sansürlemeyi içerir.

Küçük ada yollarının 7/8'inde B24'e kadar pozitif latent bölgeden en az bir nokta
satın alınmıştı. Dolayısıyla sorun yalnız ilk adayı hiç bulamamak değil. Bölgeye
rastlandıktan sonraki öğrenme de zayıf kaldı. Geometrik ayak izi, latent pozitif
bölge ve gürültülü gözlemde pozitif olma ayrı sayıldı; bu üyeliklerin hiçbiri
seçiciye verilmedi. İlk isabet öncesindeki sorgular da maliyete dahildir.

## Mekanizma hakkında bağımsız hüküm

V1, önceki açıklamanın bir parçasını düzeltti: sabit-varyanslı kompakt alternatif
B24'te neredeyse bütünüyle bastırılırken, kapılı alternatifin yerel posterior
ağırlığı yerel ailelerde yaklaşık 0.35–0.53 kaldı. Buna rağmen sınıflandırmaların
yalnız yaklaşık %0.1–0.7'si değişti. Kapıyı etkinleştirmek yeterli olmadı.

İkinci sürüm, aynı yerel varyansı tek bir tutarlı sapmayı paylaşmak için kullandı.
Çok küçük bir BA artışı getirdi; güvenilir bölgesel hata veya hedefe ulaşma kazancı
getirmedi. Bu iki deney, “önsel varyansı yerelleştirince sınır sorunu çözülür”
açıklamasını bu model/bütçe altında desteklemiyor. Bütün yerel modellerin yararsız
olduğu sonucu çıkmaz. Paylaşılan arka plan parametrelerinin düzeltmesiz modele
göre öğrenilmesi, konum/baz kısıtları ve seyrek yerel gözlem hâlâ rakip açıklamalar.

Bir sonraki **ayırıcı deney önerisi**, ortak satın alınmış veride arka plan ve
yerel bileşenin birlikte öğrenilmesini, burada kullanılan düzeltmesiz-model
parametrelerine bağlama yaklaşımıyla karşılaştırmaktır. Aynı kapı/baz ve karar
kuralı korunmalı; ilk kez negatif sonuç görünce seçici değiştirilmemeli. Ancak
mevcut önceden belirlenmiş kapsam büyütme eşiği geçmediği için bu yeni dal
çalıştırılmadı. Bu paketin önerisi güçlü GP+margin'i korumaktır.

Monitor bozukluğu ile gerçek yerel sapma aynı gözlem yasasını veriyorsa, yalnız
o kanaldan fiziksel sınırı ayırmak olanaksızdır. Ayrı kalite/çıktı bilgisi veya
açık yapısal varsayım gerekir. Bu sınırlama analitik olarak gösterildi; gerçek
monitor verisinin bozuk olduğuna dair yeni bir iddia değildir.

## Güvenilirlik, maliyet ve teslim

64 sorgu yolu ve 64 V2 tahmin tekrarı hatasız tamamlandı. Bunlar 128 bağımsız deney
değildir. 3,968 üst düzey model isteği işlendi. V1'de 75,968 bileşen çözümü ve
142,609 optimizasyon değerlendirmesi; V2'de 576 yoğun çarpanlama ve 73,728 kapalı
form güncelleme yapıldı. 320 seçilmiş optimizasyon sonucu başarılı bildirdi;
iki ayrı başlangıç yakınsamadı ve kaydı korundu. Ayrılmış sınırlar aşılmadı.

V1 dört modeli birlikte değerlendiren toplam CPU süresi 106.94 s; V2'nin mevcut arka
planlar üzerindeki ek tahmin CPU'su 27.06 s. Tepe süreç belleği 124.0/88.2 MiB.
Yükleme, kuyruk ve bazı kayıt maliyetleri bu ölçüme dahil değil; tek model süreleri
ölçülmedi. Fiziksel simülasyon saati veya toplam saat tasarrufu uydurulmadı.

Bağımsız yoğun matris/kovaryans/güncelleme kontrolleri ve 512 gerçek ön-sorgu
moment tekrarı geçti. Tekrarlarda maksimum hata 1.82e−13; margin seçimlerinde
farklı indeks yok. Bütün bütçelerde saklanan olasılıklardan metrikler yeniden
hesaplandı. Şekiller ve gerçek sorgu yolu izdüşümleri görsel olarak incelendi.
İki boyutlu izdüşüm, dört boyutlu gerçek sınır olarak sunulmadı.

Otomatik devam önce gerçek iki zamanlanmış sohbet devralmasıyla, Windows yerel
okuma/yazma, durdurma, checkpoint, yineleme engeli ve benzetilmiş kota beklemesiyle
kanıtlandı. Kampanya 25 Ekim 20:05:49 UTC'de başladı; 27 Ekim 20:05:49 UTC son sınırı
hiç sıfırlanmadı. Kanıtlı fayda çıkmadığı için sırf 48 saati doldurmak üzere kuyruk
büyütülmedi. Kapanışın gerçek görev/otomasyon durumları AUTO_RESUME_RECEIPT.json
ve evidence/CLOSURE_CHECK.json'de kaydedilir.

Çalışan, bağımsız ask/tell kodu handoff/ altındadır; ücretli ID, kalite, maliyet,
ön-sorgu hash'i ve varyans türünü taşır. Eksik monitor da sorgu maliyetidir.
Kaydedilmiş Keyhole etiketinin kullanılmadığını açıkça bildirir. Opus'un ağacı,
ortamı, işlemleri ve otomasyonları değiştirilmedi. Yerel Git, tüm dünya tahminleri,
sorgu yolları, deneme defteri ve hash indeksli paket korunmuştur.

Yerel belirsizliği daha doğru sınırlamak işe yarayan bir olasılık
düzeltmesi olabilir. Bu deneyde zor bölgeyi daha az gözlemle öğrenen bir yöntem
haline gelmedi. Olumlu küçük farkı büyütmeden, güçlü temel modeli korumak en
savunulabilir karardır.

Kanıtların giriş noktası [RESULTS_INDEX.md](RESULTS_INDEX.md); yöntem ve kaynaklar
[MODEL_DESIGN_V1](docs/MODEL_DESIGN_V1.md), [DEV_V2_PROTOCOL](docs/DEV_V2_PROTOCOL.md)
ve [SOURCE_REVIEW](docs/SOURCE_REVIEW.md) içindedir. Yerelleştirilmiş bileşenler için
[Ba–Joseph (PENDING_ARCHIVE)](../../../docs/research/ARCHIVE_MANIFEST.md#pending-2fbb5734404262ff) ve
[Davis–Hans–Santner (PENDING_ARCHIVE)](../../../docs/research/ARCHIVE_MANIFEST.md#pending-3c6fe757134715bc) en yakın temel karşılaştırmalardır;
bu çalışma onların genel bileşen fikrini yeni teori olarak sahiplenmez.
