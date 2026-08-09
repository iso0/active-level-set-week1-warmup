"""Refresh and enforce the Week 7 Phase 3 validation dashboard."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.week7_phase3_new_data_model_stability import refresh_validation


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    summary = refresh_validation(smoke=args.smoke)
    counts = summary["validation_status_counts"]
    print(f"Week 7 Phase 3 validation: {counts}")
    return 1 if counts.get("FAIL", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
