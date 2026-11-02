"""Truy cập SQLite. Đây là nơi duy nhất trong project được viết SQL."""

import sqlite3
from datetime import date
from pathlib import Path

from expense.models import Expense

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def connect(path: Path | str) -> sqlite3.Connection:
    """Mở kết nối tới database và áp dụng các migration còn thiếu."""
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    migrate(conn)
    return conn


def migrate(conn: sqlite3.Connection, migrations_dir: Path = MIGRATIONS_DIR) -> None:
    """Chạy theo thứ tự các file `NNNN_*.sql` chưa được áp dụng."""
    conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY)")
    applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
    for file in sorted(migrations_dir.glob("[0-9][0-9][0-9][0-9]_*.sql")):
        version = file.stem
        if version in applied:
            continue
        with conn:
            conn.executescript(file.read_text(encoding="utf-8"))
            conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))


def add_expense(conn: sqlite3.Connection, expense: Expense) -> Expense:
    """Lưu một khoản chi và trả về bản ghi kèm `id`."""
    with conn:
        cur = conn.execute(
            "INSERT INTO expenses (amount, category, note, spent_on) VALUES (?, ?, ?, ?)",
            (expense.amount, expense.category, expense.note, expense.spent_on.isoformat()),
        )
    return Expense(
        id=cur.lastrowid,
        amount=expense.amount,
        category=expense.category,
        note=expense.note,
        spent_on=expense.spent_on,
    )


def list_expenses(conn: sqlite3.Connection) -> list[Expense]:
    """Trả về tất cả khoản chi, mới nhất trước."""
    rows = conn.execute(
        "SELECT id, amount, category, note, spent_on FROM expenses ORDER BY spent_on DESC, id DESC"
    )
    return [
        Expense(
            id=row["id"],
            amount=row["amount"],
            category=row["category"],
            note=row["note"],
            spent_on=date.fromisoformat(row["spent_on"]),
        )
        for row in rows
    ]


def delete_expense(conn: sqlite3.Connection, expense_id: int) -> bool:
    """Xóa khoản chi theo `id`. Trả về False nếu không tồn tại."""
    with conn:
        cur = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    return cur.rowcount > 0
