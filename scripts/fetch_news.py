import feedparser
import json
import os
import time
import requests
import re
from time import mktime
from datetime import datetime
from google import genai

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

FEEDS = {
    "IRS Newsroom": "https://www.irs.gov/newsroom/feed",
    "Tax Foundation": "https://taxfoundation.org/feed/",
    "US Treasury": "https://home.treasury.gov/rss/news/press-releases",
    "Tax Policy Center": "https://www.taxpolicycenter.org/rss/taxvox",
    "Journal of Accountancy (Tax)": "https://www.journalofaccountancy.com/rss/tax.xml"
}

def clean_html(raw_html):
    """Remove HTML tags and extra whitespace from RSS snippets."""
    clean_text = re.sub(r'<[^>]+>', '', raw_html)
    return " ".join(clean_text.split())

def analyze_with_gemini(text):
    clean_snippet = clean_html(text)[:1000]  # Limit input tokens
    if not client or not clean_snippet:
        return clean_snippet[:250] + "...", ["Untagged"]
    
    prompt = f"""
    Analyze this tax news snippet: "{clean_snippet}"
    1. Write a 1-sentence summary focusing on the practical impact.
    2. Provide up to 3 short category tags (e.g., Corporate Tax, IRS, Tariffs).
    
    Output strictly in this format:
    Summary: <summary text>
    Tags: <tag1, tag2, tag3>
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        result = response.text or ""
        
        # Resilient regex parsing insensitive to case
        summary_match = re.search(r"Summary:\s*(.*?)(?=Tags:|$)", result, re.IGNORECASE | re.DOTALL)
        tags_match = re.search(r"Tags:\s*(.*)", result, re.IGNORECASE)
        
        summary = summary_match.group(1).strip() if summary_match else clean_snippet[:250] + "..."
        
        if tags_match:
            tags = [t.strip() for t in tags_match.group(1).split(",") if t.strip()]
        else:
            tags = ["General"]
            
        return summary, tags
    except Exception as e:
        print(f"Gemini API error: {e}")
        return clean_snippet[:250] + "...", ["General"]

def fetch_all():
    # Load previously processed articles to prevent re-summarizing and save API quota
    existing_items = {}
    if os.path.exists('data/news.json'):
        try:
            with open('data/news.json', 'r') as f:
                saved_data = json.load(f)
                existing_items = {item['link']: item for item in saved_data if 'link' in item}
        except Exception as e:
            print(f"Could not load existing data: {e}")

    news_items = []
    
    for source, url in FEEDS.items():
        print(f"\n--- Fetching: {source} ---")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                print(f"Failed to fetch {source}: HTTP Status {resp.status_code}")
                continue
            
            feed = feedparser.parse(resp.content)
            print(f"Found {len(feed.entries)} entries for {source}")

            for entry in feed.entries[:8]:  # Top 8 per source
                link = entry.get("link", "")
                
                # Deduplication: Re-use cached summary if link exists
                if link in existing_items:
                    print(f"Cached item found, skipping API call: {entry.title[:40]}...")
                    news_items.append(existing_items[link])
                    continue

                raw_summary = entry.get("summary", entry.get("title", ""))
                
                # Standardize publish date and epoch timestamp for reliable sorting
                parsed_time = entry.get("published_parsed") or entry.get("updated_parsed")
                timestamp = mktime(parsed_time) if parsed_time else 0
                pub_date = entry.get("published") or entry.get("updated") or ""

                print(f"Analyzing new item: {entry.title[:40]}...")
                ai_summary, ai_tags = analyze_with_gemini(raw_summary)
                
                news_items.append({
                    "title": entry.title,
                    "link": link,
                    "published": pub_date,
                    "timestamp": timestamp,
                    "source": source,
                    "summary": ai_summary,
                    "tags": ai_tags
                })
                
                if client:
                    time.sleep(3)  # Rate limit control

        except Exception as e:
            print(f"Error reading {source}: {e}")

    if news_items:
        # Deduplicate globally by link and sort by numeric epoch timestamp
        unique_items = list({item['link']: item for item in news_items}.values())
        unique_items.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
        # Keep recent 100 entries max to keep news.json lightweight
        final_feed = unique_items[:100]
        
        with open('data/news.json', 'w') as f:
            json.dump(final_feed, f, indent=2)
        print(f"\nSuccessfully saved {len(final_feed)} items to data/news.json")

if __name__ == "__main__":
    fetch_all()
