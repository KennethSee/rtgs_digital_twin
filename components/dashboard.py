"""
Shared visualization dashboard component.

Used identically across all three stages. Renders:
  1. Metric cards (avg delay, max delay, settlement rate, turnover ratio)
  2. Transaction results table (colour-coded)
  3. Daily breakdown table
  4. Per-day expandable sections when multiple days are available
  5. Exportable publication-quality charts (PNG, 300 DPI)

The only difference between stages is *when* this dashboard is called:
  - Stage 1: once, after all days complete
  - Stage 2: progressively after each day
  - Stage 3: progressively after each window
"""

import streamlit as st
import pandas as pd

from simulation.metrics import summarise_metrics, calc_daily_metrics
from simulation.engine import AVG_INTRADAY_LIQUIDITY
from components.metrics_cards import render_metrics_cards
from components.results_table import render_results_table
from components.export_charts import (
    generate_daily_metrics_chart,
    generate_transaction_timeline,
)


def render_dashboard(results_list: list, complete: bool = False,
                     avg_liquidity: float = AVG_INTRADAY_LIQUIDITY,
                     stage_name: str = '',
                     all_stage_day_results: dict = None):
    """
    Render the full visualization dashboard for simulation results.

    Args:
        results_list: List of DataFrames, one per completed period (day or window).
        complete: Whether the entire simulation is done.
        avg_liquidity: Average intraday liquidity for turnover ratio calc.
        stage_name: Name of the current stage (for chart titles).
        all_stage_day_results: Optional dict of {stage_name: [day_dfs]} for
                               cross-stage daily metrics chart.
    """
    if not results_list:
        st.info("No results yet. Run the simulation to see data here.")
        return

    # Combine all results so far
    all_results = pd.concat(results_list, ignore_index=True)

    # Overall metrics for everything run so far
    overall_metrics = summarise_metrics(all_results, avg_liquidity)
    render_metrics_cards(overall_metrics)

    # Per-day expandable sections
    if not all_results.empty and 'day' in all_results.columns:
        days = sorted(all_results['day'].unique())
        if len(days) > 1 or complete:
            for d in days:
                day_df = all_results[all_results['day'] == d]
                is_latest = (d == days[-1])
                with st.expander(f"Day {d} Results ({len(day_df)} transactions)",
                                 expanded=is_latest and not complete):
                    day_m = summarise_metrics(day_df, avg_liquidity)
                    render_metrics_cards(day_m)
                    render_results_table(day_df)

    # Full transaction table
    st.subheader("All Transactions")
    render_results_table(all_results)

    # Daily breakdown
    if complete and not all_results.empty:
        st.subheader("Daily Breakdown")
        daily = calc_daily_metrics(all_results, avg_liquidity)
        st.dataframe(daily, use_container_width=True, hide_index=True)

    # --- Exportable Charts ---
    if complete and not all_results.empty:
        st.subheader("Exportable Charts")
        st.caption("Publication-quality PNG charts at 300 DPI.")

        # Chart 1: Transaction Timeline
        timeline_png = generate_transaction_timeline(all_results, stage_name)
        st.image(timeline_png, caption=f"Transaction Timeline — {stage_name}",
                 use_container_width=True)
        st.download_button(
            label="Download Transaction Timeline (PNG)",
            data=timeline_png,
            file_name=f"transaction_timeline_{stage_name.lower().replace(' ', '_').replace('-', '_')}.png",
            mime="image/png",
            key=f"dl_timeline_{stage_name}",
        )

        # Chart 2: Daily Metrics Progression
        # Build per-day DataFrames for this stage
        days = sorted(all_results['day'].unique())
        day_dfs = [all_results[all_results['day'] == d] for d in days]

        # If cross-stage data is available, use it; otherwise just this stage
        if all_stage_day_results:
            chart_data = all_stage_day_results
        else:
            chart_data = {stage_name: day_dfs} if stage_name else {'This Stage': day_dfs}

        daily_png = generate_daily_metrics_chart(chart_data, avg_liquidity)
        st.image(daily_png, caption="Daily Metrics Progression",
                 use_container_width=True)
        st.download_button(
            label="Download Daily Metrics Chart (PNG)",
            data=daily_png,
            file_name=f"daily_metrics_{stage_name.lower().replace(' ', '_').replace('-', '_')}.png",
            mime="image/png",
            key=f"dl_daily_{stage_name}",
        )

    return overall_metrics
