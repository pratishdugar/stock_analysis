"""Stock Research App - Streamlit entry point."""
import streamlit as st

import config

st.set_page_config(page_title="Stock Research", page_icon="📈", layout="wide")
st.title("📈 Stock Research")
st.caption("Personal long-term (1-5 year) research tool. Not financial advice.")

st.info("Phase 0 foundation is running. Market analysis arrives in Phase 1.")

if config.gemini_configured():
    st.success("Gemini is configured (news analysis will be available in Phase 2).")
else:
    st.warning("Gemini is not configured. The app works without it; "
               "combined scores will show as unavailable.")

with st.expander("Ticker format examples"):
    st.markdown("- US: `AAPL`, `MSFT`\n- NSE: `RELIANCE.NS`, `TCS.NS`\n- BSE: `RELIANCE.BO`")
