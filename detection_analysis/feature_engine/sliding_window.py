"""Sliding time-window feature engine.

Consumes low-level Events from the collection layer and produces
fixed-length feature vectors over sliding time windows.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Deque, List, Optional

from collections import deque

import config
from data_collection.collection.event_types import Event, EventType

logger = logging.getLogger(__name__)


# Feature names for explainability (order matches to_vector())
FEATURE_NAMES: tuple[str, ...] = (
    "file_mod_count",
    "rename_count",
    "delete_count",
    "entropy_avg_delta",
    "child_process_count",
    "privilege_flag",
    "user_dir_activity_ratio",
    "file_create_count",
)


@dataclass
class WindowFeatures:
    """Aggregated features for a single time window."""

    start_time: datetime
    end_time: datetime
    file_mod_count: int
    rename_count: int
    delete_count: int
    entropy_avg_delta: float
    child_process_count: int
    privilege_flag: bool
    user_dir_activity_ratio: float
    file_create_count: int

    def to_vector(self) -> list[float]:
        """Return numeric feature vector. Uses log1p for counts to reduce dynamic range."""
        import math

        def scale_count(c: int) -> float:
            return float(math.log1p(c))

        return [
            scale_count(self.file_mod_count),
            scale_count(self.rename_count),
            scale_count(self.delete_count),
            float(self.entropy_avg_delta),
            scale_count(self.child_process_count),
            1.0 if self.privilege_flag else 0.0,
            float(self.user_dir_activity_ratio),
            scale_count(self.file_create_count),
        ]


def _parse_timestamp(ts: str) -> datetime:
    """Parse ISO-like timestamp into timezone-aware datetime."""
    # We format timestamps as %Y-%m-%dT%H:%M:%S.%fZ in EventMonitor
    if ts.endswith("Z"):
        ts = ts[:-1]
        return datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(ts)


def _is_user_dir(path: Optional[str]) -> bool:
    """Return True if file path appears to be in a user home directory."""
    if not path:
        return False
    try:
        resolved = str(Path(path).resolve())
    except (OSError, RuntimeError):
        return False
    normalized = resolved.replace("\\", "/").lower()
    # Heuristic: Linux/macOS home dirs, WSL-mounted Windows users, native Windows users
    return (
        normalized.startswith("/home/")
        or normalized.startswith("/root/")
        or normalized.startswith("/users/")
        or "/users/" in normalized
        or normalized.startswith("c:/users/")
        or normalized.startswith("/mnt/c/users/")
    )


class SlidingWindowEngine:
    """Maintain sliding windows over incoming events and build sequences."""

    def __init__(
        self,
        window_size_sec: float = config.WINDOW_SIZE_SEC,
        window_overlap_sec: float = config.WINDOW_OVERLAP_SEC,
        sequence_length: int = config.SEQUENCE_LENGTH,
    ) -> None:
        self.window_size = timedelta(seconds=window_size_sec)
        stride = window_size_sec - window_overlap_sec
        if stride <= 0:
            raise ValueError("window_overlap_sec must be smaller than window_size_sec")
        self.window_stride = timedelta(seconds=stride)
        self.sequence_length = sequence_length

        self._current_start: Optional[datetime] = None
        self._events: Deque[Event] = deque()
        self._windows: Deque[WindowFeatures] = deque(maxlen=sequence_length)

    def _advance_window_until_contains(self, ts: datetime) -> None:
        """Advance current window so that ts is within [start, start+size)."""
        if self._current_start is None:
            self._current_start = ts
            return

        while ts >= self._current_start + self.window_size:
            # finalize window for [start, start+size)
            window_end = self._current_start + self.window_size
            window = self._compute_features(self._current_start, window_end)
            if window:
                self._windows.append(window)
            # slide forward
            self._current_start = self._current_start + self.window_stride
            # drop events that are entirely before new window
            while self._events and _parse_timestamp(self._events[0].timestamp) < self._current_start:
                self._events.popleft()

    def _compute_features(self, start: datetime, end: datetime) -> Optional[WindowFeatures]:
        """Compute features for events in [start, end)."""
        if not self._events:
            return None

        file_mod_count = 0
        rename_count = 0
        delete_count = 0
        file_create_count = 0
        entropy_deltas: List[float] = []
        child_process_count = 0
        privilege_flag = False
        user_dir_events = 0
        total_file_events = 0

        for evt in self._events:
            ts = _parse_timestamp(evt.timestamp)
            if ts < start or ts >= end:
                continue

            if evt.event_type in {
                EventType.FILE_CREATE,
                EventType.FILE_MODIFY,
                EventType.FILE_DELETE,
                EventType.FILE_RENAME,
            }:
                total_file_events += 1
                if _is_user_dir(evt.file_path):
                    user_dir_events += 1

            if evt.event_type == EventType.FILE_MODIFY:
                file_mod_count += 1
                if evt.entropy_delta is not None:
                    entropy_deltas.append(evt.entropy_delta)
            elif evt.event_type == EventType.FILE_RENAME:
                rename_count += 1
            elif evt.event_type == EventType.FILE_DELETE:
                delete_count += 1
            elif evt.event_type == EventType.FILE_CREATE:
                file_create_count += 1
            elif evt.event_type == EventType.PROCESS_CREATE:
                # treat every process creation as a child process event
                child_process_count += 1

            if evt.privilege_flag:
                privilege_flag = True

        if total_file_events == 0 and child_process_count == 0:
            # Skip completely empty/idle windows (file_create counts as activity)
            return None

        entropy_avg_delta = 0.0
        if entropy_deltas:
            entropy_avg_delta = float(sum(entropy_deltas) / len(entropy_deltas))

        user_dir_activity_ratio = 0.0
        if total_file_events > 0:
            user_dir_activity_ratio = float(user_dir_events) / float(total_file_events)

        return WindowFeatures(
            start_time=start,
            end_time=end,
            file_mod_count=file_mod_count,
            rename_count=rename_count,
            delete_count=delete_count,
            entropy_avg_delta=round(entropy_avg_delta, 3),
            child_process_count=child_process_count,
            privilege_flag=privilege_flag,
            user_dir_activity_ratio=round(user_dir_activity_ratio, 3),
            file_create_count=file_create_count,
        )

    def add_event(self, event: Event) -> Optional[WindowFeatures]:
        """Add a new low-level event.

        Returns:
            A completed WindowFeatures if a window just closed, else None.
        """
        ts = _parse_timestamp(event.timestamp)
        self._events.append(event)
        self._advance_window_until_contains(ts)
        # last computed window is at the end of _windows if any
        if self._windows:
            return self._windows[-1]
        return None

    def tick(self, now: Optional[datetime] = None) -> None:
        """Advance windows based on current time even if no new events arrive."""
        if self._current_start is None:
            return
        ts = now or datetime.now(timezone.utc)
        self._advance_window_until_contains(ts)

    def get_sequence(self) -> list[list[float]]:
        """Return last N windows as a sequence of vectors."""
        return [w.to_vector() for w in self._windows]

    def sequence_ready(self) -> bool:
        """True if we have enough windows for a full sequence."""
        return len(self._windows) >= self.sequence_length
