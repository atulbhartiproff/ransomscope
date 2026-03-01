"""RansomScope real-time pipeline entrypoint."""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
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
from decision import DecisionEngine
from explain import ExplainabilityEngine
from feature_engine import SlidingWindowEngine
from forensics import ForensicsLogger, replay_incident
from model import ModelManager
from monitor import EventMonitor


def run_monitor(args: argparse.Namespace) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logger = logging.getLogger("ransomescope.main")

    watch_dir = args.watch or os.path.expanduser("~")
    incident_id = args.incident or datetime.now(timezone.utc).strftime("incident-%Y%m%dT%H%M%S")

    logger.info("Starting RansomScope on %s (incident_id=%s)", watch_dir, incident_id)

    monitor = EventMonitor(watch_paths=[watch_dir])
    window_engine = SlidingWindowEngine()
    model_manager = ModelManager(args.model_path)
    explainer = ExplainabilityEngine()
    decision_engine = DecisionEngine()
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
        while not stopping:
            evt = monitor.get_event(timeout=0.2)
            if evt is None:
                continue

            event_count += 1
            if args.verbose:
                logger.info(
                    "event #%d %s file=%s",
                    event_count,
                    evt.event_type,
                    (evt.file_path or "-")[:60],
                )

            # Update sliding window
            window_engine.add_event(evt)

            # Log raw event with no risk/decision for now; will be updated
            forensics.log_event(event=evt, risk_score=None, decision=None)

            n_windows = len(window_engine._windows)  # type: ignore[attr-defined]
            if n_windows > 0 and event_count % 30 == 1 and not args.verbose:
                logger.info(
                    "Windows: %d/%d (need %d for inference)",
                    n_windows, config.SEQUENCE_LENGTH, config.SEQUENCE_LENGTH,
                )

            if window_engine.sequence_ready():
                sequence = window_engine.get_sequence()
                start_infer = time.time()
                risk_score = model_manager.predict_sequence(sequence)
                infer_latency = time.time() - start_infer

                last_inference_time = infer_latency

                windows = window_engine._windows  # type: ignore[attr-defined]
                explanation = explainer.explain(risk_score, windows=windows)
                latest_process_id = evt.process_id
                decision = decision_engine.decide(risk_score, latest_process_id)

                # Monitor-friendly one-line summary
                logger.info(explanation.to_monitor_string())
                logger.info(
                    "  latency_ms=%.0f | summary=\"%s\" | action=%s",
                    infer_latency * 1000.0,
                    explanation.summary[:80],
                    decision.action,
                )
                # Detailed output for high/suspicious risk
                if risk_score >= config.THRESHOLD_BENIGN:
                    logger.info(explanation.to_detailed_string())

                # Big flashing red alert for high ransomware risk
                if risk_score >= config.THRESHOLD_SUSPICIOUS:
                    location = evt.file_path or watch_dir
                    _print_ransomware_alert(watch_dir, str(location or watch_dir), risk_score)

                # Log the same event with risk/decision for simplicity
                forensics.log_event(
                    event=evt,
                    risk_score=risk_score,
                    decision=decision.action,
                )
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

