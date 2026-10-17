# 02 · News and Gemini analysis

## Intent
Add a bounded, evidence-linked read of recent news to the quantitative view — cheaply, safely and optionally.

## Requirements
- News MUST come from free RSS: Google News search (all tickers) plus Yahoo headlines (US tickers only). Feed
  failures become warnings. ✅T
- Articles MUST be de-duplicated (same URL or same title ignoring the " - Source" suffix), filtered for relevance
  (ticker base ≥ 3 chars, or the first two significant words of the company name; a lone first word only when it is
  the whole name, so "Tata" alone does not match TCS), sorted newest first and capped at **8**. ✅T
- Gemini MUST be called only when the user clicks, with **one** request for all selected articles, using the
  official `google-genai` SDK, model from `GEMINI_MODEL` (never hard-coded), JSON response, 30 s timeout. ✅T
- The prompt MUST treat articles as untrusted data and state the user's configured horizon. ✅T
- The response MUST be validated: `news_score` number 0–100; `sentiment` ∈ positive/neutral/negative/mixed;
  `thesis_change` ∈ strengthened/unchanged/weakened/broken/unclear; `confidence` ∈ low/medium/high; `catalysts`,
  `risks`, `evidence_urls`, `data_limitations` lists of strings; evidence URLs not in the input are dropped. ✅T
- Results MUST be cached in memory for 6 hours per (model, symbol, horizon, article URLs). ✅T
- Missing key/model, quota (429/RESOURCE_EXHAUSTED), bad key, unknown model and malformed output MUST each give a
  clear message; the quantitative analysis is unaffected. ✅T
- Combined score = 0.70 × quantitative + 0.30 × news, shown **only** when both exist; otherwise *Unavailable*. ✅T

## Limitations
Gemini model availability and free-tier limits change; the user must pick a current Flash model. RSS coverage of
Indian companies is uneven. The news cache is per app process (lost on restart).
