"""Turn lab results into a decision report.

    python analyze.py lab_results --out analysis

Train = everything before the last 365 days. Test = the last 365 days, looked at ONCE for the
configuration that won on train. Also reports how many configurations look good on train but fail on
test (a measure of luck vs skill) and the rank correlation between train and test results.
"""
import argparse
import glob
import itertools
import json
import os

import numpy as np
import pandas as pd

COOL = 8
COSTS = {"futures_taker": 0.14, "spot": 0.26}     # round-trip cost, % of price (fee + slippage, both sides)
CATS = ["structure", "vsa", "price", "momentum"]
TPS = ["1_2", "1.5_2.5", "2_3", "3_4.5"]


def load(d):
    cands, don, meta = [], [], []
    for f in sorted(glob.glob(os.path.join(d, "*.json"))):
        r = json.load(open(f))
        meta.append({k: r[k] for k in ("symbol", "tf", "htf", "start", "end", "buy_hold_pct")})
        for c in r["candidates"]:
            cands.append({**c, "symbol": r["symbol"], "tf": r["tf"]})
        for tf, tr in r["donchian"].items():
            if tf == r["tf"] or tf == "1d":
                for t in tr:
                    don.append({**t, "symbol": r["symbol"], "tf": tf})
    df = pd.DataFrame(cands)
    df["time"] = pd.to_datetime(df["time"])
    dn = pd.DataFrame(don).drop_duplicates(["symbol", "tf", "time", "side"])
    dn["time"] = pd.to_datetime(dn["time"])
    return df, dn, pd.DataFrame(meta)


def cooled(df, bars=COOL):
    keep = []
    for _, g in df.sort_values("i").groupby(["symbol", "tf"]):
        last = -10 ** 9
        for idx, i in zip(g.index, g["i"]):
            if i - last >= bars:
                keep.append(idx)
                last = i
    return df.loc[keep]


def net(df, tp, cost):
    return df["R_" + tp] - cost / df["risk_pct"]


def st(r):
    r = np.asarray(r, float)
    n = len(r)
    if n == 0:
        return dict(n=0, avg=np.nan, ci=np.nan, pf=np.nan, win=np.nan)
    w, l = r[r > 0].sum(), -r[r < 0].sum()
    return dict(n=n, avg=r.mean(), ci=1.96 * r.std(ddof=1) / np.sqrt(n) if n > 1 else np.nan,
                pf=w / l if l > 0 else np.inf, win=100 * (r > 0).mean())


def line(label, s):
    if s["n"] == 0:
        return f"| {label} | 0 | | | | |"
    return f"| {label} | {s['n']} | {s['win']:.0f}% | {s['avg']:+.3f} (±{s['ci']:.3f}) | {s['pf']:.2f} |"


