"""Launch the Phase 1.21 repeat audit on every root in parallel (one process per root)."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOTS = {
    "thesis_1": r"C:\Users\ozgur\OneDrive\Masaüstü\thesis_works\thesis_1",
    "thesis_work_chatgpt": r"C:\Users\ozgur\OneDrive\Masaüstü\thesis_works\thesis_work_chatgpt",
    "lean_thesis": r"C:\Users\ozgur\OneDrive\Masaüstü\thesis_works\thesis",
    "documents_main_repo_worktree": r"C:\Users\ozgur\Documents\thesis",
    "documents_week4": r"C:\Users\ozgur\Documents\thesis-week4-chronology-restructure",
    "documents_week5": r"C:\Users\ozgur\Documents\thesis-week5-first-conduction-gp",
    "documents_week9_18b": r"C:\Users\ozgur\Documents\thesis-week9-phase1-18b-prospective-global-gpc-sur-benchmark",
    "documents_week9_19a": r"C:\Users\ozgur\Documents\thesis-week9-phase1-19a-integrity-posterior-monotonicity-audit",
    "gemini_antigravity": r"C:\Users\ozgur\.gemini\antigravity",
    "session_scratchpad": r"C:\Users\ozgur\AppData\Local\Temp\claude\C--Users-ozgur-OneDrive-Masa-st--thesis-works\5ec9a2a7-600a-4d1d-9a37-7cf7723cc0a7\scratchpad",
}


def main() -> None:
    tags = sys.argv[1:] or list(ROOTS)
    procs = []
    for tag in tags:
        code = (f"import sys; sys.argv=['a', {ROOTS[tag]!r}, {tag!r}]; "
                "from src.week9_phase1_21_repeat_audit import main; main()")
        procs.append((tag, subprocess.Popen([sys.executable, "-c", code], cwd=ROOT)))
    failed = [tag for tag, p in procs if p.wait() != 0]
    print("ALL_SCANS_DONE; failed:", failed, flush=True)


if __name__ == "__main__":
    main()
