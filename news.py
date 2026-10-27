"""News and event risk checks. Everything here fails SAFE: if a feed is down the scan still runs and
the problem is reported in status.json instead of blocking signals.

1. Economic-calendar blackout: no new signals from 30 min before to 90 min after a high-impact USD
   event (FOMC, CPI, jobs report...). Sources: a public weekly calendar feed, the FOMC decision dates
   below as a fallback, and an optional manual file `events.json` ([{"title": "...", "time": "2026-11-03T13:30:00Z"}]).
2. Headline risk: scans recent crypto news RSS for crisis keywords (hack, exploit, insolvency, ban...)
   and adds a warning to alerts. A flag only; it never blocks.
"""
import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import requests

CAL_URLS = ["https://nfs.faireconomy.media/ff_calendar_thisweek.json"]
RSS_URLS = ["https://www.coindesk.com/arc/outboundfeeds/rss/", "https://cointelegraph.com/rss"]
# FOMC rate-decision times (UTC). Source: thriveinmarkets.com/calendar/dates/fomc-2026 (checked 2026-10-27).
FOMC_FALLBACK = ["2026-10-28T18:00:00+00:00", "2026-12-09T19:00:00+00:00"]
BEFORE, AFTER = timedelta(minutes=30), timedelta(minutes=90)
KEYWORDS = ["hack", "exploit", "drained", "insolven", "bankrupt", "halts withdrawal", "suspends withdrawal",
            "depeg", "delist", "sec sues", "lawsuit", "crackdown", "outage", "rug pull", "seized", "breach"]


def _dt(s):
    d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def calendar_events():
    """(events, source, error). events = [{'title', 'time' (aware UTC)}]"""
    err = None
    for url in CAL_URLS:
        try:
            r = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            ev = [{"title": e.get("title", "?"), "time": _dt(e["date"]).astimezone(timezone.utc)}
                  for e in r.json()
                  if str(e.get("country", "")).upper() == "USD" and str(e.get("impact", "")).lower() == "high"]
            return ev, "feed", None
        except Exception as e:
            err = str(e)[:120]
    return [{"title": "FOMC rate decision", "time": _dt(t)} for t in FOMC_FALLBACK], "fallback", err


def manual_events(path="events.json"):
    try:
        with open(path) as f:
            return [{"title": e["title"], "time": _dt(e["time"])} for e in json.load(f)]
    except Exception:
        return []


def headlines(now, hours=3):
    hits, errs = [], []
    for url in RSS_URLS:
        try:
            r = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            for it in ET.fromstring(r.content).iter("item"):
                title = (it.findtext("title") or "").strip()
                try:
                    when = parsedate_to_datetime(it.findtext("pubDate"))
                    if when.tzinfo is None:
                        when = when.replace(tzinfo=timezone.utc)
                except Exception:
                    continue
                if now - when <= timedelta(hours=hours) and any(k in title.lower() for k in KEYWORDS):
                    hits.append(title[:110])
        except Exception as e:
            errs.append(f"{url.split('/')[2]}: {str(e)[:60]}")
    return hits[:3], errs


def assess(now=None):
    now = now or datetime.now(timezone.utc)
    events, source, cal_err = calendar_events()
    events += manual_events()
    blackout = None
    for e in events:
        if e["time"] - BEFORE <= now <= e["time"] + AFTER:
            blackout = {"event": e["title"], "time": e["time"].isoformat()}
            break
    upcoming = sorted((e for e in events if e["time"] > now), key=lambda e: e["time"])[:3]
    heads, herr = headlines(now)
    return {"blackout": blackout, "headlines": heads, "calendar_source": source,
            "next_events": [{"title": e["title"], "time": e["time"].isoformat()} for e in upcoming],
            "errors": ([f"calendar: {cal_err}"] if cal_err else []) + herr}
