import streamlit as st
import requests
import os
from datetime import datetime

st.set_page_config(
    page_title="swingtradev3",
    page_icon="📈",
    layout="wide",
)

# Auto-refresh every 30 seconds
# streamlit_autorefresh is not always available, using built-in rerun for simple refresh
# if "last_refresh" not in st.session_state:
#    st.session_state.last_refresh = datetime.now()

st.title("📈 swingtradev3 Dashboard")
st.caption(f"Autonomous AI Swing Trading System — v2.0 | Refreshed: {datetime.now().strftime('%H:%M:%S')}")

api_key = os.environ.get("FASTAPI_API_KEY", "")
base_url = "http://localhost:8000"
headers = {"X-API-Key": api_key}

st.divider()

# Fetch summary data
try:
    stats_res = requests.get(f"{base_url}/stats", headers=headers)
    pos_res = requests.get(f"{base_url}/positions", headers=headers)
    regime_res = requests.get(f"{base_url}/regime", headers=headers)
    
    stats = stats_res.json() if stats_res.status_code == 200 else {}
    positions = pos_res.json() if pos_res.status_code == 200 else []
    regime = regime_res.json() if regime_res.status_code == 200 else {}

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(label="Total Trades", value=stats.get("trade_count", 0))
    with col2:
        st.metric(label="Open Positions", value=len(positions))
    with col3:
        st.metric(label="Win Rate", value=f"{stats.get('win_rate', 0)*100:.1f}%")
    with col4:
        st.metric(label="Market Regime", value=regime.get("regime", "—").upper())

except Exception as e:
    st.error(f"Failed to connect to API: {e}")

st.divider()

col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("System Status")
    try:
        health_res = requests.get(f"{base_url}/health", headers=headers)
        if health_res.status_code == 200:
            health = health_res.json()
            
            # App health
            st.success(f"✅ Backend API: {health['status'].upper()}")
            st.info(f"🔄 Trading Mode: {health['mode'].upper()}")
            
            # External services (Lazy Health)
            st.divider()
            st.write("**External Services (Lazy Status)**")
            svc_cols = st.columns(len(health.get("services", {})) - 1) # exclude 'app'
            
            idx = 0
            for svc, status in health.get("services", {}).items():
                if svc == "app": continue
                
                label = svc.replace("_", " ").title()
                if status == "healthy":
                    st.success(f"✅ {label}")
                else:
                    st.error(f"❌ {label}")
    except:
        st.error("🚨 Backend API: OFFLINE")

with col_right:
    st.subheader("Quick Actions")
    if st.button("Trigger Manual Scan", use_container_width=True):
        res = requests.post(f"{base_url}/scan", headers=headers)
        if res.status_code == 200:
            st.toast("Scan Triggered!")
        else:
            st.error("Failed to trigger scan")
    
    if st.button("Refresh Dashboard", use_container_width=True):
        st.rerun()

