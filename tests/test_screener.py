from src import screener, universe


def S(sym, score, cov=0.9, dd=-0.2, risks=()):
    return {"symbol": sym, "quant_score": score, "coverage": cov, "max_drawdown": dd, "risks": list(risks)}


def test_filter_and_sort():
    data = [S("A", 60), S("B", 80), S("C", 50), S("D", None), S("E", 90, cov=0.3), S("F", 85, dd=-0.7),
            S("G", 88, risks=["x"])]
    assert [s["symbol"] for s in screener.filter_candidates(data)] == ["B", "A"]
    assert "G" in [s["symbol"] for s in screener.filter_candidates(data, exclude_risks=False)]


def test_run_screen_isolates_failures():
    def summ(sym):
        if sym == "BAD":
            raise RuntimeError("boom")
        return S(sym, 70)
    prog = []
    out, errs = screener.run_screen(["A", "BAD", "B"], summ, prog.append)
    assert [s["symbol"] for s in out] == ["A", "B"] and "BAD" in errs and prog[-1] == 1.0


def test_news_cap():
    assert len(screener.news_shortlist([S(str(i), 80) for i in range(20)], n=50)) == 3
    assert screener.news_shortlist([S("a", 1)], n=-1) == []


def test_universe_unique_and_valid():
    from src import market_data as md
    allsyms = universe.UNIVERSES["Both (30)"]
    assert len(allsyms) == len(set(allsyms)) == 30
    assert all(md.normalize_symbol(s)[0] == s for s in allsyms)
