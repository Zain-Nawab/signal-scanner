# Strategy lab report

Data: 10 coins, timeframes 15m, 1h, 4h, 2023-10-25 to 2026-10-27. Train = before 2025-10-27; test = the final 365 days (used once). Costs are round-trip % of price: futures taker 0.14% (0.05% fee + 0.02% slippage per side), spot 0.26% (0.10% + 0.03% per side). Average result is in R (multiples of the initial risk); (±) is the 95% confidence half-width. A result counts as proven only if its lower bound is above 0 with 100+ trades.

## 1. Do the confirmations carry any edge? (before costs, target 2R/3R, cooldown applied)

### 15m entries

| Subset | Trades | Win | Avg gross R (95% CI) | Profit factor |
|---|---|---|---|---|
| all candidates (score>=2) | 1339 | 35% | +0.056 (±0.080) | 1.09 |
| score = 2 | 1280 | 35% | +0.046 (±0.081) | 1.07 |
| score = 3 | 102 | 37% | +0.166 (±0.307) | 1.26 |
| score = 4 | 1 | 0% | -1.000 (±nan) | 0.00 |
| structure present | 796 | 36% | +0.038 (±0.101) | 1.06 |
| structure absent | 562 | 35% | +0.086 (±0.126) | 1.13 |
| vsa present | 581 | 36% | +0.086 (±0.123) | 1.14 |
| vsa absent | 890 | 34% | +0.015 (±0.096) | 1.02 |
| price present | 983 | 35% | +0.060 (±0.094) | 1.09 |
| price absent | 449 | 36% | +0.046 (±0.134) | 1.07 |
| momentum present | 564 | 35% | +0.043 (±0.122) | 1.07 |
| momentum absent | 866 | 35% | +0.051 (±0.099) | 1.08 |
| long only | 559 | 34% | -0.012 (±0.120) | 0.98 |
| short only | 780 | 37% | +0.105 (±0.106) | 1.17 |

### 1h entries

| Subset | Trades | Win | Avg gross R (95% CI) | Profit factor |
|---|---|---|---|---|
| all candidates (score>=2) | 368 | 37% | +0.167 (±0.160) | 1.27 |
| score = 2 | 358 | 37% | +0.168 (±0.162) | 1.27 |
| score = 3 | 21 | 33% | +0.119 (±0.709) | 1.18 |
| score = 4 | 0 | | | | |
| structure present | 222 | 37% | +0.167 (±0.206) | 1.27 |
| structure absent | 152 | 36% | +0.166 (±0.251) | 1.26 |
| vsa present | 152 | 36% | +0.104 (±0.244) | 1.16 |
| vsa absent | 249 | 36% | +0.159 (±0.195) | 1.25 |
| price present | 262 | 37% | +0.199 (±0.195) | 1.32 |
| price absent | 130 | 38% | +0.100 (±0.255) | 1.16 |
| momentum present | 162 | 36% | +0.121 (±0.236) | 1.19 |
| momentum absent | 238 | 37% | +0.181 (±0.201) | 1.29 |
| long only | 155 | 32% | +0.008 (±0.240) | 1.01 |
| short only | 213 | 41% | +0.282 (±0.214) | 1.48 |

### 4h entries

| Subset | Trades | Win | Avg gross R (95% CI) | Profit factor |
|---|---|---|---|---|
| all candidates (score>=2) | 117 | 37% | +0.171 (±0.287) | 1.27 |
| score = 2 | 112 | 37% | +0.174 (±0.295) | 1.27 |
| score = 3 | 9 | 44% | +0.057 (±0.872) | 1.10 |
| score = 4 | 0 | | | | |
| structure present | 62 | 37% | +0.178 (±0.396) | 1.28 |
| structure absent | 57 | 39% | +0.218 (±0.415) | 1.36 |
| vsa present | 46 | 41% | +0.249 (±0.454) | 1.42 |
| vsa absent | 78 | 36% | +0.141 (±0.350) | 1.22 |
| price present | 73 | 45% | +0.356 (±0.362) | 1.65 |
| price absent | 50 | 28% | -0.050 (±0.430) | 0.93 |
| momentum present | 70 | 29% | -0.043 (±0.361) | 0.94 |
| momentum absent | 53 | 49% | +0.462 (±0.427) | 1.91 |
| long only | 47 | 38% | +0.213 (±0.459) | 1.35 |
| short only | 70 | 36% | +0.142 (±0.371) | 1.22 |

## 2. Best configurations chosen on train, then checked on the untouched final year

### 15m entries

| Config (picked by train result) | Train trades | Train avg R | TEST trades | TEST avg R (95% CI) | TEST profit factor | Test avg R if spot fees | Verdict |
|---|---|---|---|---|---|---|---|
| score>=2, stop>=1%, short, TP 1.5_2.5, vol-filter=off | 140 | -0.101 | 35 | +0.312 (±0.472) | 1.60 | +0.225 | not proven |
| score>=2, stop>=1%, short, TP 1.5_2.5, vol-filter=on | 138 | -0.103 | 35 | +0.312 (±0.472) | 1.60 | +0.225 | not proven |
| score>=2, stop>=1%, short, TP 2_3, vol-filter=off | 140 | -0.124 | 35 | +0.467 (±0.541) | 1.89 | +0.381 | not proven |

