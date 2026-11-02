from typer.testing import CliRunner

from expense.cli import app, format_vnd

runner = CliRunner()


def test_format_vnd():
    assert format_vnd(1234567) == "1.234.567 ₫"


def test_add_then_list(tmp_path):
    env = {"EXPENSE_DB": str(tmp_path / "test.db")}

    args = ["add", "50000", "an-uong", "-n", "Phở", "-d", "2026-01-02"]
    result = runner.invoke(app, args, env=env)
    assert result.exit_code == 0, result.output
    assert "50.000 ₫" in result.output

    result = runner.invoke(app, ["list"], env=env)
    assert result.exit_code == 0, result.output
    assert "2026-01-02" in result.output
    assert "Tổng: 50.000 ₫" in result.output


def test_add_rejects_non_positive_amount(tmp_path):
    result = runner.invoke(app, ["add", "0", "x"], env={"EXPENSE_DB": str(tmp_path / "t.db")})
    assert result.exit_code != 0


def test_add_rejects_negative_amount_and_writes_nothing(tmp_path):
    env = {"EXPENSE_DB": str(tmp_path / "t.db")}
    result = runner.invoke(app, ["add", "-5000", "an-uong"], env=env)
    assert result.exit_code != 0

    result = runner.invoke(app, ["list"], env=env)
    assert "Chưa có khoản chi nào." in result.output


def test_delete(tmp_path):
    env = {"EXPENSE_DB": str(tmp_path / "t.db")}
    runner.invoke(app, ["add", "45000", "an-uong"], env=env)

    result = runner.invoke(app, ["delete", "1"], input="n\n", env=env)
    assert result.exit_code != 0
    assert "#1" in runner.invoke(app, ["list"], env=env).output

    result = runner.invoke(app, ["delete", "1", "--yes"], env=env)
    assert result.exit_code == 0, result.output
    assert "Chưa có khoản chi nào." in runner.invoke(app, ["list"], env=env).output

    result = runner.invoke(app, ["delete", "1", "-y"], env=env)
    assert result.exit_code == 1


def test_add_rejects_negative_amount(tmp_path):
    db_file = tmp_path / "t.db"
    result = runner.invoke(app, ["add", "-5000", "an-uong"], env={"EXPENSE_DB": str(db_file)})

    assert result.exit_code == 2
    assert "Số tiền phải là số nguyên ≥ 1" in result.output
    assert "No such option" not in result.output
    assert not db_file.exists()


def test_add_accepts_option_value_that_looks_negative(tmp_path):
    env = {"EXPENSE_DB": str(tmp_path / "t.db")}
    result = runner.invoke(app, ["add", "100", "an-uong", "--note", "-5"], env=env)

    assert result.exit_code == 0, result.output
    assert "-5" in runner.invoke(app, ["list"], env=env).output


def _env(tmp_path):
    return {"EXPENSE_DB": str(tmp_path / "t.db")}


def test_budget_set_list_remove(tmp_path):
    env = _env(tmp_path)
    assert "Chưa đặt hạn mức nào." in runner.invoke(app, ["budget", "list"], env=env).output

    result = runner.invoke(app, ["budget", "set", "An-Uong", "100000"], env=env)
    assert result.exit_code == 0, result.output
    assert "an-uong: 100.000 ₫/tháng" in result.output

    result = runner.invoke(app, ["budget", "set", "an-uong", "200000"], env=env)
    assert result.exit_code == 0, result.output
    result = runner.invoke(app, ["budget", "list", "--month", "2026-11"], env=env)
    assert "đã chi 0 ₫ / 200.000 ₫" in result.output

    result = runner.invoke(app, ["budget", "remove", "AN-UONG"], env=env)
    assert result.exit_code == 0, result.output
    assert "Chưa đặt hạn mức nào." in runner.invoke(app, ["budget", "list"], env=env).output

    result = runner.invoke(app, ["budget", "remove", "an-uong"], env=env)
    assert result.exit_code == 1


