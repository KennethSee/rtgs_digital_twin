"""
RTGS Digital Twin Simulator — Streamlit Entry Point

A multi-stage simulation demonstrating how digital twin maturity improves
Real-Time Gross Settlement (RTGS) system performance.

Three stages of maturity, all using the same PriorityQueue:
  1. Periodic Simulator — fixed parameters, batch results
  2. Real-time Twin — user adjusts threshold between days
  3. AI-enabled Twin — AI auto-adjusts threshold per window
"""

import sys
import os

# Ensure the project root is on the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

st.set_page_config(
    page_title="RTGS Digital Twin Simulator",
    page_icon="🏦",
    layout="wide",
)

st.title("RTGS Digital Twin Simulator")
st.caption(
    "Explore how increasing digital twin maturity — from periodic simulation "
    "to AI-enabled real-time adjustment — improves settlement performance "
    "in a Real-Time Gross Settlement system."
)

TABS = ["Periodic Simulator", "Real-time Twin", "AI-enabled Twin"]
tabs = st.tabs(TABS)

with tabs[0]:
    from stages.stage1_periodic import render as render_s1
    render_s1()

with tabs[1]:
    from stages.stage2_realtime import render as render_s2
    render_s2()

with tabs[2]:
    from stages.stage3_ai_enabled import render as render_s3
    render_s3()

# --- Cross-stage comparison (always visible once at least 1 stage has been run) ---
from components.comparison_chart import render_comparison_chart
from components.export_charts import generate_cross_stage_chart

if st.session_state.get('stage_results'):
    st.divider()
    st.subheader("Cross-Stage Comparison")
    render_comparison_chart(st.session_state['stage_results'])

    # Exportable version
    cross_png = generate_cross_stage_chart(st.session_state['stage_results'])
    st.download_button(
        label="Download Cross-Stage Comparison (PNG)",
        data=cross_png,
        file_name="cross_stage_comparison.png",
        mime="image/png",
        key="dl_cross_stage",
    )
