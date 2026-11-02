"""Dataclass nghiệp vụ."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class Expense:
    """Một khoản chi. `amount` là số nguyên, đơn vị đồng."""

    amount: int
    category: str
    spent_on: date
    note: str = ""
    id: int | None = None
