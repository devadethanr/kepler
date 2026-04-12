import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import os

st.set_page_config(page_title="Overview", page_icon="📊", layout="wide")
st.title("Portfolio Overview")

api_key = os.environ.get("FASTAPI_API_KEY", "")

# Fetch data from API
try:
    stats_res = requests.get("http://localhost:8000/stats", headers={"X-API-Key": api_key})
    if stats_res.status_code == 200:
        stats = stats_res.json()
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Win Rate", f"{stats.get('win_rate', 0)*100:.1f}%")
        col2.metric("Sharpe Ratio", f"{stats.get('sharpe', 0):.2f}")
        col3.metric("Total Trades", f"{stats.get('trade_count', 0)}")
        col4.metric("Kelly Multiplier", f"{stats.get('kelly_multiplier', 0):.2f}")
        
        # Mock P&L Curve
        st.subheader("Equity Curve")
        history = pd.DataFrame({
            "date": pd.date_range(start="2026-01-01", periods=10, freq="D"),
            "equity": [20000, 20100, 19950, 20300, 20500, 20400, 20800, 21000, 21500, 21800]
        })
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=history["date"], y=history["equity"], mode='lines+markers', name='Equity'))
        fig.update_layout(title="Total Account Equity (INR)", xaxis_title="Date", yaxis_title="Equity")
        st.plotly_chart(fig, use_container_width=True)
        
    else:
        st.error(f"Failed to fetch stats: {stats_res.status_code}")
except Exception as e:
    st.error(f"API Connection Error: {e}")

