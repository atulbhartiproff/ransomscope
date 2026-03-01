"""SQLite-backed forensic timeline storage."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Optional

import config
from monitor.event_types import Event

logger = logging.getLogger(__name__)


class ForensicsLogger:
    """Append-only forensic timeline logger using SQLite."""

    def __init__(self, db_path: Path | str | None = None, incident_id: Optional[str] = None) -> None:
        self.db_path = Path(db_path) if db_path is not None else config.FORENSICS_DB_PATH
        self.incident_id = incident_id or "default"
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS timeline (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                process_id INTEGER,
                file_path TEXT,
                entropy REAL,
                risk_score REAL,
                decision TEXT
            );
            """
        )
        self._conn.commit()

    def log_event(
        self,
        event: Event,
        risk_score: Optional[float] = None,
        decision: Optional[str] = None,
    ) -> None:
        """Insert a new event row into the forensic timeline."""
        self._conn.execute(
            """
            INSERT INTO timeline (
                incident_id, timestamp, event_type, process_id, file_path,
                entropy, risk_score, decision
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                self.incident_id,
                event.timestamp,
                event.event_type,
                event.process_id,
                event.file_path,
                event.entropy,
                risk_score,
                decision,
            ),
        )
        self._conn.commit()

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass
