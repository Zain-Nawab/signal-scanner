"""Daily trend-following portfolio test: an ensemble of channel-breakout systems.

Pre-specified BEFORE looking at results (to limit overfitting): entry lookbacks 10, 20 and 50 days,
exit lookback = half of the entry lookback, 2xATR initial stop, enter at the next open, long and short,
18 liquid coins that exist today (survivorship bias: coins that died are missing, which flatters long
results). Costs: 0.14% round trip (futures taker + slippage) plus 0.02% per day funding drag (a
conservative flat assumption), converted into R. Spot (long only) uses 0.26% round trip, no funding.

    python trend_lab.py --days 2300 --out trend
"""
import argparse
import json
import os

import numpy as np
import pandas as pd

import data
import lab

COINS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "SOLUSDT", "ADAUSDT", "DOGEUSDT", "TRXUSDT", "LINKUSDT",
         "AVAXUSDT", "DOTUSDT", "LTCUSDT", "BCHUSDT", "ATOMUSDT", "UNIUSDT", "ETCUSDT", "NEARUSDT", "FILUSDT"]
LOOKBACKS = (10, 20, 50)
ATR_MULT = 2.0
RISK_PER_TRADE_PCT = 0.5          # % of account risked per position when sizing (additive approximation)
FUT_RT, SPOT_RT, FUNDING_DAY = 0.14, 0.26, 0.02


def run(days):
    rows, bh = [], {}
    for sym in COINS:
        try:
            df = data.fetch_history(sym, "1d", days)
        except Exception as e:
            print("skip", sym, str(e)[:80])
            continue
        bh[sym] = {str(y): round(100 * (g.close.iloc[-1] / g.close.iloc[0] - 1), 1) for y, g in df.groupby(df.index.year)}
        for lb in LOOKBACKS:
            for t in lab.donchian(df, n_in=lb, n_out=max(lb // 2, 3), atr_mult=ATR_MULT):
                rows.append({**t, "symbol": sym, "lb": lb})
        print(sym, len(df), "days", df.index[0].date())
    t = pd.DataFrame(rows)
    t["time"], t["exit_time"] = pd.to_datetime(t.time), pd.to_datetime(t.exit_time)
    return t, bh


def apply_costs(t, mode):
    t = t.copy()
    if mode == "futures":
        t["R"] = t.R_gross - (FUT_RT + FUNDING_DAY * t.bars) / t.risk_pct
    else:                                           # spot, long only
        t = t[t.side == "long"].copy()
        t["R"] = t.R_gross - SPOT_RT / t.risk_pct
    return t


def stats(r):
    r = np.asarray(r, float)
    n = len(r)
    if n == 0:
        return "| 0 | | | | |"
    w, l = r[r > 0].sum(), -r[r < 0].sum()
    ci = 1.96 * r.std(ddof=1) / np.sqrt(n) if n > 1 else float("nan")
    return f"| {n} | {100 * (r > 0).mean():.0f}% | {r.mean():+.2f} (±{ci:.2f}) | {r.sum():+.0f} | {w / l if l else float('inf'):.2f} |"


def max_dd_r(t):
    eq = t.sort_values("exit_time").R.cumsum().values
    return float((np.maximum.accumulate(eq) - eq).max()) if len(eq) else 0.0


def report(t, bh):
    L = ["# Daily trend-following test", "",
         f"{t.symbol.nunique()} coins, {t.time.min():%Y-%m-%d} to {t.exit_time.max():%Y-%m-%d}. Ensemble of channel-breakout systems "
         f"(entry lookbacks {LOOKBACKS} days, exit at half the lookback, {ATR_MULT}xATR stop, next-open entry). "
         f"Sizing view: each trade risks {RISK_PER_TRADE_PCT}% of the account, so total R x {RISK_PER_TRADE_PCT}% = account return before compounding. "
         "Costs: futures 0.14% round trip + 0.02%/day funding; spot 0.26% round trip, long only. "
         "Survivorship bias: only coins that exist today are included, which flatters long results.", ""]
    for mode, label in (("futures", "Futures (long + short)"), ("spot", "Spot (long only)")):
        c = apply_costs(t, mode)
        L += [f"## {label}", "", "| Group | Trades | Win | Avg R net (95% CI) | Total R | Profit factor |", "|---|---|---|---|---|---|"]
        L.append("| All lookbacks combined " + stats(c.R)[0:].replace("| ", "", 1) if False else f"| All lookbacks combined {stats(c.R)}")
        for lb in LOOKBACKS:
            L.append(f"| Lookback {lb} days {stats(c[c.lb == lb].R)}")
        if mode == "futures":
            for sd in ("long", "short"):
                L.append(f"| {sd} only {stats(c[c.side == sd].R)}")
        L += ["", f"Max drawdown on realized trades (all combined): {max_dd_r(c):.1f} R = {max_dd_r(c) * RISK_PER_TRADE_PCT:.0f}% of the account at {RISK_PER_TRADE_PCT}% risk per trade.", "",
              "### By calendar year (all lookbacks, by exit date)", "", "| Year | Trades | Win | Avg R net | Total R | Account return at 0.5% risk/trade | Equal-weight buy-and-hold of these coins |", "|---|---|---|---|---|---|---|"]
        for y, g in c.groupby(c.exit_time.dt.year):
            bhy = np.mean([v[str(y)] for v in bh.values() if str(y) in v])
            L.append(f"| {y} | {len(g)} | {100 * (g.R > 0).mean():.0f}% | {g.R.mean():+.2f} | {g.R.sum():+.0f} | {g.R.sum() * RISK_PER_TRADE_PCT:+.0f}% | {bhy:+.0f}% |")
        L += ["", "### By coin (all years)", "", "| Coin | Trades | Avg R net | Total R |", "|---|---|---|---|"]
        for s, g in c.groupby("symbol"):
            L.append(f"| {s} | {len(g)} | {g.R.mean():+.2f} | {g.R.sum():+.0f} |")
        # concurrency
        ev = sorted([(a, 1) for a in c.time] + [(b, -1) for b in c.exit_time])
        cur = mx = 0
        for _, d in ev:
            cur += d
            mx = max(mx, cur)
        L += ["", f"Most positions open at once: {mx}. Average holding time: {c.bars.mean():.0f} days.", ""]
    return "\n".join(L)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=2300)
    ap.add_argument("--out", default="trend")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        COINS[:] = ["AAA", "BBB", "CCC"]
        data.fetch_history = lambda s, tf, d: data.synthetic(s, "1d", d, seed=abs(hash(s)) % 999)
    t, bh = run(a.days)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    md = report(t, bh)
    open(a.out + ".md", "w").write(md)
    t.to_csv(a.out + "_trades.csv", index=False)
    print(md)
