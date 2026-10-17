"""Build a compact summary of one stock from already-fetched data (used by save + compare)."""
from src import fundamentals, market_data as md, scoring, technicals as ta


def build_summary(symbol: str, hist, info_result, bench_close=None) -> dict:
    close = hist["Close"]
    metrics = fundamentals.extract_metrics(info_result.data if info_result is not None and info_result.ok else None)
    result = scoring.score_stock(metrics, scoring.momentum_inputs(close, bench_close))
    return {"symbol": symbol, "name": metrics.get("name"), "currency": metrics.get("currency"),
            "market": md.market_of(symbol), "quant_score": result["quant_score"], "coverage": result["coverage"],
            "label": result["label"], "risks": result["risks"], "ret_1y": ta.period_return(close, 252),
            "max_drawdown": ta.max_drawdown(close.tail(756)), "result": result, "metrics": metrics}
