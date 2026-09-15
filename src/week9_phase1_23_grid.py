"""Week 9 Phase 1.23 — the frozen synthetic benchmark grid (fixed before any synthetic result).

Units.  h = u.(x - 1/2) with u = (1,1,1,1)/2, so SD(h) = sqrt(1/12) ~ 0.289 over U[0,1]^4; the
orthogonal coordinates have the same SD.  Displacement amplitudes are in units of SD(h); length-scales
are RFF length-scales in x units.  Prevalence is the reference-set share of the positive class.
"""
from __future__ import annotations

from src.week9_phase1_23_synthetic import Cell

N_FUNCTIONS = 30
CORE_POLICIES = ("random", "margin", "coverage_then_margin_B40", "early8__coverage_then_margin_B40",
                 "early8__margin", "global_unc_div_then_margin_B40")
SENSITIVITY_POLICIES = ("margin", "coverage_then_margin_B40", "early8__coverage_then_margin_B40", "early8__margin")
STRADDLE_CELLS = ("F7_exact", "S_a0.3_l0.5_d3", "S_a0.6_l0.2_d3", "F4_fold_a0.6", "F5_islands_k8", "F6_rot60")


def core_cells() -> list[Cell]:
    cells = [Cell("F7_exact", "physics_exact")]
    for a in (0.1, 0.3, 0.6):
        for length in (0.5, 0.2):
            for d in (1, 3):
                cells.append(Cell(f"S_a{a}_l{length}_d{d}", "shift", amplitude=a, length=length, het_dim=d))
    cells += [Cell("F4_fold_a0.3", "fold", amplitude=0.3, length=0.15),
              Cell("F4_fold_a0.6", "fold", amplitude=0.6, length=0.15),
              Cell("F5_islands_k3", "islands", islands=3, island_radius=0.2),
              Cell("F5_islands_k8", "islands", islands=8, island_radius=0.2),
              Cell("F6_rot30", "rotated", angle_deg=30.0),
              Cell("F6_rot60", "rotated", angle_deg=60.0),
              Cell("F6_rot90", "rotated", angle_deg=90.0)]
    return [Cell(**{**c.__dict__, "n_functions": N_FUNCTIONS}) for c in cells]


def sensitivity_cells() -> list[Cell]:
    return [Cell("SENS_prev0.5_exact", "physics_exact", prevalence=0.5, n_functions=N_FUNCTIONS),
            Cell("SENS_prev0.5_S_a0.3_l0.5_d3", "shift", amplitude=0.3, length=0.5, het_dim=3, prevalence=0.5,
                 n_functions=N_FUNCTIONS),
            Cell("SENS_pool1000_exact", "physics_exact", pool=1000, n_functions=N_FUNCTIONS),
            Cell("SENS_pool1000_S_a0.3_l0.5_d3", "shift", amplitude=0.3, length=0.5, het_dim=3, pool=1000,
                 n_functions=N_FUNCTIONS)]


CORE = core_cells()
SENSITIVITY = sensitivity_cells()
CELLS = CORE + SENSITIVITY


def policies_for(cell: Cell) -> tuple[str, ...]:
    if cell in SENSITIVITY:
        return SENSITIVITY_POLICIES
    return CORE_POLICIES + (("straddle",) if cell.cell_id in STRADDLE_CELLS else ())


def jobs() -> list[tuple[Cell, int, str]]:
    """Core cells first (function by function, all policies of a function together), then sensitivity."""
    return [(c, i, p) for c in CELLS for i in range(c.n_functions) for p in policies_for(c)]


def family_of(cell_id: str) -> str:
    if cell_id.startswith("F7") or cell_id.endswith("_exact"):
        return "F7 effectively 1D truth"
    if cell_id.startswith("S_a0.1") :
        return "F1 physics almost correct"
    if cell_id.startswith("S_a0.3") and "_l0.5_" in cell_id:
        return "F2 smooth orthogonal variation"
    if cell_id.startswith("S_"):
        return "F3 stronger / shorter-scale deformation"
    if cell_id.startswith("F4"):
        return "F4 non-monotone departures"
    if cell_id.startswith("F5"):
        return "F5 islands / exceptions"
    if cell_id.startswith("F6"):
        return "F6 misspecified physics"
    return "sensitivity"
