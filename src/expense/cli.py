"""Định nghĩa lệnh CLI (Typer). Không viết SQL ở đây — dùng `expense.db`."""

import re
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from typer.core import TyperCommand

from expense import db
from expense.models import Budget, Expense, normalize_category

DEFAULT_DB = Path.home() / ".expense" / "expense.db"

app = typer.Typer(help="Quản lý chi tiêu cá nhân.", no_args_is_help=True)
budget_app = typer.Typer(help="Hạn mức chi mỗi tháng theo danh mục.", no_args_is_help=True)
app.add_typer(budget_app, name="budget")

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


def _validate_category(value: str) -> str:
    normalized = normalize_category(value)
    if not normalized:
        raise typer.BadParameter("Danh mục không được để trống.")
    return normalized


class _AmountCommand(TyperCommand):
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


@app.command(cls=_AmountCommand)
def add(
    amount: Annotated[
        int, typer.Argument(callback=_validate_amount, help="Số tiền (đồng, số nguyên ≥ 1).")
    ],
    category: Annotated[
        str, typer.Argument(callback=_validate_category, help="Danh mục, ví dụ an-uong.")
    ],
    note: Annotated[str, typer.Option("--note", "-n", help="Ghi chú.")] = "",
    spent_on: Annotated[
        datetime | None,
        typer.Option("--date", "-d", formats=["%Y-%m-%d"], help="Ngày chi (mặc định hôm nay)."),
    ] = None,
    force: Annotated[bool, typer.Option("--force", help="Vẫn ghi dù vượt hạn mức.")] = False,
    db_path: DbOption = DEFAULT_DB,
) -> None:
    """Thêm một khoản chi. Bị chặn nếu làm vượt hạn mức tháng, trừ khi có --force."""
    day = spent_on.date() if spent_on else date.today()
    conn = db.connect(db_path)
    over = _over_budget_message(conn, category, day, amount)
    if over and not force:
        typer.echo(f"{over}. Dùng --force để vẫn ghi.", err=True)
        raise typer.Exit(code=1)
    saved = db.add_expense(conn, Expense(amount=amount, category=category, note=note, spent_on=day))
    typer.echo(f"Đã thêm #{saved.id}: {format_vnd(saved.amount)} ({saved.category})")
    if over:
        typer.echo(f"Cảnh báo: {over}.", err=True)


def _over_budget_message(
    conn: sqlite3.Connection, category: str, day: date, amount: int
) -> str | None:
    """Trả về mô tả vượt hạn mức nếu thêm `amount` vào tháng của `day`, ngược lại None."""
    budget = db.get_budget(conn, category)
    if budget is None:
        return None
    spent = db.month_total(conn, category, day.year, day.month)
    if spent + amount <= budget.monthly_limit:
        return None
    return (
        f"Vượt hạn mức {category} tháng {day:%Y-%m}: đã chi {format_vnd(spent)}"
        f" + {format_vnd(amount)} > {format_vnd(budget.monthly_limit)}"
        f" (vượt {format_vnd(spent + amount - budget.monthly_limit)})"
    )


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


@budget_app.command("set", cls=_AmountCommand)
def budget_set(
    category: Annotated[
        str, typer.Argument(callback=_validate_category, help="Danh mục, ví dụ an-uong.")
    ],
    amount: Annotated[
        int, typer.Argument(callback=_validate_amount, help="Hạn mức/tháng (đồng, số nguyên ≥ 1).")
    ],
    db_path: DbOption = DEFAULT_DB,
) -> None:
    """Đặt hoặc cập nhật hạn mức chi mỗi tháng của một danh mục."""
    conn = db.connect(db_path)
    db.set_budget(conn, Budget(category=category, monthly_limit=amount))
    typer.echo(f"Hạn mức {category}: {format_vnd(amount)}/tháng")


@budget_app.command("list")
def budget_list(
    month: Annotated[
        datetime | None,
        typer.Option("--month", "-m", formats=["%Y-%m"], help="Tháng (mặc định tháng này)."),
    ] = None,
    db_path: DbOption = DEFAULT_DB,
) -> None:
    """Liệt kê hạn mức kèm số đã chi và còn lại trong tháng."""
    day = month.date() if month else date.today()
    conn = db.connect(db_path)
    budgets = db.list_budgets(conn)
    if not budgets:
        typer.echo("Chưa đặt hạn mức nào.")
        return
    typer.echo(f"Tháng {day:%Y-%m}")
    for b in budgets:
        spent = db.month_total(conn, b.category, day.year, day.month)
        remaining = b.monthly_limit - spent
        percent = spent * 100 // b.monthly_limit
        line = (
            f"{b.category}  đã chi {format_vnd(spent)} / {format_vnd(b.monthly_limit)}"
            f" ({percent}%)  còn {format_vnd(remaining)}"
        )
        typer.echo(f"{line}  VƯỢT" if remaining < 0 else line)


@budget_app.command("remove")
def budget_remove(
    category: Annotated[str, typer.Argument(callback=_validate_category, help="Danh mục.")],
    db_path: DbOption = DEFAULT_DB,
) -> None:
    """Xóa hạn mức của một danh mục."""
    conn = db.connect(db_path)
    if not db.delete_budget(conn, category):
        typer.echo(f"Chưa đặt hạn mức cho {category}.", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Đã xóa hạn mức {category}.")
