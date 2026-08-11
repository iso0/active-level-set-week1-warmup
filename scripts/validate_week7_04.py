"""Refresh Week 7 Phase 4 validations without rerunning scientific models."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for module_path in (ROOT, ROOT / "src"):
    module_path_text = str(module_path)
    if module_path_text not in sys.path:
        sys.path.insert(0, module_path_text)

from src.week7_phase4_new_data_feature_effects_depth_diagnostics import (  # noqa: E402
    refresh_validation,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    result = refresh_validation(smoke=args.smoke, notebook_required=True)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
