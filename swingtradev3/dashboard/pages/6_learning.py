import streamlit as st
from pathlib import Path

st.set_page_config(page_title="Learning", page_icon="🧠")
st.title("System Evolution & Learning")

st.info("The Learning Loop will be fully implemented in Phase 3.")

st.subheader("SKILL.md")
skill_path = Path(__file__).resolve().parents[2] / "strategy" / "SKILL.md"
if skill_path.exists():
    with st.expander("Current Trading Philosophy", expanded=True):
        st.markdown(skill_path.read_text())
else:
    st.error("SKILL.md not found.")
