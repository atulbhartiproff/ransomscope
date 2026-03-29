"""Real-time event monitoring: file system + process creation.

Combines watchdog (file events) and psutil (process events).
Filters system directories, computes Shannon entropy for modified files.
"""

import logging
import threading
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from queue import Empty, Queue
from typing import Callable, Optional

import psutil
from watchdog.events import (
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileMovedEvent,
    FileSystemEventHandler,
)
from watchdog.observers import Observer

import config
from data_collection.collection.entropy import compute_shannon_entropy
from data_collection.collection.event_types import Event, EventType

logger = logging.getLogger(__name__)

# Max entropy history entries per file path (for delta calculation)
ENTROPY_HISTORY_SIZE = 5


def _is_excluded_path(path: str) -> bool:
    """Return True if path is under excluded system directory."""
    try:
        resolved = str(Path(path).resolve())
    except (OSError, RuntimeError):
        return True
    return any(resolved.startswith(prefix) for prefix in config.EXCLUDED_PREFIXES)


def _check_privilege_escalation(proc: psutil.Process) -> bool:
    """Return True if process shows privilege escalation indicators.

    Checks: running as root (euid=0), or real uid != effective uid.
    """
    try:
        uids = proc.uids()
        uid, euid = uids.real, uids.effective
        if euid == 0:
            return True
        if uid != euid and euid == 0:
            return True
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    return False


def _seed_entropy_history(entropy_cache: dict[str, deque[float]], file_path: str) -> Optional[float]:
    """Compute and cache baseline entropy for a file path.

    This allows the next FILE_MODIFY event to produce a meaningful entropy delta.
    """
    entropy = compute_shannon_entropy(file_path)
    if entropy is None:
        return None
    history = entropy_cache.setdefault(file_path, deque(maxlen=ENTROPY_HISTORY_SIZE))
    history.append(entropy)
    return entropy


