import streamlit as st
import requests

import os

st.set_page_config(page_title="Overview", page_icon="📊")
st.title("Portfolio Overview")

api_key = os.environ.get("FASTAPI_API_KEY", "")

# Fetch data from API
try:
    stats_res = requests.get("http://localhost:8000/stats", headers={"X-API-Key": api_key})
    if stats_res.status_code == 200:
        stats = stats_res.json()
        st.write(f"**Win Rate:** {stats.get('win_rate', 0)*100:.1f}%")
        st.write(f"**Sharpe Ratio:** {stats.get('sharpe', 0):.2f}")
        st.write(f"**Total Trades:** {stats.get('trade_count', 0)}")
    else:
        st.error(f"Failed to fetch stats: {stats_res.status_code}")
except Exception as e:
    st.error(f"API Connection Error: {e}")

st.info("Charts and deeper portfolio analytics will be added in Phase 3.")
