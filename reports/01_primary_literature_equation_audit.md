# Phase 1.5 primary-literature equation audit

## Verdict

The process-coordinate dependence

\[
h=P\,V^{-1/2}r_0^{-3/2}
\]

has genuine physical support, but **bare `h` is not a dimensionless Keyhole number**. It is the process-parameter numerator of a material-normalized heat-transfer scaling. In this repository `LS` is the Gaussian spot **radius** `r0`, not a diameter, so the dataset mapping is valid without a factor-of-two conversion.

## Equation trace

| Primary paper | Exact equation or result | Original variables and meaning | Radius or diameter? | Dataset mapping | Verdict |
|---|---|---|---|---|---|
| Gan et al., *Nature Communications* 12, 2379 (2021), Eq. 1 | `Ke = eta P / [(Tl-T0) pi rho Cp sqrt(alpha Vs r0^3)]` | absorbed power, liquidus-to-initial temperature rise, density, heat capacity, diffusivity, scan speed and laser radius | Explicitly `r0`, laser spot radius | `P -> P`, `Vs -> VX`, `r0 -> LS`, `T0 -> ST` | **PASS**, provided material factors are not omitted when calling the result `Ke` |
| Gan et al. (2021), Eqs. 2–4 | `e* = 0.4(Ke-1.4)` and `e* proportional to eta P Vs^(-1/2) r0^(-3/2)` | `e*=e/r0` is keyhole aspect ratio | Radius | The exponents behind `h` map exactly | **PASS** for exponent motivation; not a universal classifier threshold in this simulator |
| Cunningham et al., *Science* 363, 849–852 (2019) | Direct X-ray evidence of a power-density threshold and the sequence vaporization → surface depression → instability → deep keyhole | Experimental transition evidence, not the Gan `Ke` equation | Beam/spot scale is operational; this paper is not the source of the `(-1/2,-3/2)` law | Supports physical regime interpretation, not exact `h` coefficients | **QUALIFY** |
| Hann, Iammi & Folkes, MATADOR (2010) / *Lasers in Engineering* 22, 309–317 | Normalized enthalpy is built from absorbed power divided by melting enthalpy and `sqrt(pi D u sigma^3)` | absorptivity `A`, power `P`, volumetric melting enthalpy `hs`, diffusivity `D`, speed `u`, beam scale `sigma` | Spot-size convention must be read with each paper; it is not safe to substitute diameter for Gan's `r0` | Same process exponents as `h`; material normalization is required | **PASS** for the scaling family; **QUALIFY** numerical thresholds across conventions |
| King et al., *JMPT* 214, 2915–2925 (2014) | Applies normalized-enthalpy scaling to LPBF and observes conduction-to-keyhole behavior | `A`, `P`, `hs=rho c Tm` in that formulation, diffusivity, velocity and spot scale | Paper-specific beam convention; not a license to relabel repository LS | Supports LPBF relevance of the normalized-enthalpy family | **QUALIFY** because thresholds are material and convention dependent |

Primary links: [Gan et al. 2021](https://www.nature.com/articles/s41467-021-22704-0), [Cunningham et al. 2019](https://doi.org/10.1126/science.aav4687), [King et al. 2014](https://doi.org/10.1016/j.jmatprotec.2014.06.005), [Hann et al. article record](https://www.oldcitypublishing.com/journals/lie-home/lie-issue-contents/lie-volume-22-number-5-6-2011/lie-22-5-6-p-309-317/), [Hann et al. proceedings DOI](https://doi.org/10.1007/978-1-84996-432-6_63).

## Definitions and dimensions

For SI inputs `P [W]`, `V [m s^-1]`, and `r0 [m]`,

\[
[h]=\frac{W}{\sqrt{(m\,s^{-1})m^3}}=W\,s^{1/2}m^{-2}.
\]

Therefore the Antigravity claim that `h` itself is dimensionless is **REJECT**. Gan's full `Ke` is dimensionless because `eta`, `(Tl-T0)`, `rho Cp`, and `sqrt(alpha)` supply the missing material and thermal normalization. In Gan Eq. 1 the temperature is the **liquidus temperature** `Tl` relative to initial/substrate temperature `T0`; it is not vaporization temperature. Thermal conductivity enters indirectly through `alpha=k/(rho Cp)` if diffusivity is expanded. Absorptivity is explicit. Density and heat capacity are explicit.

The Phase 1.5 `h/(Tl-ST)` calculation is deliberately labelled an **ST sensitivity coordinate**, not `Ke`: it omits absorptivity, density, heat capacity, thermal diffusivity and the `pi` factor. A universal threshold across alloys is therefore **REJECT**.

For this sensitivity only, `Tl=1933 K` is taken from Gan et al. (2021) Supplementary Table 3 for Ti-6Al-4V. This fixed value is not fitted to labels.

## Claim checks

- **PASS:** `P^1 VX^-1/2 LS^-3/2` is a literature-backed process direction when `LS=r0`.
- **QUALIFY:** Agreement of fitted exponents with this point is consistency evidence, not discovery or proof of the law.
- **REJECT:** bare `h` is dimensionless.
- **REJECT:** Gan uses melting or vaporization temperature in Eq. 1. It specifically uses liquidus temperature `Tl` and substrate/initial temperature `T0`.
- **REJECT:** `d/r0 proportional to Ke^1.69` as a Gan result. Gan reports a near-linear keyhole-aspect-ratio relation, `e*=0.4(Ke-1.4)`, in Eq. 2; no 1.69 exponent should be attributed to that paper.
- **QUALIFY:** published normalized-enthalpy thresholds can be transported only after reconciling material constants, absorptivity and beam-radius conventions.

This audit supports using `log(h)` as a physics-inspired coordinate in a single-material simulator study. It does not support calling an empirical `log(h)` cutoff a universal physical boundary.
