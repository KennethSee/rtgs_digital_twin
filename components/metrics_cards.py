"""
Shared metric card row component.
"""

import streamlit as st


def render_metrics_cards(metrics: dict):
    """
    Renders a 4-column row with key metrics.
    - Avg Payment Delay (red/amber/green)
    - Max Delay
    - Settlement Rate % (red if < 85%)
    - Turnover Ratio
    """
    col1, col2, col3, col4 = st.columns(4)

    avg_delay = metrics.get('avg_delay', 0)
    max_delay = metrics.get('max_delay', 0)
    sett_rate = metrics.get('settlement_rate', 0)
    turnover = metrics.get('turnover_ratio', 0)

    # Colour logic
    if avg_delay > 60:
        delay_delta_color = "off"
    elif avg_delay > 30:
        delay_delta_color = "off"
    else:
        delay_delta_color = "off"

    with col1:
        st.metric(
            label="Avg Payment Delay",
            value=f"{avg_delay:.1f} min",
            delta=("High" if avg_delay > 60 else "Moderate" if avg_delay > 30 else "Low"),
            delta_color=("inverse" if avg_delay > 30 else "normal"),
        )

    with col2:
        st.metric(
            label="Max Delay",
            value=f"{max_delay:.0f} min",
        )

    with col3:
        st.metric(
            label="Settlement Rate",
            value=f"{sett_rate:.1f}%",
            delta=("Below target" if sett_rate < 85 else "On target"),
            delta_color=("inverse" if sett_rate < 85 else "normal"),
        )

    with col4:
        st.metric(
            label="Turnover Ratio",
            value=f"{turnover:.2f}",
        )
