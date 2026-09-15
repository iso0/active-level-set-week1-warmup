# Week 8 final — sade Türkçe tez özeti

Bu Week 8 çalışmasında **yeni simülasyon çalıştırılmadı**. Bütün sayılar, daha önce kaydedilmiş 405 simülasyonun sonuçları sorgulanana kadar öğreniciden gizlenerek yapılan offline/retrospektif değerlendirmeden gelir.

## 1. Tez aslında ne yapmaya çalışıyor?

Amaç, pahalı eriyik-havuzu simülasyonlarını mümkün olduğunca az çağırarak manuel Keyhole/non-Keyhole geçiş bölgesini öğrenmek. Öğrenici her adımda hangi simülasyonun sonucunu görmesi gerektiğini seçiyor; başarısı, daha önce görmediği held-out simülasyonlarda ölçülüyor.

## 2. Final model nedir?

Final model bir **Binary Gaussian Process Classifier (GPC)**. Girdiler `P`, `VX`, `LS`, `ST`; çıktı `P(Keyhole)`. `ST`, **substrate temperature** demektir, katman kalınlığı değildir.

## 3. Final acquisition function nedir?

**binary_uncertainty_repulsion**. Model, Keyhole olasılığının 0.5'e yakın olduğu belirsiz noktaları tercih eder; repulsion terimi aynı yere yığılmayı azaltır.

## 4. q20/q30 nedir?

B1-q20, manuel etiketi zıt olan örneğe girdi uzayında en yakın yaklaşık %20'lik test kümesidir; q30 daha geniş yaklaşık %30'luk bölgedir. Bunlar ampirik sınır tanılarıdır, gerçek sürekli fiziksel sınır değildir.

## 5. İstenen doğruluk için kaç simülasyon gerekiyor?

Hücreler **başarılı koşulardaki medyan ilk sorgu (başarı/20)** biçimindedir. “Başarısız” koşular 81 diye uydurulmadı.

| Bölge | Hedef | Binary | Random | Max-Depth |
| --- | --- | --- | --- | --- |
| q20 | 70% | 12 (20/20) | 12 (20/20) | 13 (20/20) |
| q20 | 75% | 13 (19/20) | 17 (19/20) | 15 (20/20) |
| q20 | 80% | 16 (18/20) | 30 (14/20) | 15 (15/20) |
| q20 | 85% | 21 (15/20) | 29 (8/20) | 18.5 (12/20) |
| q20 | 90% | 27.5 (8/20) | 28 (3/20) | 22 (5/20) |
| q30 | 70% | 12 (20/20) | 12 (20/20) | 12 (20/20) |
| q30 | 75% | 12 (20/20) | 12 (20/20) | 13 (20/20) |
| q30 | 80% | 14.5 (20/20) | 16 (20/20) | 14.5 (20/20) |
| q30 | 85% | 16 (18/20) | 31 (14/20) | 17 (15/20) |
| q30 | 90% | 23 (14/20) | 44.5 (8/20) | 19 (11/20) |

## 6. Binary, Random'a göre kaç çağrı tasarruf ediyor?

| Binary bütçe | Binary q20 | Random-eşdeğer | Tasarruf | Çarpan |
| --- | --- | --- | --- | --- |
| 20 | 77.6% | 34.00 | 14.00 | 1.70x |
| 30 | 79.7% | 70.00 | 40.00 | 2.33x |
| 40 | 81.2% | >80 | >40 | >2.00x |
| 50 | 82.9% | >80 | >30 | >1.60x |
| 60 | 83.5% | >80 | >20 | >1.33x |

En güçlü tam sayısal sonuç: Binary'nin 30 sorguda ulaştığı **79.7% B1-q20 doğruluğunu** Random yaklaşık **70 sorguda** yakalıyor; yaklaşık **40 simülasyon çağrısı** tasarruf ediliyor. Binary'nin 40 sorgudaki seviyesi Random tarafından 80'e kadar yakalanmadığı için burada sonuç **>40** tasarruf alt sınırıdır.

## 7. 20/30/40/60/80 bütçelerinde sınır-bölgesi doğruluğu nedir?

| Bütçe | Binary q20 | Random q20 | Binary q30 | Random q30 |
| --- | --- | --- | --- | --- |
| 20 | 77.6% | 72.9% | 83.2% | 79.4% |
| 30 | 79.7% | 77.4% | 85.4% | 83.0% |
| 40 | 81.2% | 76.8% | 86.2% | 83.2% |
| 60 | 83.5% | 78.5% | 88.6% | 84.2% |
| 80 | 82.4% | 78.8% | 87.8% | 84.8% |

## 8. “%80 boundary certainty” diyebilir miyiz?

Hayır. “Bütçe 40'ta ortalama B1-q20 held-out doğruluğu 81.2%” diyebiliriz. Ayrıca saklanmış olasılıklar sayesinde “bütçe 40'ta B1-q20 tahminlerinin 48.2%'i en az %80 **model güveni** taşıyor” diyebiliriz. Fakat bu, fiziksel sınırın konumunu %80 kesinlikle bildiğimiz anlamına gelmez.

## 9. Max-Depth hâlâ ne katıyor?

Max-Depth global balanced accuracy AULC'sinde daha güçlü: **0.9432**, Binary **0.9171**. Bu nedenle fiziksel yorum ve genel sınıflandırma için değerli bir ikincil karşılaştırıcıdır; final sınır acquisition'ı değildir.

## 10. Hybrid neden başarısız oldu?

Gate ve eşit-rank Fusion, sorgulanan Max-Depth bilgisini kullandı ama Binary'yi B1/B2/B3 hiyerarşisinde sağlam biçimde geçemedi ve ek hesap maliyeti getirdi. Sonuç yalnızca test edilen iki sabit Hybrid için geçerlidir.

## 11. Final tez sonucu nedir?

Final öneri **Binary GPC + uncertainty-repulsion**. Bu yöntem, aynı 20 eşlenmiş offline koşuda Random'dan daha iyi ampirik sınır doğruluğu ve somut sorgu tasarrufu sağlıyor. Max-Depth ikincil fiziksel karşılaştırıcıdır. Sonuç canlı/prospektif doğrulama değil; aynı 405 kayıtlı simülasyon üzerinde tekrarlı held-out değerlendirmedir. Evrensel G3/Max-Depth eşiği, nedensellik, gerçek sürekli sınırın kesin konumu veya her problemde evrensel üstünlük iddia edilemez.
