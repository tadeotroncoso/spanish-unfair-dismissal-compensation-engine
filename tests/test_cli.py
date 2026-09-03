"""Console behaviour, cancellation and executable-entry-point regressions."""

from pathlib import Path
import subprocess
import sys

import pytest

import proyecto


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DISCLAIMER = (
    "Educational project. No support or maintenance is provided.",
    "Not legal advice or a legal recommendation. Accuracy is not guaranteed.",
)


def _provide_input(monkeypatch, values):
    iterator = iter(values)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(iterator))


def test_readme_demo_and_disclaimers(monkeypatch, capsys):
    _provide_input(monkeypatch, ["12/02/2011", "11/02/2013", "36500"])

    assert proyecto.main() == 0

    output = capsys.readouterr()
    assert "Before 12 February 2012: months=12" in output.out
    assert "From 12 February 2012: months=12" in output.out
    assert "TOTAL: 7800.00" in output.out
    for statement in DISCLAIMER:
        assert statement in output.out
    assert (
        "Educational estimate only; do not rely on it for legal or financial decisions."
        in output.out
    )
    assert output.err == ""


def test_invalid_dates_and_reversed_end_date_can_be_corrected(monkeypatch, capsys):
    _provide_input(
        monkeypatch,
        ["31/02/2024", "invalid", "01/01/2024", "31/12/2023", "01/01/2024", "36500"],
    )

    assert proyecto.main() == 0

    output = capsys.readouterr()
    assert output.out.count("Invalid date") == 2
    assert "end date must be on or after the start date" in output.out
    assert "TOTAL: 275.00" in output.out
    assert output.err == ""


def test_invalid_salaries_retry_until_valid_comma_decimal(monkeypatch, capsys):
    _provide_input(
        monkeypatch,
        [
            "01/01/2020",
            "31/01/2026",
            "invalid",
            "0",
            "-1",
            "NaN",
            "sNaN",
            "Infinity",
            "1e30",
            "0.001",
            "36500.901",
            "36500,90",
        ],
    )

    assert proyecto.main() == 0

    output = capsys.readouterr()
    assert "TOTAL: 20075.50" in output.out
    assert "Invalid" in output.out
    assert "Traceback" not in output.out + output.err
    assert output.err == ""


def test_overlong_salary_input_is_rejected_without_a_traceback(monkeypatch, capsys):
    _provide_input(monkeypatch, ["01/01/2024", "01/01/2024", "9" * 129, "36500"])

    assert proyecto.main() == 0

    output = capsys.readouterr()
    assert "Invalid" in output.out
    assert "TOTAL: 275.00" in output.out
    assert "Traceback" not in output.out + output.err
    assert output.err == ""


@pytest.mark.parametrize(
    "exception,exit_code", [(EOFError, 0), (KeyboardInterrupt, 130)]
)
@pytest.mark.parametrize("completed_prompts", [0, 1, 2])
def test_cancelled_input_exits_cleanly(
    monkeypatch, capsys, exception, exit_code, completed_prompts
):
    answers = iter(["01/01/2024", "01/01/2024"][:completed_prompts])

    def interrupted_input(_prompt):
        try:
            return next(answers)
        except StopIteration:
            raise exception from None

    monkeypatch.setattr("builtins.input", interrupted_input)

    assert proyecto.main() == exit_code

    output = capsys.readouterr()
    assert "cancel" in (output.out + output.err).lower()
    assert "Traceback" not in output.out + output.err
    assert "TOTAL:" not in output.out


def test_disclaimer_is_visible_before_collecting_input(monkeypatch, capsys):
    def stop_before_input(_prompt):
        output = capsys.readouterr()
        for statement in DISCLAIMER:
            assert statement in output.out
        raise EOFError

    monkeypatch.setattr("builtins.input", stop_before_input)

    assert proyecto.main() == 0


def test_module_import_does_not_prompt_or_print():
    completed = subprocess.run(
        [sys.executable, "-B", "-c", "import proyecto"],
        cwd=PROJECT_ROOT,
        input="",
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )

    assert completed.returncode == 0
    assert completed.stdout == ""
    assert completed.stderr == ""


def test_executed_script_runs_demo_and_propagates_success_exit_code():
    completed = subprocess.run(
        [sys.executable, "-B", str(PROJECT_ROOT / "proyecto.py")],
        cwd=PROJECT_ROOT,
        input="12/02/2011\n11/02/2013\n36500\n",
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )

    assert completed.returncode == 0
    assert "TOTAL: 7800.00" in completed.stdout
    assert completed.stderr == ""


def test_executed_script_handles_closed_standard_input():
    completed = subprocess.run(
        [sys.executable, "-B", str(PROJECT_ROOT / "proyecto.py")],
        cwd=PROJECT_ROOT,
        input="",
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )

    assert completed.returncode == 0
    assert "cancel" in completed.stdout.lower()
    assert completed.stderr == ""
