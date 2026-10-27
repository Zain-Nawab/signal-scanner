"""Research lab: collects every candidate signal plus its outcome under several target sets,
and runs a classic trend-following benchmark (Donchian breakout) for comparison.

    python lab.py BTCUSDT --tf 1h --htf 4h --days 1100 --out lab_results
Outcomes are stored GROSS (before costs) with the stop distance, so costs can be applied later
under any fee assumption (spot, futures taker, futures maker).
"""
import argparse
import json
import os

import numpy as np
import pandas as pd

import backtest
import data
from indicators import atr

MIN = data.MIN
TP_SETS = {"1_2": (1.0, 2.0), "1.5_2.5": (1.5, 2.5), "2_3": (2.0, 3.0), "3_4.5": (3.0, 4.5)}


def candidates_with_outcomes(symbol, ltf, htf, tf, htf_tf):
    cands = backtest.collect(symbol, ltf, htf, MIN[tf], MIN[htf_tf])
    out = []
    for c in cands:
        row = {k: c[k] for k in ("time", "side", "score", "cats", "atr_pct", "atr_ratio", "i")}
        ok = False
        for name, tp in TP_SETS.items():
            t = backtest.simulate(ltf, c, tp)
            if t:
                row["R_" + name] = t["R_gross"]
                row["risk_pct"] = t["risk_pct"]
                ok = True
        if ok:
            out.append(row)
    return out


def donchian(ltf, n_in=20, n_out=10, atr_mult=2.0):
    """Long/short channel breakout. Enter next open after a close beyond the N-bar channel,
    exit on a close beyond the opposite M-bar channel or on a 2xATR initial stop.
    R is measured against the 2xATR initial risk."""
    h, l, c, o = (ltf[k].values for k in ("high", "low", "close", "open"))
    a = atr(ltf).values
    hh = pd.Series(h).rolling(n_in).max().shift(1).values
    ll = pd.Series(l).rolling(n_in).min().shift(1).values
    xh = pd.Series(h).rolling(n_out).max().shift(1).values
    xl = pd.Series(l).rolling(n_out).min().shift(1).values
    trades, pos = [], None
    for i in range(max(n_in, 60), len(ltf) - 1):
        if pos is None:
            side = 1 if c[i] > hh[i] else (-1 if c[i] < ll[i] else 0)
            if side:
                e = o[i + 1]
                risk = atr_mult * a[i]
                if risk > 0:
                    pos = {"side": side, "entry": e, "risk": risk, "stop": e - side * risk, "i": i + 1}
        else:
            s = pos["side"]
            hit_stop = (l[i] <= pos["stop"]) if s == 1 else (h[i] >= pos["stop"])
            exit_sig = (c[i] < xl[i]) if s == 1 else (c[i] > xh[i])
            if hit_stop or exit_sig:
                px = pos["stop"] if hit_stop else c[i]
                R = s * (px - pos["entry"]) / pos["risk"]
                trades.append({"time": str(ltf.index[pos["i"]]), "side": "long" if s == 1 else "short",
                               "exit_time": str(ltf.index[i]), "R_gross": round(float(R), 3),
                               "risk_pct": round(100 * pos["risk"] / pos["entry"], 3), "bars": i - pos["i"]})
                pos = None
    return trades


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("symbol")
    ap.add_argument("--tf", default="1h")
    ap.add_argument("--htf", default="4h")
    ap.add_argument("--days", type=int, default=1100)
    ap.add_argument("--out", default="lab_results")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        ltf = data.synthetic(a.symbol, a.tf, a.days * 1440 // MIN[a.tf], seed=11)
        htf = ltf.resample(f"{MIN[a.htf]}min").agg({"open": "first", "high": "max", "low": "min",
                                                      "close": "last", "volume": "sum"}).dropna()
    else:
        ltf = data.fetch_history(a.symbol, a.tf, a.days)
        htf = data.fetch_history(a.symbol, a.htf, a.days + 90)
    print(f"{a.symbol} {a.tf}/{a.htf}: {len(ltf)} candles {ltf.index[0]} -> {ltf.index[-1]}")
    res = {"symbol": a.symbol, "tf": a.tf, "htf": a.htf, "start": str(ltf.index[backtest.WARM]),
           "end": str(ltf.index[-1]), "bars_per_day": 1440 // MIN[a.tf],
           "buy_hold_pct": round(100 * (ltf.close.iloc[-1] / ltf.close.iloc[backtest.WARM] - 1), 1),
           "candidates": candidates_with_outcomes(a.symbol, ltf, htf, a.tf, a.htf),
           "donchian": {a.tf: donchian(ltf), a.htf: donchian(htf)}}
    print("candidates:", len(res["candidates"]), "donchian:", {k: len(v) for k, v in res["donchian"].items()})
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, f"{a.symbol}_{a.tf}.json"), "w") as f:
        json.dump(res, f)


if __name__ == "__main__":
    main()
