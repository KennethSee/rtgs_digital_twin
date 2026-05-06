"""
Stage 3 — AI-enabled Twin

Same PriorityQueue, but the AI agent auto-updates the threshold per
processing window in real-time. No user input needed — the system
evaluates metrics after each window and adjusts automatically.

Processing windows are 15-minute intervals from 08:00 to 17:00.
"""

import os
import streamlit as st
import pandas as pd

from simulation.queues import PriorityQueue
from simulation.engine import (
    load_transactions, run_window, get_processing_windows,
    DEFAULT_BALANCES, AVG_INTRADAY_LIQUIDITY
)
from simulation.metrics import (
    summarise_metrics, recommend_threshold,
    calc_avg_payment_delay, calc_settlement_rate
)
from components.dashboard import render_dashboard
from components.txn_injector import render_txn_injector, merge_transactions


NUM_DAYS = 3
KEY = 'stg3'


def _get_data_path():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, 'data', 'sample_transactions.csv')


def render():
    st.header("Stage 3: AI-enabled Twin")
    st.markdown(
        "Same priority queue, but now the threshold is **auto-updated per processing window** "
        "by an AI agent. No human input needed — the agent evaluates metrics after each "
        "15-minute window and adjusts the threshold in real-time."
    )

    # Transaction injection
    injected_df = render_txn_injector(key_prefix=KEY)

    # Initial threshold
    initial_threshold = st.slider(
        "Starting threshold ($)",
        min_value=50, max_value=900, step=50, value=300,
        key=f'{KEY}_init_threshold',
        help="Initial threshold before the AI agent starts adjusting."
    )

    if st.button("Run Autonomous Simulation", key=f'{KEY}_run'):
        with st.spinner("Running autonomous window-by-window simulation..."):
            base_txn_df = load_transactions(_get_data_path())
            txn_df = merge_transactions(base_txn_df, injected_df)

            balances = DEFAULT_BALANCES.copy()
            threshold = initial_threshold
            all_results = []
            agent_log = []
            windows = get_processing_windows()

            progress_bar = st.progress(0)
            total_steps = NUM_DAYS * len(windows)
            step = 0

            for day in range(1, NUM_DAYS + 1):
                day_results_parts = []

                for w in windows:
                    # Run this window
                    queue = PriorityQueue(priority_threshold=threshold)
                    w_results, w_balances = run_window(
                        txn_df, queue, day,
                        w['start'], w['end'],
                        balances=balances
                    )

                    if not w_results.empty:
                        day_results_parts.append(w_results)

                    balances = w_balances
                    step += 1
                    progress_bar.progress(step / total_steps)

                    # AI agent evaluates after each window with transactions
                    if not w_results.empty:
                        w_delay = calc_avg_payment_delay(w_results)
                        w_rate = calc_settlement_rate(w_results)
                        old_threshold = threshold
                        threshold, rationale = recommend_threshold(
                            threshold, w_delay, w_rate
                        )

                        if threshold != old_threshold:
                            agent_log.append({
                                'Day': day,
                                'Window': f"{w['start']}-{w['end']}",
                                'Avg Delay': f"{w_delay:.1f} min",
                                'Sett. Rate': f"{w_rate:.1f}%",
                                'Old Threshold': f'${old_threshold}',
                                'New Threshold': f'${threshold}',
                                'Rationale': rationale,
                            })

                # Combine all windows for this day
                if day_results_parts:
                    day_results = pd.concat(day_results_parts, ignore_index=True)
                    all_results.append(day_results)

            progress_bar.empty()

            st.session_state[f'{KEY}_results'] = all_results
            st.session_state[f'{KEY}_agent_log'] = agent_log
            st.session_state[f'{KEY}_complete'] = True

            # Store for cross-stage comparison
            if all_results:
                combined = pd.concat(all_results, ignore_index=True)
                overall_metrics = summarise_metrics(combined, AVG_INTRADAY_LIQUIDITY)
                if 'stage_results' not in st.session_state:
                    st.session_state['stage_results'] = {}
                st.session_state['stage_results']['AI-enabled Twin'] = overall_metrics

    # --- Results ---
    if f'{KEY}_results' in st.session_state:
        st.divider()
        complete = st.session_state.get(f'{KEY}_complete', False)
        if complete:
            st.success("Autonomous simulation complete!")

        render_dashboard(
            st.session_state[f'{KEY}_results'],
            complete=complete,
            stage_name='AI-enabled Twin',
        )

        # Agent decision log
        if st.session_state.get(f'{KEY}_agent_log'):
            st.subheader("AI Agent Decision Log")
            log_df = pd.DataFrame(st.session_state[f'{KEY}_agent_log'])
            st.dataframe(log_df, use_container_width=True, hide_index=True)
        else:
            st.info("The AI agent made no threshold adjustments during this run.")

    # --- Reset ---
    st.divider()
    if st.button("Reset Stage", key=f'{KEY}_reset'):
        for k in list(st.session_state.keys()):
            if k.startswith(KEY):
                del st.session_state[k]
        if 'stage_results' in st.session_state:
            st.session_state['stage_results'].pop('AI-enabled Twin', None)
        st.rerun()
