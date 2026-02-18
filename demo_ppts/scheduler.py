"""
scheduler.py — Weekly demo PPT regeneration scheduler.

Runs as a background task. Checks every hour whether a weekly
regeneration is due (default: every Sunday). When triggered,
regenerates all demo PPTs with the latest data.

Usage:
    python demo_ppts/scheduler.py          # Runs in foreground
    python demo_ppts/scheduler.py --once   # Single check + generate if due
"""

from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

CHECK_INTERVAL_SECONDS = 3600  # Check every hour


def run_scheduler(once: bool = False) -> None:
    """Run the demo generation scheduler."""
    from demo_ppts.generate_demos import generate_all_demos, _load_status, needs_regeneration

    print("🕐 PPT Builder Demo Scheduler started")
    print(f"   Check interval: {CHECK_INTERVAL_SECONDS // 60} minutes")

    while True:
        now = datetime.now()
        print(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S')}] Checking if regeneration is needed...")

        status = _load_status()
        if needs_regeneration(status):
            print("📦 Regeneration due — starting demo generation...")
            try:
                generate_all_demos(force=True)
            except Exception as e:
                print(f"❌ Scheduler error: {e}")
        else:
            last = status.get("last_full_run", "never")
            print(f"✅ Demos are up to date (last run: {last})")

        if once:
            print("--once flag: exiting after single check.")
            break

        print(f"💤 Sleeping for {CHECK_INTERVAL_SECONDS // 60} minutes...")
        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    once = "--once" in sys.argv
    run_scheduler(once=once)
