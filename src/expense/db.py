"""Truy cập SQLite. Đây là nơi duy nhất trong project được viết SQL."""

import sqlite3
from datetime import date
from pathlib import Path

from expense.models import Budget, Expense, normalize_category

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def connect(path: Path | str) -> sqlite3.Connection:
    """Mở kết nối tới database và áp dụng các migration còn thiếu."""
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    # lower() / COLLATE NOCASE của SQLite chỉ xử lý ASCII ("ĂN" không thành "ăn"),
    # nên so khớp danh mục bằng hàm Python.
    conn.create_function("normalize_category", 1, normalize_category, deterministic=True)
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
        # executescript() tự COMMIT trước khi chạy, nên tự mở transaction trong script
        # để nội dung file và dòng ghi version cùng thành công hoặc cùng bị hủy.
        quoted_version = version.replace("'", "''")
        script = (
            "BEGIN;\n"
            f"{file.read_text(encoding='utf-8')}\n;\n"
            f"INSERT INTO schema_migrations (version) VALUES ('{quoted_version}');\n"
            "COMMIT;"
        )
        try:
            conn.executescript(script)
        except sqlite3.Error:
            if conn.in_transaction:
                conn.rollback()
            raise


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


def set_budget(conn: sqlite3.Connection, budget: Budget) -> None:
    """Tạo hoặc cập nhật hạn mức tháng của một danh mục."""
    with conn:
        conn.execute(
            "INSERT INTO budgets (category, monthly_limit) VALUES (?, ?) "
            "ON CONFLICT (category) DO UPDATE SET monthly_limit = excluded.monthly_limit",
            (budget.category, budget.monthly_limit),
        )


def get_budget(conn: sqlite3.Connection, category: str) -> Budget | None:
    """Trả về hạn mức của danh mục (đã chuẩn hóa), hoặc None nếu chưa đặt."""
    row = conn.execute(
        "SELECT category, monthly_limit FROM budgets WHERE category = ?", (category,)
    ).fetchone()
    return Budget(category=row["category"], monthly_limit=row["monthly_limit"]) if row else None


def list_budgets(conn: sqlite3.Connection) -> list[Budget]:
    """Trả về tất cả hạn mức, sắp theo tên danh mục."""
    rows = conn.execute("SELECT category, monthly_limit FROM budgets ORDER BY category")
    return [Budget(category=row["category"], monthly_limit=row["monthly_limit"]) for row in rows]


def delete_budget(conn: sqlite3.Connection, category: str) -> bool:
    """Xóa hạn mức của danh mục. Trả về False nếu chưa đặt."""
    with conn:
        cur = conn.execute("DELETE FROM budgets WHERE category = ?", (category,))
    return cur.rowcount > 0


def month_total(conn: sqlite3.Connection, category: str, year: int, month: int) -> int:
    """Tổng chi của danh mục (đã chuẩn hóa) trong tháng `year-month`."""
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    row = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM expenses "
        "WHERE normalize_category(category) = ? AND spent_on >= ? AND spent_on < ?",
        (category, start.isoformat(), end.isoformat()),
    ).fetchone()
    return row[0]
