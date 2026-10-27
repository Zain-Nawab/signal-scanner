"""Market data with automatic fallback between public exchange endpoints.

Only CLOSED candles are returned. No API keys are used or needed.
"""
import numpy as np
import pandas as pd
import requests

import config

MIN = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440}
BYBIT_IV = {"5m": "5", "15m": "15", "30m": "30", "1h": "60", "4h": "240", "1d": "D"}
OKX_IV = {"5m": "5m", "15m": "15m", "30m": "30m", "1h": "1H", "4h": "4H", "1d": "1D"}
BINANCE_HOSTS = ["https://data-api.binance.vision", "https://api.binance.com"]


def _df(rows):
    df = pd.DataFrame(rows, columns=["t", "open", "high", "low", "close", "volume"])
    df.index = pd.to_datetime(df.pop("t").astype("int64"), unit="ms")
    return df.astype(float).sort_index()


def _binance(symbol, interval, limit):
    last = None
    for h in BINANCE_HOSTS:
        try:
            r = requests.get(f"{h}/api/v3/klines", timeout=12,
                             params={"symbol": symbol, "interval": interval, "limit": limit})
            r.raise_for_status()
            rows = [[k[0], k[1], k[2], k[3], k[4], k[5]] for k in r.json()]
            return _df(rows).iloc[:-1]            # last candle is still forming
        except Exception as e:
            last = e
    raise ConnectionError(str(last))


def _bybit(symbol, interval, limit):
    r = requests.get("https://api.bybit.com/v5/market/kline", timeout=12,
                     params={"category": "spot", "symbol": symbol,
                             "interval": BYBIT_IV[interval], "limit": limit})
    r.raise_for_status()
    j = r.json()
    if j.get("retCode") != 0:
        raise ConnectionError(j.get("retMsg"))
    rows = [[k[0], k[1], k[2], k[3], k[4], k[5]] for k in j["result"]["list"]]
    return _df(rows).iloc[:-1]                    # newest candle is forming


def _okx(symbol, interval, limit):
    inst = symbol[:-4] + "-" + symbol[-4:]       # BTCUSDT -> BTC-USDT
    r = requests.get("https://www.okx.com/api/v5/market/candles", timeout=12,
                     params={"instId": inst, "bar": OKX_IV[interval], "limit": min(limit, 300)})
    r.raise_for_status()
    j = r.json()
    if j.get("code") != "0":
        raise ConnectionError(j.get("msg"))
    rows = [[k[0], k[1], k[2], k[3], k[4], k[5]] for k in j["data"] if k[8] == "1"]  # confirmed only
    return _df(rows)


SOURCES = {"binance": _binance, "bybit": _bybit, "okx": _okx}


def fetch_pair(symbol, ltf=None, htf=None, limit=None):
    """Return (ltf_df, htf_df, source_name, errors) from the first source that works."""
    ltf, htf, limit = ltf or config.TIMEFRAME, htf or config.HTF, limit or config.CANDLES
    errors = {}
    for name in config.DATA_SOURCES:
        fn = SOURCES.get(name)
        if not fn:
            continue
        try:
            a, b = fn(symbol, ltf, limit), fn(symbol, htf, limit)
            if len(a) < 120 or len(b) < 60:
                raise ValueError(f"too few candles ({len(a)}/{len(b)})")
            return a, b, name, errors
        except Exception as e:
            errors[name] = str(e)[:160]
    raise ConnectionError(f"all sources failed: {errors}")


# ---- helpers used only by backtest.py ----------------------------------
def fetch_history(symbol, interval, days):
    """Page through Binance public klines to get `days` of closed candles."""
    import time
    end = int(time.time() * 1000)
    cur = end - days * 86_400_000
    step = MIN[interval] * 60_000
    rows = []
    while cur < end:
        last = None
        for attempt in range(4):
            for h in BINANCE_HOSTS:
                try:
                    r = requests.get(f"{h}/api/v3/klines", timeout=20,
                                     params={"symbol": symbol, "interval": interval,
                                             "startTime": cur, "endTime": end, "limit": 1000})
                    r.raise_for_status()
                    k = r.json()
                    break
                except Exception as e:
                    last, k = e, None
            if k is not None:
                break
            time.sleep(2 * (attempt + 1))
        if k is None:
            raise ConnectionError(f"history fetch failed: {last}")
        if not k:
            break
        rows += [[x[0], x[1], x[2], x[3], x[4], x[5]] for x in k]
        cur = k[-1][0] + step
        if len(k) < 1000:
            break
    df = _df(rows)
    df = df[~df.index.duplicated()]
    return df.iloc[:-1]                           # drop the still-forming candle


def synthetic(symbol, interval, limit=500, seed=None):
    """Regime-switching random walk with volume spikes - demo/testing only."""
    rng = np.random.default_rng(seed if seed is not None else abs(hash((symbol, interval))) % 2**32)
    n = limit
    drift = np.zeros(n)
    i = 0
    while i < n:
        L = rng.integers(40, 120)
        drift[i:i + L] = rng.choice([-1, 0, 1]) * 0.0004
        i += L
    ret = drift + rng.normal(0, 0.004, n)
    close = 100 * np.exp(np.cumsum(ret))
    open_ = np.r_[close[0], close[:-1]]
    wick = np.abs(rng.normal(0, 0.003, (n, 2))) * close[:, None]
    high = np.maximum(open_, close) + wick[:, 0]
    low = np.minimum(open_, close) - wick[:, 1]
    vol = rng.lognormal(0, 0.45, n) * 1000 * (1 + 4 * (np.abs(ret) > 0.007))
    end = pd.Timestamp.utcnow().floor("min").tz_localize(None)
    idx = pd.date_range(end=end, periods=n, freq=f"{MIN[interval]}min")
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": vol}, index=idx)


def get(symbol, interval, limit=500):
    """(df, is_demo). Tries live sources, falls back to synthetic only if allowed."""
    for name in config.DATA_SOURCES:
        try:
            return SOURCES[name](symbol, interval, limit), False
        except Exception:
            continue
    if not config.ALLOW_DEMO_DATA:
        raise ConnectionError("no live data source reachable")
    return synthetic(symbol, interval, limit), True
