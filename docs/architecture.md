# Kiến trúc expense-cli

## Module trong `src/expense/`

| Module | Trách nhiệm |
|---|---|
| `cli.py` | Định nghĩa lệnh Typer (`add`, `list`, `delete`), đọc và kiểm tra tham số, định dạng output (`format_vnd`). Không chứa SQL. |
| `db.py` | Nơi duy nhất viết SQL: mở kết nối (`connect`), chạy migration (`migrate`), `add_expense`, `list_expenses`, `delete_expense`. |
| `models.py` | Dataclass `Expense` (frozen) dùng để truyền dữ liệu giữa `cli` và `db`. |

## Luồng dữ liệu của lệnh `add`

```
expense add 45000 an-uong --note "Phở"
  │
  ├─ cli.add()          Typer kiểm tra amount là int ≥ 1, --date theo dạng YYYY-MM-DD
  │                     DB lấy từ --db › EXPENSE_DB › ~/.expense/expense.db
  ├─ db.connect(path)   tạo thư mục nếu cần, mở SQLite, chạy migrate()
  ├─ Expense(...)       amount, category, note, spent_on (mặc định hôm nay)
  ├─ db.add_expense()   INSERT có tham số (?) trong transaction, trả về Expense kèm id
  └─ cli in ra          "Đã thêm #1: 45.000 ₫ (an-uong)"
```

## Schema bảng `expenses` (`migrations/0001_init.sql`)

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | |
| `amount` | INTEGER NOT NULL | Đơn vị đồng, `CHECK (amount > 0)`. Không dùng float. |
| `category` | TEXT NOT NULL | |
| `note` | TEXT NOT NULL | Mặc định `''` |
| `spent_on` | TEXT NOT NULL | Ngày dạng ISO `YYYY-MM-DD` |

## Migration

- Mỗi file trong `migrations/` có tên dạng `NNNN_ten.sql`. Các file được chạy theo thứ tự tên.
- `db.connect()` gọi `migrate()` ở mỗi lần mở kết nối. Bảng `schema_migrations(version)` lưu tên các file đã chạy, ví dụ `0001_init`.
- File mới được chạy bằng `executescript()`, xong mới ghi version. Lệnh này tự COMMIT nên file không chạy trong một transaction: lỗi giữa chừng có thể để schema dở dang.
- Không sửa migration đã commit. Muốn đổi schema thì thêm file mới, ví dụ `0002_...sql`.
- `migrations/` được tìm theo đường dẫn tương đối từ `db.py`, nên chỉ chạy đúng khi cài editable (`uv sync`).
