import sqlite3
from datetime import date

import pytest

from expense import db
from expense.models import Budget, Expense


def test_migrate_is_idempotent():
    conn = db.connect(":memory:")
    db.migrate(conn)
    versions = [r[0] for r in conn.execute("SELECT version FROM schema_migrations")]
    assert versions == ["0001_init", "0002_budgets"]


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


def _add(conn, amount, category, day):
    db.add_expense(conn, Expense(amount=amount, category=category, spent_on=day))


def test_set_get_list_delete_budget():
    conn = db.connect(":memory:")
    assert db.get_budget(conn, "an-uong") is None

    db.set_budget(conn, Budget(category="an-uong", monthly_limit=100000))
    db.set_budget(conn, Budget(category="an-uong", monthly_limit=200000))
    db.set_budget(conn, Budget(category="cafe", monthly_limit=50000))

    assert db.get_budget(conn, "an-uong") == Budget(category="an-uong", monthly_limit=200000)
    assert [b.category for b in db.list_budgets(conn)] == ["an-uong", "cafe"]

    assert db.delete_budget(conn, "an-uong") is True
    assert db.delete_budget(conn, "an-uong") is False
    assert db.get_budget(conn, "an-uong") is None


def test_budget_limit_must_be_positive():
    conn = db.connect(":memory:")
    with pytest.raises(sqlite3.IntegrityError):
        db.set_budget(conn, Budget(category="x", monthly_limit=0))


def test_month_total_empty_is_int_zero():
    conn = db.connect(":memory:")
    total = db.month_total(conn, "an-uong", 2026, 11)
    assert total == 0
    assert isinstance(total, int)


def test_month_total_respects_month_boundaries_and_category():
    conn = db.connect(":memory:")
    _add(conn, 1, "an-uong", date(2026, 10, 31))
    _add(conn, 10, "an-uong", date(2026, 11, 1))
    _add(conn, 20, "an-uong", date(2026, 11, 30))
    _add(conn, 300, "an-uong", date(2026, 12, 1))
    _add(conn, 4000, "cafe", date(2026, 11, 15))

    assert db.month_total(conn, "an-uong", 2026, 11) == 30


def test_month_total_december_rolls_over_to_next_year():
    conn = db.connect(":memory:")
    _add(conn, 10, "x", date(2026, 12, 31))
    _add(conn, 200, "x", date(2027, 1, 1))

    assert db.month_total(conn, "x", 2026, 12) == 10
    assert db.month_total(conn, "x", 2027, 1) == 200


def test_month_total_matches_unnormalized_legacy_categories():
    conn = db.connect(":memory:")
    _add(conn, 1, "An-Uong", date(2026, 11, 1))
    _add(conn, 10, " an-uong ", date(2026, 11, 2))
    _add(conn, 100, "ĂN UỐNG", date(2026, 11, 3))

    assert db.month_total(conn, "an-uong", 2026, 11) == 11
    assert db.month_total(conn, "ăn uống", 2026, 11) == 100
