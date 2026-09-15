# Week 8 Faz 1 — sade Türkçe özet

## Bu analiz neyi ölçüyor?

**Bütçe**, aktif öğrenicinin sonucunu görmesine izin verilen toplam simülasyon sayısıdır. Burada yeni simülasyon çalıştırılmadı; daha önce kaydedilmiş simülasyonlar, sorgulanana kadar öğreniciden gizlendi.

**B1-q20**, 405 örnek içindeki, zıt manuel etikete standartlaştırılmış girdi uzayında en yakın olan yaklaşık yüzde 20'lik test bölgesidir. “q20 doğruluğu %80” demek, bu seçilmiş held-out sınır-benzeri örneklerin yaklaşık %80'inin Keyhole/non-Keyhole olarak doğru sınıflandırılması demektir. Sürekli fiziksel sınırın konumunu “%80 kesinlikle biliyoruz” demek değildir.

## Bütçeye göre somut B1 doğrulukları

| Bütçe | Binary q20 | Random q20 | Binary q30 | Random q30 |
| --- | --- | --- | --- | --- |
| 20 | 77.6% | 72.9% | 83.2% | 79.4% |
| 30 | 79.7% | 77.4% | 85.4% | 83.0% |
| 40 | 81.2% | 76.8% | 86.2% | 83.2% |
| 50 | 82.9% | 77.4% | 88.0% | 83.2% |
| 60 | 83.5% | 78.5% | 88.6% | 84.2% |
| 70 | 82.9% | 79.7% | 88.0% | 85.2% |
| 80 | 82.4% | 78.8% | 87.8% | 84.8% |

## İstenen doğruluğa kaç sorguda ulaşılıyor?

Hücre biçimi **başarılı koşulardaki medyan sorgu (başarı/20)** şeklindedir. Başarısız koşular medyandan silinmedi; başarı sayısında açıkça görünür.

| Hedef | Binary q20 | Random q20 | Binary q30 | Random q30 |
| --- | --- | --- | --- | --- |
| 70% | 12 (20/20) | 12 (20/20) | 12 (20/20) | 12 (20/20) |
| 75% | 13 (19/20) | 17 (19/20) | 12 (20/20) | 12 (20/20) |
| 80% | 16 (18/20) | 30 (14/20) | 14.5 (20/20) | 16 (20/20) |
| 85% | 21 (15/20) | 29 (8/20) | 16 (18/20) | 31 (14/20) |
| 90% | 27.5 (8/20) | 28 (3/20) | 23 (14/20) | 44.5 (8/20) |

## En güçlü sorgu tasarrufu sonucu

Binary, 30 sorguda ortalama **79.7% B1-q20 doğruluğuna** ulaşıyor. Random'ın gözlenen ortalama eğrisi aynı seviyeyi ilk kez yaklaşık **70 sorguda** yakalıyor. Bu, bu performans seviyesi için yaklaşık **40 simülasyon çağrısı tasarrufu** ve **2.33x sorgu eşdeğeri** demektir. Binary'nin 40 sorgudaki 81.2% seviyesi ise Random tarafından 80'e kadar yakalanmıyor; burada yalnızca **>40** tasarruf alt sınırı söylenebilir, 80'in ötesine sayı uydurulamaz.

## Model güveni ayrı bir kavramdır

Saklanmış GPC olasılıkları bulunduğu için gerçek bir model-güveni tanısı yapılabildi. Bütçe 40'ta B1-q20 tahminlerinin **48.2%**'i en az %80 model güvenine sahip; bu yüksek-güven grubunun **93.3%**'i doğru. Bu, “fiziksel sınır %80 kesin” anlamına gelmez. Olasılıklar ayrıca sonradan kalibre edilmediği ve aynı 405 simülasyon tekrarlı katlarda kullanıldığı için kalibrasyon sonuçları tanısaldır.

## Random karşılaştırması nasıl yapıldı?

Her iki yöntem aynı 20 dış koşuyu, aynı test katlarını, aynı aday havuzlarını, aynı başlangıç permütasyonlarını ve aynı toplam bütçeyi kullanır. Random-eşdeğer bütçe yalnızca 16–80 arasındaki gözlenen Random ortalama eğrisinin komşu noktaları arasında doğrusal enterpolasyonla hesaplandı; 80 ötesine ekstrapolasyon yapılmadı.

## Keyhole keşfi neden ikincil?

Bütçe 30'da Binary ortalama **12.20**, Random **5.45** Keyhole örneği buluyor. Daha çok pozitif örnek bulmak faydalı olabilir, fakat bu tek başına sınırı daha iyi yerelleştirmek değildir; bu nedenle ana sonuç q20/q30 held-out doğruluğudur.
