"""Dataclass nghiệp vụ."""

import unicodedata
from dataclasses import dataclass
from datetime import date


def normalize_category(name: str) -> str:
    """Chuẩn hóa tên danh mục để so khớp: NFC, bỏ khoảng trắng đầu/cuối, chữ thường."""
    return unicodedata.normalize("NFC", name).strip().lower()


@dataclass(frozen=True, slots=True)
class Expense:
    """Một khoản chi. `amount` là số nguyên, đơn vị đồng."""

    amount: int
    category: str
    spent_on: date
    note: str = ""
    id: int | None = None


@dataclass(frozen=True, slots=True)
class Budget:
    """Hạn mức chi mỗi tháng của một danh mục (đã chuẩn hóa). Đơn vị đồng."""

    category: str
    monthly_limit: int
