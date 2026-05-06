"""
Cross-stage comparison bar chart component.
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots


STAGE_COLOURS = {
    'Periodic Simulator': '#6c757d',   # Gray
    'Real-time Twin': '#007bff',       # Blue
    'AI-enabled Twin': '#6f42c1',      # Purple
}

STAGE_ORDER = ['Periodic Simulator', 'Real-time Twin', 'AI-enabled Twin']


def render_comparison_chart(all_stage_results: dict):
    """
    Renders side-by-side bar charts comparing Avg Payment Delay and
    Settlement Rate across all stages that have been run.
    """
    if not all_stage_results:
        return

    # Filter to stages that have been run, in canonical order
    stages = [s for s in STAGE_ORDER if s in all_stage_results]
    if not stages:
        return

    delays = [all_stage_results[s].get('avg_delay', 0) for s in stages]
    rates = [all_stage_results[s].get('settlement_rate', 0) for s in stages]
    colours = [STAGE_COLOURS.get(s, '#999') for s in stages]

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Avg Payment Delay (min)", "Settlement Rate (%)"),
        horizontal_spacing=0.12,
    )

    fig.add_trace(
        go.Bar(
            x=stages, y=delays,
            marker_color=colours,
            text=[f"{d:.1f}" for d in delays],
            textposition='outside',
            name='Avg Delay',
            showlegend=False,
        ),
        row=1, col=1,
    )

    fig.add_trace(
        go.Bar(
            x=stages, y=rates,
            marker_color=colours,
            text=[f"{r:.1f}%" for r in rates],
            textposition='outside',
            name='Settlement Rate',
            showlegend=False,
        ),
        row=1, col=2,
    )

    fig.update_layout(
        height=400,
        margin=dict(t=40, b=20),
    )
    max_delay = max(delays) if delays else 1
    fig.update_yaxes(title_text="Minutes", row=1, col=1, range=[0, max_delay * 1.2])
    fig.update_yaxes(title_text="Percent", row=1, col=2, range=[0, 110])

    st.plotly_chart(fig, use_container_width=True)
