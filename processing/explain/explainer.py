"""Threshold-based, human-readable explanations for risk scores."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

import config
from processing.feature_engine import WindowFeatures

logger = logging.getLogger(__name__)

@dataclass
class Explanation:
    """Human-readable explanation with feature contributions."""

    risk_score: float
    level: str
    summary: str
    contributing_signals: List[str]
    feature_values: dict[str, float] = field(default_factory=dict)
    ransomware_signals: List[str] = field(default_factory=list)
    benign_signals: List[str] = field(default_factory=list)

    def to_monitor_string(self) -> str:
        """Single-line monitor-friendly output for logs."""
        parts = [
            f"RISK={self.risk_score:.3f}",
            f"LEVEL={self.level.upper()}",
        ]
        if self.ransomware_signals:
            parts.append("RANSOM_SIGNALS=[" + "; ".join(self.ransomware_signals[:3]) + "]")
        if self.benign_signals:
            parts.append("BENIGN_SIGNALS=[" + "; ".join(self.benign_signals[:2]) + "]")
        return " | ".join(parts)

    def to_detailed_string(self) -> str:
        """Multi-line detailed output for terminal."""
        lines = [
            "",
            "--- RansomScope Detection ---",
            f"  Risk Score: {self.risk_score:.3f} (0=benign, 1=ransomware)",
            f"  Level:      {self.level.upper()}",
            f"  Summary:    {self.summary}",
        ]
        if self.ransomware_signals:
            lines.append("  Ransomware indicators:")
            for s in self.ransomware_signals[:5]:
                lines.append(f"    + {s}")
        if self.benign_signals and self.risk_score < 0.7:
            lines.append("  Benign indicators:")
            for s in self.benign_signals[:3]:
                lines.append(f"    - {s}")
        if self.feature_values:
            lines.append("  Feature snapshot (latest window):")
            for name, val in list(self.feature_values.items())[:6]:
                lines.append(f"    {name}={val}")
        lines.append("------------------------")
        return "\n".join(lines)


class ExplainabilityEngine:
    """Generate explanations from recent window features with actual values."""

    def __init__(
        self,
        benign_threshold: float = config.THRESHOLD_BENIGN,
        suspicious_threshold: float = config.THRESHOLD_SUSPICIOUS,
    ) -> None:
        self.benign_threshold = benign_threshold
        self.suspicious_threshold = suspicious_threshold

    def explain(self, risk_score: float, windows: list[WindowFeatures]) -> Explanation:
        if not windows:
            return Explanation(
                risk_score=risk_score,
                level="unknown",
                summary="No window data available.",
                contributing_signals=[],
            )

        last = windows[-1]
        feature_values = {
            "file_mod_count": last.file_mod_count,
            "rename_count": last.rename_count,
            "delete_count": last.delete_count,
            "entropy_avg_delta": last.entropy_avg_delta,
            "child_process_count": last.child_process_count,
            "privilege_flag": 1 if last.privilege_flag else 0,
            "user_dir_activity_ratio": last.user_dir_activity_ratio,
            "file_create_count": last.file_create_count,
        }

        ransom_signals: List[str] = []
        benign_signals: List[str] = []

        # Ransomware indicators (high = suspicious)
        if last.entropy_avg_delta > 1.0:
            ransom_signals.append(
                f"Entropy spike +{last.entropy_avg_delta:.1f} (encryption-like)"
            )
        if last.rename_count > 5:
            ransom_signals.append(f"Rename burst: {last.rename_count} files")
        if last.file_mod_count > 15 and last.entropy_avg_delta > 0.5:
            ransom_signals.append(
                f"Modify+entropy: {last.file_mod_count} modifies, delta={last.entropy_avg_delta:.1f}"
            )
        if last.delete_count > 3:
            ransom_signals.append(f"Deletions: {last.delete_count} files")
        if last.privilege_flag:
            ransom_signals.append("Privilege escalation")
        # High modify + rename with low create = encryption pattern
        total_ops = last.file_mod_count + last.rename_count + last.delete_count
        if total_ops > 10 and last.file_create_count < 5 and last.entropy_avg_delta > 0.5:
            ransom_signals.append(
                f"Modify/rename/delete burst ({total_ops} ops), few creates"
            )

        # Benign indicators
        if last.file_create_count > 15 and last.file_mod_count < 5 and last.rename_count == 0:
            benign_signals.append(
                f"Mostly file creates ({last.file_create_count}), no renames"
            )
        if last.entropy_avg_delta < 0.3 and last.file_mod_count > 0:
            benign_signals.append(f"Low entropy delta ({last.entropy_avg_delta:.2f})")
        if last.rename_count == 0 and last.delete_count == 0:
            benign_signals.append("No renames or deletes")

        # Risk level
        if risk_score >= self.suspicious_threshold:
            level = "high" if risk_score >= 0.7 else "suspicious"
        elif risk_score <= self.benign_threshold:
            level = "benign"
        else:
            level = "suspicious"

        # Summary
        if ransom_signals:
            summary = ransom_signals[0]
            if len(ransom_signals) > 1:
                summary += f"; {ransom_signals[1]}"
        elif benign_signals:
            summary = benign_signals[0]
        else:
            summary = (
                f"Model score {risk_score:.2f}; no strong pattern (mod={last.file_mod_count}, "
                f"rename={last.rename_count}, entropy_delta={last.entropy_avg_delta:.2f})"
            )

        top_contrib = (ransom_signals + benign_signals)[:3]

        return Explanation(
            risk_score=risk_score,
            level=level,
            summary=summary,
            contributing_signals=top_contrib,
            feature_values=feature_values,
            ransomware_signals=ransom_signals,
            benign_signals=benign_signals,
        )
