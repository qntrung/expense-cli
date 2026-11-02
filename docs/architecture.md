# Kiến trúc expense-cli

## Module trong `src/expense/`

| Module | Trách nhiệm |
|---|---|
| `cli.py` | Định nghĩa lệnh Typer (`add`, `list`, `delete`, `budget set/list/remove`), kiểm tra hạn mức trước khi `add`, đọc và kiểm tra tham số, định dạng output (`format_vnd`). Không chứa SQL. |
| `db.py` | Nơi duy nhất viết SQL: mở kết nối (`connect`), chạy migration (`migrate`), `add_expense`, `list_expenses`, `delete_expense`, `set_budget`, `get_budget`, `list_budgets`, `delete_budget`, `month_total`. Đăng ký hàm SQL `normalize_category` trên mỗi kết nối. |
| `models.py` | Dataclass `Expense`, `Budget` (frozen) dùng để truyền dữ liệu giữa `cli` và `db`; hàm `normalize_category`. |

## Luồng dữ liệu của lệnh `add`

```
expense add 45000 an-uong --note "Phở"
  │
  ├─ cli.add()          Typer kiểm tra amount là int ≥ 1, --date theo dạng YYYY-MM-DD,
  │                     chuẩn hóa category (NFC, strip, chữ thường, không rỗng)
  │                     DB lấy từ --db › EXPENSE_DB › ~/.expense/expense.db
  ├─ db.connect(path)   tạo thư mục nếu cần, mở SQLite, chạy migrate()
  ├─ kiểm tra hạn mức   db.get_budget() + db.month_total() theo tháng của spent_on;
  │                     vượt mà không có --force → stderr, exit 1, không INSERT
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

## Schema bảng `budgets` (`migrations/0002_budgets.sql`)

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `category` | TEXT PK | Đã chuẩn hóa bằng `normalize_category` |
| `monthly_limit` | INTEGER NOT NULL | Đơn vị đồng, `CHECK (monthly_limit > 0)`. Áp dụng cho mọi tháng |

`expenses.category` cũ có thể chưa chuẩn hóa, nên `month_total` so khớp bằng `normalize_category(category) = ?`. Không dùng `lower()` / `COLLATE NOCASE` vì SQLite chỉ xử lý chữ ASCII.

## Migration

- Mỗi file trong `migrations/` có tên dạng `NNNN_ten.sql`. Các file được chạy theo thứ tự tên.
- `db.connect()` gọi `migrate()` ở mỗi lần mở kết nối. Bảng `schema_migrations(version)` lưu tên các file đã chạy, ví dụ `0001_init`.
- Nội dung file và dòng ghi version được bọc trong `BEGIN; … COMMIT;` rồi chạy bằng `executescript()`. Nếu lỗi, toàn bộ bị rollback và lần sau file được chạy lại.
- Không sửa migration đã commit. Muốn đổi schema thì thêm file mới, ví dụ `0002_...sql`.
- `migrations/` được tìm theo đường dẫn tương đối từ `db.py`, nên chỉ chạy đúng khi cài editable (`uv sync`).
