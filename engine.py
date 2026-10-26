"""Signal engine.

A setup must (1) agree with the higher-timeframe trend, (2) be confirmed by at
least MIN_CATEGORIES of 4 independent categories, (3) offer a sane stop, and
(4) have room to reach target before the nearest opposing swing level.

Categories:
  structure  - market structure (HH/HL or LH/LL, break of structure)
  vsa        - Volume Spread Analysis on the signal candle
  price      - price action (pin bar, engulfing, liquidity sweep) at a key level
  momentum   - RSI / MACD / EMA reclaim
Only the last *closed* candle is evaluated, so signals do not repaint.
"""
from dataclasses import dataclass, field, asdict
import numpy as np
import pandas as pd

import config
from indicators import ema, rsi, atr, macd_hist, vwap_daily, swings

CATS = ["structure", "vsa", "price", "momentum"]


@dataclass
class Signal:
    symbol: str
    side: str
    time: str
    entry: float
    stop: float
    tp1: float
    tp2: float
    rr1: float
    grade: str
    score: int
    reasons: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


def prepare(df):
    d = df.copy()
    d["ema21"], d["ema50"] = ema(d.close, 21), ema(d.close, 50)
    d["rsi"], d["atr"] = rsi(d.close), atr(d)
    d["mh"] = macd_hist(d.close)
    d["vwap"] = vwap_daily(d)
    d["vol_avg"] = d.volume.rolling(20).mean()
    d["spr_avg"] = (d.high - d.low).rolling(20).mean()
    return d


def htf_trend(htf):
    """+1 up, -1 down, 0 neutral from the higher timeframe (closed candles)."""
    e21, e50 = ema(htf.close, 21), ema(htf.close, 50)
    c, a, b = htf.close.iloc[-1], e21.iloc[-1], e50.iloc[-1]
    slope = e50.iloc[-1] - e50.iloc[-4]
    if a > b and c > b and slope > 0:
        return 1
    if a < b and c < b and slope < 0:
        return -1
    return 0


# ---------------------------------------------------------------- categories
def structure(d, highs, lows, side):
    """Returns (ok, text)."""
    i, c, a = len(d) - 1, d.close.iloc[-1], d.atr.iloc[-1]
    if len(highs) < 2 or len(lows) < 2:
        return False, ""
    (_, h1), (_, h2) = highs[-2], highs[-1]
    (_, l1), (_, l2) = lows[-2], lows[-1]
    near21 = abs(c - d.ema21.iloc[-1]) < 2.5 * a  # not overextended
    if side == "long":
        trend = h2 > h1 and l2 > l1
        bos = any(d.close.iloc[-k] > h2 for k in range(1, 4)) and d.close.iloc[-8:-3].max() <= h2 * 1.002
        if (trend or bos) and near21:
            return True, "HH/HL structure intact" if trend else "Bullish break of structure"
    else:
        trend = h2 < h1 and l2 < l1
        bos = any(d.close.iloc[-k] < l2 for k in range(1, 4)) and d.close.iloc[-8:-3].min() >= l2 * 0.998
        if (trend or bos) and near21:
            return True, "LH/LL structure intact" if trend else "Bearish break of structure"
    return False, ""


def vsa(d, side):
    x, p = d.iloc[-1], d.iloc[-2]
    spread = x.high - x.low
    if spread <= 0 or np.isnan(x.vol_avg):
        return False, ""
    cp = (x.close - x.low) / spread          # close position in range
    rv = x.volume / x.vol_avg                # relative volume
    wide, narrow = spread > 1.3 * x.spr_avg, spread < 0.8 * x.spr_avg
    lo20, hi20 = d.low.iloc[-21:-1].min(), d.high.iloc[-21:-1].max()
    low_vol = x.volume < min(p.volume, d.volume.iloc[-3])
    down_bar, up_bar = x.close < p.close, x.close > p.close
    if side == "long":
        if x.low < lo20 and cp > 0.55 and rv > 1.2:
            return True, f"Spring / stopping volume (rv {rv:.1f}x, closed in upper range)"
        if x.close < d.ema50.iloc[-1] and rv > 1.8 and wide and cp > 0.5:
            return True, f"Selling climax absorbed (rv {rv:.1f}x)"
        if down_bar and narrow and low_vol and x.close > d.ema50.iloc[-1]:
            return True, "No supply (narrow down bar on low volume)"
        if rv > 1.5 and narrow and cp > 0.6 and p.close < p.open:
            return True, "Absorption: effort without result at lows"
    else:
        if x.high > hi20 and cp < 0.45 and rv > 1.2:
            return True, f"Upthrust (rv {rv:.1f}x, closed in lower range)"
        if x.close > d.ema50.iloc[-1] and rv > 1.8 and wide and cp < 0.5:
            return True, f"Buying climax (rv {rv:.1f}x)"
        if up_bar and narrow and low_vol and x.close < d.ema50.iloc[-1]:
            return True, "No demand (narrow up bar on low volume)"
        if rv > 1.5 and narrow and cp < 0.4 and p.close > p.open:
            return True, "Absorption: effort without result at highs"
    return False, ""


