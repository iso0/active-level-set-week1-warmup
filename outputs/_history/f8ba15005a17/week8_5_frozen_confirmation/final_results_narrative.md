# Week 8.5 final results narrative

## Nereden nereye geldik?

Week 8'de Binary uncertainty-repulsion yönteminin Random'dan daha iyi göründüğünü bulmuştuk. Fakat Random için her outer split'te yalnız bir trajectory bulunuyordu. Bu nedenle “40 simulator call kazandık” ve “2.33 kat daha verimliyiz” gibi pratik iddiaların Random şansına ne kadar bağlı olduğunu bilmiyorduk. Ayrıca başarının uncertainty'den mi yoksa eklenen spatial repulsion'dan mı geldiği açık değildi.

Week 8.5 bu iki soruyu, yeni bir yöntem icat etmeden ve yeni simulator çalıştırmadan, dondurulmuş bir confirmation/ablation protokolüyle test etti.

## Ne test ettik ve neden?

- 20 tamamen yeni split repeat'i × 5 grouped outer fold = 100 matched outer run.
- Her run'da aynı test fold, training pool ve 16-query initial design.
- Her outer run için 30 bağımsız Random continuation: toplam 3000 Random trajectory.
- 100 uncertainty-only `binary_margin` trajectory.
- 100 historical h=0.15 `binary_uncertainty_repulsion` trajectory.
- Primary endpoint: Fold-B1-q20 accuracy AULC, total budget 16–80.
- Practical endpoint: Fold-B1-q20 accuracy >=0.80'in üç ardışık checkpoint boyunca korunması.
- Random crossing oranı yetersiz kaldığı için önceden yazılmış kurala göre bütün yöntemler önce 120'ye, sonra 160'a kadar uzatıldı.

B1 yalnız evaluation içindir. Acquisition hiçbir aşamada B1/B2/B3, test label'ı veya sorgulanmamış pool label'ı görmedi.

## Ana sonuç

Uncertainty-only sampling'in Random üzerindeki near-boundary performans üstünlüğü doğrulandı:

| Fold-B1-q20 AULC 16–80 | Değer |
|---|---:|
| Binary margin | 0.8135 |
| Random | 0.7762 |
| Fark | **+0.0373** |
| %95 iki taraflı interval | **+0.0301 ile +0.0444** |

20 repeat'in 20'sinde de fark Binary lehineydi. Yani sonuç tek bir şanslı split'ten gelmiyor.

Budget 40'ta:

- B1-q20 accuracy: **%81.7 vs %77.5**.
- B1-q30 accuracy: **%87.1 vs %82.9**.
- B1-q20 Keyhole recall: **%71.1 vs %60.7**.
- B1-q20 balanced accuracy: **%79.7 vs %74.1**.

Destek: `run_level_metrics.csv`, `repeat_level_metrics.csv`, `bootstrap_or_hierarchical_ci.csv`, Figure 01, Figure 02 ve Figure 04.

## Random'a göre gerçekten kaç query kazandık?

Basit ve censoring'siz tek bir sayı söyleyemiyoruz. Horizon 160'a rağmen:

- Margin trajectory'lerinin 91/100'ü persistent %80 hedefini geçti.
- Random trajectory'lerinin 2493/3000'i geçti: **%83.1**.
- Random'ın %16.9'u hâlâ right-censored.

Önceden tanımlanmış H=160 ile sınırlandırılmış karşılaştırmada:

- Margin ortalama burden: **39.1 query**.
- Random ortalama burden: **59.2 query**.
- Tahmini fark: **20.1 query daha az**.
- %95 iki taraflı interval: **12.5–26.7 query**.

Bu, “H=160 içinde sınırlandırılmış query burden estimate” olarak söylenebilir. “Gerçek crossing kesin olarak 20 query erken olur” şeklinde söylenemez; geçmeyen trajectory'lerin gerçek crossing zamanını bilmiyoruz.

Destek: `query_crossings.csv`, `query_savings_summary.csv`, `bootstrap_or_hierarchical_ci.csv` ve Figure 03.

## Kaç kat efficient diyebilir miyiz?

Restricted H=160 burden ratio point estimate'i **1.51x**; iki taraflı %95 interval **1.29x–1.76x**.

Fakat protokol clean multiplier için en az %95 finite Random crossing şartı koymuştu; elde edilen oran %83.1. Bu yüzden:

