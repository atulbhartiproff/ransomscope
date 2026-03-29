#!/usr/bin/env python3
"""Generate benign filesystem activity for RansomScope testing.

Run this in a separate terminal while RansomScope is watching the target directory.
Example: python response_forensics/scripts/generate_benign_activity.py /tmp/ransomescope_test
"""

from __future__ import annotations

import argparse
import shutil
import string
import time
from pathlib import Path

import random


def write_text_file(path: Path, size_kb: int = 4) -> None:
    """Write a text-like file with low entropy."""
    chars = string.ascii_letters + string.digits + " \n"
    n = size_kb * 1024
    data = "".join(random.choice(chars) for _ in range(n))
    path.write_text(data)


def benign_bulk_copy(root: Path) -> None:
    """Simulate bulk copy: create source files, then copy to destination."""
    src = root / "src"
    dst = root / "dst"
    src.mkdir(parents=True, exist_ok=True)
    dst.mkdir(parents=True, exist_ok=True)

    for i in range(50):
        f = src / f"file_{i}.txt"
        write_text_file(f, size_kb=2)
        time.sleep(0.02)

    for i in range(50):
        shutil.copy2(src / f"file_{i}.txt", dst / f"file_{i}.txt")
        time.sleep(0.02)


def benign_unzip(root: Path) -> None:
    """Simulate zip extraction: create many small files in a directory."""
    unzipped = root / "unzipped"
    unzipped.mkdir(exist_ok=True)
    for i in range(120):
        write_text_file(unzipped / f"unz_{i}.txt", size_kb=1)
        time.sleep(0.01)


def benign_git_clone(root: Path) -> None:
    """Simulate git clone: create nested dir structure and many small files."""
    repo = root / "repo"
    repo.mkdir(exist_ok=True)
    for d in ["src", "tests", "docs"]:
        (repo / d).mkdir(exist_ok=True)
    files = [
        "README.md", "setup.py", "main.py",
        "src/__init__.py", "src/utils.py", "src/helpers.py",
        "tests/test_main.py", "tests/test_utils.py", "docs/index.md",
    ]
    for f in files:
        p = repo / f
        p.parent.mkdir(parents=True, exist_ok=True)
        write_text_file(p, size_kb=1)
        time.sleep(0.01)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate benign filesystem activity for RansomScope testing"
    )
    parser.add_argument(
        "target_dir",
        type=str,
        help="Directory to generate activity in (must be watched by RansomScope)",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        choices=["all", "copy", "unzip", "git"],
        default="all",
        help="Which scenario to run (default: all)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Initial delay in seconds before starting (default: 0.5)",
    )
    args = parser.parse_args()

    root = Path(args.target_dir)
    if not root.exists():
        root.mkdir(parents=True)
    if not root.is_dir():
        raise SystemExit(f"Target is not a directory: {root}")

    time.sleep(args.delay)

    if args.scenario in ("all", "copy"):
        print("Running: bulk copy")
        benign_bulk_copy(root)
    if args.scenario in ("all", "unzip"):
        print("Running: unzip simulation")
        benign_unzip(root)
    if args.scenario in ("all", "git"):
        print("Running: git clone simulation")
        benign_git_clone(root)

    print("Done.")


if __name__ == "__main__":
    main()
