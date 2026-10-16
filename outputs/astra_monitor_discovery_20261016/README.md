# Astra — monitor discovery, 16 October 2026

**Selected prototype delivered; synthetic performance is NOT RUN.** The code reacts
to a surprising **paid scalar observation**, checks its neighborhood, spends at
most four local queries on that episode, and preserves global exploration. It
uses no future-outcome integration and does not restart BA_RISK.

The last user instruction is authoritative. The older V1/V2 and balanced-decision
packages remain preserved. This package is in the separate Codex workspace, not
the thesis checkout. No merge, push, real-data fit or physical simulation was run.

## Entry points

| File | Use |
|---|---|
| [discovery.py](discovery.py) | Direct `ask(Predictions)` / `tell(Observation)` selector; standard library only |
| [DESIGN.md](DESIGN.md) | Chosen method, mechanism, limitations, matched comparisons and endpoints |
| [DATA_CONTRACT.md](DATA_CONTRACT.md) | Paid-output boundary, posterior provenance, invalid channels, integration example |
| [MONITOR_MODEL_SUPPORT.md](MONITOR_MODEL_SUPPORT.md) | Concrete energy/temperature questions, six-basis input × time kernel, physical definitions |
| [OPUS_HANDOFF.md](OPUS_HANDOFF.md) | Execution reservation, command, independent checks, bounded integration request |
| [run_pilot.py](run_pilot.py) | Reproducible, resumable synthetic runner; fails closed without a coordinator reservation |
| [monitor_support.py](monitor_support.py) | Duration-weighted integration, support accounting and a positive-semidefinite time kernel |
| [FITFREE_CHECKS.json](FITFREE_CHECKS.json) | Actually executed software checks; zero model fits |
| [FROZEN_MANIFEST.json](FROZEN_MANIFEST.json) | Prospective seeds, worlds, controls, budgets, metrics and code hashes |

Use `python -B test_fitfree.py` for deterministic contract checks and
`python -B run_pilot.py --dry-run` to inspect the frozen plan. The numerical command
and the sole coordination record are specified in `OPUS_HANDOFF.md`.

## Actual work versus proposed computation

The deterministic tests exercise triggering, local confirmation using the
**before-anchor posterior**, expiry/quota, global exploration, calibration and
quality gates, rejection of unpaid fields, and physical-time arithmetic. They also
show an unavoidable failure: a spatially correlated monitor bias passing quality
checks can look exactly like a physical local deviation. These are software and
logic checks, **not a measured acquisition advantage**.

No new reservation for this job was present in the accessible Opus pool plan.
Therefore there are **zero synthetic GP fits and zero real-data fits by Astra**.
The numerical reference checks and all 34 trajectories are prepared for Opus.
The complete numerical envelope is one thread, at most 1,200 cumulative seconds,
578 controlled fit requests plus four independent reference fits, and 650 total
GP component solves. There is no automatic continuation or refinement ladder.

## Türkçe kısa açıklama

Yeni soru şu: Modelin beklemediği bir sonucu satın aldıktan sonra, yakınında benzer
davranış gösteren bir bölge var mı ve o bölgenin sınırını daha az sorguyla
öğrenebilir miyiz? Seçici önce yakın bir koşuyla kontrol ediyor; destek yoksa iki
yerel kontrolden sonra bırakıyor, destek varsa toplam en fazla dört yerel sorgu
kullanıyor. Her dört seçimden biri genel keşfe, en az biri genel sınır öğrenmeye
ayrılıyor. Bu, gelecekteki bütün sonuçları hesaplayan pahalı bir yöntem değil.

Çalıştırdığım şey küçük yazılım/sözleşme testleri. GP pilotunu çalıştırmadım:
koordinasyon kaydında bana ayrılmış pay yok. Dolayısıyla daha az simülasyon,
Keyhole başarısı veya kısa-K iyileşmesi iddia etmiyorum. Enerji ve sıcaklık
eğrilerini öğrenmek, kısa-K sonucundan bağımsız bir araştırma sorusu olarak kaldı.
Yeni fikir olarak şaşkınlık kullanımını sahiplenmiyorum; çok yakın yayımlanmış
yöntemler var. Buradaki katkı, sınır öğrenme hedefiyle sınırlı yerel tepkiyi,
kalite denetimini ve açık bir ücretli-veri sözleşmesini birlikte sınayan prototip.

**Tek önerilen hemen sonraki işlem:** Opus, tek koordinasyon kaydında bir iş
parçacığı ayırıp `OPUS_HANDOFF.md` içindeki sınırlı pilotu çalıştırsın. En ayırt edici
karşılaştırma, aynı genel keşif takviminde yerel tepkiyi açmak ve kapatmak.
