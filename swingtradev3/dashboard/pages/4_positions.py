import streamlit as st
import requests
import pandas as pd

import os

st.set_page_config(page_title="Positions", page_icon="💼")
st.title("Open Positions")

api_key = os.environ.get("FASTAPI_API_KEY", "")

try:
    res = requests.get("http://localhost:8000/positions", headers={"X-API-Key": api_key})
    if res.status_code == 200:
        positions = res.json()
        if not positions:
            st.info("No open positions.")
        else:
            df = pd.DataFrame(positions)
            st.dataframe(
                df[["ticker", "quantity", "entry_price", "current_price", "stop_price", "target_price"]],
                use_container_width=True
            )
            
            st.write("### Detailed View")
            for pos in positions:
                with st.expander(f"{pos['ticker']} ({pos['quantity']} shares)"):
                    st.json(pos)
    else:
        st.error(f"Failed to fetch positions: {res.status_code}")
except Exception as e:
    st.error(f"API Connection Error: {e}")
