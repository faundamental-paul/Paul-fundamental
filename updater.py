import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

# Fluxuri RSS + GDELT Live Global Wire (aduce știri noi 24/7, inclusiv seara/noaptea)
RSS_FEEDS = [
    ("Reuters / Google News FX", "https://news.google.com/rss/search?q=forex+OR+%22central+bank%22+OR+%22interest+rate%22+OR+geopolitics+OR+%22crude+oil%22&hl=en-US&gl=US&ceid=US:en"),
    ("Federal Reserve & USD", "https://news.google.com/rss/search?q=%22Federal+Reserve%22+OR+FOMC+OR+Powell+OR+Waller&hl=en-US&gl=US&ceid=US:en"),
    ("ECB / BoE / BoJ / RBA", "https://news.google.com/rss/search?q=ECB+OR+%22Bank+of+England%22+OR+%22Bank+of+Japan%22+OR+RBA+OR+SNB&hl=en-US&gl=US&ceid=US:en"),
    ("Geopolitics & Oil", "https://news.google.com/rss/search?q=%22Strait+of+Hormuz%22+OR+OPEC+OR+tariffs+OR+%22Middle+East%22+oil&hl=en-US&gl=US&ceid=US:en")
]

GDELT_URL = (
    "https://api.gdeltproject.org/api/v2/doc/doc?query="
    + urllib.parse.quote('("Federal Reserve" OR "ECB" OR "Bank of England" OR "Bank of Japan" OR "RBA" OR "interest rate" OR "crude oil" OR "tariffs" OR "Strait of Hormuz")')
    + "&mode=ArtList&maxrecords=25&format=json&sort=DateDesc"
)

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
    bearish = any(w in low for w in ["cut", "dovish", "drop", "fall", "crisis", "deadlock", "slow", "weak"])
    impacts = []
    rules = [
        ("USD", ["fed", "fomc", "powell", "waller", "bowman", "us ", "dollar", "treasury", "tariff"]),
        ("EUR", ["ecb", "lagarde", "euro", "france", "germany", "oat", "bund"]),
        ("GBP", ["boe", "bank of england", "bailey", "uk ", "britain", "sterling"]),
        ("JPY", ["boj", "bank of japan", "ueda", "yen", "japan"]),
        ("CHF", ["snb", "swiss", "franc", "schlegel"]),
        ("AUD", ["rba", "australia", "aussie", "bullock", "china"]),
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

    # 1. Fetch from RSS Feeds
    for source_name, url in RSS_FEEDS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                xml_data = resp.read()
            root = ET.fromstring(xml_data)
            for item in root.findall(".//item")[:10]:
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                pub = (item.findtext("pubDate") or "").strip()
                if not title or title.lower() in seen_titles:
                    continue
                seen_titles.add(title.lower())
                try:
                    dt = parsedate_to_datetime(pub).astimezone(timezone.utc)
                except Exception:
                    dt = datetime.now(timezone.utc)
                stories.append({
                    "title": title,
                    "url": link,
                    "sources": [source_name],
                    "publishedAt": dt.isoformat(),
                    "timeAgo": format_time_ago(dt),
                    "impactScore": 8,
                    "currencyImpacts": detect_impacts(title),
                    "summaryEn": f"Live institutional wire ({source_name}): {title}."
                })
        except Exception:
            continue

    # 2. Fetch from GDELT Global Live Wire
    try:
        req = urllib.request.Request(GDELT_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
        for art in data.get("articles", []):
            title = (art.get("title") or "").strip()
            if not title or len(title) < 20 or title.lower() in seen_titles:
                continue
            seen_titles.add(title.lower())
            dt = datetime.now(timezone.utc)
            stories.append({
                "title": title,
                "url": art.get("url") or "https://www.reuters.com/",
                "sources": [art.get("domain") or "Global Wire"],
                "publishedAt": dt.isoformat(),
                "timeAgo": "Just now",
                "impactScore": 8,
                "currencyImpacts": detect_impacts(title),
                "summaryEn": f"Live macro & geopolitical report ({art.get('domain', 'Wire')}): {title}."
            })
    except Exception:
        pass

    stories.sort(key=lambda x: x["publishedAt"], reverse=True)
    return stories[:35]

if __name__ == "__main__":
    now_utc = datetime.now(timezone.utc)
    payload = {
        "updatedAt": now_utc.isoformat(),
        "storyCount": 0,
        "stories": fetch_all_stories()
    }
    payload["storyCount"] = len(payload["stories"])
    with open("feed.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Saved {payload['storyCount']} fresh stories at {payload['updatedAt']}")
