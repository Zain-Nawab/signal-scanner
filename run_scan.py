"""One-shot scan, run by GitHub Actions every 15 minutes.

Reads/writes state in STATE_DIR (the `data` branch checkout):
  signals.json  all signals so far (used for de-duplication)
  status.json   latest watchlist + health info (read by the dashboard)
  candles.json  recent candles for the dashboard chart
Delivery: Make.com webhook first (it sends Telegram + logs to Sheets);
direct Telegram only if the webhook call fails.
"""
import argparse
import json
import os
from datetime import datetime, timezone, timedelta

import config
import data
from engine import evaluate
from notifier import format_signal, post_webhook, send_telegram

OUT = os.getenv("STATE_DIR", "out")


def load(name, default):
    try:
        with open(os.path.join(OUT, name)) as f:
            return json.load(f)
    except Exception:
        return default


def save(name, obj):
    with open(os.path.join(OUT, name), "w") as f:
        json.dump(obj, f, separators=(",", ":"))


def now():
    return datetime.now(timezone.utc)


def payload_of(sig):
    d = sig.to_dict()
    d["reasons"] = " | ".join(f"{k}: {v}" for k, v in d["reasons"].items())
    return d


def deliver(payload):
    if post_webhook(payload):
        return "make"
    if send_telegram(format_signal(payload)):
        return "telegram-direct"
    return "failed"


def is_new(sig, history):
    for h in history:
        if h["symbol"] == sig.symbol and h["side"] == sig.side:
            if h["time"] == sig.time:
                return False
            age = (now() - datetime.fromisoformat(h["created"])).total_seconds()
            if age < config.COOLDOWN_CANDLES * 15 * 60:
                return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test-signal", action="store_true", help="send one fake signal through the delivery chain")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    if args.test_signal:
        p = {"symbol": "TEST-ONLY", "side": "long", "grade": "B", "score": 3, "entry": 100, "stop": 98,
             "tp1": 104, "tp2": 106, "reasons": "Connection test, not a real signal",
             "time": now().strftime("%Y-%m-%d %H:%M UTC")}
        print("test signal delivered via:", deliver(p))
        return

    history = load("signals.json", [])
    status = {"last_scan": now().isoformat(), "symbols": config.SYMBOLS, "timeframe": config.TIMEFRAME,
              "htf": config.HTF, "min_confirmations": config.MIN_CATEGORIES,
              "source": None, "watch": {}, "errors": {}, "new_signals": 0}
    candles = {}
    for sym in config.SYMBOLS:
        try:
            ltf, htf, src, errs = data.fetch_pair(sym)
            status["source"] = src
            if errs:
                status["errors"][sym + " (fallback)"] = errs
            sig, st = evaluate(sym, ltf, htf, detail=True)
            status["watch"][sym] = st
            candles[sym] = [{"time": int(t.timestamp()), "open": r.open, "high": r.high,
                             "low": r.low, "close": r.close} for t, r in ltf.tail(120).iterrows()]
            # ignore data older than ~3 candles (exchange lag / outage)
            fresh = now() - (ltf.index[-1].tz_localize("UTC").to_pydatetime() + timedelta(minutes=15)) < timedelta(minutes=45)
            if sig and fresh and is_new(sig, history):
                p = payload_of(sig)
                p["created"] = now().isoformat()
                p["delivered_via"] = deliver(p)
                history.insert(0, p)
                status["new_signals"] += 1
                print("SIGNAL", sym, sig.side, p["delivered_via"])
            elif sig and not fresh:
                status["errors"][sym] = "signal skipped: data is stale"
        except Exception as e:
            status["errors"][sym] = str(e)[:300]
    save("signals.json", history[:200])
    save("status.json", status)
    save("candles.json", candles)
    print(f"scan done: source={status['source']} new={status['new_signals']} errors={len(status['errors'])}")


if __name__ == "__main__":
    main()
