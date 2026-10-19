## Corrected endpoint tables (total revealed simulations, startup included)

first_qualifying = first recorded budget at the level; confirmation_spend = b + 4 for the first b with the level at b and b + 4 (the simulations actually spent to confirm). Mean (median; range) over the repeats that reached it; '–' = censored at the horizon.

### Region: BA ≥ 0.95

| model | acq | completed | first_qualifying | confirmation_spend | spend_per_repeat |
|---|---|---|---|---|---|
| M0 | MAXIMIN | 2/8 | 45.400 (median 50.0; 26–57) | 35.500 (median 35.5; 30–41) | –,–,–,41,–,30,–,– |
| M0 | RANDOM | 2/8 | 46.600 (median 49.0; 32–60) | 49.000 (median 49.0; 45–53) | 45,–,–,–,53,–,–,– |
| M0 | STRADDLE | 8/8 | 26.500 (median 25.5; 18–34) | 33.375 (median 34.0; 27–40) | 27,38,36,29,29,33,40,35 |
| M0 | TRUVAR | 8/8 | 27.625 (median 28.0; 16–37) | 34.000 (median 36.0; 20–42) | 37,37,33,20,27,35,42,41 |
| SHQ | MAXIMIN | 3/8 | 44.857 (median 44.0; 33–60) | 40.667 (median 37.0; 37–48) | –,–,–,37,–,37,–,48 |
| SHQ | RANDOM | 3/8 | 43.500 (median 42.5; 34–55) | 50.000 (median 53.0; 38–59) | 38,–,–,–,53,–,–,59 |
| SHQ | STRADDLE | 8/8 | 21.625 (median 22.0; 15–26) | 27.125 (median 26.5; 25–30) | 26,26,30,26,27,28,25,29 |
| SHQ | TRUVAR | 8/8 | 28.000 (median 28.0; 18–36) | 32.625 (median 32.5; 22–41) | 36,22,31,41,32,33,37,29 |

### Keyhole label: BA ≥ 0.93

| arm | completed | first_qualifying | confirmation_spend | spend_per_repeat |
|---|---|---|---|---|
| E1_MAXIMIN | 8/8 | 23.500 (median 23.0; 14–34) | 29.375 (median 27.0; 18–41) | 41,27,25,27,34,18,25,38 |
| E1_STRADDLE | 8/8 | 19.500 (median 17.5; 11–31) | 23.750 (median 21.5; 15–35) | 21,35,29,29,22,19,20,15 |
| G3_MARGIN | 8/8 | 23.500 (median 22.0; 19–30) | 28.250 (median 28.5; 23–34) | 30,23,27,31,25,34,24,32 |
| PHYSCF_ATS_MARGIN | 8/8 | 13.125 (median 13.0; 11–17) | 17.875 (median 17.5; 15–21) | 16,20,19,17,18,17,21,15 |
| PHYSCF_ATS_MAXIMIN | 8/8 | 15.750 (median 15.5; 11–22) | 23.750 (median 20.0; 16–51) | 19,21,51,25,18,16,21,19 |
| PHYSCF_A_MARGIN | 8/8 | 17.250 (median 18.5; 10–23) | 24.625 (median 25.5; 17–31) | 24,26,27,31,27,25,17,20 |
| PHYSMC_ATS_MARGIN | 8/8 | 14.875 (median 15.0; 11–20) | 19.875 (median 19.0; 15–27) | 16,16,27,19,15,19,24,23 |

Paired confirmation-spend differences (label; exploratory; only pairs where both arms confirmed):

| contrast | pairs_observed | mean_spend_difference | fewer/equal/more |
|---|---|---|---|
| PHYSCF_ATS_MARGIN − E1_STRADDLE | 8/8 | -5.875 | 6/1/1 |
| PHYSCF_ATS_MARGIN − G3_MARGIN | 8/8 | -10.375 | 8/0/0 |
| E1_STRADDLE − G3_MARGIN | 8/8 | -4.500 | 6/0/2 |
| PHYSMC_ATS_MARGIN − E1_STRADDLE | 8/8 | -3.875 | 5/1/2 |
| PHYSCF_A_MARGIN − E1_STRADDLE | 8/8 | 0.875 | 3/0/5 |

### Physical outputs: per-output and JOINT (all 8 at their levels at the same budget)

