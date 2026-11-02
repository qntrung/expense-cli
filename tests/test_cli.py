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
