"""Combine per-coin backtest results into report.md / summary.json.

    python report.py results/ --out report
Splits trades at the midpoint of the test period: first half = in-sample (where rules were
designed and looked at), second half = out-of-sample (the number that matters).
"""
import argparse
import glob
import json
import os

import numpy as np
import pandas as pd


def stats(r):
    r = np.asarray(r, dtype=float)
    n = len(r)
    if n == 0:
        return {"n": 0}
    w, l = r[r > 0].sum(), -r[r < 0].sum()
    eq = np.cumsum(r)
    ci = 1.96 * r.std(ddof=1) / np.sqrt(n) if n > 1 else float("nan")
    return {"n": n, "win": round(100 * (r > 0).mean()), "avg": round(r.mean(), 3), "ci": round(ci, 3),
            "total": round(r.sum(), 1), "pf": round(w / l, 2) if l > 0 else float("inf"),
            "dd": round((np.maximum.accumulate(eq) - eq).max(), 1)}


def fmt(s):
    if not s["n"]:
        return "| 0 | | | | | |"
    return f"| {s['n']} | {s['win']}% | {s['avg']:+.3f} (±{s['ci']:.3f}) | {s['total']:+.1f} | {s['pf']} | {s['dd']} |"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results_dir")
    ap.add_argument("--out", default="report")
    a = ap.parse_args()
    files = sorted(glob.glob(os.path.join(a.results_dir, "*.json")))
    res = [json.load(open(f)) for f in files]
    start = min(pd.Timestamp(r["start"]) for r in res)
    end = max(pd.Timestamp(r["end"]) for r in res)
    mid = start + (end - start) / 2
    names = list(res[0]["variants"].keys())
    L = [f"# Backtest report", "",
         f"Period {start:%Y-%m-%d} to {end:%Y-%m-%d}; split at {mid:%Y-%m-%d} (first half in-sample, second half out-of-sample).",
         f"Coins: {', '.join(r['symbol'] for r in res)}. Costs: {res[0]['fee_per_side']*100:.2f}% fee + {res[0]['slip_per_side']*100:.2f}% slippage per side. "
         "Entry at next candle open. R = profit in units of initial risk, net of costs. (±) is the 95% confidence half-width of the average.", "",
         "Coin moves over the period (buy and hold): " + ", ".join(f"{r['symbol']} {r['buy_hold_pct']:+.0f}%" for r in res), ""]
    summary = {}
    hdr = "| Trades | Win | Avg net R (95% CI) | Total R | Profit factor | Max drawdown R |\n|---|---|---|---|---|---|"
    for name in names:
        rows = []
        for r in res:
            for t in r["variants"][name]:
                rows.append({**t, "symbol": r["symbol"]})
        df = pd.DataFrame(rows)
        L += [f"## {name}", "", "| Period | " + hdr.split("\n")[0][2:], "|---" + hdr.split("\n")[1], ]
        summary[name] = {}
        for label, sel in (("In-sample", lambda d: d[pd.to_datetime(d.time) < mid]),
                           ("Out-of-sample", lambda d: d[pd.to_datetime(d.time) >= mid]),
                           ("All", lambda d: d)):
            sub = sel(df) if len(df) else df
            s = stats(sub["R_net"].values if len(sub) else [])
            g = stats(sub["R_gross"].values if len(sub) else [])
            summary[name][label] = {**s, "avg_gross": g.get("avg")}
            L.append(f"| {label} " + fmt(s))
        L.append("")
        if len(df):
            L += ["", f"Average cost per trade: {df.cost_R.mean():.2f} R; median stop distance {df.risk_pct.median():.2f}% of price; "
                      f"average gross R {df.R_gross.mean():+.3f}.", ""]
            if name.startswith("default"):
                L += ["Out-of-sample by coin:", "", "| Coin " + hdr.split("\n")[0][2:], "|---" + hdr.split("\n")[1]]
                oos = df[pd.to_datetime(df.time) >= mid]
                for sym, g in oos.groupby("symbol"):
                    L.append(f"| {sym} " + fmt(stats(g.R_net.values)))
                L.append("")
    with open(a.out + ".md", "w") as f:
        f.write("\n".join(L))
    with open(a.out + ".json", "w") as f:
        json.dump(summary, f, indent=1)
    print("\n".join(L))


if __name__ == "__main__":
    main()
