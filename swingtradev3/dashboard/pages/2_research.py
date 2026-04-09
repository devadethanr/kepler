import streamlit as st
import requests
import json

import os

st.set_page_config(page_title="Research Scan", page_icon="🔍")
st.title("Research Scan Results")

api_key = os.environ.get("FASTAPI_API_KEY", "")

if st.button("Trigger New Scan"):
    try:
        res = requests.post("http://localhost:8000/scan", headers={"X-API-Key": api_key})
        if res.status_code == 200:
            st.success("Scan triggered successfully in background.")
        else:
            st.error(f"Failed to trigger scan: {res.text}")
    except Exception as e:
        st.error(f"API Connection Error: {e}")

try:
    res = requests.get("http://localhost:8000/scan/status", headers={"X-API-Key": api_key})
    if res.status_code == 200:
        data = res.json()
        st.subheader(f"Status: {data.get('status').upper()}")
        if data.get('started_at'):
            st.text(f"Started at: {data['started_at']}")
        
        result = data.get("result")
        if result:
            st.divider()
            st.subheader(f"Scan Date: {result.get('scan_date')}")
            st.write(f"**Total Screened:** {result.get('total_screened')} | **Qualified:** {result.get('qualified_count')}")
            
            shortlist = result.get("shortlist", [])
            if shortlist:
                st.write(f"### Shortlist ({len(shortlist)})")
                for stock in shortlist:
                    with st.expander(f"{stock['ticker']} - Score: {stock['score']}"):
                        st.write(f"**Setup Type:** {stock.get('setup_type')}")
                        st.write(f"**Reasoning:** {stock.get('confidence_reasoning')}")
                        st.json(stock)
            else:
                st.info("No stocks made the shortlist.")
                
    else:
        st.error(f"Failed to fetch scan status: {res.status_code}")
except Exception as e:
    st.error(f"API Connection Error: {e}")
