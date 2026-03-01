"""Decision engine: map risk scores to actions and prompt user."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import config

logger = logging.getLogger(__name__)


@dataclass
class Decision:
    """Decision taken for a given risk score."""

    risk_score: float
    level: str
    action: str  # "none", "kill", "quarantine", "safe"
    process_id: Optional[int]


class DecisionEngine:
    """Interactive decision engine for high-risk situations."""

    def decide(self, risk_score: float, process_id: Optional[int]) -> Decision:
        """Return decision, prompting user on high risk."""
        if risk_score <= config.THRESHOLD_BENIGN:
            level = "benign"
            return Decision(risk_score=risk_score, level=level, action="none", process_id=process_id)

        if risk_score < config.THRESHOLD_SUSPICIOUS:
            level = "suspicious"
            return Decision(risk_score=risk_score, level=level, action="none", process_id=process_id)

        level = "high"
        # High risk: prompt user in terminal
        logger.warning(
            "High ransomware risk detected (score=%.3f) for process %s", risk_score, process_id
        )
        print("\n[High Risk] RansomScope detected high ransomware risk.")
        print(f"Risk score: {risk_score:.3f}, process id: {process_id}")
        print("Choose action:")
        print("  [k] Kill process")
        print("  [q] Quarantine (no-op placeholder)")
        print("  [s] Mark as safe")

        action = "none"
        try:
            choice = input("Enter choice [k/q/s]: ").strip().lower()
        except EOFError:
            choice = "s"

        if choice == "k":
            action = "kill"
            if process_id is not None:
                try:
                    import psutil

                    proc = psutil.Process(process_id)
                    proc.terminate()
                    logger.warning("Sent terminate to process %s", process_id)
                except Exception as exc:  # noqa: BLE001
                    logger.error("Failed to terminate process %s: %s", process_id, exc)
        elif choice == "q":
            action = "quarantine"
            # Quarantine is intentionally a no-op placeholder in this academic project.
            logger.warning("User selected quarantine (no-op).")
        else:
            action = "safe"
            logger.info("User marked process %s as safe", process_id)

        return Decision(risk_score=risk_score, level=level, action=action, process_id=process_id)

