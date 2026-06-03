import sys
import asyncio

# Must run before other async operations on Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import streamlit as st
from ui.styles import get_custom_css
from ui.sidebar import render_sidebar
from ui.landing import render_landing
from ui.dashboard import render_dashboard

# ─────────────────────────────────────────────
#  PAGE CONFIG & INITIALIZATION
# ─────────────────────────────────────────────
st.set_page_config(
    layout="wide",
    page_title="Adherence Intelligence",
    page_icon="◈",
    initial_sidebar_state="expanded"
)

# Initialize Session State
for key, default in [
    ("audit_results", None),
    ("audit_company", None),
    ("matching_folders", []),
    ("has_searched", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# Apply Global Fonts and CSS
st.markdown('<link href="https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">', unsafe_allow_html=True)
st.markdown(f'<style>{get_custom_css()}</style>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  RENDER APPLICATION
# ─────────────────────────────────────────────
render_sidebar()

if st.session_state.audit_results is None:
    render_landing()
else:
    render_dashboard()