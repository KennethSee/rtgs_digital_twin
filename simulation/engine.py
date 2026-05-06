"""
Simulation engine wrapping PSSimPy's BasicSim.

Handles running simulations, parsing output CSVs, and managing state
between runs at different granularities:
  - run_full_simulation: all days at once (Stage 1)
  - run_single_day: one day at a time (Stage 2)
  - run_window: one processing window at a time (Stage 3)
"""

import os
import uuid
import tempfile
import pandas as pd
import numpy as np
from typing import Optional, List
from collections import defaultdict

from PSSimPy.simulator import BasicSim
from PSSimPy.transaction import Transaction
from PSSimPy.credit_facilities import AbstractCreditFacility
from PSSimPy.account import Account


# ---------------------------------------------------------------------------
# No-credit facility: prevents PSSimPy from auto-lending, creating real delays
# ---------------------------------------------------------------------------
class NoCreditFacility(AbstractCreditFacility):
    """Credit facility that never lends — forces transactions to queue."""

    def __init__(self):
        super().__init__()

    def calculate_fee(self, amount: float = 0) -> float:
        return 0.0

    def lend_credit(self, account: Account, amount: float) -> None:
        pass  # Do not lend

    def collect_repayment(self, account: Account) -> None:
        pass  # Nothing to repay


# ---------------------------------------------------------------------------
# Default bank/account data
# ---------------------------------------------------------------------------
BANK_NAMES = ['MAS', 'DBS', 'OCBC', 'UOB', 'SCB', 'HSBC']

DEFAULT_BALANCES = {
    'acc_MAS': 5000,
    'acc_DBS': 1200,
    'acc_OCBC': 900,
    'acc_UOB': 1100,
    'acc_SCB': 700,
    'acc_HSBC': 800,
}

AVG_INTRADAY_LIQUIDITY = sum(DEFAULT_BALANCES.values()) / len(DEFAULT_BALANCES)

# Processing window definitions (15-minute intervals from 08:00 to 17:00)
WINDOW_SIZE_MINUTES = 15
OPEN_TIME = '08:00'
CLOSE_TIME = '17:00'
OPEN_MINUTES = 8 * 60   # 480
CLOSE_MINUTES = 17 * 60  # 1020


def _time_to_minutes(time_str: str) -> int:
    if not time_str or pd.isna(time_str):
        return 0
    parts = str(time_str).split(':')
    return int(parts[0]) * 60 + int(parts[1])


