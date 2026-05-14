from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil

from .config import AnnouncerConfig, load_config
from .script import load_script


@dataclass(frozen=True)
class DoctorCheck:
    level: str
    name: str
    message: str


@dataclass(frozen=True)
class DoctorReport:
    checks: list[DoctorCheck]

    @property
    def has_errors(self) -> bool:
        return any(check.level == "error" for check in self.checks)


def run_doctor(
    config_path: Path,
    script_path: Path | None = None,
    output_dir: Path | None = None,
) -> DoctorReport:
    checks: list[DoctorCheck] = []
    config = _load_config(config_path, checks)
    if config is None:
        return DoctorReport(checks)

    _check_ootp(config, checks)
    _check_voice(config, checks)
    if script_path is not None:
        _check_script(script_path, config, checks)
    if output_dir is not None:
        _check_output_dir(output_dir, checks)

    return DoctorReport(checks)


def render_doctor_report(report: DoctorReport) -> str:
    lines = ["OOTP announcer doctor report", ""]
    for check in report.checks:
        lines.append(f"[{check.level.upper()}] {check.name}: {check.message}")
    if not report.checks:
        lines.append("[OK] doctor: no checks were run")
    lines.append("")
    lines.append("Result: failed" if report.has_errors else "Result: passed")
    return "\n".join(lines)


def _load_config(path: Path, checks: list[DoctorCheck]) -> AnnouncerConfig | None:
    if not path.exists():
        checks.append(DoctorCheck("error", "config", f"Config file not found: {path}"))
        return None
    try:
        config = load_config(path)
    except Exception as exc:
        checks.append(DoctorCheck("error", "config", f"Could not load config: {exc}"))
        return None

    checks.append(DoctorCheck("ok", "config", f"Loaded {path}"))
    return config


def _check_ootp(config: AnnouncerConfig, checks: list[DoctorCheck]) -> None:
    if config.ootp.root is None:
        checks.append(
            DoctorCheck(
                "warning",
                "ootp.root",
                "No OOTP root configured; run discover/inspect on the game PC.",
            )
        )
        return

    if not config.ootp.root.exists():
        checks.append(
            DoctorCheck("error", "ootp.root", f"Configured root does not exist: {config.ootp.root}")
        )
        return

    checks.append(DoctorCheck("ok", "ootp.root", f"Found {config.ootp.root}"))
    pronunciation = config.ootp.root / config.ootp.pronunciation_file
    if pronunciation.exists():
        checks.append(DoctorCheck("ok", "pronunciation", f"Found {pronunciation}"))
    else:
        checks.append(
            DoctorCheck(
                "warning",
                "pronunciation",
                f"Pronunciation file not found at expected path: {pronunciation}",
            )
        )


def _check_voice(config: AnnouncerConfig, checks: list[DoctorCheck]) -> None:
    voice = config.voice
    if voice.backend == "dry-run":
        checks.append(
            DoctorCheck(
                "warning",
                "voice",
                "Using dry-run backend; generated files will not contain real audio.",
            )
        )
        return

    if voice.backend == "piper":
        binary = shutil.which(voice.piper_binary)
        if binary:
            checks.append(DoctorCheck("ok", "piper_binary", f"Found {binary}"))
        else:
            checks.append(
                DoctorCheck("error", "piper_binary", f"Not found on PATH: {voice.piper_binary}")
            )

        if voice.piper_model is None:
            checks.append(DoctorCheck("error", "piper_model", "Piper model is not configured"))
        elif voice.piper_model.exists():
            checks.append(DoctorCheck("ok", "piper_model", f"Found {voice.piper_model}"))
        else:
            checks.append(
                DoctorCheck("error", "piper_model", f"Model file not found: {voice.piper_model}")
            )
        return

    if voice.backend == "command":
        template = voice.command_template
        if not template.strip():
            checks.append(DoctorCheck("error", "command_template", "Command template is empty"))
        elif "{text}" not in template or "{output}" not in template:
            checks.append(
                DoctorCheck(
                    "error",
                    "command_template",
                    "Command template must include both {text} and {output}",
                )
            )
        else:
            checks.append(DoctorCheck("ok", "command_template", "Template contains required placeholders"))


def _check_script(
    script_path: Path,
    config: AnnouncerConfig,
    checks: list[DoctorCheck],
) -> None:
    if not script_path.exists():
        checks.append(DoctorCheck("error", "script", f"Script file not found: {script_path}"))
        return

    try:
        lines = load_script(script_path, config.audio.extension)
    except Exception as exc:
        checks.append(DoctorCheck("error", "script", f"Could not load script: {exc}"))
        return

    if lines:
        checks.append(DoctorCheck("ok", "script", f"Loaded {len(lines)} announcer line(s)"))
    else:
        checks.append(DoctorCheck("warning", "script", "Script contains no announcer lines"))


def _check_output_dir(output_dir: Path, checks: list[DoctorCheck]) -> None:
    parent = output_dir.expanduser().parent
    if parent.exists():
        checks.append(DoctorCheck("ok", "output", f"Output parent exists: {parent}"))
    else:
        checks.append(DoctorCheck("error", "output", f"Output parent does not exist: {parent}"))
