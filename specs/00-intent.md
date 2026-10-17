# 00 · Product intent

## Why this exists
A single, private, free place where one person can **research stocks** and **see and manage all of their
investments** — Indian and US stocks, mutual funds and SIPs, gold, fixed deposits, retirement products and private
investments — with **explainable, long-term (5+ year)** buy / hold / review prompts.

## User
One retail investor in India who also holds US stocks; not a programmer; may start from a phone (Claude Code) and
later run the app on a Windows PC. Wants to avoid paying for data or tools and to avoid manual debugging.

## Principles (apply to every feature)
1. **Explain, don't dictate.** Every score or recommendation shows its inputs, thresholds and reasons. Outputs are
   research prompts, never trading instructions; a weak holding means *review*, never an automatic sell.
2. **Long-term first.** Default horizon 5 years (configurable). Short-term price moves and the user's purchase price
   (sunk cost) never drive a recommendation.
3. **Honest about data.** Missing values are skipped, never treated as zero. Low coverage marks an assessment
   *incomplete*. Data source, currency and date are shown. Different currencies are never added without a rate.
4. **Works offline from AI.** Everything except news analysis works without a Gemini key; the combined score is
   shown as *Unavailable* rather than silently replaced by the quantitative score.
5. **Private by default.** Personal holdings live only in a local SQLite file that git ignores. No secrets in the repo.
6. **Free and frugal.** Free data sources (Yahoo via yfinance, RSS, mfapi.in) and Gemini's free tier only; bounded,
   cached, on-demand API calls.
7. **Simple code.** Small functions in small modules; pure logic in `src/` with injectable data fetchers; Streamlit
   only in `app.py` / `ui_portfolio.py`. No agents, RAG, vector DBs, cloud deployment or heavy abstractions.

## Non-goals
Automated trading or order placement; real-time quotes; tax filing or tax optimisation; multi-user accounts;
hosting the app on the internet; guaranteeing data accuracy.

## Constraints
Python 3.11+ (CI tests 3.12 on Linux and Windows); Streamlit UI; must install and run on Windows with `setup.ps1` /
`run.ps1`; automated tests must never need network access or real API keys.
