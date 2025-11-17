import os
import requests

def fetch_newsdata(query, language="en", page_size=10):
    key = os.environ.get("NEWSDATA_API_KEY")
    if not key:
        return []
    url = "https://newsdata.io/api/1/news"
    params = {"apikey": key, "q": query, "language": language, "page": 1}
    results = []
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    for item in data.get("results", [])[:page_size]:
        results.append(item)
    return results