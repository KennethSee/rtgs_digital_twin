"""
Publication-quality exportable charts for the RTGS Digital Twin Simulator.

Generates matplotlib figures at 300 DPI suitable for academic papers.
Two chart types:
  1. Daily metrics progression — how metrics evolve day-by-day
  2. Transaction timeline — submission vs settlement with delay visible
"""

import io
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for Streamlit
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from typing import Optional

from simulation.metrics import (
    calc_avg_payment_delay, calc_max_payment_delay,
    calc_settlement_rate, calc_turnover_ratio
)
from simulation.engine import AVG_INTRADAY_LIQUIDITY


# --- Consistent academic styling ---
STAGE_COLOURS = {
    'Periodic Simulator': '#636363',
    'Real-time Twin': '#2171b5',
    'AI-enabled Twin': '#6a51a3',
}

STAGE_MARKERS = {
    'Periodic Simulator': 's',
    'Real-time Twin': 'o',
    'AI-enabled Twin': '^',
}

STAGE_LINESTYLES = {
    'Periodic Simulator': '--',
    'Real-time Twin': '-',
    'AI-enabled Twin': '-.',
}


def _apply_paper_style():
    """Apply clean, publication-ready matplotlib style."""
    plt.rcParams.update({
        'font.family': 'serif',
        'font.size': 10,
        'axes.labelsize': 11,
        'axes.titlesize': 12,
        'xtick.labelsize': 9,
        'ytick.labelsize': 9,
        'legend.fontsize': 9,
        'figure.dpi': 300,
        'savefig.dpi': 300,
        'savefig.bbox': 'tight',
        'savefig.pad_inches': 0.1,
        'axes.spines.top': False,
        'axes.spines.right': False,
        'axes.grid': True,
        'grid.alpha': 0.3,
        'grid.linestyle': ':',
    })


