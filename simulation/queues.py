"""
Custom Queue subclass for the RTGS Digital Twin Simulator.

A single PriorityQueue is used across all three stages. Stages differ only
in the *frequency* at which the threshold parameter is updated:
  - Stage 1 (Periodic Simulator): threshold fixed for the entire run
  - Stage 2 (Real-time Twin): threshold updated by user between days
  - Stage 3 (AI-enabled Twin): threshold auto-updated per processing window

The queue implements balance-aware dequeue criteria: during each batch
dequeue pass, balance is "reserved" as transactions are checked in sorted
order. This makes the sorting order meaningful — higher-priority
transactions claim available liquidity first.
"""

from typing import Tuple, List
from PSSimPy.queues import AbstractQueue
from PSSimPy.transaction import Transaction


def _time_to_minutes(time_str: str) -> int:
    """Convert HH:MM string to minutes since midnight."""
    if not time_str:
        return 0
    parts = time_str.split(':')
    return int(parts[0]) * 60 + int(parts[1])


class PriorityQueue(AbstractQueue):
    """
    Priority queue controlled by a dollar threshold.
    Transactions with amount >= threshold are settled first (highest value first).
    Others are settled in FIFO order.

    Balance-aware dequeue criteria prevent over-commitment within each
    batch dequeue pass.
    """

    _threshold = 300  # Class-level threshold (set before simulation)
    _reserved = {}
    _counter = 0

    def __init__(self, priority_threshold: int = 300):
        PriorityQueue._threshold = priority_threshold
        PriorityQueue._counter = 0
        PriorityQueue._reserved = {}
        super().__init__()

    @classmethod
    def set_threshold(cls, threshold: int):
        """Update the priority threshold between runs."""
        cls._threshold = threshold

    def enqueue(self, transaction: Transaction) -> None:
        PriorityQueue._counter += 1
        transaction._pq_order = PriorityQueue._counter
        super().enqueue(transaction)

    @staticmethod
    def sorting_logic(queue_item: Tuple[Transaction, int]) -> int:
        txn, period = queue_item
        if txn.amount >= PriorityQueue._threshold:
            # Negative amount: higher value = smaller number = higher priority
            # Offset by -100000 to ensure priority items always come before non-priority
            return -100000 - txn.amount
        # Non-priority: FIFO order (positive numbers, after all priority items)
        return getattr(txn, '_pq_order', _time_to_minutes(txn.time))

    @staticmethod
    def dequeue_criteria(queue_item: Tuple[Transaction, int]) -> bool:
        txn, _ = queue_item
        sender = txn.sender_account
        reserved = PriorityQueue._reserved.get(sender.id, 0)
        available = sender.balance - reserved
        if available >= txn.amount:
            PriorityQueue._reserved[sender.id] = reserved + txn.amount
            return True
        return False

    def begin_dequeueing(self) -> List[Transaction]:
        PriorityQueue._reserved = {}
        result = super().begin_dequeueing()
        PriorityQueue._reserved = {}
        return result
