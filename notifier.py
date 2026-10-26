import requests
import config


def format_signal(s):
    arrow = "LONG" if s["side"] == "long" else "SHORT"
    lines = [f"{arrow} {s['symbol']} | Grade {s['grade']} ({s['score']}/4)",
             f"Entry: {s['entry']}", f"Stop: {s['stop']}",
             f"TP1 (2R): {s['tp1']}", f"TP2 (3R): {s['tp2']}", "",
             f"Why: {s['reasons']}", f"Candle: {s['time']}", "",
             "Alert only. No trade was placed."]
    return "\n".join(lines)


def post_webhook(payload):
    """POST the signal to the Make.com webhook. True on HTTP 2xx."""
    if not config.MAKE_WEBHOOK_URL:
        return False
    try:
        return requests.post(config.MAKE_WEBHOOK_URL, json=payload, timeout=15).ok
    except Exception:
        return False


def send_telegram(text):
    """Direct fallback if Make is unreachable."""
    if not (config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID):
        return False
    try:
        r = requests.post(f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage",
                          json={"chat_id": config.TELEGRAM_CHAT_ID, "text": text}, timeout=15)
        return r.ok
    except Exception:
        return False
