import sqlite3
from datetime import date

import pytest

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


def test_failed_migration_is_rolled_back(tmp_path):
    (tmp_path / "0001_init.sql").write_text("CREATE TABLE a (x INTEGER);")
    (tmp_path / "0002_broken.sql").write_text("CREATE TABLE b (x INTEGER);\nTHIS IS NOT SQL;")
    conn = sqlite3.connect(":memory:")

    with pytest.raises(sqlite3.Error):
        db.migrate(conn, tmp_path)

    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert "a" in tables
    assert "b" not in tables
    versions = [r[0] for r in conn.execute("SELECT version FROM schema_migrations")]
    assert versions == ["0001_init"]
    assert not conn.in_transaction
