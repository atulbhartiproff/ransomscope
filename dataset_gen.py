"""Synthetic dataset generation for RansomScope.

Event collection does NOT rely on real OS file monitoring.
Benign vs ransomware scenarios are strongly differentiated for better model learning.
"""

from __future__ import annotations

import argparse
import csv
import logging
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, List

from collection.event_types import Event, EventType
from processing.feature_engine import SlidingWindowEngine

logger = logging.getLogger(__name__)

SYNTHETIC_BASE = "/home/user/synthetic/workspace"


def _timestamp(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _make_event(
    ts: datetime,
    event_type: str,
    file_path: str | None = None,
    entropy: float | None = None,
    entropy_delta: float | None = None,
    process_id: int | None = 1234,
    parent_pid: int | None = 1200,
    privilege_flag: bool = False,
    metadata: dict | None = None,
) -> Event:
    return Event(
        timestamp=_timestamp(ts),
        event_type=event_type,
        file_path=file_path,
        entropy=entropy,
        entropy_delta=entropy_delta,
        process_id=process_id,
        parent_pid=parent_pid,
        privilege_flag=privilege_flag,
        metadata=metadata or {},
    )


def benign_scenario(base_ts: datetime, emit: Callable[[Event], None]) -> None:
    """Benign: many file_create, NO file_modify with high entropy, NO renames/deletes.

    - Bulk copy, unzip extraction
    - Low entropy, no extension changes
    - Distinct from ransomware
    """
    ts = base_ts
    base = f"{SYNTHETIC_BASE}/benign"
    src = f"{base}/src"
    dst = f"{base}/dst"
    zip_dst = f"{base}/unzipped"

    # Bulk copy: create source files (no entropy_delta - create only)
    for i in range(25):
        emit(_make_event(ts, EventType.FILE_CREATE, file_path=f"{src}/file_{i}.txt", entropy=4.5))
        ts += timedelta(seconds=0.7)

    for i in range(25):
        emit(_make_event(ts, EventType.FILE_CREATE, file_path=f"{dst}/file_{i}.txt", entropy=4.5))
        ts += timedelta(seconds=0.5)

    # Zip extraction: many small file creates
    for i in range(60):
        emit(_make_event(ts, EventType.FILE_CREATE, file_path=f"{zip_dst}/unz_{i}.txt", entropy=4.0))
        ts += timedelta(seconds=0.12)

    emit(_make_event(ts, EventType.PROCESS_CREATE))


def ransomware_scenario(base_ts: datetime, emit: Callable[[Event], None]) -> None:
    """Ransomware: file_modify with HIGH entropy_delta, burst of renames, deletes.

    - Create victims, then encrypt (modify + high entropy)
    - Rename to .enc, delete originals
    - Strong signal for model
    """
    ts = base_ts
    base = f"{SYNTHETIC_BASE}/ransom"
    work = f"{base}/target"

    # Create victim files
    for i in range(25):
        emit(_make_event(ts, EventType.FILE_CREATE, file_path=f"{work}/doc_{i}.txt", entropy=4.2))
        ts += timedelta(seconds=0.25)

    ts += timedelta(seconds=1.5)

    # Encrypt: file_modify with HIGH entropy delta (3-4), then rename, delete
    for i in range(25):
        # High entropy_delta = encryption
        entropy_delta = 3.5 + random.uniform(0, 0.5)
        emit(
            _make_event(
                ts,
                EventType.FILE_MODIFY,
                file_path=f"{work}/doc_{i}.txt",
                entropy=7.8,
                entropy_delta=entropy_delta,
            )
        )
        ts += timedelta(seconds=0.35)

        emit(
            _make_event(
                ts,
                EventType.FILE_RENAME,
                file_path=f"{work}/doc_{i}.txt",
                metadata={"dest_path": f"{work}/doc_{i}.enc"},
            )
        )
        ts += timedelta(seconds=0.15)

        if random.random() < 0.4:
            emit(_make_event(ts, EventType.FILE_DELETE, file_path=f"{work}/doc_{i}.enc"))
            ts += timedelta(seconds=0.08)

    for _ in range(6):
        emit(_make_event(ts, EventType.PROCESS_CREATE))
        ts += timedelta(seconds=0.15)


def collect_sequence(
    label: int,
    window_engine: SlidingWindowEngine,
    base_ts: datetime | None = None,
) -> list[float] | None:
    base_ts = base_ts or datetime.now(timezone.utc)

    def emit(evt: Event) -> None:
        window_engine.add_event(evt)

    if label == 0:
        benign_scenario(base_ts, emit)
    else:
        ransomware_scenario(base_ts, emit)

    if window_engine.sequence_ready():
        seq = window_engine.get_sequence()
        flat: list[float] = []
        for vec in seq:
            flat.extend(vec)
        return flat
    return None


def generate_dataset(args: argparse.Namespace) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    out_path = Path(args.output)

    rows: list[list[float]] = []
    base_ts = datetime.now(timezone.utc)

    for _ in range(args.benign_runs):
        engine = SlidingWindowEngine()
        flat = collect_sequence(label=0, window_engine=engine, base_ts=base_ts)
        base_ts += timedelta(seconds=60)
        if flat:
            rows.append([0.0] + flat)

    for _ in range(args.ransom_runs):
        engine = SlidingWindowEngine()
        flat = collect_sequence(label=1, window_engine=engine, base_ts=base_ts)
        base_ts += timedelta(seconds=60)
        if flat:
            rows.append([1.0] + flat)

    if not rows:
        logger.warning("No sequences collected; check window/sequence config.")
        return

    with out_path.open("w", newline="") as f:
        writer = csv.writer(f)
        seq_len = len(rows[0]) - 1
        header = ["label"] + [f"f{i}" for i in range(seq_len)]
        writer.writerow(header)
        writer.writerows(rows)

    pos = sum(1 for r in rows if r[0] >= 0.5)
    neg = len(rows) - pos
    logger.info("Wrote %d rows to %s (benign=%d, ransomware=%d)", len(rows), out_path, neg, pos)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic dataset for RansomScope")
    parser.add_argument("--output", type=str, default="ransomescope_dataset.csv")
    parser.add_argument("--benign-runs", type=int, default=15)
    parser.add_argument("--ransom-runs", type=int, default=15)
    return parser.parse_args()


if __name__ == "__main__":
    generate_dataset(parse_args())
