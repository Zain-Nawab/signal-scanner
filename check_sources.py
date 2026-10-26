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
