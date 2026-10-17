"""Quant-first screener over a curated list. No news/Gemini here: news is only run on a few shortlisted names."""
MAX_NEWS_CANDIDATES = 3  # hard cap on Gemini requests per screen


def run_screen(symbols, summarize, progress=None) -> tuple[list[dict], dict[str, str]]:
    """summarize(symbol) -> summary dict (see report.build_summary) or raises. Returns (summaries, errors)."""
    out, errors = [], {}
    for i, sym in enumerate(symbols):
        try:
            out.append(summarize(sym))
        except Exception as exc:
            errors[sym] = str(exc) or type(exc).__name__
        if progress:
            progress((i + 1) / len(symbols))
    return out, errors


def filter_candidates(summaries, min_score=55.0, min_coverage=0.6, max_drawdown=-0.6, exclude_risks=True):
    """Keep complete assessments passing the thresholds; sort by score (high first)."""
    keep = []
    for s in summaries:
        if s["quant_score"] is None or s["coverage"] < min_coverage or s["quant_score"] < min_score:
            continue
        if s["max_drawdown"] is not None and s["max_drawdown"] < max_drawdown:
            continue
        if exclude_risks and s["risks"]:
            continue
        keep.append(s)
    return sorted(keep, key=lambda s: s["quant_score"], reverse=True)


def news_shortlist(candidates, n=MAX_NEWS_CANDIDATES):
    return candidates[: max(0, min(n, MAX_NEWS_CANDIDATES))]