def price_action(d, highs, lows, side):
    x, p = d.iloc[-1], d.iloc[-2]
    body, rng, a = abs(x.close - x.open), x.high - x.low, d.atr.iloc[-1]
    if rng <= 0:
        return False, ""
    up_w, lo_w = x.high - max(x.open, x.close), min(x.open, x.close) - x.low
    sup = [v for _, v in lows[-3:]]
    res = [v for _, v in highs[-3:]]
    if side == "long":
        at_level = any(abs(x.low - s) < 0.75 * a for s in sup[-2:]) or abs(x.low - d.ema50.iloc[-1]) < 0.5 * a
        if any(x.low < s - 0.1 * a and s < x.close for s in sup[-2:]):
            return True, "Liquidity sweep below swing low, reclaimed"
        if at_level and lo_w >= 2 * max(body, 1e-9) and lo_w >= 0.5 * rng and x.close > x.open - 0.0:
            return True, "Bullish pin bar at support"
        if at_level and x.close > x.open and p.close < p.open and x.close > p.open and x.open <= p.close and body > 0.8 * a * 0.5:
            return True, "Bullish engulfing at support"
    else:
        at_level = any(abs(x.high - r) < 0.75 * a for r in res[-2:]) or abs(x.high - d.ema50.iloc[-1]) < 0.5 * a
        if any(x.high > r + 0.1 * a and x.close < r for r in res[-2:]):
            return True, "Liquidity sweep above swing high, rejected"
        if at_level and up_w >= 2 * max(body, 1e-9) and up_w >= 0.5 * rng:
            return True, "Bearish pin bar at resistance"
        if at_level and x.close < x.open and p.close > p.open and x.close < p.open and x.open >= p.close and body > 0.8 * a * 0.5:
            return True, "Bearish engulfing at resistance"
    return False, ""


def momentum(d, side):
    x = d.iloc[-1]
    pts, why = 0, []
    r, h = d.rsi, d["mh"]
    if side == "long":
        if r.iloc[-1] > r.iloc[-2] and r.iloc[-6:-1].min() < 40:
            pts += 1; why.append("RSI turning up from <40")
        if h.iloc[-1] > h.iloc[-2] > h.iloc[-3]:
            pts += 1; why.append("MACD histogram rising")
        if x.close > x.ema21 and d.close.iloc[-2] <= d.ema21.iloc[-2] or x.close > x.vwap > x.open:
            pts += 1; why.append("Reclaimed EMA21/VWAP")
    else:
        if r.iloc[-1] < r.iloc[-2] and r.iloc[-6:-1].max() > 60:
            pts += 1; why.append("RSI turning down from >60")
        if h.iloc[-1] < h.iloc[-2] < h.iloc[-3]:
            pts += 1; why.append("MACD histogram falling")
        if x.close < x.ema21 and d.close.iloc[-2] >= d.ema21.iloc[-2] or x.close < x.vwap < x.open:
            pts += 1; why.append("Lost EMA21/VWAP")
    return pts >= 2, " + ".join(why)


# ---------------------------------------------------------------------- main
def evaluate(symbol, ltf, htf, detail=False):
    """Evaluate the last closed candle. ltf/htf must contain closed candles only.
    Returns a Signal or None (or a status dict when detail=True)."""
    if len(ltf) < 120 or len(htf) < 60:
        return (None, {}) if detail else None
    d = prepare(ltf)
    highs, lows = swings(d.iloc[-150:].reset_index(), n=3)
    trend = htf_trend(htf)
    x, a = d.iloc[-1], d.atr.iloc[-1]
    status = {}
    best = None
    for side in ("long", "short"):
        want = 1 if side == "long" else -1
        res = {
            "structure": structure(d.iloc[-150:], highs, lows, side),
            "vsa": vsa(d, side),
            "price": price_action(d.iloc[-150:], highs, lows, side),
            "momentum": momentum(d, side),
        }
        score = sum(ok for ok, _ in res.values())
        status[side] = {"score": score, "htf_ok": trend == want,
                        "cats": {k: v[0] for k, v in res.items()}}
        if trend != want or score < config.MIN_CATEGORIES:
            continue
        # --- trade plan
        base = d.iloc[-150:]
        off = len(d) - 150
        if side == "long":
            swing = min([v for i, v in lows[-2:]] + [x.low])
            stop = swing - config.ATR_SL_MULT * a
            risk = x.close - stop
            tp1, tp2 = x.close + config.TP_RR * risk, x.close + config.TP2_RR * risk
            blockers = [v for _, v in highs if v > x.close]
            room = (min(blockers) - x.close) / risk if blockers else 99
        else:
            swing = max([v for i, v in highs[-2:]] + [x.high])
            stop = swing + config.ATR_SL_MULT * a
            risk = stop - x.close
            tp1, tp2 = x.close - config.TP_RR * risk, x.close - config.TP2_RR * risk
            blockers = [v for _, v in lows if v < x.close]
            room = (x.close - max(blockers)) / risk if blockers else 99
        if risk <= 0 or risk > 3 * a or risk < 0.4 * a:
            status[side]["rejected"] = "stop distance out of range"; continue
        if room < config.MIN_RR:
            status[side]["rejected"] = "no room to target (opposing swing too close)"; continue
        sig = Signal(symbol, side, str(d.index[-1]), round(x.close, 6), round(stop, 6),
                     round(tp1, 6), round(tp2, 6), round(config.TP_RR, 2),
                     "A" if score == 4 else "B", score,
                     {k: v[1] for k, v in res.items() if v[0]})
        sig.reasons["htf"] = "1H trend " + ("up" if trend == 1 else "down")
        if best is None or sig.score > best.score:
            best = sig
    status["htf_trend"] = trend
    status["price"] = float(x.close)
    return (best, status) if detail else best
