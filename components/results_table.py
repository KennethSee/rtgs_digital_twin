"""
Shared results table component with colour-coded delay and status columns.
"""

import streamlit as st
import pandas as pd


def render_results_table(results_df: pd.DataFrame):
    """
    Renders a colour-coded Streamlit dataframe.
    - delay_minutes: red if > 60, amber if > 30, green otherwise
    - status: green for 'Success', red for 'Failed'
    """
    if results_df.empty:
        st.info("No transactions to display.")
        return

    display_df = results_df.copy()

    # Rename columns for display
    col_map = {
        'id': 'ID',
        'day': 'Day',
        'sender': 'Sender',
        'recipient': 'Recipient',
        'amount': 'Amount ($)',
        'submitted_time': 'Submitted',
        'settled_time': 'Settled',
        'delay_minutes': 'Delay (min)',
        'status': 'Status',
    }
    display_cols = [c for c in col_map.keys() if c in display_df.columns]
    display_df = display_df[display_cols].rename(columns=col_map)

    def colour_delay(val):
        try:
            v = float(val)
        except (ValueError, TypeError):
            return ''
        if v > 60:
            return 'background-color: #f8d7da; color: #721c24'  # Red
        elif v > 30:
            return 'background-color: #fff3cd; color: #856404'  # Amber
        else:
            return 'background-color: #d4edda; color: #155724'  # Green

    def colour_status(val):
        if val == 'Success':
            return 'background-color: #d4edda; color: #155724'
        elif val == 'Failed':
            return 'background-color: #f8d7da; color: #721c24'
        return ''

    styled = display_df.style
    # Use applymap (pandas <1.3) or map (pandas >=1.3) for cell-wise styling
    _style_fn = styled.applymap if hasattr(styled, 'applymap') else styled.map
    if 'Delay (min)' in display_df.columns:
        styled = _style_fn(colour_delay, subset=['Delay (min)'])
    if 'Status' in display_df.columns:
        styled = _style_fn(colour_status, subset=['Status'])

    st.dataframe(styled, use_container_width=True, hide_index=True, height=400)