class EventMonitor:
    """Collects file and process events in real time.

    Emits structured Event objects to a queue for downstream processing.
    """

    def __init__(
        self,
        watch_paths: list[str | Path],
        event_queue: Optional[Queue[Event]] = None,
        on_event: Optional[Callable[[Event], None]] = None,
    ) -> None:
        """Initialize monitor.

        Args:
            watch_paths: Directories to watch for file events.
            event_queue: If provided, events are put here.
            on_event: If provided, called for each event (alternative to queue).
        """
        self._watch_paths = [str(p) for p in watch_paths]
        self._event_queue = event_queue or Queue[Event]()
        self._on_event = on_event

        self._observer: Optional[Observer] = None
        self._entropy_cache: dict[str, deque[float]] = {}
        self._known_pids: set[int] = set()
        self._process_poll_interval = 0.5
        self._stop_event = threading.Event()
        self._process_thread: Optional[threading.Thread] = None

    def _emit(self, event: Event) -> None:
        """Emit event to queue and/or callback."""
        self._event_queue.put(event)
        if self._on_event:
            try:
                self._on_event(event)
            except Exception as e:
                logger.exception("on_event callback error: %s", e)

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    def _compute_entropy_and_delta(self, file_path: str) -> tuple[Optional[float], Optional[float]]:
        """Compute entropy and delta from previous value."""
        entropy = compute_shannon_entropy(file_path)
        if entropy is None:
            return None, None

        history = self._entropy_cache.setdefault(file_path, deque(maxlen=ENTROPY_HISTORY_SIZE))
        prev = history[-1] if history else None
        history.append(entropy)

        delta: Optional[float] = None
        if prev is not None:
            delta = round(entropy - prev, 2)

        return entropy, delta

    def _create_file_event(
        self,
        event_type: str,
        src_path: str,
        dest_path: Optional[str] = None,
        process_id: Optional[int] = None,
        parent_pid: Optional[int] = None,
    ) -> Event:
        """Build a file-related Event."""
        entropy: Optional[float] = None
        entropy_delta: Optional[float] = None
        pid = process_id
        ppid = parent_pid

        if event_type == EventType.FILE_MODIFY and not _is_excluded_path(src_path):
            entropy, entropy_delta = self._compute_entropy_and_delta(src_path)
        elif event_type in {EventType.FILE_CREATE, EventType.FILE_RENAME} and not _is_excluded_path(src_path):
            entropy = _seed_entropy_history(self._entropy_cache, src_path)

        if pid is None or ppid is None:
            try:
                proc = psutil.Process()
                pid = proc.pid
                ppid = proc.ppid()
            except Exception:
                pass

        privilege_flag = False
        if pid is not None:
            try:
                proc = psutil.Process(pid)
                privilege_flag = _check_privilege_escalation(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        return Event(
            timestamp=self._timestamp(),
            event_type=event_type,
            file_path=src_path,
            entropy=entropy,
            entropy_delta=entropy_delta,
            process_id=pid,
            parent_pid=ppid,
            privilege_flag=privilege_flag,
            metadata={"dest_path": dest_path} if dest_path else {},
        )

    def _create_process_event(self, proc: psutil.Process) -> Event:
        """Build a process creation Event."""
        privilege_flag = _check_privilege_escalation(proc)
        try:
            name = proc.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            name = None

        return Event(
            timestamp=self._timestamp(),
            event_type=EventType.PROCESS_CREATE,
            process_id=proc.pid,
            parent_pid=proc.ppid(),
            process_name=name,
            privilege_flag=privilege_flag,
        )

    def _on_file_event(self, event: object) -> None:
        """Handle watchdog file system event."""
        src_path: str
        dest_path: Optional[str] = None
        event_type: str

        if isinstance(event, FileCreatedEvent):
            event_type = EventType.FILE_CREATE
            src_path = event.src_path
        elif isinstance(event, FileModifiedEvent):
            event_type = EventType.FILE_MODIFY
            src_path = event.src_path
        elif isinstance(event, FileDeletedEvent):
            event_type = EventType.FILE_DELETE
            src_path = event.src_path
        elif isinstance(event, FileMovedEvent):
            event_type = EventType.FILE_RENAME
            src_path = event.src_path
            dest_path = event.dest_path
        else:
            return

        if _is_excluded_path(src_path):
            return
        if dest_path and _is_excluded_path(dest_path):
            return

        evt = self._create_file_event(event_type, src_path, dest_path)
        self._emit(evt)

    def _poll_processes(self) -> None:
        """Poll for new processes and emit PROCESS_CREATE events."""
        try:
            for proc in psutil.process_iter(["pid", "ppid", "name"]):
                pid = proc.info.get("pid")
                if pid is None:
                    continue
                if pid not in self._known_pids:
                    self._known_pids.add(pid)
                    evt = self._create_process_event(proc)
                    self._emit(evt)
        except Exception as e:
            logger.debug("Process poll error: %s", e)

    def _process_poll_loop(self) -> None:
        """Background thread for process polling."""
        while not self._stop_event.wait(timeout=self._process_poll_interval):
            self._poll_processes()

    def start(self) -> None:
        """Start file and process monitoring."""
        handler = _FileEventHandler(self._on_file_event)

        self._observer = Observer()
        for path in self._watch_paths:
            p = Path(path)
            if not p.exists():
                logger.warning("Watch path does not exist: %s", path)
                continue
            if not p.is_dir():
                logger.warning("Watch path is not a directory: %s", path)
                continue
            self._observer.schedule(handler, path, recursive=True)
            logger.info("Watching: %s", path)

        self._observer.start()

        # Seed known PIDs
        for proc in psutil.process_iter(["pid"]):
            pid = proc.info.get("pid")
            if pid is not None:
                self._known_pids.add(pid)

        self._stop_event.clear()
        self._process_thread = threading.Thread(target=self._process_poll_loop, daemon=True)
        self._process_thread.start()

        logger.info("EventMonitor started")

    def stop(self) -> None:
        """Stop monitoring."""
        self._stop_event.set()
        if self._process_thread:
            self._process_thread.join(timeout=2.0)
            self._process_thread = None
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=2.0)
            self._observer = None
        logger.info("EventMonitor stopped")

    def get_event(self, timeout: float = 0.1) -> Optional[Event]:
        """Get next event from queue. Returns None if empty or timeout."""
        try:
            return self._event_queue.get(timeout=timeout)
        except Empty:
            return None


class _FileEventHandler(FileSystemEventHandler):
    """Forward watchdog events to EventMonitor."""

    def __init__(self, callback: Callable[[object], None]) -> None:
        super().__init__()
        self._callback = callback

    def on_created(self, event: FileCreatedEvent) -> None:
        self._callback(event)

    def on_modified(self, event: FileModifiedEvent) -> None:
        self._callback(event)

    def on_deleted(self, event: FileDeletedEvent) -> None:
        self._callback(event)

    def on_moved(self, event: FileMovedEvent) -> None:
        self._callback(event)
