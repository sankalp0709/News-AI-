import os
import sys
import json
import datetime as dt
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from agents.rl_feedback import compute_reward
from agents.trend import compute as trend_compute

def make_items(n=5):
    now = dt.datetime.utcnow()
    items = []
    for i in range(n):
        items.append({
            "id": f"t{i}",
            "title": f"Item {i}",
            "summary_short": "a",
            "summary_medium": "b",
            "category": "general",
            "language": "en",
            "polarity": "neutral",
            "tone": "calm",
            "timestamp": (now - dt.timedelta(minutes=30*i)).isoformat()
        })
    return items

def test_rl_numeric():
    signals = {"editor_approve": 1.0, "user_like": 0.5, "user_skip": 0.0}
    r = compute_reward(signals)
    assert r > 0

def test_trend_basic():
    items = make_items(6)
    scores = trend_compute(items)
    assert "general" in scores
    s = scores["general"]
    assert 0.0 <= s <= 1.0

if __name__ == "__main__":
    test_rl_numeric()
    test_trend_basic()
    print(json.dumps({"rl_reward_positive": True, "trend_score_valid": True}))