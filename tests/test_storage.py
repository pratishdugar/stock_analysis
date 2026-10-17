from src import storage as st


def test_watchlist_roundtrip(tmp_path):
    p = tmp_path / "a.db"
    st.add_watchlist("AAPL", p); st.add_watchlist("AAPL", p); st.add_watchlist("TCS.NS", p)
    assert st.list_watchlist(p) == ["AAPL", "TCS.NS"]
    st.remove_watchlist("AAPL", p)
    assert st.list_watchlist(p) == ["TCS.NS"]


def test_research_upsert_and_history(tmp_path):
    p = tmp_path / "a.db"
    st.save_research("AAPL", 70.0, 0.9, "Hold", path=p, day="2025-01-01")
    st.save_research("AAPL", 71.0, 0.9, "Hold", news_score=60, combined_score=67.7, path=p, day="2025-01-01")
    st.save_research("AAPL", 72.0, 0.9, "Hold", path=p, day="2025-01-02")
    h = st.research_history("AAPL", path=p)
    assert [r["day"] for r in h] == ["2025-01-02", "2025-01-01"] and h[1]["news_score"] == 60
    assert st.research_history("MSFT", path=p) == []


def test_corrupted_db_is_recovered(tmp_path):
    p = tmp_path / "bad.db"
    p.write_bytes(b"this is not a sqlite database" * 50)
    assert st.list_watchlist(p) == []
    assert (tmp_path / "bad.db.corrupt").exists()
    st.add_watchlist("X", p)
    assert st.list_watchlist(p) == ["X"]
