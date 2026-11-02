"""Định nghĩa lệnh CLI (Typer). Không viết SQL ở đây — dùng `expense.db`."""

import re
from datetime import date, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from typer.core import TyperCommand

from expense import db
from expense.models import Expense

DEFAULT_DB = Path.home() / ".expense" / "expense.db"

app = typer.Typer(help="Quản lý chi tiêu cá nhân.", no_args_is_help=True)

DbOption = Annotated[Path, typer.Option("--db", envvar="EXPENSE_DB", help="Đường dẫn file SQLite.")]


AMOUNT_ERROR = "Số tiền phải là số nguyên ≥ 1"
_NEGATIVE_NUMBER = re.compile(r"-\d+")


def format_vnd(amount: int) -> str:
    """Định dạng số đồng, ví dụ 50000 -> '50.000 ₫'."""
    return f"{amount:,}".replace(",", ".") + " ₫"


def _validate_amount(value: int) -> int:
    if value < 1:
        raise typer.BadParameter(f"{AMOUNT_ERROR} (nhận được {value}).")
    return value


class _AddCommand(TyperCommand):
    """Báo lỗi số tiền âm rõ ràng thay vì để parser hiểu `-5000` là option `-5`."""

    def parse_args(self, ctx: Any, args: list[str]) -> list[str]:  # noqa: ANN401
        # Tên các option nhận giá trị (--note, -n, --date, ...): token ngay sau chúng là
        # giá trị option, ví dụ `--note -5`, không phải số tiền.
        value_options = {
            name
            for param in self.params
            if param.param_type_name == "option" and not getattr(param, "is_flag", False)
            for name in param.opts
        }
        skip_next = False
        for arg in args:
            if skip_next:
                skip_next = False
                continue
            if arg == "--":
                break
            if arg in value_options:
                skip_next = True
            elif _NEGATIVE_NUMBER.fullmatch(arg):
                raise typer.BadParameter(
                    f"{AMOUNT_ERROR} (nhận được {arg}).", ctx=ctx, param_hint="'AMOUNT'"
                )
        return super().parse_args(ctx, args)


@app.command(cls=_AddCommand)
def add(
    amount: Annotated[
        int, typer.Argument(callback=_validate_amount, help="Số tiền (đồng, số nguyên ≥ 1).")
    ],
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