def _minutes_to_time(minutes: int) -> str:
    """Convert minutes since midnight to HH:MM string."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def get_processing_windows() -> List[dict]:
    """
    Return list of processing windows for one day.
    Each window dict: {'start': 'HH:MM', 'end': 'HH:MM', 'start_min': int, 'end_min': int}
    """
    windows = []
    t = OPEN_MINUTES
    while t < CLOSE_MINUTES:
        end = min(t + WINDOW_SIZE_MINUTES, CLOSE_MINUTES)
        windows.append({
            'start': _minutes_to_time(t),
            'end': _minutes_to_time(end),
            'start_min': t,
            'end_min': end,
        })
        t = end
    return windows


def get_banks_df():
    return pd.DataFrame({'name': BANK_NAMES})


def get_accounts_df(balances: Optional[dict] = None):
    if balances is None:
        balances = DEFAULT_BALANCES
    ids = [f'acc_{b}' for b in BANK_NAMES]
    return pd.DataFrame({
        'id': ids,
        'owner': BANK_NAMES,
        'balance': [balances.get(aid, 0) for aid in ids],
        'posted_collateral': [0] * len(BANK_NAMES),
    })


def load_transactions(csv_path: str) -> pd.DataFrame:
    return pd.read_csv(csv_path)


def get_transactions_for_day(all_txns: pd.DataFrame, day: int) -> pd.DataFrame:
    """Filter transactions for a single day and reset day column to 1."""
    day_txns = all_txns[all_txns['day'] == day].copy()
    day_txns['day'] = 1
    return day_txns


def get_transactions_for_window(day_txns: pd.DataFrame, window_start_min: int,
                                 window_end_min: int) -> pd.DataFrame:
    """
    Filter a day's transactions to those submitted within a processing window.
    Assumes day_txns already has day=1.
    """
    minutes = day_txns['time'].apply(_time_to_minutes)
    mask = (minutes >= window_start_min) & (minutes < window_end_min)
    return day_txns[mask].copy()


def _prepare_txn_dict(txn_df: pd.DataFrame) -> dict:
    """Convert transaction DataFrame to dict format for PSSimPy."""
    return {
        'sender_account': txn_df['sender_account'].tolist(),
        'recipient_account': txn_df['recipient_account'].tolist(),
        'amount': txn_df['amount'].tolist(),
        'time': txn_df['time'].tolist(),
        'day': txn_df['day'].tolist(),
    }


def parse_sim_output(sim_name: str, work_dir: str) -> pd.DataFrame:
    """
    Read PSSimPy's processed_transactions CSV and compute delay metrics.

    Returns DataFrame with columns:
        id, sender, recipient, amount, day, submitted_time, settled_time,
        delay_minutes, status
    """
    csv_path = os.path.join(work_dir, f'{sim_name}-processed_transactions.csv')
    if not os.path.exists(csv_path):
        return pd.DataFrame(columns=[
            'id', 'sender', 'recipient', 'amount', 'day',
            'submitted_time', 'settled_time', 'delay_minutes', 'status'
        ])

    df = pd.read_csv(csv_path)

    results = []
    for idx, row in df.iterrows():
        sub_time = str(row.get('submission_time', ''))
        set_time = str(row.get('settlement_time', ''))
        status = str(row.get('status', 'Failed'))

        if status == 'Success' and sub_time and set_time and sub_time != 'nan' and set_time != 'nan':
            delay = _time_to_minutes(set_time) - _time_to_minutes(sub_time)
            if delay < 0:
                delay = 0
        else:
            delay = 0

        results.append({
            'id': idx + 1,
            'sender': row.get('from_account', ''),
            'recipient': row.get('to_account', ''),
            'amount': row.get('amount', 0),
            'day': row.get('submission_day', row.get('day', 1)),
            'submitted_time': sub_time,
            'settled_time': set_time,
            'delay_minutes': delay,
            'status': status,
        })

    return pd.DataFrame(results)


def _cleanup_sim_files(sim_name: str, work_dir: str):
    """Remove PSSimPy-generated CSV files."""
    suffixes = [
        'processed_transactions', 'transaction_fees',
        'queue_stats', 'account_balance', 'credit_facility'
    ]
    for suffix in suffixes:
        path = os.path.join(work_dir, f'{sim_name}-{suffix}.csv')
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass


def _read_end_of_day_balances(sim_name: str, work_dir: str) -> dict:
    """Read account balances from the last time entry in account_balance CSV."""
    csv_path = os.path.join(work_dir, f'{sim_name}-account_balance.csv')
    if not os.path.exists(csv_path):
        return DEFAULT_BALANCES.copy()

    df = pd.read_csv(csv_path)
    if df.empty:
        return DEFAULT_BALANCES.copy()

    last_day = df['day'].max()
    last_entries = df[df['day'] == last_day]
    last_time = last_entries['time'].iloc[-1]
    final = last_entries[last_entries['time'] == last_time]

    balances = {}
    for _, row in final.iterrows():
        balances[row['account']] = row['balance']

    return balances


def _run_sim(txn_df: pd.DataFrame, queue_instance, balances: Optional[dict],
             open_time: str = OPEN_TIME, close_time: str = CLOSE_TIME,
             num_days: int = 1) -> tuple:
    """
    Core simulation runner. All public functions delegate here.

    Returns: (results_df, end_balances)
    """
    Transaction.clear_instances()

    if txn_df.empty:
        return pd.DataFrame(columns=[
            'id', 'sender', 'recipient', 'amount', 'day',
            'submitted_time', 'settled_time', 'delay_minutes', 'status'
        ]), (balances or DEFAULT_BALANCES.copy())

    work_dir = tempfile.mkdtemp(prefix='rtgs_sim_')
    sim_name = f'rtgs_{uuid.uuid4().hex[:8]}'

    original_dir = os.getcwd()
    os.chdir(work_dir)

    try:
        banks_df = get_banks_df()
        accounts_df = get_accounts_df(balances)
        txn_dict = _prepare_txn_dict(txn_df)

        sim = BasicSim(
            name=sim_name,
            banks=banks_df,
            accounts=accounts_df,
            transactions=txn_dict,
            queue=queue_instance,
            open_time=open_time,
            close_time=close_time,
            processing_window=WINDOW_SIZE_MINUTES,
            num_days=num_days,
            credit_facility=NoCreditFacility(),
            eod_clear_queue=False,
            eod_force_settlement=True,
        )
        sim.run()

        results = parse_sim_output(sim_name, work_dir)
        eod_balances = _read_end_of_day_balances(sim_name, work_dir)
        _cleanup_sim_files(sim_name, work_dir)

    finally:
        os.chdir(original_dir)

    return results, eod_balances


def run_full_simulation(txn_df: pd.DataFrame, queue_instance, num_days: int = 3,
                        balances: Optional[dict] = None) -> pd.DataFrame:
    """
    Run a complete multi-day simulation (Stage 1).

    Returns: Results DataFrame with delay metrics.
    """
    results, _ = _run_sim(txn_df, queue_instance, balances, num_days=num_days)
    return results


def run_single_day(txn_df: pd.DataFrame, queue_instance, day: int,
                   balances: Optional[dict] = None) -> tuple:
    """
    Run a single-day simulation (Stage 2).

    Returns: (results_df, end_of_day_balances)
    """
    day_txns = get_transactions_for_day(txn_df, day)
    results, eod_balances = _run_sim(day_txns, queue_instance, balances)
    # Fix the day column to reflect actual day number
    if not results.empty:
        results['day'] = day
    return results, eod_balances


def run_window(txn_df: pd.DataFrame, queue_instance, day: int,
               window_start: str, window_end: str,
               balances: Optional[dict] = None) -> tuple:
    """
    Run a single processing-window simulation (Stage 3).

    Args:
        txn_df: Full transaction DataFrame (all days)
        queue_instance: PriorityQueue instance
        day: Day number
        window_start: Start time 'HH:MM'
        window_end: End time 'HH:MM'
        balances: Starting balances

    Returns: (results_df, end_of_window_balances)
    """
    day_txns = get_transactions_for_day(txn_df, day)
    ws_min = _time_to_minutes(window_start)
    we_min = _time_to_minutes(window_end)
    window_txns = get_transactions_for_window(day_txns, ws_min, we_min)

    results, eod_balances = _run_sim(
        window_txns, queue_instance, balances,
        open_time=window_start, close_time=window_end
    )
    if not results.empty:
        results['day'] = day
    return results, eod_balances
