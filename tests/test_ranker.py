import os
import sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT)
from scripts.smart_feed import priority

def test_priority_sorting():
    ts = {"general": 0.8}
    a = {"category": "general", "polarity": "positive", "confidence_score": 0.9, "timestamp": "2025-11-21T00:00:00Z"}
    b = {"category": "general", "polarity": "negative", "confidence_score": 0.1, "timestamp": "2025-11-21T00:00:00Z"}
    sa = priority(a, ts)
    sb = priority(b, ts)
    assert sa >= sb