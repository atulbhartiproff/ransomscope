"""RansomScope real-time pipeline entrypoint."""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

BOLD_RED = "\033[1;31m"
BOLD_WHITE = "\033[1;37m"
RESET = "\033[0m"
BLINK = "\033[5m"


def _print_ransomware_alert(watch_dir: str, location: str, risk_score: float) -> None:
    """Print flashing red RANSOMWARE DETECTED banner with location."""
    loc = (location or watch_dir)[:55]
    wd = watch_dir[:55]
    banner = f"""
{BOLD_RED}{BLINK}
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║               ⚠  RANSOMWARE DETECTED  ⚠                           ║
║                                                                   ║
║   Risk Score: {risk_score:.3f}                                                  ║
║   Location:   {wd:<56} ║
║   Activity:   {loc:<56} ║
║                                                                   ║
║   TAKE ACTION IMMEDIATELY                                         ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
{RESET}"""
    # Print flashing effect (3 cycles)
    for _ in range(3):
        print(banner, flush=True)
        time.sleep(0.35)
        sys.stdout.write("\033[F" * 12)
        sys.stdout.flush()
        time.sleep(0.15)
    print(banner, flush=True)


import config
from data_collection.collection import EventMonitor
from response_forensics.forensics import ForensicsLogger, replay_incident
from detection_analysis.decision import DecisionEngine
from response_forensics.explain import ExplainabilityEngine
from detection_analysis.feature_engine import SlidingWindowEngine
from detection_analysis.model import ModelManager


