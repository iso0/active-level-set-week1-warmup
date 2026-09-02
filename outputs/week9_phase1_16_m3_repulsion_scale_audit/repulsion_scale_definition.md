# Repulsion scale definition

At each budget, distances are computed in the same outer-training-pool StandardScaler coordinates used by M3. For each unqueried candidate, `d_min` is its distance to the queried set; `s_B=median(d_min)` and `lambda_B=c*s_B`. The score is `A_margin * (1-exp(-d_min^2/(2*lambda_B^2)))`. The fixed predeclared multipliers are 0.25, 0.5, 1, 2, and 4. No held-out label enters the score.
