from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from common import get_nested, load_config
from config_checks import CheckResult, run_environment_checks, summarize_results
from data_contracts import ValidationIssue, has_errors, load_json_array, summarize_issues, validate_alignment, validate_tts_chunks
from run_pipeline import STAGES, format_manifest_summary, read_stage_manifest, stage_status


@dataclass(frozen=True)
class StageReport:
    stage_id: int
    name: str
    status: str
    detail: str
    last_run: str | None = None


@dataclass(frozen=True)
class CommandReport:
    command: str
    available: bool
    output: str | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a diagnostic report for local pipeline troubleshooting")
    parser.add_argument("--config", default="configs/local.yaml", help="Path to YAML config file")
    parser.add_argument("--from-stage", type=int, default=0, help="First stage to include in status report")
    parser.add_argument("--to-stage", type=int, default=8, help="Last stage to include in status report")
    parser.add_argument("--include-artifacts", action="store_true", help="Validate ASR/refined JSON and TTS chunks when configured files exist")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument("--output", help="Optional file path to write the report")
    return parser.parse_args()


def _safe_run(command: list[str]) -> CommandReport:
    try:
        completed = subprocess.run(command, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=5)
    except FileNotFoundError:
        return CommandReport(command=command[0], available=False)
    except Exception as exc:
        return CommandReport(command=command[0], available=True, output=f"error: {exc}")
    first_line = (completed.stdout or "").strip().splitlines()[0] if completed.stdout else ""
    return CommandReport(command=command[0], available=True, output=first_line)


def _git_head() -> str | None:
    try:
        completed = subprocess.run(["git", "rev-parse", "--short", "HEAD"], check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=5)
    except Exception:
        return None
    value = completed.stdout.strip()
    return value or None


def _load_config_or_error(config_path: str) -> tuple[dict[str, Any], str | None]:
    try:
        return load_config(config_path), None
    except Exception as exc:
        return {}, str(exc)


def collect_stage_reports(cfg: dict[str, Any], from_stage: int, to_stage: int) -> list[StageReport]:
    reports: list[StageReport] = []
    for stage_id, name, _cmd in STAGES:
        if not from_stage <= stage_id <= to_stage:
            continue
        status, detail = stage_status(stage_id, cfg)
        manifest = read_stage_manifest(stage_id, name, cfg)
        reports.append(
            StageReport(
                stage_id=stage_id,
                name=name,
                status=status,
                detail=detail,
                last_run=format_manifest_summary(manifest) if manifest else None,
            )
        )
    return reports


def _configured_path_exists(cfg: dict[str, Any], key: str) -> bool:
    value = get_nested(cfg, key)
    return bool(value) and Path(str(value)).exists()


def collect_artifact_issues(cfg: dict[str, Any], include_chunks: bool = True) -> tuple[list[ValidationIssue], str | None]:
    if not _configured_path_exists(cfg, "paths.asr_json") or not _configured_path_exists(cfg, "paths.refined_json"):
        return [], "ASR or refined JSON file is not available yet"

    try:
        asr = load_json_array(get_nested(cfg, "paths.asr_json"))
        refined = load_json_array(get_nested(cfg, "paths.refined_json"))
    except Exception as exc:
        return [ValidationIssue("ERROR", "artifacts", f"cannot load configured JSON artifacts: {exc}")], None

    issues: list[ValidationIssue] = []
    issues.extend(validate_alignment(asr, refined))
    if include_chunks:
        chunk_dir = get_nested(cfg, "paths.dub_chunk_dir")
        if chunk_dir:
            issues.extend(validate_tts_chunks(refined, chunk_dir))
        else:
            issues.append(ValidationIssue("ERROR", "tts_chunks", "missing configured path: paths.dub_chunk_dir"))
    return issues, None


def collect_report(config_path: str, from_stage: int, to_stage: int, include_artifacts: bool) -> dict[str, Any]:
    cfg, config_error = _load_config_or_error(config_path)
    report: dict[str, Any] = {
        "project": "VoxCPM Translator",
        "config": {
            "path": config_path,
            "loaded": config_error is None,
            "error": config_error,
        },
        "system": {
            "python": sys.version.split()[0],
            "executable": sys.executable,
            "platform": platform.platform(),
            "cwd": str(Path.cwd()),
            "git_head": _git_head(),
        },
        "commands": [asdict(_safe_run(["ffmpeg", "-version"])), asdict(_safe_run(["ffprobe", "-version"])), asdict(_safe_run(["audio-separator", "--help"]))],
        "environment": None,
        "stages": [],
        "artifacts": None,
    }

    if config_error is not None:
        return report

    env_results = run_environment_checks(cfg)
    report["environment"] = {
        "summary": summarize_results(env_results),
        "results": [result.to_dict() for result in env_results],
    }
    report["stages"] = [asdict(item) for item in collect_stage_reports(cfg, from_stage, to_stage)]

    if include_artifacts:
        issues, skipped_reason = collect_artifact_issues(cfg)
        report["artifacts"] = {
            "skipped_reason": skipped_reason,
            "summary": summarize_issues(issues),
            "has_errors": has_errors(issues),
            "issues": [issue.to_dict() for issue in issues],
        }

    return report


def _summary_line(summary: dict[str, int], keys: list[str]) -> str:
    return " ".join(f"{key}={summary.get(key, 0)}" for key in keys)


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# VoxCPM Translator diagnostic report")
    lines.append("")
    config = report["config"]
    lines.append("## Config")
    lines.append(f"- Path: `{config['path']}`")
    lines.append(f"- Loaded: `{config['loaded']}`")
    if config.get("error"):
        lines.append(f"- Error: `{config['error']}`")
        return "\n".join(lines) + "\n"

    lines.append("")
    lines.append("## System")
    system = report["system"]
    lines.append(f"- Python: `{system['python']}`")
    lines.append(f"- Platform: `{system['platform']}`")
    lines.append(f"- Git head: `{system.get('git_head') or 'unknown'}`")

    lines.append("")
    lines.append("## Commands")
    for command in report["commands"]:
        status = "available" if command["available"] else "missing"
        detail = f" — {command['output']}" if command.get("output") else ""
        lines.append(f"- `{command['command']}`: {status}{detail}")

    environment = report.get("environment")
    if environment:
        lines.append("")
        lines.append("## Environment checks")
        lines.append(f"- Summary: `{_summary_line(environment['summary'], ['OK', 'WARN', 'FAIL'])}`")
        for result in environment["results"]:
            lines.append(f"- [{result['level']}] {result['name']}: {result['message']}")

    lines.append("")
    lines.append("## Stage status")
    for stage in report["stages"]:
        suffix = f" | {stage['last_run']}" if stage.get("last_run") else ""
        lines.append(f"- [{stage['stage_id']}] {stage['name']}: {stage['status']} — {stage['detail']}{suffix}")

    artifacts = report.get("artifacts")
    if artifacts:
        lines.append("")
        lines.append("## Artifact validation")
        if artifacts.get("skipped_reason"):
            lines.append(f"- Skipped: {artifacts['skipped_reason']}")
        else:
            lines.append(f"- Summary: `{_summary_line(artifacts['summary'], ['ERROR', 'WARN', 'INFO'])}`")
            for issue in artifacts["issues"]:
                lines.append(f"- [{issue['level']}] {issue['path']}: {issue['message']}")

    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    report = collect_report(args.config, args.from_stage, args.to_stage, include_artifacts=args.include_artifacts)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n" if args.json else render_markdown(report)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")

    return 0


if __name__ == "__main__":
    sys.exit(main())
