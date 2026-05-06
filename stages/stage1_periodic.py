"""
Stage 1 — Periodic Simulator (No Twin)

Fixed parameters for the entire run. The PriorityQueue threshold is set
once before simulation and never updated. All days run to completion
before any results are shown.
"""

import os
import streamlit as st
import pandas as pd

from simulation.queues import PriorityQueue
from simulation.engine import (
    load_transactions, run_full_simulation,
    DEFAULT_BALANCES, AVG_INTRADAY_LIQUIDITY
)
from simulation.metrics import summarise_metrics
from components.dashboard import render_dashboard
from components.txn_injector import render_txn_injector, merge_transactions


NUM_DAYS = 3
KEY = 'stg1'


def _get_data_path():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, 'data', 'sample_transactions.csv')


def render():
    st.header("Stage 1: Periodic Simulator")
    st.markdown(
        "Fixed-parameter simulation — the priority threshold is set once and "
        "**never updated** during the run. All days execute before results are shown. "
        "This represents a system with no digital twin feedback loop."
    )

    # --- Configuration ---
    threshold = st.slider(
        "Priority threshold ($)",
        min_value=50, max_value=900, step=50, value=300,
        key=f'{KEY}_threshold',
        help="Transactions with amount >= this threshold are settled first."
    )

    # Transaction injection
    injected_df = render_txn_injector(key_prefix=KEY)

    # --- Run ---
    if st.button("Run Full Simulation", key=f'{KEY}_run'):
        with st.spinner("Running 3-day simulation with fixed parameters..."):
            base_txn_df = load_transactions(_get_data_path())
            txn_df = merge_transactions(base_txn_df, injected_df)

            queue = PriorityQueue(priority_threshold=threshold)
            results = run_full_simulation(txn_df, queue, num_days=NUM_DAYS)

            # Store results as list (one entry = all days combined)
            st.session_state[f'{KEY}_results'] = [results]
            st.session_state[f'{KEY}_complete'] = True

            # Store for cross-stage comparison
            if 'stage_results' not in st.session_state:
                st.session_state['stage_results'] = {}
            metrics = summarise_metrics(results, AVG_INTRADAY_LIQUIDITY)
            st.session_state['stage_results']['Periodic Simulator'] = metrics

    # --- Results ---
    if f'{KEY}_results' in st.session_state:
        st.divider()
        complete = st.session_state.get(f'{KEY}_complete', False)
        if complete:
            st.success("Simulation complete!")
        render_dashboard(
            st.session_state[f'{KEY}_results'],
            complete=complete,
            stage_name='Periodic Simulator',
        )

    # --- Reset ---
    st.divider()
    if st.button("Reset Stage", key=f'{KEY}_reset'):
        for k in list(st.session_state.keys()):
            if k.startswith(KEY):
                del st.session_state[k]
        if 'stage_results' in st.session_state:
            st.session_state['stage_results'].pop('Periodic Simulator', None)
        st.rerun()
