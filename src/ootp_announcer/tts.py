from __future__ import annotations

from pathlib import Path
import os
import shlex
import subprocess

from .config import VoiceSettings


class TtsError(RuntimeError):
    """Raised when the configured speech engine cannot synthesize a line."""


def synthesize(text: str, output: Path, voice: VoiceSettings) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)

    if voice.backend == "dry-run":
        _write_dry_run(text, output)
        return
    if voice.backend == "piper":
        _run_piper(text, output, voice)
        return
    if voice.backend == "command":
        _run_command_template(text, output, voice)
        return

    raise TtsError(f"Unsupported backend: {voice.backend}")


def _write_dry_run(text: str, output: Path) -> None:
    output.write_text(
        "DRY RUN - configure a TTS backend to generate audio.\n\n"
        f"{text}\n",
        encoding="utf-8",
    )


def _run_piper(text: str, output: Path, voice: VoiceSettings) -> None:
    if voice.piper_model is None:
        raise TtsError("voice.piper_model is required when backend is 'piper'")

    command = [
        voice.piper_binary,
        "--model",
        str(voice.piper_model),
        "--output_file",
        str(output),
    ]
    if voice.speaker_id is not None:
        command.extend(["--speaker", str(voice.speaker_id)])

    try:
        completed = subprocess.run(
            command,
            input=text,
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise TtsError(f"Piper executable not found: {voice.piper_binary}") from exc

    if completed.returncode != 0:
        raise TtsError(
            "Piper failed with exit code "
            f"{completed.returncode}: {completed.stderr.strip()}"
        )


def _run_command_template(text: str, output: Path, voice: VoiceSettings) -> None:
    if not voice.command_template.strip():
        raise TtsError("voice.command_template is required when backend is 'command'")

    formatted = voice.command_template.format(
        text=_quote_argument(text),
        output=_quote_argument(str(output)),
    )
    command = shlex.split(formatted, posix=(os.name != "nt"))
    if not command:
        raise TtsError("voice.command_template produced an empty command")

    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        raise TtsError(f"TTS command not found: {command[0]}") from exc

    if completed.returncode != 0:
        raise TtsError(
            "TTS command failed with exit code "
            f"{completed.returncode}: {completed.stderr.strip()}"
        )
    if not output.exists():
        raise TtsError(f"TTS command completed but did not create {output}")


def _quote_argument(value: str) -> str:
    if os.name == "nt":
        escaped = value.replace('"', r"\"")
        return f'"{escaped}"'
    return shlex.quote(value)
