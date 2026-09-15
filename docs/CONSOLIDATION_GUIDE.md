# Birleştirme ve kullanım

2026-09-14 envanteri: kullanıcının belirttiği üç konum (üçüncünün gerçekte bulunan
`Masaüstü/thesis_works/thesis_1/` yolu), bunlarla ilişkili iki yerel tez kopyası ve
44 farklı erişilebilir Git dalı uç ağacı karşılaştırıldı. İlk okuma sırasında uzun
Windows yollarında oluşan 52 hata giderildi; son envanterde okuma hatası yoktur.
Ortamlar, derlenmiş Python önbellekleri ve Git iç dosyaları bilimsel dosya sayımına
dahil edilmedi. Bilimsel checkpoint/smoke dosyaları dahil edildi.

## Nerede çalışılmalı?

Bu deponun `main` dalında çalışın. Eski klasörler emniyet kopyası olarak tutulur;
onlarda yeni aşama başlatmayın. OneDrive kopyasındaki `.git` işaretçisi başka
klasörün çalışma ağacına aittir; bağımsız bir repo değildir. Eski dallar ve stash
kayıtları silinmedi. Yeni fazlar mevcut adları yeniden kullanmadan indekslenmelidir.

## Çalıştırma

Komutları depo kökünden çalıştırın. Mevcut bilimsel ortamla örnekler:

```powershell
python -m src.tools.validate_project_consolidation
python -m pytest src/tests/test_week9_phase1_20_m3_g3_margin_acquisition.py -q
python -m src.tools.resolve_thesis_path tests/test_week9_phase1_20_m3_g3_margin_acquisition.py
```

Yeni bir ortam için `python -m pip install -r requirements.txt` kullanın.
Eski `.venv` başka bağımlılıklar içerebilir; doğrulama raporu gerçekten kullanılan
Python ve paket sürümlerini belirtir. Tarihsel notebooklar saklanan yürütme çıktılarıyla
korunur; hepsini yeniden çalıştırmak pahalı deneyleri başlatabilir.
ALSE yardımcı paketi için `PYTHONPATH=src` veya `sys.path` içinde `src` gerekir.
`src/research/` altındaki eski R&D kodlarının ortam/yol kısıtları kendi README'sindedir.

## Sürüm ve dosya kanıtı

`outputs/project_consolidation/source_manifest.json.gz`, her dosyanın kaynak konumunu,
Git commit/ref bilgisini, ham Git blob kimliğini, SHA-256 değerini ve yeni yolunu içerir.
Aynı içerik tek kopyada tutulur; aynı adlı farklı içerik `_history/<blob>/` altında
korunur. Düzenleme gereken yapılandırma ve yardımcı kodların özgün halleri de korunur.
Yarım yükleme izleri `_incomplete_imports/` altındadır. Bunlar tamamlanmış çıktı sayılmaz.

Eski bilimsel manifestlerin hashleri değiştirilmedi. Eski bir yol taşınmışsa
`resolve_thesis_path` ile, gerektiğinde `--sha256 HASH` vererek özgün dosyaya erişin.
`file_catalog.csv.gz` tüm yeni yolları kolay filtrelenebilir biçimde verir.
`phase_catalog.json` aşama sayfalarının makine tarafından okunabilen karşılığıdır.

Bu envanter yalnızca erişilebilir kaynakların birleşimini kanıtlar. Kaynaklarda hiç
bulunmayan, başka disklerde kalan veya hiç yürütülmemiş bir deneyin varlığını kanıtlamaz.
Bu işlem sırasında uzun bilimsel deneyler yeniden koşturulmaz; dosya bütünlüğü,
yapı, notebook okunabilirliği ve seçili regresyon testleri ayrı raporlanır.

## Tarihsel testlerin kapsamı

Bazı eski testler yalnızca kendi aşamalarının eklendiği Git ağacını varsayar ve başka haftaların eklenmesini değişiklik sayar. Birleşik main üzerinde bu tarihsel Git-sınırı testleri otomatik olarak geçerli değildir. Model/veri testleri ile dosya bütünlüğü kontrolü ayrı raporlanır; eski Phase 2 manifest istisnası [açık hata kaydındadır](../outputs/project_consolidation/KNOWN_LEGACY_ISSUES.md).
