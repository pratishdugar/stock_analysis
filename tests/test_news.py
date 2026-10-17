from datetime import datetime

from src import news

RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel>
<item><title>Apple launches new iPhone - Reuters</title><link>http://a/1</link><pubDate>Mon, 13 Oct 2025 10:00:00 GMT</pubDate><description>&lt;b&gt;Apple&lt;/b&gt; news</description></item>
<item><title>Apple launches new iPhone - Bloomberg</title><link>http://a/2</link><pubDate>Mon, 13 Oct 2025 11:00:00 GMT</pubDate></item>
<item><title>Weather in Paris</title><link>http://a/3</link><pubDate>Tue, 14 Oct 2025 11:00:00 GMT</pubDate></item>
<item><title>Apple earnings beat</title><link>http://a/4</link><pubDate>Tue, 14 Oct 2025 12:00:00 GMT</pubDate></item>
</channel></rss>"""


def test_collect_dedupes_filters_sorts():
    arts, warn = news.collect_news("AAPL", "Apple Inc.", getter=lambda u: RSS)
    assert [a["url"] for a in arts] == ["http://a/4", "http://a/1"]
    assert all(isinstance(a["published"], datetime) for a in arts)
    assert "<b>" not in arts[1]["summary"]


def test_limit():
    assert len(news.collect_news("AAPL", "Apple Inc.", getter=lambda u: RSS, limit=1)[0]) == 1


def test_feed_failure_is_warning_not_crash():
    def boom(u):
        raise ConnectionError("x")
    arts, warn = news.collect_news("AAPL", "Apple Inc.", getter=boom)
    assert arts == [] and any("unavailable" in w for w in warn)


def test_indian_symbol_skips_yahoo_feed():
    assert len(news.feed_urls("TCS.NS", "Tata Consultancy Services")) == 1


def test_relevance_short_symbol_not_matched_loosely():
    a = {"title": "A big day for everyone", "summary": ""}
    assert not news.is_relevant(a, "A", None)