def run_monitor(args: argparse.Namespace) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logger = logging.getLogger("ransomescope.main")

    watch_dir = args.watch or os.path.expanduser("~")
    incident_id = args.incident or datetime.now(timezone.utc).strftime("incident-%Y%m%dT%H%M%S")

    logger.info("Starting RansomScope on %s (incident_id=%s)", watch_dir, incident_id)

    monitor = EventMonitor(watch_paths=[watch_dir])
    window_engine = SlidingWindowEngine()
    model_manager = ModelManager(args.model_path)
    benign_threshold = args.benign_threshold
    suspicious_threshold = args.suspicious_threshold
    if suspicious_threshold <= benign_threshold:
        raise ValueError("--suspicious-threshold must be greater than --benign-threshold")

    explainer = ExplainabilityEngine(
        benign_threshold=benign_threshold,
        suspicious_threshold=suspicious_threshold,
    )
    decision_engine = DecisionEngine(
        benign_threshold=benign_threshold,
        suspicious_threshold=suspicious_threshold,
    )
    forensics = ForensicsLogger(incident_id=incident_id)

    stopping = False

    def handle_sigint(signum, frame) -> None:  # type: ignore[override]
        nonlocal stopping
        stopping = True
        logger.info("Received signal %s; stopping...", signum)

    signal.signal(signal.SIGINT, handle_sigint)
    signal.signal(signal.SIGTERM, handle_sigint)

    monitor.start()
    try:
        last_inference_time: Optional[float] = None
        event_count = 0
        last_inferred_window_count = 0
        latest_process_id: Optional[int] = None
        latest_location: Optional[str] = None
        last_risk_score: Optional[float] = None
        last_level: str = "warmup"
        last_summary: str = "Collecting windows"
        verbose_snapshot_every = 20

        def maybe_infer() -> None:
            nonlocal last_inference_time, last_inferred_window_count, last_risk_score, last_level, last_summary
            n_windows_local = len(window_engine._windows)  # type: ignore[attr-defined]
            if n_windows_local <= last_inferred_window_count:
                return
            windows = window_engine._windows  # type: ignore[attr-defined]
            if not windows:
                return

            infer_latency = 0.0
            if window_engine.sequence_ready():
                sequence = window_engine.get_sequence()
                start_infer = time.time()
                risk_score_local = model_manager.predict_sequence(sequence)
                infer_latency = time.time() - start_infer
            else:
                if not args.demo_force_high_risk:
                    return
                risk_score_local = max(0.0, benign_threshold - 0.01)

            last_inference_time = infer_latency
            explanation = explainer.explain(risk_score_local, windows=windows)
            if args.demo_force_high_risk and explanation.ransomware_signals:
                risk_score_local = max(risk_score_local, suspicious_threshold + 0.01)
                explanation = explainer.explain(risk_score_local, windows=windows)

            decision = decision_engine.decide(risk_score_local, latest_process_id)
            last_risk_score = risk_score_local
            last_level = explanation.level.upper()
            last_summary = explanation.summary[:80]

            logger.info(explanation.to_monitor_string())
            logger.info(
                "  latency_ms=%.0f | summary=\"%s\" | action=%s",
                infer_latency * 1000.0,
                explanation.summary[:80],
                decision.action,
            )
            if risk_score_local >= benign_threshold:
                logger.info(explanation.to_detailed_string())

            if risk_score_local >= suspicious_threshold:
                location = latest_location or watch_dir
                _print_ransomware_alert(watch_dir, str(location), risk_score_local)

            last_inferred_window_count = n_windows_local

        while not stopping:
            evt = monitor.get_event(timeout=0.2)
            if evt is None:
                window_engine.tick()
                maybe_infer()
                continue

            event_count += 1

            # Update sliding window
            window_engine.add_event(evt)
            latest_process_id = evt.process_id
            latest_location = evt.file_path or latest_location

            # Log raw event with no risk/decision for now; will be updated
            forensics.log_event(event=evt, risk_score=None, decision=None)

            n_windows = len(window_engine._windows)  # type: ignore[attr-defined]
            if n_windows > 0 and event_count % 30 == 1 and not args.verbose:
                logger.info(
                    "Windows: %d/%d (need %d for inference)",
                    n_windows, config.SEQUENCE_LENGTH, config.SEQUENCE_LENGTH,
                )
            if args.verbose and (event_count == 1 or event_count % verbose_snapshot_every == 0):
                last_window = window_engine._windows[-1] if n_windows > 0 else None  # type: ignore[attr-defined]
                file_name = Path(evt.file_path).name if evt.file_path else "-"
                if last_window:
                    mod_count = last_window.file_mod_count
                    rename_count = last_window.rename_count
                    delete_count = last_window.delete_count
                    create_count = last_window.file_create_count
                    entropy_delta = last_window.entropy_avg_delta
                else:
                    mod_count = rename_count = delete_count = create_count = 0
                    entropy_delta = 0.0

                risk_text = f"{last_risk_score:.3f}" if last_risk_score is not None else "n/a"
                logger.info(
                    "activity e=%d win=%d/%d last=%s:%s | mod=%d ren=%d del=%d crt=%d entΔ=%.2f | risk=%s level=%s | %s",
                    event_count,
                    n_windows,
                    config.SEQUENCE_LENGTH,
                    evt.event_type,
                    file_name[:28],
                    mod_count,
                    rename_count,
                    delete_count,
                    create_count,
                    entropy_delta,
                    risk_text,
                    last_level,
                    last_summary,
                )

            maybe_infer()
    finally:
        monitor.stop()
        forensics.close()
        logger.info("RansomScope stopped.")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RansomScope real-time ransomware detector")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_p = subparsers.add_parser("run", help="Run real-time detector")
    run_p.add_argument("--watch", type=str, help="Directory to watch (default: current user's home)")
    run_p.add_argument("--model-path", type=str, default="ransomescope_lstm.pt", help="Path to model file")
    run_p.add_argument(
        "--incident",
        type=str,
        help="Optional incident id label (otherwise auto-generated)",
    )
    run_p.add_argument(
        "--verbose",
        action="store_true",
        help="Log every event; default is periodic window status",
    )
    run_p.add_argument(
        "--benign-threshold",
        type=float,
        default=config.THRESHOLD_BENIGN,
        help="Risk threshold for benign classification (default from config)",
    )
    run_p.add_argument(
        "--suspicious-threshold",
        type=float,
        default=config.THRESHOLD_SUSPICIOUS,
        help="Risk threshold for high-risk prompt/banner (default from config)",
    )
    run_p.add_argument(
        "--demo-force-high-risk",
        action="store_true",
        help="Demo mode: force high-risk when ransomware signals are present",
    )

    replay_p = subparsers.add_parser("replay", help="Replay forensic timeline")
    replay_p.add_argument("incident_id", type=str, help="Incident id to replay")

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv or sys.argv[1:])
    if args.command == "run":
        run_monitor(args)
    elif args.command == "replay":
        replay_incident(args.incident_id)


if __name__ == "__main__":
    main()

