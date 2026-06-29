import subprocess

import dev_check


def test_selected_checks_defaults_to_full_suite() -> None:
    args = type("Args", (), {"check": None})()

    assert [check.name for check in dev_check.selected_checks(args)] == dev_check.DEFAULT_CHECKS
    assert "config-schema" in dev_check.DEFAULT_CHECKS
    assert "demo-smoke" in dev_check.DEFAULT_CHECKS


def test_run_check_dry_run_does_not_execute() -> None:
    check = dev_check.CHECKS["compile"]

    result = dev_check.run_check(check, dry_run=True)

    assert result.status == "DRY-RUN"
    assert "compileall" in result.detail


def test_run_check_skips_missing_required_executable(monkeypatch) -> None:
    monkeypatch.setattr(dev_check.shutil, "which", lambda name: None)

    result = dev_check.run_check(dev_check.CHECKS["shell"])

    assert result.status == "SKIP"
    assert "bash" in result.detail


def test_run_check_reports_failure(monkeypatch) -> None:
    def fake_run(command, cwd):
        return subprocess.CompletedProcess(command, 2)

    monkeypatch.setattr(dev_check.subprocess, "run", fake_run)

    result = dev_check.run_check(dev_check.CHECKS["tests"])

    assert result.status == "FAIL"
    assert result.returncode == 2


def test_config_schema_check_is_available() -> None:
    check = dev_check.CHECKS["config-schema"]

    assert check.command[1] == "scripts/check_config_schema.py"
    assert "configs/default.yaml" in check.command


def test_demo_smoke_check_is_available() -> None:
    check = dev_check.CHECKS["demo-smoke"]

    assert check.command[-1] == "scripts/run_demo_smoke.py"
    assert "no-model" in check.description


def test_main_stops_on_first_failure(monkeypatch, capsys) -> None:
    monkeypatch.setattr(dev_check, "parse_args", lambda: type("Args", (), {"list": False, "check": ["compile", "tests"], "dry_run": False, "keep_going": False})())

    calls = []

    def fake_run_check(check, dry_run=False):
        calls.append(check.name)
        return dev_check.CheckResult(check.name, "FAIL", "broken", 1)

    monkeypatch.setattr(dev_check, "run_check", fake_run_check)

    assert dev_check.main() == 1
    assert calls == ["compile"]
    assert "[FAIL] compile" in capsys.readouterr().out
