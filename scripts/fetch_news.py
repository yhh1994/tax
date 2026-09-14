import feedparser
import json
from datetime import datetime

FEEDS = {
    "IRS Newsroom": "https://www.irs.gov/newsroom/feed",
    "Tax Foundation": "https://taxfoundation.org/feed/",
    "US Treasury Releases": "https://home.treasury.gov/rss/news/press-releases"
}

def fetch_all():
    news_items = []
    for source, url in FEEDS.items():
        feed = feedparser.parse(url)
        for entry in feed.entries[:10]:  # Top 10 per source
            news_items.append({
                "title": entry.title,
                "link": entry.link,
                "published": entry.get("published", entry.get("updated", "")),
                "source": source,
                "summary": entry.get("summary", "")[:250] + "..."
            })
    
    # Sort by latest
    news_items.sort(key=lambda x: x['published'], reverse=True)
    
    with open('data/news.json', 'w') as f:
        json.dump(news_items, f, indent=2)

if __name__ == "__main__":
    fetch_all()
