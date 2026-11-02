# expense-cli

CLI quản lý chi tiêu cá nhân. Python 3.12, Typer, SQLite.

```bash
uv sync
uv run expense add 50000 an-uong --note "Phở"
uv run expense list
```

Đường dẫn database mặc định là `~/.expense/expense.db`, có thể đổi bằng biến môi trường `EXPENSE_DB` hoặc tùy chọn `--db`.
