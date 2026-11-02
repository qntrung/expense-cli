"""Định nghĩa lệnh CLI (Typer). Không viết SQL ở đây — dùng `expense.db`."""

from datetime import date, datetime
from pathlib import Path
from typing import Annotated

import typer

from expense import db
from expense.models import Expense

DEFAULT_DB = Path.home() / ".expense" / "expense.db"

app = typer.Typer(help="Quản lý chi tiêu cá nhân.", no_args_is_help=True)

DbOption = Annotated[Path, typer.Option("--db", envvar="EXPENSE_DB", help="Đường dẫn file SQLite.")]


def format_vnd(amount: int) -> str:
    """Định dạng số đồng, ví dụ 50000 -> '50.000 ₫'."""
    return f"{amount:,}".replace(",", ".") + " ₫"


@app.command()
def add(
    amount: Annotated[int, typer.Argument(min=1, help="Số tiền (đồng, số nguyên).")],
    category: Annotated[str, typer.Argument(help="Danh mục, ví dụ an-uong.")],
    note: Annotated[str, typer.Option("--note", "-n", help="Ghi chú.")] = "",
    spent_on: Annotated[
        datetime | None,
        typer.Option("--date", "-d", formats=["%Y-%m-%d"], help="Ngày chi (mặc định hôm nay)."),
    ] = None,
    db_path: DbOption = DEFAULT_DB,
) -> None:
    """Thêm một khoản chi."""
    conn = db.connect(db_path)
    saved = db.add_expense(
        conn,
        Expense(
            amount=amount,
            category=category,
            note=note,
            spent_on=spent_on.date() if spent_on else date.today(),
        ),
    )
    typer.echo(f"Đã thêm #{saved.id}: {format_vnd(saved.amount)} ({saved.category})")


@app.command("list")
def list_cmd(db_path: DbOption = DEFAULT_DB) -> None:
    """Liệt kê các khoản chi."""
    conn = db.connect(db_path)
    expenses = db.list_expenses(conn)
    if not expenses:
        typer.echo("Chưa có khoản chi nào.")
        return
    for e in expenses:
        line = f"#{e.id}  {e.spent_on.isoformat()}  {format_vnd(e.amount):>14}  {e.category}"
        typer.echo(f"{line}  {e.note}".rstrip())
    typer.echo(f"Tổng: {format_vnd(sum(e.amount for e in expenses))}")


@app.command()
def delete(
    expense_id: Annotated[
        int, typer.Argument(metavar="ID", help="ID khoản chi (xem bằng `list`).")
    ],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Bỏ qua bước xác nhận.")] = False,
    db_path: DbOption = DEFAULT_DB,
) -> None:
    """Xóa một khoản chi."""
    if not yes:
        typer.confirm(f"Xóa khoản chi #{expense_id}?", abort=True)
    conn = db.connect(db_path)
    if not db.delete_expense(conn, expense_id):
        typer.echo(f"Không tìm thấy khoản chi #{expense_id}.", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Đã xóa #{expense_id}.")