def _fig_to_png_bytes(fig) -> bytes:
    """Convert a matplotlib figure to PNG bytes at 300 DPI."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    buf.seek(0)
    plt.close(fig)
    return buf.getvalue()


def _time_to_minutes(time_str: str) -> float:
    """Convert HH:MM to minutes since midnight."""
    if not time_str or str(time_str) == 'nan':
        return 0
    parts = str(time_str).split(':')
    return int(parts[0]) * 60 + int(parts[1])


# =========================================================================
# Chart 1: Daily Metrics Progression
# =========================================================================

def generate_daily_metrics_chart(
    stage_results: dict,
    avg_liquidity: float = AVG_INTRADAY_LIQUIDITY,
) -> bytes:
    """
    Generate a 2x2 panel chart showing day-by-day metric progression
    across all completed stages.

    Args:
        stage_results: Dict mapping stage name -> list of DataFrames
                       (one per day). Each DataFrame has the standard
                       results columns.
        avg_liquidity: For turnover ratio calculation.

    Returns:
        PNG bytes at 300 DPI.
    """
    _apply_paper_style()

    fig, axes = plt.subplots(2, 2, figsize=(7.5, 5.5))
    fig.suptitle('Daily Metrics Progression by Stage', fontsize=13, fontweight='bold', y=1.02)

    metric_fns = [
        ('Avg Payment Delay (min)', calc_avg_payment_delay),
        ('Max Payment Delay (min)', calc_max_payment_delay),
        ('Settlement Rate (%)', calc_settlement_rate),
        ('Turnover Ratio', lambda df: calc_turnover_ratio(df, avg_liquidity)),
    ]

    for ax, (title, fn) in zip(axes.flat, metric_fns):
        for stage_name, day_dfs in stage_results.items():
            if not day_dfs:
                continue
            days = list(range(1, len(day_dfs) + 1))
            values = [fn(df) for df in day_dfs]

            colour = STAGE_COLOURS.get(stage_name, '#333')
            marker = STAGE_MARKERS.get(stage_name, 'o')
            ls = STAGE_LINESTYLES.get(stage_name, '-')

            ax.plot(days, values, color=colour, marker=marker, markersize=6,
                    linestyle=ls, linewidth=1.5, label=stage_name)

        ax.set_title(title, fontsize=10)
        ax.set_xlabel('Day')
        ax.set_xticks(range(1, max(len(v) for v in stage_results.values()) + 1))
        # Collect max value across all stages for this metric to set y range
        all_vals = []
        for day_dfs in stage_results.values():
            if day_dfs:
                all_vals.extend([fn(df) for df in day_dfs])
        y_max = max(all_vals) * 1.15 if all_vals and max(all_vals) > 0 else 1
        ax.set_ylim(0, y_max)

    # Single shared legend below the figure
    handles, labels = axes[0, 0].get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels, loc='lower center', ncol=len(labels),
                   bbox_to_anchor=(0.5, -0.06), frameon=False)

    fig.tight_layout()
    return _fig_to_png_bytes(fig)


# =========================================================================
# Chart 2: Transaction Timeline
# =========================================================================

def generate_transaction_timeline(
    results_df: pd.DataFrame,
    stage_name: str = '',
) -> bytes:
    """
    Generate a transaction timeline chart showing submission and settlement
    times, with delay visible as horizontal distance between the two points.

    Each transaction is a horizontal line from submission to settlement,
    colour-coded by delay severity. Failed transactions shown as red markers.

    Args:
        results_df: Standard results DataFrame with submitted_time,
                    settled_time, delay_minutes, status, day columns.
        stage_name: Label for the chart title.

    Returns:
        PNG bytes at 300 DPI.
    """
    _apply_paper_style()

    if results_df.empty:
        fig, ax = plt.subplots(figsize=(7.5, 3))
        ax.text(0.5, 0.5, 'No transactions to display', ha='center', va='center',
                transform=ax.transAxes, fontsize=12, color='#999')
        return _fig_to_png_bytes(fig)

    df = results_df.copy()
    df['sub_min'] = df['submitted_time'].apply(_time_to_minutes)
    df['set_min'] = df['settled_time'].apply(_time_to_minutes)

    # Sort by day then submission time for nice vertical layout
    df = df.sort_values(['day', 'sub_min']).reset_index(drop=True)

    days = sorted(df['day'].unique())
    n_days = len(days)

    fig_height = max(3.5, len(df) * 0.18 + 1.5)
    fig, axes = plt.subplots(1, n_days, figsize=(3.2 * n_days, fig_height),
                             sharey=False, squeeze=False)

    title = 'Transaction Timeline'
    if stage_name:
        title += f' — {stage_name}'
    fig.suptitle(title, fontsize=13, fontweight='bold', y=1.02)

    for col_idx, day in enumerate(days):
        ax = axes[0, col_idx]
        day_df = df[df['day'] == day].reset_index(drop=True)

        for i, row in day_df.iterrows():
            y = len(day_df) - i  # Top-to-bottom ordering

            if row['status'] == 'Failed':
                ax.plot(row['sub_min'], y, 'x', color='#d32f2f', markersize=7,
                        markeredgewidth=1.5, zorder=5)
                continue

            delay = row['delay_minutes']
            if delay > 60:
                colour = '#d32f2f'   # Red
                alpha = 0.9
            elif delay > 30:
                colour = '#f57c00'   # Amber
                alpha = 0.85
            elif delay > 15:
                colour = '#1976d2'   # Blue
                alpha = 0.7
            else:
                colour = '#388e3c'   # Green
                alpha = 0.7

            # Horizontal line from submission to settlement
            ax.plot([row['sub_min'], row['set_min']], [y, y],
                    color=colour, linewidth=2, alpha=alpha, solid_capstyle='round')
            # Submission marker (circle)
            ax.plot(row['sub_min'], y, 'o', color=colour, markersize=4, alpha=alpha)
            # Settlement marker (diamond)
            ax.plot(row['set_min'], y, 'D', color=colour, markersize=3.5, alpha=alpha)

            # Transaction label
            sender = str(row['sender']).replace('acc_', '')
            recipient = str(row['recipient']).replace('acc_', '')
            label = f"{sender}→{recipient} ${int(row['amount'])}"
            ax.text(row['sub_min'] - 2, y, label, ha='right', va='center',
                    fontsize=6.5, color='#444')

        ax.set_title(f'Day {day}', fontsize=10)
        ax.set_xlabel('Time (minutes since midnight)')

        # X-axis: show hours
        hour_ticks = list(range(480, 1080, 60))  # 08:00 to 17:00
        hour_labels = [f'{t // 60:02d}:00' for t in hour_ticks]
        ax.set_xticks(hour_ticks)
        ax.set_xticklabels(hour_labels, rotation=45, fontsize=7)
        ax.set_xlim(450, 1050)

        ax.set_yticks([])
        ax.set_ylabel('')

    # Legend
    legend_elements = [
        mpatches.Patch(color='#388e3c', alpha=0.7, label='Delay ≤ 15 min'),
        mpatches.Patch(color='#1976d2', alpha=0.7, label='Delay 15–30 min'),
        mpatches.Patch(color='#f57c00', alpha=0.85, label='Delay 30–60 min'),
        mpatches.Patch(color='#d32f2f', alpha=0.9, label='Delay > 60 min'),
        plt.Line2D([0], [0], marker='x', color='#d32f2f', linestyle='None',
                   markersize=7, markeredgewidth=1.5, label='Failed'),
    ]
    fig.legend(handles=legend_elements, loc='lower center', ncol=5,
               bbox_to_anchor=(0.5, -0.08), frameon=False, fontsize=8)

    fig.tight_layout()
    return _fig_to_png_bytes(fig)


# =========================================================================
# Chart 3: Cross-stage comparison (bonus — useful for papers)
# =========================================================================

def generate_cross_stage_chart(
    stage_metrics: dict,
) -> bytes:
    """
    Generate a grouped bar chart comparing final metrics across stages.

    Args:
        stage_metrics: Dict mapping stage name -> metrics dict
                       (with keys avg_delay, settlement_rate, turnover_ratio).

    Returns:
        PNG bytes at 300 DPI.
    """
    _apply_paper_style()

    stage_order = ['Periodic Simulator', 'Real-time Twin', 'AI-enabled Twin']
    stages = [s for s in stage_order if s in stage_metrics]
    if not stages:
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.text(0.5, 0.5, 'No stage results available', ha='center', va='center',
                transform=ax.transAxes)
        return _fig_to_png_bytes(fig)

    metrics_to_plot = [
        ('Avg Delay\n(min)', 'avg_delay', False),
        ('Max Delay\n(min)', 'max_delay', False),
        ('Settlement\nRate (%)', 'settlement_rate', True),
        ('Turnover\nRatio', 'turnover_ratio', True),
    ]

    fig, axes = plt.subplots(1, len(metrics_to_plot), figsize=(9, 4))
    fig.suptitle('Cross-Stage Performance Comparison', fontsize=13,
                 fontweight='bold', y=1.05)

    x = np.arange(len(stages))
    colours = [STAGE_COLOURS.get(s, '#333') for s in stages]

    for ax, (label, key, higher_better) in zip(axes, metrics_to_plot):
        values = [stage_metrics[s].get(key, 0) for s in stages]
        bars = ax.bar(x, values, color=colours, width=0.6, edgecolor='white',
                      linewidth=0.5)

        # Value labels on bars
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                    f'{val:.1f}', ha='center', va='bottom', fontsize=8,
                    fontweight='bold')

        ax.set_ylabel(label, fontsize=9)
        ax.set_xticks(x)
        ax.set_xticklabels([s.replace(' ', '\n') for s in stages], fontsize=7.5)
        ax.set_ylim(bottom=0, top=max(values) * 1.25 if max(values) > 0 else 1)

    fig.tight_layout()
    return _fig_to_png_bytes(fig)