> “Restricted H=160 analizinde burden ratio 1.51x çıktı” diyebiliriz.

Şunu diyemeyiz:

> “Binary kesin/confirmed olarak 1.51 kat sample-efficient.”

Eski “2.33x” claimi kullanılmamalı.

## Repulsion gerçekten işe yarıyor mu?

Primary performans açısından anlamlı ek katkı doğrulanmadı:

- Full AULC 16–80 farkı: **+0.00183**.
- Low-budget AULC 16–40 farkı: **+0.00261**.
- İki endpoint'in ortak güvenli alt sınırı: **-0.000625**.

Repulsion biraz daha uzak noktalar seçiyor, fakat etki küçük:

- Low-budget mean nearest-distance artışı: **+0.00996**.
- Full-horizon artışı: **+0.00517**.
- Bunun karşılığında seçilen uncertainty biraz düşüyor.
- Low-budget seçimlerin %81.3'ünde margin ve repulsion zaten aynı noktayı seçiyor.
- Keyhole seçim oranı neredeyse aynı: %25.06 vs %25.02.

Yani repulsion'ın yaptığı şey gerçek ama küçük: bazen en belirsiz noktadan biraz vazgeçip daha uzak bir noktaya gidiyor. Bu küçük diversity artışı boundary accuracy'ye güçlü ve güvenilir bir improvement olarak dönmüyor.

Tez açısından bu kötü sonuç değil. Tam tersine, ana kazanımın karmaşık repulsion katmanından değil, uncertainty-directed sampling'den geldiğini gösteriyor. Primary yöntem olarak daha basit `binary_margin` savunulabilir; repulsion secondary heuristic veya future-work olarak kalabilir.

Destek: `repulsion_ablation_summary.csv`, `repulsion_mechanism_diagnostics.csv`, `repulsion_mechanism_summary.csv`, Figure 05 ve Figure 06.

## Ioan'a ne göstermeliyim?

### CURRENT STATUS

Offline finite-pool real-data confirmation completed on the frozen 405 simulations. Manual `has_keyhole` is the only ground truth. Fold-B1-q20 is an evaluation-only empirical near-boundary subset and never enters acquisition.

### BEST RESULT

With 20 new grouped repeat blocks and 30 matched Random continuations per outer split, uncertainty-only Binary GPC achieved Fold-B1-q20 accuracy AULC 0.8135 versus 0.7762 for Random. The difference is +0.0373, with a two-sided 95% interval of +0.0301 to +0.0444; all 20 repeat-block contrasts were positive.

### PRACTICAL QUERY-SAVING RESULT

For a persistent Fold-B1-q20 accuracy target of 0.80, the restricted H=160 estimate is 20.1 fewer queries, with a two-sided 95% interval of 12.5 to 26.7. However, only 83.1% of Random trajectories crossed by 160, so this remains a censor-aware qualified estimate rather than a clean uncensored saving claim. The restricted burden ratio is 1.51x, not a confirmed general multiplier.

### REPULSION ABLATION

Historical h=0.15 repulsion added only +0.00183 full-range AULC and +0.00261 low-budget AULC over margin. The simultaneous lower bound crosses zero. Repulsion slightly increases selected-point distance but does not provide a robust performance gain; uncertainty-only is the preferred primary method.

### LIMITATIONS

The study reuses the same 405 saved simulations, is not prospective, does not validate domain shift, and evaluates a manual-label-derived empirical boundary subset rather than a continuous physical boundary. Query-saving estimates remain right-censored.

### NEXT STEP

Use uncertainty-only Binary GPC as the primary thesis method, keep repulsion as a negative/near-null ablation, and reserve any clean real-world “X queries saved” claim for a prospective or larger-pool study with sufficiently complete target crossings.

## Asla söylenmemesi gereken claimler

- “40 simulator calls are guaranteed to be saved.”
- “Binary is confirmed 2.33x more sample-efficient.”
- “Binary is confirmed 1.51x more efficient” without saying it is an H=160 restricted, censored estimate.
- “Repulsion significantly improves boundary accuracy.”
- “B1-q20 is the true physical boundary” or “80% boundary certainty.”
- “20 repeats are 20 independent physical experiments.”
- “The method is validated for unseen datasets or a prospective simulator campaign.”
- “All random seeds are collision-free.” Random order seeds are unique, but 12 pairs of distinct fit keys share a reduced 32-bit seed.
