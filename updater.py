import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

# Surse RSS directe care NU blocheaza serverele GitHub Actions si publica 24/7
RSS_FEEDS = [
    ("CNBC Economy & Central Banks", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258"),
    ("CNBC World & Geopolitics", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100727362"),
    ("Yahoo Finance Forex & Macro", "https://finance.yahoo.com/news/rssindex"),
    ("MarketWatch Top Stories", "https://feeds.content.dowjones.io/public/rss/mw_topstories"),
    ("Federal Reserve Press", "https://www.federalreserve.gov/feeds/press_all.xml"),
    ("ECB Press & Speeches", "https://www.ecb.europa.eu/rss/press.html")
]

KEYWORDS = [
    "fed", "fomc", "powell", "rate", "inflation", "cpi", "ecb", "lagarde",
    "boe", "bank of england", "bailey", "boj", "bank of japan", "yen", "ueda",
    "rba", "snb", "boc", "dollar", "euro", "sterling", "forex", "currency",
    "oil", "crude", "opec", "hormuz", "war", "tariff", "china", "iran",
    "sanction", "treasury", "yield", "bond", "recession", "central bank", "cut", "hike"
]

def format_time_ago(dt):
    now = datetime.now(timezone.utc)
    diff = max(60, int((now - dt).total_seconds()))
    if diff < 3600:
        return f"{diff // 60}m ago"
    if diff < 86400:
        return f"{diff // 3600}h ago"
    return f"{diff // 86400}d ago"

def detect_impacts(title):
    low = title.lower()
    bearish = any(w in low for w in ["cut", "dovish", "drop", "fall", "crisis", "deadlock", "slow", "weak", "slump", "plunge"])
    impacts = []
    rules = [
        ("USD", ["fed", "fomc", "powell", "waller", "bowman", "us ", "u.s.", "dollar", "treasury", "tariff", "america"]),
        ("EUR", ["ecb", "lagarde", "euro", "france", "germany", "oat", "bund", "europe"]),
        ("GBP", ["boe", "bank of england", "bailey", "uk ", "u.k.", "britain", "sterling", "pound"]),
        ("JPY", ["boj", "bank of japan", "ueda", "yen", "japan", "tokyo"]),
        ("CHF", ["snb", "swiss", "franc", "schlegel", "switzerland"]),
        ("AUD", ["rba", "australia", "aussie", "bullock", "china", "iron ore"]),
        ("NZD", ["rbnz", "new zealand", "kiwi"]),
        ("CAD", ["boc", "bank of canada", "canada", "loonie", "oil", "crude", "opec"])
    ]
    for code, kws in rules:
        if any(k in low for k in kws):
            direction = "BEARISH" if bearish and code not in ["USD", "CHF"] else "BULLISH"
            impacts.append({"code": code, "dir": direction})
    if not impacts:
        impacts.append({"code": "USD", "dir": "BULLISH"})
    return impacts

def fetch_all_stories():
    seen_titles = set()
    stories = []

    for source_name, url in RSS_FEEDS:
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/rss+xml, application/xml, text/xml, */*"
                }
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                xml_data = resp.read()
            root = ET.fromstring(xml_data)
            for item in root.findall(".//item")[:20]:
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                pub = (item.findtext("pubDate") or "").strip()
                desc = (item.findtext("description") or "").strip()
                if not title or title.lower() in seen_titles:
                    continue
                low = (title + " " + desc).lower()
                if not any(kw in low for kw in KEYWORDS):
                    continue
                seen_titles.add(title.lower())
                try:
                    dt = parsedate_to_datetime(pub).astimezone(timezone.utc)
                except Exception:
                    dt = datetime.now(timezone.utc)
                clean_desc = desc.replace("<p>", "").replace("</p>", "").strip()
                summary = clean_desc[:320] if len(clean_desc) > 30 else f"Live wire ({source_name}): {title}."
                ago_str = format_time_ago(dt)
                days_old = max(0, int((datetime.now(timezone.utc) - dt).total_seconds() // 86400))
                is_geo = any(w in low for w in ["war", "hormuz", "oil", "opec", "tariff", "sanction", "iran", "china"])
                stories.append({
                    "title": title,
                    "url": link or "https://www.cnbc.com/world/",
                    "sources": [source_name],
                    "publishedAt": dt.isoformat(),
                    "daysAgo": days_old,
                    "timeAgo": ago_str,
                    "timeLabel": ago_str,
                    "category": "GEOPOLITICS" if is_geo else "MONETARY",
                    "horizon": "SHORT" if is_geo else "MEDIUM",
                    "impact": 8,
                    "impactScore": 8,
                    "currencyImpacts": detect_impacts(low),
                    "summaryEn": summary
                })
        except Exception as exc:
            print(f"Feed warning ({source_name}): {exc}")
            continue

    stories.sort(key=lambda x: x["publishedAt"], reverse=True)
    return stories[:35]

if __name__ == "__main__":
    now_utc = datetime.now(timezone.utc)
    stories = fetch_all_stories()
    payload = {
        "updatedAt": now_utc.isoformat(),
        "storyCount": len(stories),
        "stories": stories
    }
    with open("feed.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Saved {payload['storyCount']} fresh stories at {payload['updatedAt']}")
