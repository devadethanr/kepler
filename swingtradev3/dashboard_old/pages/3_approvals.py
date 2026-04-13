import streamlit as st
import requests

import os

st.set_page_config(page_title="Approvals", page_icon="✅")
st.title("Pending Trade Approvals")

api_key = os.environ.get("FASTAPI_API_KEY", "")

try:
    res = requests.get("http://localhost:8000/approvals", headers={"X-API-Key": api_key})
    if res.status_code == 200:
        approvals = res.json()
        if not approvals:
            st.info("No pending approvals at this time.")
        else:
            for approval in approvals:
                if approval.get("approved"):
                    continue
                with st.expander(f"{approval.get('ticker')} - Score: {approval.get('score')} ({approval.get('setup_type')})", expanded=True):
                    st.write(f"**Reasoning:** {approval.get('confidence_reasoning')}")
                    st.write(f"**Entry Zone:** {approval.get('entry_zone', {}).get('low')} - {approval.get('entry_zone', {}).get('high')}")
                    st.write(f"**Stop Loss:** {approval.get('stop_price')}")
                    st.write(f"**Target:** {approval.get('target_price')}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Approve", key=f"approve_{approval.get('ticker')}"):
                            try:
                                resp = requests.post(f"http://localhost:8000/approvals/{approval.get('ticker')}/yes", headers={"X-API-Key": api_key})
                                if resp.status_code == 200:
                                    st.success("Trade Approved!")
                                    st.rerun()
                                else:
                                    st.error("Approval failed.")
                            except Exception as e:
                                st.error(str(e))
                    with col2:
                        if st.button("❌ Reject", key=f"reject_{approval.get('ticker')}"):
                            try:
                                resp = requests.post(f"http://localhost:8000/approvals/{approval.get('ticker')}/no", headers={"X-API-Key": api_key})
                                if resp.status_code == 200:
                                    st.success("Trade Rejected.")
                                    st.rerun()
                                else:
                                    st.error("Rejection failed.")
                            except Exception as e:
                                st.error(str(e))
    else:
        st.error(f"Failed to fetch approvals: {res.status_code}")
except Exception as e:
    st.error(f"API Connection Error: {e}")
