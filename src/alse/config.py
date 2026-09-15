"""Project paths. The only place that knows where things live on disk."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "alse"
RESULTS_DIR = PROJECT_ROOT / "outputs" / "alse" / "results"
OUTPUTS_DIR = PROJECT_ROOT / "outputs" / "alse" / "outputs"
DOCS_DIR = PROJECT_ROOT / "docs" / "alse"

POPULATION_CSV = DATA_DIR / "population.csv"

# The archived ChatGPT/Codex worktree (read-only). Used by reproduction tests
# and by experiments that replay frozen artifacts. Override with ALSE_ARCHIVE.
ARCHIVE_ROOT = Path(
    os.environ.get("ALSE_ARCHIVE", PROJECT_ROOT)
).resolve()
ARCHIVE_OUTPUTS = ARCHIVE_ROOT / "outputs"


def archive_available() -> bool:
    return (ARCHIVE_ROOT / "src").is_dir() and ARCHIVE_OUTPUTS.is_dir()


def archive_file(relpath: str, revision: str = "HEAD") -> Path:
    """Path to an archive file, materialised from the archive's git history if absent.

    The OneDrive copy of the archive is a working-tree snapshot that predates its
    branch tip (commit 2552078 added the completed Phase 1.18B outputs), so files
    tracked at HEAD can be missing on disk. Missing files are written once to
    ``outputs/_archive_cache/<revision>/<relpath>`` via ``git show`` and that copy
    is returned. Raises FileNotFoundError if the path exists nowhere.
    """
    import subprocess

    on_disk = ARCHIVE_ROOT / relpath
    if on_disk.is_file():
        return on_disk
    cached = OUTPUTS_DIR / "_archive_cache" / revision / relpath
    if cached.is_file():
        return cached
    result = subprocess.run(
        ["git", "-C", str(ARCHIVE_ROOT), "show", f"{revision}:{relpath.replace(os.sep, '/')}"],
        capture_output=True,
    )
    if result.returncode != 0:
        raise FileNotFoundError(f"{relpath} not in archive working tree nor at {revision}")
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(result.stdout)
    return cached


def output_dir(experiment: str) -> Path:
    """Create and return outputs/<experiment>/ (gitignored)."""
    path = OUTPUTS_DIR / experiment
    path.mkdir(parents=True, exist_ok=True)
    return path
