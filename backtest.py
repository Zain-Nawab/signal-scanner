"""Walk-forward backtest of the signal engine.

Usage: python backtest.py [SYMBOL] [--days 60] [--demo]
Each signal is entered at the signal candle close; SL/TP1 are checked candle by
candle (if both are hit in one candle, SL is assumed first - conservative).
Half the position exits at TP1, the stop moves to breakeven, rest exits at TP2.
"""
import sys
import pandas as pd
import config
import data
from engine import evaluate

PER_HTF = {"15m": 4, "30m": 2, "1h": 1}


def run(ltf, htf, symbol="TEST", warmup=200):
    trades, cool = [], -999
    for i in range(warmup, len(ltf) - 1):
        t = ltf.index[i]
        sub = ltf.iloc[max(0, i - 400):i + 1]
        h = htf[htf.index + pd.Timedelta(hours=1) <= t + pd.Timedelta(minutes=15)].iloc[-120:]
        if i - cool < config.COOLDOWN_CANDLES:
            continue
        s = evaluate(symbol, sub, h)
        if not s:
            continue
        cool = i
        risk = abs(s.entry - s.stop)
        long = s.side == "long"
        stop, tp1_hit, r = s.stop, False, None
        for j in range(i + 1, min(i + 120, len(ltf))):
            hi, lo = ltf.high.iloc[j], ltf.low.iloc[j]
            hit_sl = lo <= stop if long else hi >= stop
            hit1 = hi >= s.tp1 if long else lo <= s.tp1
            hit2 = hi >= s.tp2 if long else lo <= s.tp2
            if hit_sl:
                r = (0.5 * config.TP_RR) if tp1_hit else -1.0   # BE after TP1 -> only banked half
                break
            if not tp1_hit and hit1:
                tp1_hit, stop = True, s.entry
            if tp1_hit and hit2:
                r = 0.5 * config.TP_RR + 0.5 * config.TP2_RR
                break
        if r is None:  # timed out: mark to market
            px = ltf.close.iloc[min(i + 119, len(ltf) - 1)]
            m = ((px - s.entry) if long else (s.entry - px)) / risk
            r = 0.5 * config.TP_RR + 0.5 * m if tp1_hit else m
        trades.append({"time": s.time, "side": s.side, "grade": s.grade, "R": round(r, 2)})
    return pd.DataFrame(trades)


def summary(t):
    if t.empty:
        return "No trades."
    w = t[t.R > 0]
    eq = t.R.cumsum()
    dd = (eq.cummax() - eq).max()
    return (f"trades={len(t)} win%={len(w) / len(t) * 100:.0f} avgR={t.R.mean():.2f} "
            f"totalR={t.R.sum():.1f} maxDD(R)={dd:.1f}")


if __name__ == "__main__":
    sym = next((a for a in sys.argv[1:] if a.isalpha() or a.endswith("USDT")), "BTCUSDT")
    if "--demo" in sys.argv:
        config.ALLOW_DEMO_DATA = True
    ltf, demo1 = data.get(sym, config.TIMEFRAME, 1000)
    if demo1:  # keep demo HTF consistent with the demo LTF
        htf = ltf.resample("1h").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
    else:
        htf, _ = data.get(sym, config.HTF, 500)
    print(f"{sym} {'(SYNTHETIC DATA)' if demo1 else '(live data)'} {len(ltf)} candles")
    t = run(ltf, htf, sym)
    print(summary(t))
    if not t.empty:
        print(t.groupby("grade").R.agg(["count", "mean"]))