| model | acq | target | completed | first_qualifying | confirmation_spend | spend_per_repeat |
|---|---|---|---|---|---|---|
| M0 | MAXIMIN | JOINT | 0/8 | 73.333 (median 72.0; 68–80) | – | –,–,–,–,–,–,–,– |
| M0 | MAXIMIN | laser_T0_W | 8/8 | 23.500 (median 20.0; 20–36) | 27.500 (median 24.0; 24–40) | 24,24,28,24,32,24,24,40 |
| M0 | MAXIMIN | log_A_um | 8/8 | 13.000 (median 12.0; 8–16) | 17.000 (median 16.0; 12–20) | 16,20,16,16,20,20,12,16 |
| M0 | MAXIMIN | log_etot_T0_J | 8/8 | 21.000 (median 18.0; 16–44) | 25.000 (median 22.0; 20–48) | 24,48,20,24,24,20,20,20 |
| M0 | MAXIMIN | log_ke_T0_nJ | 8/8 | 8.000 (median 8.0; 8–8) | 13.000 (median 12.0; 12–20) | 12,20,12,12,12,12,12,12 |
| M0 | MAXIMIN | log_npart_T0 | 8/8 | 21.000 (median 18.0; 16–44) | 25.000 (median 22.0; 20–48) | 24,48,20,24,24,20,20,20 |
| M0 | MAXIMIN | tmax_T0_K | 8/8 | 12.000 (median 12.0; 8–16) | 16.000 (median 16.0; 12–20) | 16,16,20,16,12,12,16,20 |
| M0 | MAXIMIN | vmax_spike_logratio | 8/8 | 37.500 (median 36.0; 28–48) | 42.500 (median 44.0; 32–52) | 32,48,52,40,48,32,40,48 |
| M0 | MAXIMIN | vmax_spike_us | 0/8 | 73.333 (median 72.0; 68–80) | – | –,–,–,–,–,–,–,– |
| M0Q | MAXIMIN | JOINT | 0/8 | 68.000 (median 68.0; 68–68) | – | –,–,–,–,–,–,–,– |
| M0Q | MAXIMIN | laser_T0_W | 8/8 | 24.000 (median 22.0; 20–36) | 28.000 (median 26.0; 24–40) | 24,24,28,28,32,24,24,40 |
| M0Q | MAXIMIN | log_A_um | 8/8 | 13.000 (median 12.0; 8–16) | 17.000 (median 16.0; 12–20) | 16,20,16,16,20,20,12,16 |
| M0Q | MAXIMIN | log_etot_T0_J | 8/8 | 16.500 (median 16.0; 12–20) | 20.500 (median 20.0; 16–24) | 20,16,20,24,24,20,20,20 |
| M0Q | MAXIMIN | log_ke_T0_nJ | 8/8 | 8.000 (median 8.0; 8–8) | 12.000 (median 12.0; 12–12) | 12,12,12,12,12,12,12,12 |
| M0Q | MAXIMIN | log_npart_T0 | 8/8 | 17.000 (median 16.0; 16–20) | 21.000 (median 20.0; 20–24) | 20,20,20,24,24,20,20,20 |
| M0Q | MAXIMIN | tmax_T0_K | 8/8 | 12.000 (median 12.0; 8–16) | 16.000 (median 16.0; 12–20) | 16,16,20,16,12,12,16,20 |
| M0Q | MAXIMIN | vmax_spike_logratio | 8/8 | 36.500 (median 34.0; 28–48) | 43.000 (median 46.0; 32–52) | 32,48,52,44,48,32,40,48 |
| M0Q | MAXIMIN | vmax_spike_us | 0/8 | 68.000 (median 68.0; 68–68) | – | –,–,–,–,–,–,–,– |
| M0Q | MOIVR | JOINT | 5/8 | 58.667 (median 58.0; 44–76) | 60.000 (median 56.0; 48–80) | 56,–,–,80,48,–,48,68 |
| M0Q | MOIVR | laser_T0_W | 8/8 | 24.000 (median 24.0; 20–28) | 28.000 (median 28.0; 24–32) | 24,28,24,28,28,28,32,32 |
| M0Q | MOIVR | log_A_um | 8/8 | 12.500 (median 12.0; 8–16) | 16.500 (median 16.0; 12–20) | 16,20,16,16,20,16,12,16 |
| M0Q | MOIVR | log_etot_T0_J | 8/8 | 15.500 (median 16.0; 12–20) | 19.500 (median 20.0; 16–24) | 20,16,16,20,24,20,20,20 |
| M0Q | MOIVR | log_ke_T0_nJ | 8/8 | 8.000 (median 8.0; 8–8) | 12.000 (median 12.0; 12–12) | 12,12,12,12,12,12,12,12 |
| M0Q | MOIVR | log_npart_T0 | 8/8 | 16.500 (median 16.0; 12–20) | 20.500 (median 20.0; 16–24) | 24,20,16,20,24,20,20,20 |
| M0Q | MOIVR | tmax_T0_K | 8/8 | 11.000 (median 12.0; 8–12) | 15.000 (median 16.0; 12–16) | 16,16,16,16,12,12,16,16 |
| M0Q | MOIVR | vmax_spike_logratio | 8/8 | 27.000 (median 28.0; 20–36) | 31.000 (median 32.0; 24–40) | 32,32,28,28,32,24,40,32 |
| M0Q | MOIVR | vmax_spike_us | 5/8 | 58.667 (median 58.0; 44–76) | 60.000 (median 56.0; 48–80) | 56,–,–,80,48,–,48,68 |
| M0Q | RANDOM | JOINT | 2/8 | 68.800 (median 68.0; 64–80) | 70.000 (median 70.0; 68–72) | –,–,–,–,72,–,68,– |
| M0Q | RANDOM | laser_T0_W | 8/8 | 21.000 (median 20.0; 16–24) | 25.000 (median 24.0; 20–28) | 24,28,20,24,24,28,24,28 |
| M0Q | RANDOM | log_A_um | 8/8 | 14.000 (median 14.0; 8–20) | 18.000 (median 18.0; 12–24) | 16,24,20,16,20,20,12,16 |
| M0Q | RANDOM | log_etot_T0_J | 8/8 | 18.000 (median 16.0; 12–24) | 22.000 (median 20.0; 16–28) | 20,16,20,28,24,28,20,20 |
| M0Q | RANDOM | log_ke_T0_nJ | 8/8 | 8.000 (median 8.0; 8–8) | 13.500 (median 12.0; 12–24) | 12,12,12,12,24,12,12,12 |
| M0Q | RANDOM | log_npart_T0 | 8/8 | 19.500 (median 20.0; 16–24) | 24.500 (median 24.0; 20–28) | 24,20,28,28,24,28,20,24 |
| M0Q | RANDOM | tmax_T0_K | 8/8 | 11.000 (median 12.0; 8–12) | 15.000 (median 16.0; 12–16) | 16,16,16,16,12,12,16,16 |
| M0Q | RANDOM | vmax_spike_logratio | 8/8 | 41.500 (median 42.0; 32–52) | 48.000 (median 48.0; 40–56) | 48,52,56,40,56,48,44,40 |
| M0Q | RANDOM | vmax_spike_us | 2/8 | 64.000 (median 68.0; 40–80) | 70.000 (median 70.0; 68–72) | –,–,–,–,72,–,68,– |
| SHQ | MAXIMIN | JOINT | 0/8 | – | – | –,–,–,–,–,–,–,– |
| SHQ | MAXIMIN | laser_T0_W | 8/8 | 20.000 (median 20.0; 16–24) | 24.000 (median 24.0; 20–28) | 20,24,28,24,28,24,20,24 |
| SHQ | MAXIMIN | log_A_um | 8/8 | 11.500 (median 12.0; 8–12) | 15.500 (median 16.0; 12–16) | 16,16,16,12,16,16,16,16 |
| SHQ | MAXIMIN | log_etot_T0_J | 8/8 | 13.000 (median 12.0; 12–16) | 17.000 (median 16.0; 16–20) | 16,16,16,16,20,16,20,16 |
| SHQ | MAXIMIN | log_ke_T0_nJ | 8/8 | 9.500 (median 8.0; 8–12) | 13.500 (median 12.0; 12–16) | 12,12,16,12,16,12,16,12 |
| SHQ | MAXIMIN | log_npart_T0 | 8/8 | 13.000 (median 12.0; 12–16) | 17.000 (median 16.0; 16–20) | 16,16,16,16,20,16,20,16 |
| SHQ | MAXIMIN | tmax_T0_K | 8/8 | 12.000 (median 12.0; 12–12) | 16.000 (median 16.0; 16–16) | 16,16,16,16,16,16,16,16 |
| SHQ | MAXIMIN | vmax_spike_logratio | 8/8 | 31.500 (median 30.0; 20–48) | 35.500 (median 34.0; 24–52) | 24,44,44,24,28,28,40,52 |
| SHQ | MAXIMIN | vmax_spike_us | 0/8 | – | – | –,–,–,–,–,–,–,– |
| SHQ | MOIVR | JOINT | 1/8 | 56.000 (median 56.0; 56–56) | 60.000 (median 60.0; 60–60) | –,60,–,–,–,–,–,– |
| SHQ | MOIVR | laser_T0_W | 8/8 | 16.500 (median 16.0; 16–20) | 20.500 (median 20.0; 20–24) | 20,20,20,20,20,20,24,20 |
| SHQ | MOIVR | log_A_um | 8/8 | 11.500 (median 12.0; 8–12) | 15.500 (median 16.0; 12–16) | 16,16,16,12,16,16,16,16 |
| SHQ | MOIVR | log_etot_T0_J | 8/8 | 15.000 (median 16.0; 12–16) | 19.000 (median 20.0; 16–20) | 20,16,20,20,20,20,20,16 |
| SHQ | MOIVR | log_ke_T0_nJ | 8/8 | 9.500 (median 8.0; 8–12) | 13.500 (median 12.0; 12–16) | 12,12,16,12,16,12,16,12 |
| SHQ | MOIVR | log_npart_T0 | 8/8 | 15.500 (median 16.0; 12–16) | 19.500 (median 20.0; 16–20) | 20,16,20,20,20,20,20,20 |
| SHQ | MOIVR | tmax_T0_K | 8/8 | 12.000 (median 12.0; 12–12) | 16.000 (median 16.0; 16–16) | 16,16,16,16,16,16,16,16 |
| SHQ | MOIVR | vmax_spike_logratio | 8/8 | 26.000 (median 26.0; 20–32) | 30.000 (median 30.0; 24–36) | 28,32,24,28,32,28,32,36 |
| SHQ | MOIVR | vmax_spike_us | 1/8 | 56.000 (median 56.0; 56–56) | 60.000 (median 60.0; 60–60) | –,60,–,–,–,–,–,– |
| SHQ | RANDOM | JOINT | 7/8 | 62.000 (median 64.0; 36–72) | 65.714 (median 68.0; 40–76) | –,68,40,76,68,68,76,64 |
| SHQ | RANDOM | laser_T0_W | 8/8 | 20.000 (median 20.0; 16–24) | 24.000 (median 24.0; 20–28) | 24,24,28,24,24,20,20,28 |
| SHQ | RANDOM | log_A_um | 8/8 | 12.500 (median 12.0; 8–16) | 16.500 (median 16.0; 12–20) | 16,16,20,12,16,20,16,16 |
| SHQ | RANDOM | log_etot_T0_J | 8/8 | 15.500 (median 16.0; 12–16) | 19.500 (median 20.0; 16–20) | 20,16,20,20,20,20,20,20 |
| SHQ | RANDOM | log_ke_T0_nJ | 8/8 | 10.000 (median 8.0; 8–16) | 14.000 (median 12.0; 12–20) | 12,12,20,12,16,12,16,12 |
| SHQ | RANDOM | log_npart_T0 | 8/8 | 15.500 (median 16.0; 12–16) | 20.500 (median 20.0; 16–28) | 20,16,28,20,20,20,20,20 |
| SHQ | RANDOM | tmax_T0_K | 8/8 | 13.000 (median 12.0; 12–16) | 17.000 (median 16.0; 16–20) | 16,16,20,16,20,16,16,16 |
| SHQ | RANDOM | vmax_spike_logratio | 8/8 | 30.500 (median 28.0; 24–40) | 35.500 (median 32.0; 28–52) | 32,32,32,32,52,36,40,28 |
| SHQ | RANDOM | vmax_spike_us | 7/8 | 62.000 (median 64.0; 36–72) | 65.714 (median 68.0; 40–76) | –,68,40,76,68,68,76,64 |

### Joint 8-output completion, every arm (confirmation spend per repeat; NaN = censored at B80)

| model | acq | confirmed | censored | n | ever_qualified |
|---|---|---|---|---|---|
| M0 | MAXIMIN | 0 | 8 | 8 | 3/8 reached at least once |
| M0Q | MAXIMIN | 0 | 8 | 8 | 1/8 reached at least once |
| M0Q | MOIVR | 5 | 3 | 8 | 6/8 reached at least once |
| M0Q | RANDOM | 2 | 6 | 8 | 5/8 reached at least once |
| SHQ | MAXIMIN | 0 | 8 | 8 | 0/8 reached at least once |
| SHQ | MOIVR | 1 | 7 | 8 | 1/8 reached at least once |
| SHQ | RANDOM | 7 | 1 | 8 | 8/8 reached at least once |

| model | acq | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|
| M0Q | MOIVR | 56 | – | – | 80 | 48 | – | 48 | 68 |
| M0Q | RANDOM | – | – | – | – | 72 | – | 68 | – |
| SHQ | MOIVR | – | 60 | – | – | – | – | – | – |
| SHQ | RANDOM | – | 68 | 40 | 76 | 68 | 68 | 76 | 64 |

