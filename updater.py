import json, time, urllib.request, xml.etree.ElementTree as ET, re

FEEDS = [
    ("Bloomberg Markets", "https://feeds.bloomberg.com/markets/news.rss", "BANKS"),
    ("Reuters World & Macro", "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best", "GEOPOLITICS"),
    ("ING Think FX & Macro", "https://think.ing.com/rss/", "BANKS"),
    ("Federal Reserve Speeches", "https://www.federalreserve.gov/feeds/speeches.xml", "CB_PM"),
    ("ECB Press & Speeches", "https://www.ecb.europa.eu/rss/press.html", "CB_PM"),
    ("Bank of England News", "https://www.bankofengland.co.uk/rss/news", "CB_PM"),
    ("RBA Media Releases", "https://www.rba.gov.au/rss/rss-cb-media-releases.xml", "CB_PM"),
    ("Politico Europe", "https://www.politico.eu/feed/", "CB_PM")
]

RULES = [
    (r"\b(fed|fomc|powell|waller|bowman|us cpi|nonfarm|nfp|us gdp|us pmi|dollar)\b", "USD"),
    (r"\b(ecb|lagarde|schnabel|eurozone|france|oat|bund|euro cpi|german pmi)\b", "EUR"),
    (r"\b(boe|bailey|breeden|uk gilt|sterling|britain|uk cpi|uk wages)\b", "GBP"),
    (r"\b(boj|ueda|yen|japan|shunto|tokyo cpi)\b", "JPY"),
    (r"\b(snb|schlegel|swiss|franc)\b", "CHF"),
    (r"\b(rba|bullock|australia|aussie|australian jobs|australian cpi)\b", "AUD"),
    (r"\b(rbnz|orr|new zealand|kiwi)\b", "NZD"),
    (r"\b(boc|macklem|canada|loonie|opec|crude|canadian cpi)\b", "CAD"),
    (r"\b(gold|bullion|hormuz|missile|war|ceasefire)\b", "XAU")
]

def classify(title):
    low = title.lower()
    is_dovish = bool(re.search(r"\b(cut|easing|dovish|unemployment jump|weak jobs|cool cpi|miss|contraction|ceasefire|truce)\b", low))
    impacts = []
    for pat, code in RULES:
        if re.search(pat, low):
            direction = "BEARISH" if (is_dovish and code not in ["XAU", "CHF", "JPY"]) else "BULLISH"
            if code == "EUR" and re.search(r"\b(france|oat|deficit|gridlock)\b", low):
                direction = "BEARISH"
            impacts.append({"code": code, "dir": direction})
    if not impacts:
        impacts.append({"code": "USD", "dir": "BULLISH"})
    return impacts

stories = []
now_ms = int(time.time() * 1000)

for source_name, url, default_cat in FEEDS:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 GeoFX-Bot"})
        xml_data = urllib.request.urlopen(req, timeout=12).read()
        root = ET.fromstring(xml_data)
        for idx, item in enumerate(root.findall(".//item")[:6]):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or url).strip()
            desc = re.sub(r"<[^>]+>", "", (item.findtext("description") or title)).strip()[:340]
            if not title:
                continue
            stories.append({
                "id": f"auto-{abs(hash(title))}",
                "title": title,
                "sources": [source_name],
                "url": link,
                "category": default_cat,
                "publishedMs": now_ms - idx * 600000,
                "impactScore": 8,
                "horizonType": "LONG" if re.search(r"\b(cpi|jobs|gdp|rate|hike|cut|tariff|war|budget|inflation)\b", title.lower()) else "MEDIUM",
                "horizonLabel": "Long-Term: 14–45+ Days (Structural)",
                "horizonReason": "Auto-ingested from live institutional wire (Bloomberg/Reuters/Central Bank RSS).",
                "summaryEn": desc,
                "keyTakeaways": ["Auto-synced from live wire.", "Recalculates Risk-On/Off, 1–100 Strength & G8 bias automatically."],
                "currencyImpacts": classify(title),
                "isSeed": False
            })
    except Exception:
        pass

with open("feed.json", "w", encoding="utf-8") as f:
    json.dump({"updatedAtMs": now_ms, "stories": stories[:45]}, f, indent=2)
