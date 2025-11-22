import os
import sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT)
from agents.summarizer import summarize_short, summarize_medium

def test_summarizer_outputs():
    text = "AI transforms industry. New models enable automation and insights."
    s1 = summarize_short(text)
    s2 = summarize_medium(text)
    assert isinstance(s1, str) and len(s1) > 0
    assert isinstance(s2, str) and len(s2) > 0