def test_budget_set_rejects_invalid_input(tmp_path):
    env = _env(tmp_path)
    assert runner.invoke(app, ["budget", "set", "x", "0"], env=env).exit_code == 2
    assert runner.invoke(app, ["budget", "set", "  ", "1000"], env=env).exit_code == 2

    result = runner.invoke(app, ["budget", "set", "x", "-5000"], env=env)
    assert result.exit_code == 2
    assert "Số tiền phải là số nguyên ≥ 1" in result.output
    assert "No such option" not in result.output


def test_add_rejects_blank_category(tmp_path):
    result = runner.invoke(app, ["add", "1000", "   "], env=_env(tmp_path))
    assert result.exit_code == 2


def test_add_within_and_at_budget_limit(tmp_path):
    env = _env(tmp_path)
    runner.invoke(app, ["budget", "set", "an-uong", "100000"], env=env)

    result = runner.invoke(app, ["add", "60000", "an-uong", "-d", "2026-11-01"], env=env)
    assert result.exit_code == 0, result.output
    result = runner.invoke(app, ["add", "40000", "an-uong", "-d", "2026-11-02"], env=env)
    assert result.exit_code == 0, result.output
    assert "Cảnh báo" not in result.output


def test_add_over_budget_is_blocked_and_writes_nothing(tmp_path):
    env = _env(tmp_path)
    runner.invoke(app, ["budget", "set", "an-uong", "100000"], env=env)
    runner.invoke(app, ["add", "100000", "an-uong", "-d", "2026-11-01"], env=env)

    result = runner.invoke(app, ["add", "1", "AN-UONG", "-d", "2026-11-02"], env=env)
    assert result.exit_code == 1
    assert "Vượt hạn mức an-uong tháng 2026-11" in result.output
    assert "vượt 1 ₫" in result.output
    assert "--force" in result.output

    output = runner.invoke(app, ["list"], env=env).output
    assert "#2" not in output
    assert "Tổng: 100.000 ₫" in output


def test_add_over_budget_with_force_writes_and_warns(tmp_path):
    env = _env(tmp_path)
    runner.invoke(app, ["budget", "set", "an-uong", "100000"], env=env)

    result = runner.invoke(
        app, ["add", "150000", "an-uong", "-d", "2026-11-01", "--force"], env=env
    )
    assert result.exit_code == 0, result.output
    assert "Đã thêm #1" in result.output
    assert "Cảnh báo: Vượt hạn mức an-uong" in result.output

    result = runner.invoke(app, ["budget", "list", "--month", "2026-11"], env=env)
    assert "(150%)" in result.output
    assert "VƯỢT" in result.output


def test_add_without_budget_is_unaffected(tmp_path):
    env = _env(tmp_path)
    runner.invoke(app, ["budget", "set", "an-uong", "1000"], env=env)
    result = runner.invoke(app, ["add", "999999", "cafe", "-d", "2026-11-01"], env=env)
    assert result.exit_code == 0, result.output


def test_add_counts_against_month_of_spent_on(tmp_path):
    env = _env(tmp_path)
    runner.invoke(app, ["budget", "set", "an-uong", "100000"], env=env)
    runner.invoke(app, ["add", "100000", "an-uong", "-d", "2026-10-15"], env=env)

    result = runner.invoke(app, ["add", "1000", "an-uong", "-d", "2026-10-31"], env=env)
    assert result.exit_code == 1
    assert "tháng 2026-10" in result.output

    result = runner.invoke(app, ["add", "1000", "an-uong", "-d", "2026-11-01"], env=env)
    assert result.exit_code == 0, result.output


def test_budget_list_shows_spent_and_remaining(tmp_path):
    env = _env(tmp_path)
    runner.invoke(app, ["budget", "set", "an-uong", "200000"], env=env)
    runner.invoke(app, ["add", "50000", "An-Uong", "-d", "2026-11-03"], env=env)
    runner.invoke(app, ["add", "70000", "an-uong", "-d", "2026-12-01"], env=env)

    result = runner.invoke(app, ["budget", "list", "-m", "2026-11"], env=env)
    assert result.exit_code == 0, result.output
    assert "Tháng 2026-11" in result.output
    assert "đã chi 50.000 ₫ / 200.000 ₫ (25%)  còn 150.000 ₫" in result.output
    assert "VƯỢT" not in result.output
