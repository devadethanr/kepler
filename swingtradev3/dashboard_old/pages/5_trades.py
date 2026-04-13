import streamlit as st
import requests
import pandas as pd

import os

st.set_page_config(page_title="Trades", page_icon="📜")
st.title("Trade History")

api_key = os.environ.get("FASTAPI_API_KEY", "")

try:
    res = requests.get("http://localhost:8000/trades", headers={"X-API-Key": api_key})
    if res.status_code == 200:
        trades = res.json()
        if not trades:
            st.info("No closed trades yet.")
        else:
            df = pd.DataFrame(trades)
            st.dataframe(
                df[["ticker", "quantity", "entry_price", "exit_price", "pnl_abs", "pnl_pct", "exit_reason"]],
                use_container_width=True
            )
            
            st.write("### Detailed View")
            for trade in trades:
                with st.expander(f"{trade['ticker']} ({trade['exit_reason']}) - P&L: ₹{trade['pnl_abs']:.2f}"):
                    st.json(trade)
    else:
        st.error(f"Failed to fetch trades: {res.status_code}")
except Exception as e:
    st.error(f"API Connection Error: {e}")
