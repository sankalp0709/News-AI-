import os
import requests

def fetch_gnews(query, lang="en", max_results=10):
    token = os.environ.get("GNEWS_API_KEY")
    if not token:
        return []
    url = "https://gnews.io/api/v4/search"
    params = {"q": query, "lang": lang, "max": max_results, "token": token}
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
    return data.get("articles", [])