Luck check (32 configurations with 100+ train trades): 0% were profitable on train, 25% on test; rank correlation between train and test results +0.75 (near 0 means train performance did not predict test performance, i.e. mostly luck). Best gross (pre-cost) train average: +0.103 R.

### 1h entries

| Config (picked by train result) | Train trades | Train avg R | TEST trades | TEST avg R (95% CI) | TEST profit factor | Test avg R if spot fees | Verdict |
|---|---|---|---|---|---|---|---|
| score>=2, stop>=0.5%, short, TP 2_3, vol-filter=off | 137 | +0.225 | 60 | +0.091 (±0.379) | 1.14 | -0.013 | not proven |
| score>=2, stop>=0.5%, short, TP 2_3, vol-filter=on | 137 | +0.225 | 60 | +0.091 (±0.379) | 1.14 | -0.013 | not proven |
| score>=2, stop>=0%, short, TP 2_3, vol-filter=off | 145 | +0.210 | 68 | +0.019 (±0.358) | 1.03 | -0.112 | not proven |

Luck check (28 configurations with 100+ train trades): 50% were profitable on train, 43% on test; rank correlation between train and test results +0.82 (near 0 means train performance did not predict test performance, i.e. mostly luck). Best gross (pre-cost) train average: +0.334 R.

### 4h entries

Not enough trades on train for any configuration (needs 100+).

## 3. Benchmark: simple trend following (20-bar channel breakout, 10-bar exit, 2xATR stop)

| Timeframe / side / costs | Period | Trades | Win | Avg R (95% CI) | Profit factor |
|---|---|---|---|---|---|
| 15m / both / futures_taker | train | 21855 | 28% | -0.157 (±0.024) | 0.77 |
| 15m / both / futures_taker | TEST | 10500 | 26% | -0.215 (±0.036) | 0.71 |
| 15m / long / futures_taker | train | 11254 | 28% | -0.144 (±0.034) | 0.78 |
| 15m / long / futures_taker | TEST | 5225 | 24% | -0.237 (±0.056) | 0.68 |
| 1d / both / futures_taker | train | 231 | 29% | +0.515 (±0.567) | 1.88 |
| 1d / both / futures_taker | TEST | 85 | 45% | +0.367 (±0.338) | 1.89 |
| 1d / long / futures_taker | train | 128 | 35% | +1.314 (±0.998) | 3.44 |
| 1d / long / futures_taker | TEST | 48 | 27% | +0.038 (±0.497) | 1.07 |
| 1h / both / futures_taker | train | 5187 | 31% | +0.002 (±0.050) | 1.00 |
| 1h / both / futures_taker | TEST | 2528 | 29% | -0.032 (±0.097) | 0.95 |
| 1h / long / futures_taker | train | 2697 | 32% | +0.064 (±0.074) | 1.11 |
| 1h / long / futures_taker | TEST | 1216 | 27% | +0.024 (±0.175) | 1.04 |
| 4h / both / futures_taker | train | 1242 | 33% | +0.119 (±0.130) | 1.22 |
| 4h / both / futures_taker | TEST | 646 | 27% | -0.022 (±0.169) | 0.97 |
| 4h / long / futures_taker | train | 669 | 33% | +0.318 (±0.226) | 1.56 |
| 4h / long / futures_taker | TEST | 318 | 24% | -0.031 (±0.278) | 0.95 |

## 3b. Is any result stable across years? (score>=2, TP 2R/3R, net of futures-taker costs, cooldown applied)

### 15m entries

| Year | Longs: trades / avg R | Shorts: trades / avg R |
|---|---|---|
| 2023 | 38 / -0.67 | 33 / -0.42 |
| 2024 | 186 / -0.28 | 272 / -0.08 |
| 2025 | 185 / -0.30 | 256 / -0.26 |
| 2026 | 150 / -0.35 | 219 / -0.26 |

### 1h entries

| Year | Longs: trades / avg R | Shorts: trades / avg R |
|---|---|---|
| 2023 | 6 / +0.10 | 1 / +2.33 |
| 2024 | 54 / -0.17 | 69 / -0.02 |
| 2025 | 50 / -0.23 | 86 / +0.32 |
| 2026 | 45 / +0.02 | 57 / +0.06 |

### 4h entries

| Year | Longs: trades / avg R | Shorts: trades / avg R |
|---|---|---|
| 2023 | 2 / -1.03 | - |
| 2024 | 17 / +0.33 | 20 / -0.07 |
| 2025 | 17 / +0.49 | 26 / +0.31 |
| 2026 | 11 / -0.43 | 24 / -0.04 |

## 4. Market context

Buy-and-hold change over each job's whole period (the market the strategies were tested in):

ADAUSDT -48% to -28%, AVAXUSDT -58% to -15%, BNBUSDT +218% to +231%, BTCUSDT +112% to +132%, DOGEUSDT -1% to +16%, ETHUSDT +12% to +30%, LINKUSDT -23% to +3%, LTCUSDT -21% to -18%, SOLUSDT +72% to +207%, XRPUSDT +110% to +136% (range across timeframes because start dates differ slightly).