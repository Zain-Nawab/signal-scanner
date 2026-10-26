"""Indicator helpers (pandas/numpy only)."""
import numpy as np
import pandas as pd


def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def rsi(close, n=14):
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50)


def atr(df, n=14):
    pc = df["close"].shift()
    tr = pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def macd_hist(close, fast=12, slow=26, sig=9):
    m = ema(close, fast) - ema(close, slow)
    return m - ema(m, sig)


def vwap_daily(df):
    """VWAP anchored to each UTC day."""
    tp = (df["high"] + df["low"] + df["close"]) / 3
    day = df.index.floor("D")
    pv = (tp * df["volume"]).groupby(day).cumsum()
    v = df["volume"].groupby(day).cumsum()
    return pv / v.replace(0, np.nan)


def swings(df, n=3):
    """Confirmed pivots: a pivot at i is only known after n bars to its right
    (no repainting). Returns lists of (index_position, price)."""
    h, l = df["high"].values, df["low"].values
    highs, lows = [], []
    for i in range(n, len(df) - n):
        if h[i] == h[i - n:i + n + 1].max() and h[i] > h[i - 1]:
            highs.append((i, h[i]))
        if l[i] == l[i - n:i + n + 1].min() and l[i] < l[i - 1]:
            lows.append((i, l[i]))
    return highs, lows
