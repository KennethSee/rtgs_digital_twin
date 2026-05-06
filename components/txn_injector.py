"""
Manual transaction injection component.

Allows users to add custom transactions on top of the base CSV data,
creating ad-hoc scenarios without predefined scenario definitions.
"""

import streamlit as st
import pandas as pd

from simulation.engine import BANK_NAMES


ACCOUNT_IDS = [f'acc_{b}' for b in BANK_NAMES]


def render_txn_injector(key_prefix: str = 'inj') -> pd.DataFrame:
    """
    Renders a transaction injection form and returns a DataFrame of
    injected transactions (may be empty).

    The returned DataFrame has columns matching sample_transactions.csv:
        id, sender_account, recipient_account, amount, time, day

    Args:
        key_prefix: Unique prefix for Streamlit widget keys (avoids
                    collisions when used across multiple stages).

    Returns:
        DataFrame of injected transactions (empty if none added).
    """
    state_key = f'{key_prefix}_injected_txns'
    if state_key not in st.session_state:
        st.session_state[state_key] = []

    with st.expander("Add Custom Transactions", expanded=False):
        st.caption(
            "Inject additional transactions on top of the base data. "
            "These are combined with the CSV transactions before simulation."
        )

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            sender = st.selectbox(
                "Sender", ACCOUNT_IDS,
                key=f'{key_prefix}_sender'
            )
        with col2:
            # Filter out sender from recipient options
            recipient_options = [a for a in ACCOUNT_IDS if a != sender]
            recipient = st.selectbox(
                "Recipient", recipient_options,
                key=f'{key_prefix}_recipient'
            )
        with col3:
            amount = st.number_input(
                "Amount ($)", min_value=50, max_value=5000, value=500, step=50,
                key=f'{key_prefix}_amount'
            )
        with col4:
            time_val = st.text_input(
                "Time (HH:MM)", value="09:00",
                key=f'{key_prefix}_time'
            )

        day = st.number_input(
            "Day", min_value=1, max_value=10, value=1, step=1,
            key=f'{key_prefix}_day'
        )

        col_add, col_clear = st.columns([1, 1])
        with col_add:
            if st.button("Add Transaction", key=f'{key_prefix}_add'):
                # Validate time format
                try:
                    parts = time_val.split(':')
                    h, m = int(parts[0]), int(parts[1])
                    if not (0 <= h <= 23 and 0 <= m <= 59):
                        raise ValueError
                    formatted_time = f"{h:02d}:{m:02d}"
                except (ValueError, IndexError):
                    st.error("Invalid time format. Use HH:MM (e.g., 09:00).")
                    formatted_time = None

                if formatted_time and sender != recipient:
                    new_txn = {
                        'sender_account': sender,
                        'recipient_account': recipient,
                        'amount': int(amount),
                        'time': formatted_time,
                        'day': int(day),
                    }
                    st.session_state[state_key].append(new_txn)
                    st.rerun()

        with col_clear:
            if st.button("Clear All", key=f'{key_prefix}_clear'):
                st.session_state[state_key] = []
                st.rerun()

        # Show current injected transactions
        if st.session_state[state_key]:
            st.markdown(f"**{len(st.session_state[state_key])} injected transaction(s):**")
            inj_df = pd.DataFrame(st.session_state[state_key])
            st.dataframe(inj_df, use_container_width=True, hide_index=True)

    # Build return DataFrame
    if st.session_state[state_key]:
        inj_df = pd.DataFrame(st.session_state[state_key])
        # Assign IDs starting from 1000 to avoid collision with base data
        inj_df['id'] = range(1000, 1000 + len(inj_df))
        return inj_df
    else:
        return pd.DataFrame(columns=['id', 'sender_account', 'recipient_account',
                                      'amount', 'time', 'day'])


def merge_transactions(base_df: pd.DataFrame, injected_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge base CSV transactions with injected transactions.

    Returns a combined DataFrame ready for simulation.
    """
    if injected_df.empty:
        return base_df

    # Ensure column alignment
    cols = ['id', 'sender_account', 'recipient_account', 'amount', 'time', 'day']
    base = base_df.copy()
    injected = injected_df.copy()

    # Only keep columns that exist in both
    for c in cols:
        if c not in base.columns:
            if c == 'id':
                base['id'] = range(1, len(base) + 1)
            else:
                base[c] = None
        if c not in injected.columns:
            injected[c] = None

    combined = pd.concat([base[cols], injected[cols]], ignore_index=True)
    return combined
