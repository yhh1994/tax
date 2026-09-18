import feedparser
import json
import os
import re
import requests
from time import mktime

# Custom headers prevent government servers (IRS/Treasury) from blocking requests
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

FEEDS = {
    "IRS Newsroom": "https://www.irs.gov/newsroom/feed",
    "Tax Foundation": "https://taxfoundation.org/feed/",
    "US Treasury": "https://home.treasury.gov/rss/news/press-releases",
    "Tax Policy Center": "https://www.taxpolicycenter.org/rss/taxvox",
    "Journal of Accountancy (Tax)": "https://www.journalofaccountancy.com/rss/tax.xml"
}

def clean_summary(raw_html, max_length=280):
    """Strips HTML tags and trims text cleanly to a sentence boundary."""
    if not raw_html:
        return ""
    clean_text = re.sub(r'<[^>]+>', '', raw_html)
    clean_text = " ".join(clean_text.split())
    if len(clean_text) > max_length:
        return clean_text[:max_length].rsplit(' ', 1)[0] + "..."
    return clean_text

def fetch_all():
    news_items = []
    
    for source, url in FEEDS.items():
        print(f"Fetching: {source}")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                print(f"  Failed: Status {resp.status_code}")
                continue
            
            feed = feedparser.parse(resp.content)
            print(f"  Found {len(feed.entries)} entries")

            for entry in feed.entries[:10]:  # Top 10 entries per source
                link = entry.get("link", "")
                raw_summary = entry.get("summary", entry.get("description", entry.get("title", "")))
                
                # Convert structured date tuples to numeric timestamps for accurate sorting
                parsed_time = entry.get("published_parsed") or entry.get("updated_parsed")
                timestamp = mktime(parsed_time) if parsed_time else 0
                pub_date = entry.get("published") or entry.get("updated") or ""

                news_items.append({
                    "title": entry.get("title", ""),
                    "link": link,
                    "published": pub_date,
                    "timestamp": timestamp,
                    "source": source,
                    "summary": clean_summary(raw_summary)
                })

        except Exception as e:
            print(f"  Error reading {source}: {e}")

    if news_items:
        # Deduplicate globally by article URL
        unique_items = list({item['link']: item for item in news_items if item['link']}.values())
        
        # Sort chronologically by publication timestamp
        unique_items.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
        # Keep recent 100 entries
        final_feed = unique_items[:100]
        
        os.makedirs('data', exist_ok=True)
        with open('data/news.json', 'w') as f:
            json.dump(final_feed, f, indent=2)
        print(f"\nSuccessfully saved {len(final_feed)} items to data/news.json")

if __name__ == "__main__":
    fetch_all()
