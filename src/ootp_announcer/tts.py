from __future__ import annotations

import json
from pathlib import Path
import os
import shlex
import subprocess
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

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
    if voice.backend == "elevenlabs":
        _run_elevenlabs(text, output, voice)
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


def _normalize_elevenlabs_api_key(raw: str) -> str:
    """Strip whitespace and accidental wrapping quotes from copy/paste."""
    key = (raw or "").strip()
    # One key per file: if there are multiple lines, use the first non-empty line only.
    if "\n" in key or "\r" in key:
        key = key.replace("\r\n", "\n").replace("\r", "\n")
        for line in key.split("\n"):
            line = line.strip()
            if line:
                key = line
                break
    lowered = key.lower()
    for prefix in ("api key:", "apikey:", "xi-api-key:", "key:", "elevenlabs_api_key=", "bearer "):
        if lowered.startswith(prefix):
            key = key[len(prefix) :].strip()
            break
    if len(key) >= 2 and key[0] == key[-1] and key[0] in {'"', "'"}:
        key = key[1:-1].strip()
    if key.startswith("\ufeff"):
        key = key.lstrip("\ufeff").strip()
    return key


def _elevenlabs_key_and_source_from_environment() -> tuple[str, str]:
    """Return (key, short_description) from file or env only."""
    path = (os.environ.get("ELEVENLABS_API_KEY_FILE") or "").strip()
    if path:
        try:
            file_key = Path(path).expanduser().read_text(encoding="utf-8")
            fk = _normalize_elevenlabs_api_key(file_key)
            if fk:
                return fk, f"ELEVENLABS_API_KEY_FILE ({path})"
        except OSError:
            pass
    env_key = _normalize_elevenlabs_api_key(os.environ.get("ELEVENLABS_API_KEY", ""))
    if env_key:
        return env_key, "ELEVENLABS_API_KEY"
    return "", ""


def describe_elevenlabs_api_key_source(voice: VoiceSettings | None) -> tuple[str, str]:
    """Return (key, short_description) using env/file first, then optional TOML voice settings."""
    ek, esrc = _elevenlabs_key_and_source_from_environment()
    if ek:
        return ek, esrc
    if voice is None:
        return "", ""
    tk = _normalize_elevenlabs_api_key(voice.elevenlabs_api_key)
    if tk:
        return tk, "voice.elevenlabs_api_key in TOML"
    return "", ""


def _elevenlabs_api_key_from_env_or_keyfile() -> str:
    """Read API key from ELEVENLABS_API_KEY_FILE first, then ELEVENLABS_API_KEY (not from TOML)."""
    key, _ = _elevenlabs_key_and_source_from_environment()
    return key


def _elevenlabs_api_key(voice: VoiceSettings) -> str:
    key, _ = describe_elevenlabs_api_key_source(voice)
    return key


def _elevenlabs_http_error_hint(status_code: int, detail_text: str) -> str:
    """Short hint for common ElevenLabs HTTP error bodies (JSON or plain text)."""
    low = detail_text.lower()
    status = ""
    try:
        blob = json.loads(detail_text)
    except json.JSONDecodeError:
        blob = None
    if isinstance(blob, dict):
        inner = blob.get("detail")
        if isinstance(inner, dict):
            status = str(inner.get("status", "")).lower()
        elif isinstance(inner, str):
            status = inner.lower()
    if status == "quota_exceeded" or "quota_exceeded" in low or "credits remaining" in low:
        return (
            " This is your ElevenLabs usage/credit limit (not a wrong password). "
            "See credits required vs remaining in the message. Fix: add credits / upgrade plan, "
            "wait for quota reset, use model eleven_turbo_v2_5 (often cheaper), shorten lines, "
            "or build fewer lines with --max-lines."
        )
    if status == "invalid_api_key" or "invalid_api_key" in low:
        return (
            " ElevenLabs rejected the API key. Check the key in Notepad (one line). "
            "If using ELEVENLABS_API_KEY_FILE, run Remove-Item Env:ELEVENLABS_API_KEY. "
            "Create a fresh key in ElevenLabs → Profile → API keys if needed."
        )
    if status_code == 429 or "too many requests" in low:
        return (
            " Rate limited: wait briefly, increase delay_seconds_after_each_line in your TOML, "
            "or build in smaller batches (--max-lines)."
        )
    return ""


def fetch_elevenlabs_user_json(api_key: str) -> dict[str, object]:
    """Call GET /v1/user to confirm the API key is valid (no audio generation)."""
    key = _normalize_elevenlabs_api_key(api_key)
    if not key:
        raise TtsError("No API key provided to verify.")

    request = Request(
        "https://api.elevenlabs.io/v1/user",
        method="GET",
        headers={"xi-api-key": key, "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        hint = _elevenlabs_http_error_hint(exc.code, detail)
        raise TtsError(f"ElevenLabs HTTP {exc.code}: {detail[:2000]}.{hint}") from exc
    except URLError as exc:
        raise TtsError(f"ElevenLabs request failed: {exc.reason}") from exc

    try:
        parsed: dict[str, object] = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise TtsError("ElevenLabs returned non-JSON from /v1/user") from exc
    return parsed


def _run_elevenlabs(text: str, output: Path, voice: VoiceSettings) -> None:
    api_key = _elevenlabs_api_key(voice)
    if not api_key:
        raise TtsError(
            "ElevenLabs API key missing: set environment variable ELEVENLABS_API_KEY, "
            "or ELEVENLABS_API_KEY_FILE pointing to a UTF-8 text file containing the key on one line, "
            "or voice.elevenlabs_api_key in announcer.toml (do not commit real keys)."
        )

    voice_id = quote(voice.elevenlabs_voice_id, safe="")
    out_fmt = voice.elevenlabs_output_format.strip()
    url = (
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        f"?{urlencode({'output_format': out_fmt})}"
    )
    payload = {
        "text": text,
        "model_id": voice.elevenlabs_model_id,
        "voice_settings": {
            "stability": float(voice.elevenlabs_stability),
            "similarity_boost": float(voice.elevenlabs_similarity_boost),
            "style": float(voice.elevenlabs_style),
            "use_speaker_boost": bool(voice.elevenlabs_use_speaker_boost),
        },
    }
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        method="POST",
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
    )
    try:
        with urlopen(request, timeout=120) as response:
            data = response.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        hint = _elevenlabs_http_error_hint(exc.code, detail)
        raise TtsError(f"ElevenLabs HTTP {exc.code}: {detail[:2000]}.{hint}") from exc
    except URLError as exc:
        raise TtsError(f"ElevenLabs request failed: {exc.reason}") from exc

    if not data:
        raise TtsError("ElevenLabs returned an empty response body")

    output.write_bytes(data)


