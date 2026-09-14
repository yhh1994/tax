import feedparser
import json
import os
import time
import requests
from datetime import datetime
from google import genai

# Pass a standard browser User-Agent so government servers (IRS/Treasury) don't block request
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# Initialize Gemini Client safely
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

FEEDS = {
    "IRS Newsroom": "https://www.irs.gov/newsroom/feed",
    "Tax Foundation": "https://taxfoundation.org/feed/",
    "US Treasury": "https://home.treasury.gov/rss/news/press-releases"
}

def analyze_with_gemini(text):
    if not client or not text:
        return text[:250] + "...", ["Untagged"]
    
    prompt = f"""
    Analyze this tax news snippet: "{text}"
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
        result = response.text
        
        summary_part = result.split("Tags:")[0].replace("Summary:", "").strip()
        tags_part = result.split("Tags:")[1].strip() if "Tags:" in result else "General"
        tags = [t.strip() for t in tags_part.split(",")]
        
        return summary_part, tags
    except Exception as e:
        print(f"Gemini API error: {e}")
        return text[:250] + "...", ["General"]

def fetch_all():
    news_items = []
    
    for source, url in FEEDS.items():
        print(f"\n--- Fetching: {source} ---")
        try:
            # Download XML content explicitly using Custom Headers
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                print(f"Failed to fetch {source}: HTTP Status {resp.status_code}")
                continue
            
            # Parse fetched string directly
            feed = feedparser.parse(resp.content)
            print(f"Found {len(feed.entries)} entries for {source}")

            for entry in feed.entries[:5]:  # Limit to 5 per source
                raw_summary = entry.get("summary", entry.get("title", ""))
                
                # Resilient fallback date parser across varying XML schemas
                pub_date = entry.get("published") or entry.get("updated") or entry.get("dc:date") or ""
                
                print(f"Processing item: {entry.title[:50]}...")
                ai_summary, ai_tags = analyze_with_gemini(raw_summary)
                
                news_items.append({
                    "title": entry.title,
                    "link": entry.link,
                    "published": pub_date,
                    "source": source,
                    "summary": ai_summary,
                    "tags": ai_tags
                })
                
                # Maintain rate limit spacing for Gemini API
                if client:
                    time.sleep(4)

        except Exception as e:
            print(f"Error reading {source}: {e}")

    # Ensure list isn't empty before sorting/writing
    if news_items:
        # Sort items safely handling blank date strings
        news_items.sort(key=lambda x: x['published'], reverse=True)
        
        with open('data/news.json', 'w') as f:
            json.dump(news_items, f, indent=2)
        print(f"\nSuccessfully wrote {len(news_items)} items to data/news.json")
    else:
        print("\nWarning: No items were fetched from any source.")

if __name__ == "__main__":
    fetch_all()
