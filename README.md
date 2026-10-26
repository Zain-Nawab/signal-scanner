# Signal Scanner

Scans BTC, ETH, SOL, BNB and XRP every 15 minutes (15m entries, 1H trend filter) and signals only when
the 1H trend agrees and at least 3 of 4 confirmations line up on the last closed candle:
**structure** (HH/HL, LH/LL, break of structure), **VSA**, **price action**, **momentum**.
Each signal has entry, stop, TP1 (2R), TP2 (3R), a grade and the reasons. Alerts only, no trades are placed.

Runs free on GitHub Actions. No server, no exchange keys.

```
GitHub Actions (every 15 min) --> run_scan.py --> Make.com webhook --> Telegram + Google Sheet journal
                                       |                  (Telegram direct only if the webhook fails)
                                       +--> data branch --> GitHub Pages dashboard
```

## One-time setup

1. **Secrets** (Settings > Secrets and variables > Actions > New repository secret):
   - `MAKE_WEBHOOK_URL`: the Make custom webhook address
   - `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID`: used only if the webhook fails
2. **Pages**: Settings > Pages > Source: *Deploy from a branch* > Branch `data` / `(root)`.
   (The `data` branch appears after the first scan run.)
3. **Test the chain**: Actions > scan > Run workflow > tick *test_signal*. One `TEST-ONLY` alert should reach
   Telegram and one row the sheet.

## Files

- `engine.py`, `indicators.py`: the signal logic. `config.py`: thresholds.
- `run_scan.py`: one scan, de-duplication, delivery. `data.py`: Binance / Bybit / OKX public data with fallback.
- `backtest.py`: walk-forward test (`python backtest.py BTCUSDT`). Fees and slippage are not yet modelled.
- `check_sources.py`: which exchange endpoints GitHub's servers can reach (writes to the `check` branch).

Not financial advice. Backtest and paper-trade before risking money.
