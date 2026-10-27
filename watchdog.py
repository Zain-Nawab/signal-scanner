"""Hourly health check, independent of the scan job. Alerts on Telegram if scanning has stalled or
every symbol is failing. Alerts only inside a window after the problem starts, so it does not spam."""
import json
import os
import sys
from datetime import datetime, timezone

from notifier import send_telegram

path = os.path.join(os.getenv("STATE_DIR", "data"), "status.json")
try:
    st = json.load(open(path))
except Exception as e:
    send_telegram(f"WATCHDOG: cannot read scanner state ({str(e)[:80]}). Check the repository Actions tab.")
    sys.exit(0)

age = (datetime.now(timezone.utc) - datetime.fromisoformat(st["last_scan"])).total_seconds() / 60
errs = st.get("errors", {})
all_failing = bool(st.get("symbols")) and len([k for k in errs if "(fallback)" not in k]) >= len(st["symbols"])
print(f"last scan {age:.0f} min ago; errors={len(errs)}; all_failing={all_failing}")
if 50 <= age < 115:
    send_telegram(f"WATCHDOG: no scan for {age:.0f} minutes. The 15-minute job may be delayed or failing. "
                  "Check the Actions tab of the signal-scanner repository.")
elif all_failing and age < 30:
    send_telegram("WATCHDOG: the scanner is running but every symbol is failing (data source problem). "
                  f"Example: {next(iter(errs.values()))[:120]}")
