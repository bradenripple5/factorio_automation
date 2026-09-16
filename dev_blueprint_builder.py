"""Run the Qt blueprint builder and automatically reload it after code edits."""

import subprocess
import sys
import time
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BUILDER = ROOT / "qt_blueprint_builder.py"
IGNORED_PARTS = {".git", ".venv", "venv", "__pycache__", "node_modules"}


def source_snapshot():
    """Return Python source modification times without requiring watchdog."""
    snapshot = {}
    for directory, subdirectories, filenames in os.walk(ROOT, topdown=True):
        # Prune ignored trees before os.walk tries to enter them. Filtering the
        # paths after rglob() is too late for broken junctions in node_modules.
        subdirectories[:] = [
            name for name in subdirectories if name not in IGNORED_PARTS
        ]
        directory = Path(directory)
        for filename in filenames:
            if filename.endswith(".py"):
                path = directory / filename
                snapshot[path] = path.stat().st_mtime_ns
    return snapshot


def launch_builder():
    return subprocess.Popen(
        [sys.executable, "-B", str(BUILDER), *sys.argv[1:]],
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
