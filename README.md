# RTGS Digital Twin Simulator

A Streamlit application that simulates a Real-Time Gross Settlement (RTGS) system and demonstrates how increasing digital twin maturity improves settlement performance. Built on [PSSimPy](https://github.com/KennethSee/PSSimPy), an agent-based payment system simulator.

## What it does

The simulator runs the same set of interbank transactions through three stages of digital twin maturity, all using the same priority queue mechanism. The stages differ only in how frequently the queue's priority threshold is updated:

1. **Periodic Simulator** — threshold is fixed before the run and never updated. All days execute before results are shown.
2. **Real-time Twin** — threshold can be updated by the user between simulated days, informed by a rule-based recommendation engine and progressive metrics.
3. **AI-enabled Twin** — threshold is auto-adjusted per 15-minute processing window by an AI agent, with no human input required.

Each stage produces the same set of visualisations (metric cards, colour-coded transaction tables, daily breakdowns) and exportable publication-quality charts (300 DPI PNG) for cross-stage comparison.

## Quick start

```bash
# Clone and install
git clone <repo-url>
pip install -r requirements.txt

# Run
streamlit run app.py
```

Requires Python 3.8+.

## Project structure

```
rtgs_digital_twin/
├── app.py                          # Streamlit entry point (3-tab layout)
├── data/
│   └── sample_transactions.csv     # 45 transactions across 3 days, 6 banks
├── simulation/
│   ├── queues.py                   # PriorityQueue with balance-aware dequeue
│   ├── engine.py                   # PSSimPy wrapper (full, day, window runs)
│   └── metrics.py                  # Delay, settlement rate, turnover ratio
├── stages/
│   ├── stage1_periodic.py          # Fixed-parameter batch simulation
│   ├── stage2_realtime.py          # Day-by-day with user adjustment
│   └── stage3_ai_enabled.py        # Window-by-window with AI adjustment
├── components/
│   ├── dashboard.py                # Shared visualisation dashboard
│   ├── metrics_cards.py            # Metric card row
│   ├── results_table.py            # Colour-coded transaction table
│   ├── comparison_chart.py         # Cross-stage Plotly bar charts
│   ├── export_charts.py            # Publication-quality matplotlib exports
│   └── txn_injector.py             # Manual transaction injection UI
└── requirements.txt
```

## License

See [LICENSE](rtgs_digital_twin/LICENSE).
