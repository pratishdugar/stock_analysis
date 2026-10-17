import json
from datetime import datetime, timezone

import pytest

from src import gemini_analysis as ga

ARTS = [{"title": "Apple up", "url": "http://a/1", "summary": "s", "source": "X",
         "published": datetime(2025, 1, 1, tzinfo=timezone.utc)}]
GOOD = {"news_score": 72, "sentiment": "Positive", "catalysts": ["c"], "risks": ["r"], "thesis_change": "unchanged",
        "confidence": "medium", "evidence_urls": ["http://a/1", "http://fake"], "data_limitations": []}


class Client:
    def __init__(self, text=None, exc=None):
        self.calls, self._t, self._e = 0, text, exc
        self.models = self

    def generate_content(self, **kw):
        self.calls += 1
        if self._e:
            raise self._e
        return type("R", (), {"text": self._t})()


@pytest.fixture(autouse=True)
def clear():
    ga._cache.clear()


def test_validate_good_and_drops_fake_urls():
    r = ga.validate_response("```json\n" + json.dumps(GOOD) + "\n```", {"http://a/1"})
    assert r["news_score"] == 72 and r["sentiment"] == "positive" and r["evidence_urls"] == ["http://a/1"]


@pytest.mark.parametrize("bad", ["not json", "[]", json.dumps({**GOOD, "news_score": 150}),
                                 json.dumps({**GOOD, "news_score": "high"}), json.dumps({**GOOD, "sentiment": "wow"}),
                                 json.dumps({**GOOD, "risks": "none"}), json.dumps({**GOOD, "news_score": True})])
def test_validate_rejects_bad(bad):
    with pytest.raises(ValueError):
        ga.validate_response(bad)


def test_success_and_cache_one_call():
    c = Client(json.dumps(GOOD))
    a = ga.analyze_news("AAPL", ARTS, client=c)
    b = ga.analyze_news("AAPL", ARTS, client=c)
    assert a.ok and b.from_cache and c.calls == 1


def test_quota_error_fallback():
    r = ga.analyze_news("AAPL", ARTS, client=Client(exc=RuntimeError("429 RESOURCE_EXHAUSTED")))
    assert not r.ok and "quota" in r.error


def test_malformed_output_fallback():
    r = ga.analyze_news("AAPL", ARTS, client=Client("oops"))
    assert not r.ok and "unusable" in r.error


def test_not_configured(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert "not configured" in ga.analyze_news("AAPL", ARTS).error


def test_no_articles():
    assert not ga.analyze_news("AAPL", [], client=Client("x")).ok


def test_prompt_marks_articles_untrusted():
    p = ga.build_prompt("AAPL", ARTS)
    assert "untrusted DATA" in p and "http://a/1" in p
