"""Tracks what happened to each signal after it was sent (paper-trading record).

Same rules as the backtest: stop checked before targets inside a candle; half off at TP1 then
stop to breakeven; the rest at TP2; time stop after 120 candles. R is before fees.
"""
import pandas as pd

MAX_HOLD = 120


def resolve(sig, ltf):
    """Return (outcome, R, closed_at) once the signal is finished, else None."""
    t0 = pd.Timestamp(sig["time"])
    after = ltf[ltf.index > t0]
    if after.empty:
        return None
    long = sig["side"] == "long"
    e, stop, tp1, tp2 = (float(sig[k]) for k in ("entry", "stop", "tp1", "tp2"))
    risk = abs(e - stop)
    if risk <= 0:
        return None
    r1, r2 = abs(tp1 - e) / risk, abs(tp2 - e) / risk
    cur, hit1 = stop, False
    for n, (ts, row) in enumerate(after.iterrows(), 1):
        sl = row.low <= cur if long else row.high >= cur
        t1 = row.high >= tp1 if long else row.low <= tp1
        t2 = row.high >= tp2 if long else row.low <= tp2
        if sl:
            return ("breakeven after TP1", round(0.5 * r1, 2), str(ts)) if hit1 else ("stopped out", -1.0, str(ts))
        if not hit1 and t1:
            hit1, cur = True, e
        if hit1 and t2:
            return "hit TP2", round(0.5 * r1 + 0.5 * r2, 2), str(ts)
        if n >= MAX_HOLD:
            m = (row.close - e) / risk * (1 if long else -1)
            return "timed out", round(0.5 * r1 + 0.5 * m if hit1 else m, 2), str(ts)
    return None


def summary(history):
    done = [h for h in history if h.get("outcome") and h.get("R") is not None]
    wins = [h for h in done if h["R"] > 0]
    return {"signals": len(history), "open": sum(1 for h in history if not h.get("outcome") and not h.get("suppressed")),
            "closed": len(done), "win_pct": round(100 * len(wins) / len(done)) if done else None,
            "total_R": round(sum(h["R"] for h in done), 2)}
