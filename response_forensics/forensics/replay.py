"""CLI-friendly incident replay."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import config

logger = logging.getLogger(__name__)


def replay_incident(incident_id: str, db_path: Path | str | None = None) -> None:
    """Print forensic timeline for given incident id in chronological order."""
    path = Path(db_path) if db_path is not None else config.FORENSICS_DB_PATH
    if not path.exists():
        raise SystemExit(f"Forensics database not found at {path}")

    conn = sqlite3.connect(path)
    try:
        cursor = conn.execute(
            """
            SELECT timestamp, event_type, process_id, file_path, entropy, risk_score, decision
            FROM timeline
            WHERE incident_id = ?
            ORDER BY timestamp ASC, id ASC;
            """,
            (incident_id,),
        )
        rows = cursor.fetchall()
        if not rows:
            print(f"No events found for incident_id={incident_id}")
            return

        print(f"=== Replay for incident_id={incident_id} ===")
        for ts, event_type, pid, file_path, entropy, risk, decision in rows:
            print(
                f"{ts} | {event_type:13s} | pid={pid} | file={file_path} | "
                f"entropy={entropy} | risk={risk} | decision={decision}"
            )
    finally:
        conn.close()

