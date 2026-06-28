from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Check:
    name: str
    command: list[str]
    description: str
    requires: str | None = None


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    detail: str
    returncode: int = 0


CHECKS = {
    "compile": Check(
        name="compile",
        command=[sys.executable, "-m", "compileall", "scripts"],
        description="compile all Python scripts",
    ),
    "shell": Check(
        name="shell",
        command=["bash", "-n", "scripts/01_process_vocals.sh"],
        description="check shell script syntax",
        requires="bash",
    ),
    "tests": Check(
        name="tests",
        command=[sys.executable, "-m", "pytest", "-q"],
        description="run unit tests",
    ),
    "pipeline-dry-run": Check(
        name="pipeline-dry-run",
        command=[
            sys.executable,
            "scripts/run_pipeline.py",
            "--config",
            "configs/default.yaml",
            "--dry-run",
            "--from-stage",
            "0",
            "--to-stage",
            "6",
        ],
        description="dry-run the default pipeline command plan",
    ),
}

DEFAULT_CHECKS = ["compile", "shell", "tests", "pipeline-dry-run"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run lightweight local development checks")
    parser.add_argument(
        "--check",
        action="append",
        choices=sorted(CHECKS),
        help="Check to run. Can be repeated. Defaults to the full lightweight suite.",
    )
    parser.add_argument("--list", action="store_true", help="List available checks and exit")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing them")
    parser.add_argument("--keep-going", action="store_true", help="Continue after a failed check")
    return parser.parse_args()


def command_text(command: list[str]) -> str:
    return " ".join(command)


def run_check(check: Check, dry_run: bool = False) -> CheckResult:
    if check.requires and shutil.which(check.requires) is None:
        return CheckResult(check.name, "SKIP", f"missing executable: {check.requires}")

    if dry_run:
        return CheckResult(check.name, "DRY-RUN", command_text(check.command))

    completed = subprocess.run(check.command, cwd=ROOT)
    if completed.returncode == 0:
        return CheckResult(check.name, "OK", check.description)
    return CheckResult(check.name, "FAIL", command_text(check.command), completed.returncode)


def render_result(result: CheckResult) -> str:
    suffix = f" (exit {result.returncode})" if result.returncode else ""
    return f"[{result.status}] {result.name}: {result.detail}{suffix}"


def selected_checks(args: argparse.Namespace) -> list[Check]:
    names = args.check or DEFAULT_CHECKS
    return [CHECKS[name] for name in names]


def main() -> int:
    args = parse_args()

    if args.list:
        for name in DEFAULT_CHECKS:
            check = CHECKS[name]
            print(f"{name}: {command_text(check.command)}")
        return 0

    failed = False
    for check in selected_checks(args):
        print(f"==> {check.name}: {check.description}")
        result = run_check(check, dry_run=args.dry_run)
        print(render_result(result))
        if result.status == "FAIL":
            failed = True
            if not args.keep_going:
                break

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
