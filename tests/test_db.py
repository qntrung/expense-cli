from datetime import date

from expense import db
from expense.models import Expense


def test_migrate_is_idempotent():
    conn = db.connect(":memory:")
    db.migrate(conn)
    versions = [r[0] for r in conn.execute("SELECT version FROM schema_migrations")]
    assert versions == ["0001_init"]


def test_add_and_list_expenses():
    conn = db.connect(":memory:")
    db.add_expense(conn, Expense(amount=30000, category="cafe", spent_on=date(2026, 1, 1)))
    saved = db.add_expense(
        conn, Expense(amount=50000, category="an-uong", note="Phở", spent_on=date(2026, 1, 2))
    )

    assert saved.id is not None
    expenses = db.list_expenses(conn)
    assert [e.amount for e in expenses] == [50000, 30000]
    assert expenses[0].note == "Phở"
    assert isinstance(expenses[0].amount, int)


def test_delete_expense():
    conn = db.connect(":memory:")
    saved = db.add_expense(conn, Expense(amount=10000, category="x", spent_on=date(2026, 1, 1)))
    assert saved.id is not None

    assert db.delete_expense(conn, saved.id) is True
    assert db.list_expenses(conn) == []
    assert db.delete_expense(conn, saved.id) is False
