"""Week 18 D1 — max-depth extraction follows the Week 7 definition (valid rows only; depth = max(0, −z_min))."""
import numpy as np

from src.week18_new_depth import max_depth_um


def test_max_depth_uses_valid_rows_and_week7_depth(tmp_path):
    rows = np.array([
        [0.0, 1e-4, 0.0, 1e-4, -5e-5, 1e-5],       # depth 50 µm
        [0.0, 1e-4, 0.0, 1e-4, -1.2e-4, 1e-5],     # depth 120 µm  (maximum)
        [3.402823e+38, -3.402823e+38, 3.402823e+38, -3.402823e+38, 3.402823e+38, -3.402823e+38],  # no-melt sentinel
        [0.0, 1e-4, 0.0, 1e-4, 2e-5, 3e-5],        # above the substrate: depth 0
    ])
    b = tmp_path / "position-bounds_melt.dat"; np.savetxt(b, rows, delimiter=",")
    t = tmp_path / "time.dat"; np.savetxt(t, np.arange(4) * 1e-6)
    r = max_depth_um(b, t)
    assert r["valid_rows"] == 3 and r["malformed_rows"] == 0
    assert abs(r["max_depth_um"] - 120.0) < 1e-9 and r["max_depth_row_index"] == 1
    assert r["time_increasing"] and r["time_rows_match"]
