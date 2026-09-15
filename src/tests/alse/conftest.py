"""pytest configuration: project on sys.path, optional access to the archive."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from alse.config import ARCHIVE_ROOT, archive_available  # noqa: E402


def pytest_collection_modifyitems(config, items):
    if archive_available():
        return
    skip = pytest.mark.skip(reason=f"archive not found at {ARCHIVE_ROOT}")
    for item in items:
        if "archive" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def archive_root() -> Path:
    """Path to the archived worktree; tests using it must carry @pytest.mark.archive."""
    return ARCHIVE_ROOT


@pytest.fixture(scope="session")
def archive_src():
    """Make the archive's ``src`` package importable (``import src.<module>``).

    Only import modules without import-time side effects (avoid
    week6_phase2/phase4, week7_phase3/phase4).
    """
    root = str(ARCHIVE_ROOT)
    if root not in sys.path:
        sys.path.append(root)
    import src  # noqa: F401

    return src
