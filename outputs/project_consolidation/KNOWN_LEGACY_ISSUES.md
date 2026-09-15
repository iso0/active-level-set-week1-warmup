# Kaynakta mevcut Phase 2 manifest tutarsızlıkları

Birleştirme dosya kaybı denetimi ile tarihsel bilimsel manifest denetimi farklıdır.
`da913797d14b171bec55d3708f96aa87f09a4f94` Git ağacındaki iki rapor,
aynı ağacın `run_manifest.json` dosyasında kayıtlı SHA-256 değerleriyle uyuşmaz.
LF/CRLF satır sonu dönüşümü de bu iki dosya için eşleşme sağlamaz. Özgün Git
dosyaları korundu; eski manifest, uyumsuzluğu gizlemek amacıyla değiştirilmedi.

| Dosya | Eski manifestin beklediği SHA-256 | Mevcut kaynak SHA-256 |
|---|---|---|
| `outputs/week9_phase2_temporal_width_dynamics/SUPERVISOR_PHASE2_ONE_PAGE.md` | `3a1a21ccb75f64967add17385120b9436a9ec35ec2d7ae4a24dd31eeb802b013` | `0e76ee771ad78dd22ac78650e125b0efe3d81ce7a567e2fcb7d44d45c67728b3` |
| `outputs/week9_phase2_temporal_width_dynamics/claim_ledger.md` | `de592b0e1a886180873d4f4eac80070df45bb426b5ac7cd77acc1aeeca3d7f22` | `4aa396207675afad55728f085ee1669d00ac666c2177d55ed418aac46a87fcbf` |

Diğer altı metin/notebook dosyasında salt satır sonu değişikliği kayıtlı hashle
**birebir** eşleştiği için bu kayıtlı baytlar geri kuruldu; Git'teki sürümleri
`_history/` altında saklandı. Aritmetik, model veya rapor iddiası değiştirilmedi.

Phase 2'nin seçili testlerinde **13 geçti, 1 başarısız**. Başarısız test yukarıdaki
manifest eşleşmesidir. Notebooku yeniden çalıştıran test ve başka bir dalın sabit
Git ağacını varsayan tarihsel değişiklik testi bu birleştirme denetimine dahil edilmedi.
Yeni ana ortamda G3 Phase 1.20 ve ALSE veri/protokol/ölçüt testlerinin **62/62**'si geçti.
Toplam **75 geçti, 1 kaynakta mevcut manifest hatası**; bütün eski deneylerin veya
tüm tarihsel test takımının tekrar geçtiği iddia edilmiyor.

Bu istisna `validation.json` içinde de açıkça kaydedilir. Sonradan bilimsel manifest
bakımı yapılırsa eski kayıt tutulmalı ve yeni manifest ayrı bir sürüm olarak üretilmelidir.
