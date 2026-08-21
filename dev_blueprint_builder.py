"""Run the Qt blueprint builder and automatically reload it after code edits."""

import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BUILDER = ROOT / "qt_blueprint_builder.py"
IGNORED_PARTS = {".git", ".venv", "venv", "__pycache__"}


def source_snapshot():
    """Return Python source modification times without requiring watchdog."""
    return {
        path: path.stat().st_mtime_ns
        for path in ROOT.rglob("*.py")
        if not IGNORED_PARTS.intersection(path.relative_to(ROOT).parts)
    }


def launch_builder():
    return subprocess.Popen(
        [sys.executable, "-B", str(BUILDER)],
        cwd=ROOT,
    )


def main():
    snapshot = source_snapshot()
    child = launch_builder()
    try:
        while child.poll() is None:
            time.sleep(0.5)
            updated = source_snapshot()
            if updated == snapshot:
                continue
            snapshot = updated
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
            # Briefly debounce editors that save a file through multiple writes.
            time.sleep(0.25)
            snapshot = source_snapshot()
            child = launch_builder()
    finally:
        if child.poll() is None:
            child.terminate()


if __name__ == "__main__":
    main()
