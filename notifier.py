import time

import requests

import config


def _retry(fn, tries=3):
    for k in range(tries):
        try:
            if fn():
                return True
        except Exception:
            pass
        time.sleep(2 * (k + 1))
    return False


def format_signal(s, notes=None):
    arrow = "LONG" if s["side"] == "long" else "SHORT"
    entry, stop = float(s["entry"]), float(s["stop"])
    risk = abs(entry - stop)
    chase = entry + 0.25 * risk if s["side"] == "long" else entry - 0.25 * risk
    lines = [f"{arrow} {s['symbol']} | Grade {s['grade']} ({s['score']}/4)",
             f"Entry: {s['entry']}  (skip it if price is already beyond {chase:.6g})",
             f"Stop: {s['stop']}", f"TP1 (2R): {s['tp1']}", f"TP2 (3R): {s['tp2']}", "",
             f"Why: {s['reasons']}", f"Candle: {s['time']}",
             "Size: (account x 1%) / (entry - stop)"]
    for n in notes or []:
        lines.append(n)
    lines += ["", "Alert only. No trade was placed."]
    return "\n".join(lines)


def post_webhook(payload):
    """POST the signal to the Make.com webhook (journal). True on HTTP 2xx."""
    if not config.MAKE_WEBHOOK_URL:
        return False
    return _retry(lambda: requests.post(config.MAKE_WEBHOOK_URL, json=payload, timeout=15).ok)


def send_telegram(text):
    if not (config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID):
        return False
    return _retry(lambda: requests.post(
        f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": config.TELEGRAM_CHAT_ID, "text": text}, timeout=15).ok)
