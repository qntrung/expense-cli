# expense-cli

CLI quản lý chi tiêu cá nhân. Python 3.12, Typer, SQLite.

```bash
uv sync
uv run expense add 50000 an-uong --note "Phở"
uv run expense list
```

## Hạn mức theo tháng

```bash
uv run expense budget set an-uong 2000000   # đặt / cập nhật hạn mức mỗi tháng
uv run expense budget list --month 2026-11  # đã chi, còn lại, đánh dấu VƯỢT
uv run expense budget remove an-uong
```

Nếu khoản `add` làm tổng chi trong tháng (theo ngày `--date`) vượt hạn mức của danh mục, lệnh bị chặn với exit code 1 và không ghi gì. Thêm `--force` để vẫn ghi (kèm cảnh báo). Tên danh mục được chuẩn hóa: bỏ khoảng trắng đầu/cuối và chuyển chữ thường, nên `An-Uong` và `an-uong` là một.

Đường dẫn database mặc định là `~/.expense/expense.db`, có thể đổi bằng biến môi trường `EXPENSE_DB` hoặc tùy chọn `--db`.
