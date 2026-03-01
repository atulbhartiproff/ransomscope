"""Simple test for the monitoring layer.

Run from project root: python test_monitor.py
Requires Linux/Fedora (watchdog/inotify). On Windows, use WSL or a VM.
"""
import logging
import os
import sys
import tempfile
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from monitor import EventMonitor

if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"Watching: {tmpdir}")
        monitor = EventMonitor(watch_paths=[tmpdir])
        monitor.start()

        try:
            # Generate some events
            test_file = os.path.join(tmpdir, "test.txt")
            with open(test_file, "w") as f:
                f.write("hello world")
            time.sleep(0.2)
            with open(test_file, "w") as f:
                f.write("modified content")
            time.sleep(0.2)
            os.rename(test_file, os.path.join(tmpdir, "renamed.txt"))
            time.sleep(0.2)

            # Collect events for 2 seconds
            for _ in range(20):
                evt = monitor.get_event(timeout=0.1)
                if evt:
                    print(evt.to_dict())
            print("Done.")
        finally:
            monitor.stop()
