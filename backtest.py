"""Walk-forward backtest with realistic costs.

    python backtest.py BTCUSDT --days 365 --out results     (live history, needs exchange access)
    python backtest.py BTCUSDT --demo --days 200            (synthetic data, code check only)

Realism rules
- Signal is evaluated on a CLOSED candle; the trade enters at the NEXT candle's open.
- Stop and targets keep the levels the signal printed. R is measured from the real entry price.
- If stop and a target are hit inside the same candle, the stop is assumed hit first.
- Half the position exits at TP1, the stop then moves to breakeven, the rest exits at TP2.
- Costs: taker fee + slippage on entry and exit, converted into R.
- One pass finds all candidate signals (score >= 2); variants then filter them, so rule variants
  are compared on the same candles.
Variants include a REVERSED sanity check: the same signals traded in the opposite direction
with a mirrored stop. A real edge should do clearly worse when reversed.
"""
import argparse
import json
import os

import numpy as np
import pandas as pd

import config
import data
import engine
from indicators import ema

FEE = 0.0010        # taker fee per side (0.10%)
SLIP = 0.0003       # assumed slippage per side (0.03%)
WARM, WINDOW, MAX_HOLD = 200, 400, 120

VARIANTS = {
    "default (score>=3, TP 2R/3R)":   dict(min_score=3, tp=(2.0, 3.0)),
    "looser (score>=2)":              dict(min_score=2, tp=(2.0, 3.0)),
    "strict (score=4 only)":          dict(min_score=4, tp=(2.0, 3.0)),
    "score>=3, TP 1.5R/2.5R":         dict(min_score=3, tp=(1.5, 2.5)),
    "score>=3, TP 1R/2R":             dict(min_score=3, tp=(1.0, 2.0)),
    "REVERSED default (sanity check)": dict(min_score=3, tp=(2.0, 3.0), invert=True),
}


def htf_trend_series(htf):
    e21, e50 = ema(htf.close, 21), ema(htf.close, 50)
    c = htf.close.values
    t = np.zeros(len(htf), dtype=int)
    for j in range(4, len(htf)):
        a, b, slope = e21.iloc[j], e50.iloc[j], e50.iloc[j] - e50.iloc[j - 3]
        if a > b and c[j] > b and slope > 0:
            t[j] = 1
        elif a < b and c[j] < b and slope < 0:
            t[j] = -1
    return t


def collect(symbol, ltf, htf, ltf_min=15, htf_min=60):
    """All candidate signals with score >= 2 (HTF trend aligned), one per candle.
    Also records features (which confirmations fired, volatility) for later analysis."""
    config.MIN_CATEGORIES = 2
    d = engine.prepare(ltf)
    atr_ratio = (d.atr / d.atr.rolling(50).mean()).values
    tr = htf_trend_series(htf)
    hidx = htf.index
    off = pd.Timedelta(minutes=htf_min - ltf_min)   # an HTF bar is usable once it has closed
    cands = []
    for i in range(WARM, len(ltf) - 1):
        t = ltf.index[i]
        pos = hidx.searchsorted(t - off, side="right") - 1
        if pos < 60 or tr[pos] == 0:
            continue
        s = engine.evaluate(symbol, None, None, _prep=d.iloc[max(0, i - WINDOW + 1):i + 1], _trend=int(tr[pos]))
        if s:
            cands.append({"i": i, "time": str(t), "side": s.side, "score": s.score,
                          "entry": s.entry, "stop": s.stop,
                          "cats": sorted(k for k in s.reasons if k != "htf"),
                          "atr_pct": round(float(d.atr.iloc[i] / d.close.iloc[i] * 100), 3),
                          "atr_ratio": round(float(atr_ratio[i]), 2) if atr_ratio[i] == atr_ratio[i] else 1.0})
    return cands


