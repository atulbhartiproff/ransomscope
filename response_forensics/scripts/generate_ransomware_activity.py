#!/usr/bin/env python3
"""Generate ransomware-like filesystem activity for RansomScope testing.

WARNING: Use ONLY in a throwaway test directory. This modifies and renames files.
Run in a separate terminal while RansomScope is watching the target directory.
Example: python response_forensics/scripts/generate_ransomware_activity.py /tmp/ransomescope_test
"""

from __future__ import annotations

import argparse
import os
import secrets
import time
from pathlib import Path


def ransomware_simulation(root: Path) -> None:
    """Simulate ransomware: create files, encrypt (high-entropy rewrite), rename, optionally delete.

    Generates high volume of activity to fill 10 windows (~35s of events) in a single run.
    """
    victims_dir = root / "victims"
    victims_dir.mkdir(parents=True, exist_ok=True)

    # Create victim files (text content) - 80 files
    victims: list[Path] = []
    for i in range(80):
        f = victims_dir / f"doc_{i}.txt"
        f.write_text("example document content " * 50)
        victims.append(f)
        time.sleep(0.02)

    time.sleep(0.5)

    # Encrypt: rewrite with random bytes (high entropy), rename to .enc - 80 operations
    for f in victims:
        f.write_bytes(secrets.token_bytes(2048))  # High entropy
        enc = f.with_suffix(".enc")
        f.rename(enc)
        if secrets.token_bytes(1)[0] % 3 == 0:  # ~33% delete
            enc.unlink(missing_ok=True)
        time.sleep(0.02)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate ransomware-like activity for RansomScope testing"
    )
    parser.add_argument(
        "target_dir",
        type=str,
        help="Directory to generate activity in (MUST be a throwaway test dir)",
    )
    parser.add_argument("--delay", type=float, default=0.5, help="Initial delay (sec)")
    args = parser.parse_args()

    root = Path(args.target_dir)
    if not root.exists():
        root.mkdir(parents=True)
    if not root.is_dir():
        raise SystemExit(f"Target is not a directory: {root}")

    print(f"WARNING: Simulating ransomware activity in {root}")
    print("Press Ctrl+C within 2 seconds to abort...")
    time.sleep(min(2.0, args.delay + 1))

    ransomware_simulation(root)
    print("Done (ransomware-like activity).")


if __name__ == "__main__":
    main()
