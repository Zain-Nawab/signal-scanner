"""One-shot scan, run by GitHub Actions every 15 minutes.

State lives in STATE_DIR (the `data` branch checkout):
  signals.json  every signal so far, with delivery status and outcome (paper-trading record)
  status.json   latest watchlist, news state, health info (read by the dashboard and the watchdog)
  candles.json  recent candles for the dashboard chart
Delivery: Telegram directly (primary) and the Make.com webhook (Google Sheets journal). A failed
channel is retried on the next scans for up to 3 hours.
"""
import argparse
import json
import os
from datetime import datetime, timezone, timedelta

import config
import data
import news
import tracker
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


def deliver(p, notes=None):
    return {"telegram": send_telegram(format_signal(p, notes)), "make": post_webhook(p)}


def is_new(sig, history):
    for h in history:
        if h["symbol"] == sig.symbol and h["side"] == sig.side:
            if h["time"] == sig.time:
                return False
            age = (now() - datetime.fromisoformat(h["created"])).total_seconds()
            if age < config.COOLDOWN_CANDLES * 15 * 60:
                return False
    return True


def retry_failed(history):
    """Re-send channels that failed, for signals younger than 3 hours."""
    for h in history[:30]:
        if h.get("suppressed") or h.get("outcome"):
            continue
        if now() - datetime.fromisoformat(h["created"]) > timedelta(hours=3):
            continue
        s = h.setdefault("sent", {})
        if not s.get("telegram"):
            s["telegram"] = send_telegram("(late) " + format_signal(h, h.get("notes")))
        if not s.get("make"):
            s["make"] = post_webhook(h)


def track_outcomes(history, sym, ltf):
    for h in history:
        if h["symbol"] != sym or h.get("outcome") or h.get("suppressed"):
            continue
        if pd_ts(h["time"]) < ltf.index[0]:
            h["outcome"], h["R"] = "unresolved (data gap)", None
            continue
        r = tracker.resolve(h, ltf)
        if r:
            h["outcome"], h["R"], h["closed"] = r
            send_telegram(f"RESULT {h['symbol']} {h['side']}: {r[0]}, {r[1]:+.2f}R (before fees)")


def pd_ts(s):
    import pandas as pd
    return pd.Timestamp(s)


def daily_digest(history, status, prev):
    today = now().strftime("%Y-%m-%d")
    status["last_digest"] = prev.get("last_digest")
    if now().hour != 0 or prev.get("last_digest") == today:
        return
    last24 = [h for h in history if now() - datetime.fromisoformat(h["created"]) < timedelta(hours=24)]
    s = tracker.summary(history)
    nxt = (status.get("news") or {}).get("next_events") or []
    text = (f"Daily summary {today} (UTC)\nSignals in the last 24h: {len(last24)}\n"
            f"Open: {s['open']} | Closed: {s['closed']} | Win rate: {s['win_pct']}% | Total: {s['total_R']:+.2f}R (before fees)\n"
            f"Data source: {status.get('source')} | Scan errors: {len(status['errors'])}"
            + (f"\nNext high-impact event: {nxt[0]['title']} at {nxt[0]['time'][:16].replace('T', ' ')} UTC" if nxt else "")
            + "\nPaper-trading record only. Not financial advice.")
    if send_telegram(text):
        status["last_digest"] = today


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test-signal", action="store_true", help="send one fake signal through every delivery channel")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    if args.test_signal:
        p = {"symbol": "TEST-ONLY", "side": "long", "grade": "B", "score": 3, "entry": 100, "stop": 98,
             "tp1": 104, "tp2": 106, "reasons": "Connection test, not a real signal",
             "time": now().strftime("%Y-%m-%d %H:%M UTC")}
        res = deliver(p)
        res.update(time=now().isoformat(), telegram_secrets_set=bool(config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID),
                   webhook_secret_set=bool(config.MAKE_WEBHOOK_URL))
        save("last_test.json", res)
        print("test signal:", res)
        return

    prev = load("status.json", {})
    history = load("signals.json", [])
    news_state = news.assess()
    status = {"last_scan": now().isoformat(), "symbols": config.SYMBOLS, "timeframe": config.TIMEFRAME,
              "htf": config.HTF, "min_confirmations": config.MIN_CATEGORIES, "source": None, "watch": {},
              "errors": {}, "new_signals": 0, "suppressed": 0, "news": news_state}
    retry_failed(history)
    candles = {}
    for sym in config.SYMBOLS:
        try:
            ltf, htf, src, errs = data.fetch_pair(sym)
            status["source"] = src
            if errs:
                status["errors"][sym + " (fallback)"] = errs
            track_outcomes(history, sym, ltf)
            sig, st = evaluate(sym, ltf, htf, detail=True)
            status["watch"][sym] = st
            candles[sym] = [{"time": int(t.timestamp()), "open": r.open, "high": r.high,
                             "low": r.low, "close": r.close} for t, r in ltf.tail(120).iterrows()]
            # ignore data older than ~3 candles (exchange lag / outage)
            fresh = now() - (ltf.index[-1].tz_localize("UTC").to_pydatetime() + timedelta(minutes=15)) < timedelta(minutes=45)
            if sig and fresh and is_new(sig, history):
                p = payload_of(sig)
                p["created"] = now().isoformat()
                if news_state["blackout"]:
                    p.update(suppressed=True, reason=f"news window: {news_state['blackout']['event']}")
                    status["suppressed"] += 1
                    print("SUPPRESSED", sym, sig.side, p["reason"])
                else:
                    notes = [f"WARNING headline: {h}" for h in news_state["headlines"]]
                    nxt = [e for e in news_state["next_events"]
                           if datetime.fromisoformat(e["time"]) - now() < timedelta(hours=3)]
                    notes += [f"Note: {e['title']} at {e['time'][11:16]} UTC" for e in nxt]
                    p["notes"] = notes
                    p["sent"] = deliver(p, notes)
                    status["new_signals"] += 1
                    print("SIGNAL", sym, sig.side, p["sent"])
                history.insert(0, p)
            elif sig and not fresh:
                status["errors"][sym] = "signal skipped: data is stale"
        except Exception as e:
            status["errors"][sym] = str(e)[:300]
    status["summary"] = tracker.summary(history)
    daily_digest(history, status, prev)
    save("signals.json", history[:200])
    save("status.json", status)
    save("candles.json", candles)
    print(f"scan done: source={status['source']} new={status['new_signals']} suppressed={status['suppressed']} "
          f"errors={len(status['errors'])} news_errors={len(news_state['errors'])}")


if __name__ == "__main__":
    main()
