"""Structured event types for RansomScope."""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class Event:
    """Structured event emitted by the monitoring layer."""

    timestamp: str
    event_type: str
    file_path: Optional[str] = None
    entropy: Optional[float] = None
    entropy_delta: Optional[float] = None
    process_id: Optional[int] = None
    parent_pid: Optional[int] = None
    process_name: Optional[str] = None
    privilege_flag: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize event to dictionary for logging/JSON."""
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "file_path": self.file_path,
            "entropy": self.entropy,
            "entropy_delta": self.entropy_delta,
            "process_id": self.process_id,
            "parent_pid": self.parent_pid,
            "process_name": self.process_name,
            "privilege_flag": self.privilege_flag,
            **self.metadata,
        }


class EventType:
    """Event type constants."""

    FILE_CREATE = "file_create"
    FILE_MODIFY = "file_modify"
    FILE_DELETE = "file_delete"
    FILE_RENAME = "file_rename"
    PROCESS_CREATE = "process_create"
