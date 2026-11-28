from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from tests.conftest import make_report
from warnbot.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("WARNBOT_DB", str(tmp_path / "app.db"))
    monkeypatch.delenv("NTFY_URL", raising=False)


@pytest.fixture
def report(tmp_path: Path, report_rows: list[list[Any]]) -> Path:
    path = tmp_path / "report.xlsx"
    path.write_bytes(make_report(report_rows))
    return path


def test_dry_run_then_status(report: Path) -> None:
    result = runner.invoke(app, ["run", "--dry-run", "--file", str(report)])
    assert result.exit_code == 0, result.output
    assert "First run: seeded 3 existing notices" in result.output
    status = runner.invoke(app, ["status"])
    assert "notices: none" in status.output  # the dry run changed nothing
    assert "ok (dry run)  seeded 3 notices from 5 rows" in status.output


def test_first_real_run_seeds(report: Path) -> None:
    assert runner.invoke(app, ["run", "--file", str(report)]).exit_code == 0
    assert "notices: seeded 3" in runner.invoke(app, ["status"]).output


def test_a_bad_report_fails_the_run(tmp_path: Path) -> None:
    bad = tmp_path / "bad.xlsx"
    bad.write_bytes(b"not a workbook")
    result = runner.invoke(app, ["run", "--file", str(bad)])
    assert result.exit_code == 1
    assert "FAILED" in runner.invoke(app, ["status"]).output


def test_rejects_a_zero_cap() -> None:
    assert runner.invoke(app, ["run", "--max", "0"]).exit_code != 0