def simulate(ltf, c, tp, invert=False):
    o, h, l, cl = (ltf[k].values for k in ("open", "high", "low", "close"))
    i = c["i"]
    j0 = i + 1
    side_long = (c["side"] == "long") != invert
    e0, risk0 = c["entry"], abs(c["entry"] - c["stop"])
    if invert:
        stop = e0 + risk0 if c["side"] == "long" else e0 - risk0
    else:
        stop = c["stop"]
    sgn = 1 if side_long else -1
    tp1, tp2 = e0 + sgn * tp[0] * risk0, e0 + sgn * tp[1] * risk0
    entry = o[j0]
    risk = (entry - stop) if side_long else (stop - entry)
    if risk <= 0 or (side_long and entry >= tp1) or (not side_long and entry <= tp1):
        return None                                   # gapped through stop or target: no trade
    r1, r2 = abs(tp1 - entry) / risk, abs(tp2 - entry) / risk
    cost_r = 2 * (FEE + SLIP) * entry / risk
    cur_stop, hit1, R = stop, False, None
    last = min(j0 + MAX_HOLD, len(ltf)) - 1
    for j in range(j0, last + 1):
        sl = l[j] <= cur_stop if side_long else h[j] >= cur_stop
        t1 = h[j] >= tp1 if side_long else l[j] <= tp1
        t2 = h[j] >= tp2 if side_long else l[j] <= tp2
        if sl:
            R = 0.5 * r1 if hit1 else -1.0
            break
        if not hit1 and t1:
            hit1, cur_stop = True, entry
        if hit1 and t2:
            R = 0.5 * r1 + 0.5 * r2
            break
    if R is None:                                     # time stop: mark to market
        m = sgn * (cl[last] - entry) / risk
        R = 0.5 * r1 + 0.5 * m if hit1 else m
    return {"time": c["time"], "side": "long" if side_long else "short", "score": c["score"],
            "R_gross": round(R, 3), "R_net": round(R - cost_r, 3), "cost_R": round(cost_r, 3),
            "risk_pct": round(100 * risk / entry, 3)}


def run_variants(ltf, cands):
    out = {}
    for name, v in VARIANTS.items():
        trades, last_i = [], -10**9
        for c in cands:
            if c["score"] < v["min_score"] or c["i"] - last_i < config.COOLDOWN_CANDLES:
                continue
            t = simulate(ltf, c, v["tp"], v.get("invert", False))
            if t:
                trades.append(t)
                last_i = c["i"]
        out[name] = trades
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("symbol")
    ap.add_argument("--days", type=int, default=365)
    ap.add_argument("--out", default="results")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        ltf = data.synthetic(a.symbol, "15m", a.days * 96, seed=7)
        htf = ltf.resample("1h").agg({"open": "first", "high": "max", "low": "min",
                                      "close": "last", "volume": "sum"}).dropna()
    else:
        ltf = data.fetch_history(a.symbol, "15m", a.days)
        htf = data.fetch_history(a.symbol, "1h", a.days + 10)
    print(f"{a.symbol}: {len(ltf)} x 15m candles, {ltf.index[0]} -> {ltf.index[-1]}")
    cands = collect(a.symbol, ltf, htf)
    print(f"candidate signals (score>=2, trend aligned): {len(cands)}")
    res = {"symbol": a.symbol, "demo": a.demo, "start": str(ltf.index[WARM]), "end": str(ltf.index[-1]),
           "buy_hold_pct": round(100 * (ltf.close.iloc[-1] / ltf.close.iloc[WARM] - 1), 1),
           "fee_per_side": FEE, "slip_per_side": SLIP, "variants": run_variants(ltf, cands)}
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, f"{a.symbol}.json"), "w") as f:
        json.dump(res, f)
    for k, v in res["variants"].items():
        print(f"  {k}: {len(v)} trades, avg net R {np.mean([t['R_net'] for t in v]) if v else 0:.3f}")


if __name__ == "__main__":
    main()