def passes(s):
    return s["n"] >= 100 and s["avg"] - s["ci"] > 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--out", default="analysis")
    a = ap.parse_args()
    df, dn, meta = load(a.dir)
    end = pd.to_datetime(meta["end"]).max()
    cutoff = end - pd.Timedelta(days=365)
    L = ["# Strategy lab report", "",
         f"Data: {meta.symbol.nunique()} coins, timeframes {', '.join(sorted(meta.tf.unique()))}, "
         f"{pd.to_datetime(meta.start).min():%Y-%m-%d} to {end:%Y-%m-%d}. "
         f"Train = before {cutoff:%Y-%m-%d}; test = the final 365 days (used once). "
         f"Costs are round-trip % of price: futures taker {COSTS['futures_taker']}% (0.05% fee + 0.02% slippage per side), "
         f"spot {COSTS['spot']}% (0.10% + 0.03% per side). Average result is in R (multiples of the initial risk); "
         "(±) is the 95% confidence half-width. A result counts as proven only if its lower bound is above 0 with 100+ trades.", ""]
    out = {}

    # ---- 1. which confirmations carry an edge (gross, before costs) ------------------------------
    L += ["## 1. Do the confirmations carry any edge? (before costs, target 2R/3R, cooldown applied)", ""]
    for tf in sorted(df.tf.unique()):
        d = df[(df.tf == tf) & df["R_2_3"].notna()]
        L += [f"### {tf} entries", "", "| Subset | Trades | Win | Avg gross R (95% CI) | Profit factor |", "|---|---|---|---|---|"]
        rows = [("all candidates (score>=2)", d)] + [(f"score = {k}", d[d.score == k]) for k in (2, 3, 4)]
        for c in CATS:
            rows += [(f"{c} present", d[d.cats.apply(lambda x: c in x)]), (f"{c} absent", d[d.cats.apply(lambda x: c not in x)])]
        rows += [("long only", d[d.side == "long"]), ("short only", d[d.side == "short"])]
        for label, sub in rows:
            sub = cooled(sub) if len(sub) else sub
            L.append(line(label, st(sub["R_2_3"].values if len(sub) else [])))
        L.append("")

    # ---- 2. configuration grid with strict train/test ------------------------------------------
    L += ["## 2. Best configurations chosen on train, then checked on the untouched final year", ""]
    grid = []
    for tf in sorted(df.tf.unique()):
        d = df[df.tf == tf]
        for score, minrisk, side, tp, vol in itertools.product((2, 3), (0, 0.5, 1, 2), ("both", "long"), ("2_3", "1.5_2.5"), (False, True)):
            m = (d.score >= score) & (d.risk_pct >= minrisk) & d["R_" + tp].notna()
            if side == "long":
                m &= d.side == "long"
            if vol:
                m &= d.atr_ratio < 2
            sub = cooled(d[m]) if m.any() else d[m]
            tr, te = sub[sub.time < cutoff], sub[sub.time >= cutoff]
            row = dict(tf=tf, cfg=f"score>={score}, stop>={minrisk}%, {side}, TP {tp}, vol-filter={'on' if vol else 'off'}")
            for nm, x in (("tr", tr), ("te", te)):
                s = st(net(x, tp, COSTS["futures_taker"]).values if len(x) else [])
                row.update({f"n_{nm}": s["n"], f"avg_{nm}": s["avg"], f"ci_{nm}": s["ci"], f"pf_{nm}": s["pf"], f"win_{nm}": s["win"]})
            row["avg_te_spot"] = st(net(te, tp, COSTS["spot"]).values if len(te) else [])["avg"]
            row["avg_tr_gross"] = st(tr["R_" + tp].values if len(tr) else [])["avg"]
            grid.append(row)
    g = pd.DataFrame(grid)
    out["grid"] = g.replace([np.inf, -np.inf], None).to_dict("records")
    for tf in sorted(g.tf.unique()):
        x = g[(g.tf == tf) & (g.n_tr >= 100)].copy()
        L += [f"### {tf} entries", ""]
        if x.empty:
            L += ["Not enough trades on train for any configuration (needs 100+).", ""]
            continue
        top = x.sort_values("avg_tr", ascending=False).head(3)
        L += ["| Config (picked by train result) | Train trades | Train avg R | TEST trades | TEST avg R (95% CI) | TEST profit factor | Test avg R if spot fees | Verdict |",
              "|---|---|---|---|---|---|---|---|"]
        for _, r in top.iterrows():
            ok = r.n_te >= 100 and r.avg_te - r.ci_te > 0
            L.append(f"| {r.cfg} | {r.n_tr:.0f} | {r.avg_tr:+.3f} | {r.n_te:.0f} | {r.avg_te:+.3f} (±{r.ci_te:.3f}) | {r.pf_te:.2f} | {r.avg_te_spot:+.3f} | {'PASS' if ok else 'not proven'} |")
        sk = x.dropna(subset=["avg_tr", "avg_te"])
        rho = sk["avg_tr"].rank().corr(sk["avg_te"].rank()) if len(sk) > 3 else float("nan")
        L += ["", f"Luck check ({len(x)} configurations with 100+ train trades): {100 * (x.avg_tr > 0).mean():.0f}% were profitable on train, "
                  f"{100 * (x.avg_te > 0).mean():.0f}% on test; rank correlation between train and test results {rho:+.2f} "
                  "(near 0 means train performance did not predict test performance, i.e. mostly luck). "
                  f"Best gross (pre-cost) train average: {x.avg_tr_gross.max():+.3f} R.", ""]

    # ---- 3. trend-following benchmark -------------------------------------------------------------
    L += ["## 3. Benchmark: simple trend following (20-bar channel breakout, 10-bar exit, 2xATR stop)", "",
          "| Timeframe / side / costs | Period | Trades | Win | Avg R (95% CI) | Profit factor |", "|---|---|---|---|---|---|"]
    dn_out = {}
    for tf in sorted(dn.tf.unique()):
        d = dn[dn.tf == tf]
        for side in ("both", "long"):
            x = d if side == "both" else d[d.side == "long"]
            for cn, cv in COSTS.items():
                for per, y in (("train", x[x.time < cutoff]), ("TEST", x[x.time >= cutoff])):
                    s = st((y.R_gross - cv / y.risk_pct).values if len(y) else [])
                    dn_out[f"{tf}/{side}/{cn}/{per}"] = {k: (None if isinstance(v, float) and not np.isfinite(v) else v) for k, v in s.items()}
                    if cn == "futures_taker":
                        L.append(line(f"{tf} / {side} / {cn}", s).replace(" | ", f" | {per} | ", 1))
    out["donchian"] = dn_out
    L.append("")

    # ---- 4. context --------------------------------------------------------------------------------
    L += ["## 4. Market context", "", "Buy-and-hold change over each job's whole period (the market the strategies were tested in):", ""]
    ctx = meta.groupby("symbol").buy_hold_pct.agg(["min", "max"])
    L.append(", ".join(f"{s} {r['min']:+.0f}% to {r['max']:+.0f}%" for s, r in ctx.iterrows()) + " (range across timeframes because start dates differ slightly).")
    with open(a.out + ".md", "w") as f:
        f.write("\n".join(L))
    with open(a.out + ".json", "w") as f:
        json.dump(out, f, default=str)
    print("\n".join(L))


if __name__ == "__main__":
    main()
