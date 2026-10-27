# Backtest report

Period 2025-10-29 to 2026-10-27; split at 2026-04-28 (first half in-sample, second half out-of-sample).
Coins: BNBUSDT, BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT. Costs: 0.10% fee + 0.03% slippage per side. Entry at next candle open. R = profit in units of initial risk, net of costs. (±) is the 95% confidence half-width of the average.

Coin moves over the period (buy and hold): BNBUSDT -34%, BTCUSDT -29%, ETHUSDT -42%, SOLUSDT -49%, XRPUSDT -51%

## default (score>=3, TP 2R/3R)

| Period | Trades | Win | Avg net R (95% CI) | Total R | Profit factor | Max drawdown R |
|---|---|---|---|---|---|---|
| In-sample | 12 | 25% | -0.893 (±0.827) | -10.7 | 0.28 | 9.4 |
| Out-of-sample | 7 | 43% | -0.452 (±1.380) | -3.2 | 0.59 | 7.6 |
| All | 19 | 32% | -0.730 (±0.712) | -13.9 | 0.39 | 15.2 |


Average cost per trade: 0.76 R; median stop distance 0.32% of price; average gross R +0.031.

Out-of-sample by coin:

| Coin Trades | Win | Avg net R (95% CI) | Total R | Profit factor | Max drawdown R |
|---|---|---|---|---|---|---|
| BNBUSDT | 3 | 100% | +1.486 (±0.617) | +4.5 | inf | 0.0 |
| BTCUSDT | 2 | 0% | -2.223 (±0.041) | -4.4 | 0.0 | 2.2 |
| ETHUSDT | 2 | 0% | -1.588 (±0.446) | -3.2 | 0.0 | 1.8 |

## looser (score>=2)

| Period | Trades | Win | Avg net R (95% CI) | Total R | Profit factor | Max drawdown R |
|---|---|---|---|---|---|---|
| In-sample | 128 | 29% | -0.726 (±0.266) | -92.9 | 0.38 | 96.7 |
| Out-of-sample | 118 | 31% | -0.806 (±0.313) | -95.1 | 0.36 | 100.2 |
| All | 246 | 30% | -0.764 (±0.204) | -188.0 | 0.37 | 193.6 |


Average cost per trade: 0.81 R; median stop distance 0.42% of price; average gross R +0.049.

## strict (score=4 only)

| Period | Trades | Win | Avg net R (95% CI) | Total R | Profit factor | Max drawdown R |
|---|---|---|---|---|---|---|
| In-sample | 0 | | | | | |
| Out-of-sample | 0 | | | | | |
| All | 0 | | | | | |

## score>=3, TP 1.5R/2.5R

| Period | Trades | Win | Avg net R (95% CI) | Total R | Profit factor | Max drawdown R |
|---|---|---|---|---|---|---|
| In-sample | 12 | 25% | -0.748 (±0.782) | -9.0 | 0.32 | 7.6 |
| Out-of-sample | 7 | 43% | -0.667 (±1.188) | -4.7 | 0.39 | 7.6 |
| All | 19 | 32% | -0.718 (±0.640) | -13.6 | 0.35 | 12.9 |


Average cost per trade: 0.76 R; median stop distance 0.32% of price; average gross R +0.044.

## score>=3, TP 1R/2R

| Period | Trades | Win | Avg net R (95% CI) | Total R | Profit factor | Max drawdown R |
|---|---|---|---|---|---|---|
| In-sample | 12 | 17% | -0.852 (±0.591) | -10.2 | 0.18 | 8.9 |
| Out-of-sample | 7 | 29% | -0.882 (±0.998) | -6.2 | 0.2 | 7.6 |
| All | 19 | 21% | -0.863 (±0.507) | -16.4 | 0.18 | 15.1 |


Average cost per trade: 0.76 R; median stop distance 0.32% of price; average gross R -0.102.

## REVERSED default (sanity check)

| Period | Trades | Win | Avg net R (95% CI) | Total R | Profit factor | Max drawdown R |
|---|---|---|---|---|---|---|
| In-sample | 12 | 33% | -0.799 (±0.830) | -9.6 | 0.3 | 9.9 |
| Out-of-sample | 7 | 14% | -1.453 (±1.072) | -10.2 | 0.14 | 9.3 |
| All | 19 | 26% | -1.040 (±0.655) | -19.8 | 0.23 | 20.1 |


Average cost per trade: 0.76 R; median stop distance 0.32% of price; average gross R -0.281.
