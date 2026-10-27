"""Phase 0: which exchange endpoints are reachable from this machine (GitHub's runner)?"""
import json
import os
import data

out = {}
for name, fn in data.SOURCES.items():
    r = {}
    for iv in ("15m", "1h"):
        try:
            df = fn("BTCUSDT", iv, 300)
            r[iv] = {"ok": True, "rows": len(df), "last_closed": str(df.index[-1])}
        except Exception as e:
            r[iv] = {"ok": False, "error": str(e)[:200]}
    out[name] = r
    print(name, json.dumps(r))
os.makedirs(os.getenv("STATE_DIR", "out"), exist_ok=True)
with open(os.path.join(os.getenv("STATE_DIR", "out"), "check.json"), "w") as f:
    json.dump(out, f, indent=1)

# --- news feeds (reachability from the runner) ---
import news
ev, src, err = news.calendar_events()
hl, herr = news.headlines(__import__("datetime").datetime.now(__import__("datetime").timezone.utc), hours=48)
out["news"] = {"calendar_source": src, "calendar_events": len(ev), "calendar_error": err,
               "sample_events": [(e["title"], str(e["time"])) for e in ev[:5]],
               "headline_hits_48h": hl, "rss_errors": herr}
print("news", json.dumps(out["news"], default=str))
with open(os.path.join(os.getenv("STATE_DIR", "out"), "check.json"), "w") as f:
    json.dump(out, f, indent=1, default=str)
