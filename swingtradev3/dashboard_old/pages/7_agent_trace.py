import streamlit as st
import os
from pathlib import Path

st.set_page_config(page_title="Agent Trace", page_icon="🤖")
st.title("ADK Agent Trace View")

st.info("Visualizing agent traces from logs/research.log.")

log_path = Path(__file__).resolve().parents[2] / "logs" / "research.log"

if log_path.exists():
    with open(log_path, "r") as f:
        logs = f.readlines()
        
    st.text_area("Research Logs", value="".join(logs[-100:]), height=500)
else:
    st.warning("No research logs found yet.")
