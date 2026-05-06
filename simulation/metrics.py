"""
Metric calculation functions for the RTGS Digital Twin Simulator.
"""

import pandas as pd
from typing import Optional


def _time_to_minutes(time_str: str) -> int:
    """Convert HH:MM string to minutes since midnight."""
    if not time_str or pd.isna(time_str):
        return 0
    parts = str(time_str).split(':')
    return int(parts[0]) * 60 + int(parts[1])


def calc_avg_payment_delay(results_df: pd.DataFrame) -> float:
    """
    Average Payment Delay = sum(settlement_time - submission_time) / N
    Only considers successfully settled transactions.
    """
    settled = results_df[results_df['status'] == 'Success'].copy()
    if settled.empty:
        return 0.0
    return settled['delay_minutes'].mean()


def calc_max_payment_delay(results_df: pd.DataFrame) -> float:
    """Maximum delay across all settled transactions."""
    settled = results_df[results_df['status'] == 'Success']
    if settled.empty:
        return 0.0
    return settled['delay_minutes'].max()


def calc_turnover_ratio(results_df: pd.DataFrame, avg_intraday_liquidity: float) -> float:
    """
    Turnover Ratio = total value settled / average intraday liquidity.
    Higher is better (more value moved per unit of liquidity).
    """
    if avg_intraday_liquidity <= 0:
        return 0.0
    settled = results_df[results_df['status'] == 'Success']
    total_settled = settled['amount'].sum()
    return total_settled / avg_intraday_liquidity


def calc_settlement_rate(results_df: pd.DataFrame) -> float:
    """Percentage of transactions successfully settled (not failed)."""
    if results_df.empty:
        return 0.0
    settled_count = (results_df['status'] == 'Success').sum()
    return (settled_count / len(results_df)) * 100


def calc_daily_metrics(results_df: pd.DataFrame, avg_liquidity: float = 4700.0) -> pd.DataFrame:
    """Returns per-day breakdown of all metrics."""
    days = sorted(results_df['day'].unique())
    rows = []
    for d in days:
        day_df = results_df[results_df['day'] == d]
        rows.append({
            'Day': d,
            'Avg Delay (min)': round(calc_avg_payment_delay(day_df), 1),
            'Max Delay (min)': round(calc_max_payment_delay(day_df), 1),
            'Settlement Rate (%)': round(calc_settlement_rate(day_df), 1),
            'Turnover Ratio': round(calc_turnover_ratio(day_df, avg_liquidity), 2)
        })
    return pd.DataFrame(rows)


def summarise_metrics(results_df: pd.DataFrame, avg_liquidity: float = 4700.0) -> dict:
    """Returns dict with all metrics for display."""
    return {
        'avg_delay': round(calc_avg_payment_delay(results_df), 1),
        'max_delay': round(calc_max_payment_delay(results_df), 1),
        'settlement_rate': round(calc_settlement_rate(results_df), 1),
        'turnover_ratio': round(calc_turnover_ratio(results_df, avg_liquidity), 2)
    }


def recommend_threshold(current_threshold: int, avg_delay: float, settlement_rate: float) -> tuple:
    """
    Rule-based recommendation heuristic for adjusting priority threshold.

    Returns: (new_threshold, rationale_text)
    """
    if avg_delay > 60:
        new_threshold = max(50, current_threshold - 150)
        return new_threshold, "High congestion detected — lowering threshold significantly to prioritize more transactions."
    elif avg_delay > 40:
        new_threshold = max(50, current_threshold - 100)
        return new_threshold, "Moderate delays observed — lowering threshold to improve throughput."
    elif settlement_rate < 85:
        new_threshold = max(50, current_threshold - 150)
        return new_threshold, "Low settlement rate — lowering threshold to settle more transactions."
    elif avg_delay < 25 and settlement_rate > 95:
        new_threshold = min(900, current_threshold + 100)
        return new_threshold, "System performing well — raising threshold to conserve liquidity prioritization."
    else:
        return current_threshold, "No adjustment recommended — current threshold is adequate."
