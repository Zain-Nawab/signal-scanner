# Daily trend-following test

18 coins, 2020-09-13 to 2026-10-22. Ensemble of channel-breakout systems (entry lookbacks (10, 20, 50) days, exit at half the lookback, 2.0xATR stop, next-open entry). Sizing view: each trade risks 0.5% of the account, so total R x 0.5% = account return before compounding. Costs: futures 0.14% round trip + 0.02%/day funding; spot 0.26% round trip, long only. Survivorship bias: only coins that exist today are included, which flatters long results.

## Futures (long + short)

| Group | Trades | Win | Avg R net (95% CI) | Total R | Profit factor |
|---|---|---|---|---|---|
| All lookbacks combined | 3486 | 31% | +0.43 (±0.17) | +1512 | 1.83 |
| Lookback 10 days | 1818 | 32% | +0.22 (±0.12) | +401 | 1.48 |
| Lookback 20 days | 1096 | 33% | +0.50 (±0.26) | +550 | 1.91 |
| Lookback 50 days | 572 | 27% | +0.98 (±0.80) | +561 | 2.47 |
| long only | 1788 | 31% | +0.96 (±0.32) | +1715 | 2.69 |
| short only | 1698 | 32% | -0.12 (±0.05) | -203 | 0.74 |

Max drawdown on realized trades (all combined): 196.1 R = 98% of the account at 0.5% risk per trade.

### By calendar year (all lookbacks, by exit date)

| Year | Trades | Win | Avg R net | Total R | Account return at 0.5% risk/trade | Equal-weight buy-and-hold of these coins |
|---|---|---|---|---|---|---|
| 2020 | 130 | 12% | -0.39 | -51 | -25% | +63% |
| 2021 | 508 | 40% | +2.46 | +1247 | +624% | +1127% |
| 2022 | 578 | 30% | -0.07 | -39 | -19% | -71% |
| 2023 | 555 | 31% | -0.07 | -38 | -19% | +145% |
| 2024 | 627 | 33% | +0.69 | +434 | +217% | +62% |
| 2025 | 604 | 25% | -0.15 | -90 | -45% | -38% |
| 2026 | 484 | 35% | +0.10 | +47 | +24% | -13% |

### By coin (all years)

| Coin | Trades | Avg R net | Total R |
|---|---|---|---|
| ADAUSDT | 200 | +0.85 | +169 |
| ATOMUSDT | 213 | -0.07 | -15 |
| AVAXUSDT | 188 | +0.79 | +148 |
| BCHUSDT | 204 | -0.01 | -2 |
| BNBUSDT | 195 | +0.85 | +165 |
| BTCUSDT | 189 | +0.71 | +135 |
| DOGEUSDT | 188 | +1.41 | +265 |
| DOTUSDT | 201 | +0.25 | +51 |
| ETCUSDT | 184 | +0.29 | +54 |
| ETHUSDT | 182 | +0.60 | +110 |
| FILUSDT | 188 | +0.18 | +34 |
| LINKUSDT | 215 | -0.11 | -23 |
| LTCUSDT | 204 | -0.14 | -28 |
| NEARUSDT | 191 | +0.59 | +113 |
| SOLUSDT | 196 | +0.81 | +158 |
| TRXUSDT | 186 | +0.18 | +33 |
| UNIUSDT | 184 | +0.34 | +62 |
| XRPUSDT | 178 | +0.47 | +83 |

Most positions open at once: 54. Average holding time: 20 days.

## Spot (long only)

| Group | Trades | Win | Avg R net (95% CI) | Total R | Profit factor |
|---|---|---|---|---|---|
| All lookbacks combined | 1788 | 31% | +0.99 (±0.32) | +1767 | 2.75 |
| Lookback 10 days | 916 | 33% | +0.57 (±0.24) | +523 | 2.16 |
| Lookback 20 days | 560 | 33% | +1.12 (±0.49) | +627 | 2.92 |
| Lookback 50 days | 312 | 24% | +1.98 (±1.45) | +617 | 3.72 |

Max drawdown on realized trades (all combined): 134.6 R = 67% of the account at 0.5% risk per trade.

### By calendar year (all lookbacks, by exit date)

| Year | Trades | Win | Avg R net | Total R | Account return at 0.5% risk/trade | Equal-weight buy-and-hold of these coins |
|---|---|---|---|---|---|---|
| 2020 | 75 | 16% | -0.11 | -8 | -4% | +63% |
| 2021 | 297 | 48% | +4.48 | +1329 | +665% | +1127% |
| 2022 | 244 | 15% | -0.42 | -102 | -51% | -71% |
| 2023 | 284 | 29% | +0.04 | +10 | +5% | +145% |
| 2024 | 363 | 39% | +1.44 | +522 | +261% | +62% |
| 2025 | 282 | 30% | +0.13 | +38 | +19% | -38% |
| 2026 | 243 | 26% | -0.09 | -22 | -11% | -13% |

### By coin (all years)

| Coin | Trades | Avg R net | Total R |
|---|---|---|---|
| ADAUSDT | 92 | +2.08 | +191 |
| ATOMUSDT | 106 | -0.04 | -4 |
| AVAXUSDT | 93 | +1.59 | +148 |
| BCHUSDT | 108 | +0.02 | +2 |
| BNBUSDT | 109 | +1.76 | +192 |
| BTCUSDT | 101 | +1.62 | +163 |
| DOGEUSDT | 103 | +2.70 | +278 |
| DOTUSDT | 94 | +0.58 | +54 |
| ETCUSDT | 86 | +0.84 | +72 |
| ETHUSDT | 98 | +1.19 | +117 |
| FILUSDT | 85 | +0.46 | +39 |
| LINKUSDT | 119 | -0.03 | -4 |
| LTCUSDT | 118 | -0.09 | -10 |
| NEARUSDT | 90 | +1.35 | +122 |
| SOLUSDT | 97 | +1.80 | +174 |
| TRXUSDT | 105 | +0.64 | +67 |
| UNIUSDT | 90 | +0.74 | +66 |
| XRPUSDT | 94 | +1.07 | +101 |

Most positions open at once: 54. Average holding time: 20 days.
