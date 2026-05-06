"""
Stage 2 — Real-time Twin

Same PriorityQueue as Stage 1, but the user can update the threshold
at each day boundary based on stats shown progressively. After each day
completes, metrics are displayed and the user decides whether to adjust
the threshold before proceeding to the next day.
"""

import os
import streamlit as st
import pandas as pd

from simulation.queues import PriorityQueue
from simulation.engine import (
    load_transactions, run_single_day,
    DEFAULT_BALANCES, AVG_INTRADAY_LIQUIDITY
)
from simulation.metrics import (
    summarise_metrics, recommend_threshold,
    calc_avg_payment_delay, calc_settlement_rate
)
from components.dashboard import render_dashboard
from components.txn_injector import render_txn_injector, merge_transactions


NUM_DAYS = 3
KEY = 'stg2'


def _get_data_path():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, 'data', 'sample_transactions.csv')


def _init_state():
    defaults = {
        f'{KEY}_sim_day': 1,
        f'{KEY}_results_all': [],
        f'{KEY}_balances': DEFAULT_BALANCES.copy(),
        f'{KEY}_threshold': 300,
        f'{KEY}_complete': False,
        f'{KEY}_awaiting_decision': False,
        f'{KEY}_recommendation': None,
        f'{KEY}_decision_log': [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def render():
    st.header("Stage 2: Real-time Twin")
    st.markdown(
        "Same priority queue, but now the threshold can be **updated between days**. "
        "After each day, review the metrics and a rule-based recommendation, then "
        "accept or override the suggested adjustment."
    )

    _init_state()
    base_txn_df = load_transactions(_get_data_path())

    # Transaction injection (shared across the whole stage run)
    injected_df = render_txn_injector(key_prefix=KEY)
    txn_df = merge_transactions(base_txn_df, injected_df)

    current_day = st.session_state[f'{KEY}_sim_day']

    if not st.session_state[f'{KEY}_complete']:
        # --- Phase A: Run the current day ---
        if not st.session_state[f'{KEY}_awaiting_decision']:
            st.subheader(f"Day {current_day} of {NUM_DAYS}")
            st.info(f"Current threshold: **${st.session_state[f'{KEY}_threshold']}**")

            if st.button(f"Run Day {current_day}", key=f'{KEY}_run_{current_day}'):
                with st.spinner(f"Simulating Day {current_day}..."):
                    queue = PriorityQueue(
                        priority_threshold=st.session_state[f'{KEY}_threshold']
                    )
                    results, eod_balances = run_single_day(
                        txn_df, queue, current_day,
                        balances=st.session_state[f'{KEY}_balances']
                    )

                    st.session_state[f'{KEY}_results_all'].append(results)
                    st.session_state[f'{KEY}_balances'] = eod_balances

                    # Generate recommendation
                    avg_delay = calc_avg_payment_delay(results)
                    sett_rate = calc_settlement_rate(results)
                    new_thresh, rationale = recommend_threshold(
                        st.session_state[f'{KEY}_threshold'], avg_delay, sett_rate
                    )
                    st.session_state[f'{KEY}_recommendation'] = {
                        'new_threshold': new_thresh,
                        'rationale': rationale,
                        'avg_delay': avg_delay,
                        'settlement_rate': sett_rate,
                    }

                    if current_day >= NUM_DAYS:
                        st.session_state[f'{KEY}_complete'] = True
                        st.session_state[f'{KEY}_decision_log'].append({
                            'Day': current_day,
                            'Action': 'Final day — no adjustment',
                            'Threshold': st.session_state[f'{KEY}_threshold'],
                            'Rationale': 'Simulation complete',
                        })
                    else:
                        st.session_state[f'{KEY}_awaiting_decision'] = True

                    st.rerun()

        # --- Phase B: Show recommendation and get decision ---
        else:
            st.subheader(f"Day {current_day} Complete — Review & Adjust")
            rec = st.session_state[f'{KEY}_recommendation']

            # Recommendation box
            st.markdown(
                f"""<div style="background-color: #d4edda; padding: 16px; border-radius: 8px;
                border-left: 4px solid #28a745; margin: 12px 0;">
                <strong>Recommendation:</strong> Set threshold to <strong>${rec['new_threshold']}</strong><br>
                <em>{rec['rationale']}</em><br>
                <small>Based on: Avg delay = {rec['avg_delay']:.1f} min, Settlement rate = {rec['settlement_rate']:.1f}%</small>
                </div>""",
                unsafe_allow_html=True
            )

            col1, col2 = st.columns(2)
            with col1:
                if st.button(
                    f"Accept recommendation (${rec['new_threshold']})",
                    key=f'{KEY}_accept_{current_day}'
                ):
                    st.session_state[f'{KEY}_decision_log'].append({
                        'Day': current_day,
                        'Action': 'Accepted',
                        'Threshold': rec['new_threshold'],
                        'Rationale': rec['rationale'],
                    })
                    st.session_state[f'{KEY}_threshold'] = rec['new_threshold']
                    st.session_state[f'{KEY}_awaiting_decision'] = False
                    st.session_state[f'{KEY}_sim_day'] = current_day + 1
                    st.rerun()

            with col2:
                if st.button("Override", key=f'{KEY}_override_{current_day}'):
                    st.session_state[f'{KEY}_show_override'] = True

            if st.session_state.get(f'{KEY}_show_override'):
                override_val = st.number_input(
                    "Enter custom threshold ($)",
                    min_value=50, max_value=900, step=50,
                    value=st.session_state[f'{KEY}_threshold'],
                    key=f'{KEY}_override_input_{current_day}'
                )
                if st.button("Apply Override", key=f'{KEY}_apply_override_{current_day}'):
                    st.session_state[f'{KEY}_decision_log'].append({
                        'Day': current_day,
                        'Action': f'Overridden to ${override_val}',
                        'Threshold': override_val,
                        'Rationale': 'User override',
                    })
                    st.session_state[f'{KEY}_threshold'] = override_val
                    st.session_state[f'{KEY}_awaiting_decision'] = False
                    st.session_state[f'{KEY}_show_override'] = False
                    st.session_state[f'{KEY}_sim_day'] = current_day + 1
                    st.rerun()

    # --- Progressive dashboard (shows all days completed so far) ---
    if st.session_state[f'{KEY}_results_all']:
        st.divider()
        complete = st.session_state[f'{KEY}_complete']
        if complete:
            st.success("All 3 days complete!")

            # Store for cross-stage comparison
            all_results = pd.concat(
                st.session_state[f'{KEY}_results_all'], ignore_index=True
            )
            overall_metrics = summarise_metrics(all_results, AVG_INTRADAY_LIQUIDITY)
            if 'stage_results' not in st.session_state:
                st.session_state['stage_results'] = {}
            st.session_state['stage_results']['Real-time Twin'] = overall_metrics

        render_dashboard(
            st.session_state[f'{KEY}_results_all'],
            complete=complete,
            stage_name='Real-time Twin',
        )

    # Decision audit trail
    if st.session_state[f'{KEY}_decision_log']:
        st.subheader("Decision Audit Trail")
        log_df = pd.DataFrame(st.session_state[f'{KEY}_decision_log'])
        st.dataframe(log_df, use_container_width=True, hide_index=True)

    # --- Reset ---
    st.divider()
    if st.button("Reset Stage", key=f'{KEY}_reset'):
        for k in list(st.session_state.keys()):
            if k.startswith(KEY):
                del st.session_state[k]
        if 'stage_results' in st.session_state:
            st.session_state['stage_results'].pop('Real-time Twin', None)
        st.rerun()
