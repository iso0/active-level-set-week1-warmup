Round 2 research package, 4 October 2026

Main document: marginal_information_rounds_1_2.tex (standalone article, amsthm).
Contains the literature verdict table, mathematical proofs from rounds 1-2,
Week 15 item-by-item audit, and one finite-pool Laplace-GP test per new result.

Verification: verification_results.json records the checks and source hash.
verify_round2.py reproduces the numerical and exact rare-marginal calculations.
prove_three_point_budget.py reconstructs and exactly verifies the 36 rational
certificates proving the sharp N=3, B=2 margin ratio 4/5.
three_point_budget_certificates.json contains the explicit coefficients.
The same coefficients appear in the LaTeX proof and were matched exactly.

Dependencies of scratch checkers: Python, NumPy; SciPy for certificate discovery.
All certificate validity comparisons use exact fractions, not tolerances.

Scope: fixed-pool Hamming loss unless explicitly stated otherwise. No NSD
competitive guarantee is claimed. General sharp finite-N,B ratio remains open.
Priority is not established. The requested Astra-ultra audits hit a usage limit;
new extensions did not receive a completed independent second proof audit.

Repository was inspected read-only. No thesis experiment was rerun or modified.
The native LaTeX compiler twice returned: Unable to find standard directories
for platform. Source structural checks pass; PDF compilation/layout unverified.
