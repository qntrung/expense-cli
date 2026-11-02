# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# expense-cli

CLI quản lý chi tiêu cá nhân. Python 3.12, Typer, SQLite.

## Lệnh thường dùng
- Cài đặt: `uv sync`
- Chạy test: `uv run pytest -q`
- Chạy một test: `uv run pytest tests/test_<module>.py::test_<name> -q`
- Lint + format: `uv run ruff check . --fix && uv run ruff format .`
- Chạy app: `uv run expense --help`

## Kiến trúc
- `src/expense/cli.py`    – định nghĩa lệnh (Typer), KHÔNG chứa SQL
- `src/expense/db.py`     – truy cập SQLite, nơi duy nhất được viết SQL
- `src/expense/models.py` – dataclass nghiệp vụ
- `migrations/`           – file SQL đánh số 0001_, 0002_, ...

`db.connect()` tự áp dụng migration còn thiếu (theo dõi trong bảng `schema_migrations`). Thư mục `migrations/` được tìm theo đường dẫn tương đối từ `src/expense/db.py`, nên app chạy đúng khi cài editable (`uv sync`). File DB mặc định là `~/.expense/expense.db`, có thể đổi bằng `--db` hoặc biến môi trường `EXPENSE_DB`. Test dùng `:memory:` hoặc `tmp_path`.

## Quy ước
- Type hint đầy đủ; hàm public có docstring
- Tiền lưu dạng số nguyên (đồng). KHÔNG dùng float cho tiền
- Mỗi tính năng mới phải có test trong `tests/`
- Commit theo Conventional Commits (feat:, fix:, chore:, ...)

## Không được làm
- Không sửa migration đã commit, hãy tạo migration mới
- Không commit file `*.db` hoặc `.env`
