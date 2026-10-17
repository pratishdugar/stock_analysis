"""Free RSS news collection with dedupe and relevance filtering. Network is injectable."""
import re
from datetime import datetime, timezone
from urllib.parse import quote_plus

MAX_ARTICLES = 8
TIMEOUT = 10
_STOP = {"inc", "corp", "corporation", "ltd", "limited", "co", "company", "plc", "the", "holdings", "group"}


def _name_words(name: str | None) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", (name or "").lower()) if w not in _STOP]


def feed_urls(symbol: str, name: str | None) -> list[str]:
    base = symbol.split(".")[0]
    words = _name_words(name)
    q = quote_plus(f'"{" ".join(words[:3])}" stock' if words else f"{base} stock")
    urls = [f"https://news.google.com/rss/search?q={q}&hl=en&ceid=US:en"]
    if "." not in symbol:  # Yahoo's headline feed is only reliable for US tickers
        urls.append(f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US")
    return urls


def _http_get(url: str) -> bytes:
    import requests
    r = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "stock-research-app/0.1"})
    r.raise_for_status()
    return r.content


def _parse(content: bytes) -> list[dict]:
    import feedparser
    out = []
    for e in feedparser.parse(content).entries:
        pub = None
        if getattr(e, "published_parsed", None):
            pub = datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
        out.append({"title": (e.get("title") or "").strip(), "url": e.get("link") or "",
                    "summary": re.sub(r"<[^>]+>", "", e.get("summary") or "")[:300],
                    "source": (e.get("source") or {}).get("title", "") if isinstance(e.get("source"), dict) else "",
                    "published": pub})
    return out


def _key(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower().rsplit(" - ", 1)[0]).strip()


def dedupe(articles: list[dict]) -> list[dict]:
    seen, out = set(), []
    for a in articles:
        k = _key(a["title"])
        if not a["title"] or not a["url"] or k in seen or a["url"] in seen:
            continue
        seen.update({k, a["url"]})
        out.append(a)
    return out


def is_relevant(article: dict, symbol: str, name: str | None) -> bool:
    text = f"{article['title']} {article['summary']}".lower()
    terms = {symbol.split(".")[0].lower()} if len(symbol.split(".")[0]) >= 3 else set()
    words = _name_words(name)
    if words:
        terms.add(" ".join(words[:2]))
        # A lone first word ("Tata", "Reliance") is only safe when it IS the whole name ("Apple Inc.").
        if len(words) == 1 and len(words[0]) >= 4:
            terms.add(words[0])
    return any(re.search(rf"\b{re.escape(t)}\b", text) for t in terms)


def collect_news(symbol: str, name: str | None = None, getter=None, limit: int = MAX_ARTICLES):
    """Return (articles, warnings). Never raises; failed feeds become warnings."""
    getter = getter or _http_get
    arts, warnings = [], []
    for url in feed_urls(symbol, name):
        try:
            arts += _parse(getter(url))
        except Exception as exc:
            warnings.append(f"News feed unavailable ({type(exc).__name__}).")
    arts = [a for a in dedupe(arts) if is_relevant(a, symbol, name)]
    arts.sort(key=lambda a: a["published"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    arts = arts[:limit]
    if not arts:
        warnings.append("No relevant recent articles found.")
    return arts, warnings
