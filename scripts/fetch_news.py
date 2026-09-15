import json
import re
from google import genai
from google.genai import types
import os

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

prompt = """
Search for the top 5 latest tax news updates, IRS announcements, or tax policy updates from the past week.

For each item, format the output strictly as a JSON list of objects with the following keys:
- "title": Clean title of the news story
- "source": Source or organization name (e.g., IRS, Tax Foundation, Wall Street Journal)
- "published": Publication date or relative time (e.g., "2026-09-14" or "2 days ago")
- "link": Direct reference link or news page URL if available
- "summary": A 1-2 sentence summary highlighting the practical tax impact
- "tags": A list of up to 3 short string tags (e.g., ["IRS", "Corporate Tax", "Deductions"])

Return ONLY valid JSON matching this schema:
[
  {
    "title": "...",
    "source": "...",
    "published": "...",
    "link": "...",
    "summary": "...",
    "tags": ["...", "..."]
  }
]
"""

try:
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[
                types.Tool(
                    google_search=types.GoogleSearch()
                )
            ]
        )
    )

    raw_text = response.text.strip()
    json_match = re.search(r'\[.*\]', raw_text, re.DOTALL)
    
    if json_match:
        news_data = json.loads(json_match.group(0))
        with open('./data/news.json', 'w') as f:
            json.dump(news_data, f, indent=2)
        print(f"Successfully generated {len(news_data)} tax news items with Gemini.")
    else:
        print("Failed to parse JSON array from Gemini response.")

except Exception as e:
    print(f"Error executing Gemini search request: {e}")
