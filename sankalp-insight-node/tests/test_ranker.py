import os
import json
import datetime as dt
import importlib.util

def load_module(path):
    spec = importlib.util.spec_from_file_location('smart_feed', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def test_rank_orders_by_priority():
    path = os.path.join('scripts','smart_feed.py')
    mod = load_module(path)
    now = dt.datetime.utcnow().isoformat()
    items = [
        {"id":"1","category":"business","polarity":"positive","confidence":0.9,"timestamp":now},
        {"id":"2","category":"business","polarity":"neutral","confidence":0.4,"timestamp":now},
        {"id":"3","category":"technology","polarity":"negative","confidence":0.2,"timestamp":now}
    ]
    ranked = mod.rank(items)
    assert len(ranked) == 3
    assert ranked[0]['priority_score'] >= ranked[-1]['priority_score']