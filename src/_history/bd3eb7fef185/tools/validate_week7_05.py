"""Refresh Week 7 Phase 5 validation and output-manifest hashes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.week7_phase5_keyhole_physical_proxy_analysis import refresh_validation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    result = refresh_validation(smoke=args.smoke, notebook_required=not args.smoke)
    print(json.dumps(result, indent=2))
