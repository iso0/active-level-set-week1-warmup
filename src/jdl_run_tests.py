"""Run the study's invariant and regression tests (queue entry point; `--threads 1` is accepted for the host count)."""
import os
import sys

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

import pytest

FILES = ["src/tests/test_joint_depth_label.py", "src/tests/test_jdl_v2.py", "src/tests/test_week20_c3.py", "src/tests/test_week20_development.py",
         "src/tests/test_week20_track1_ext.py", "src/tests/test_week19_dev_pilot.py", "src/tests/test_week19_pilot_review.py", "src/tests/test_week19_sequences.py"]

if __name__ == "__main__":
    sys.exit(pytest.main(["-q", "-p", "no:cacheprovider", *FILES]))
