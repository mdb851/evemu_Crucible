from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class OotpSettings:
    root: Path | None
    pronunciation_file: str


@dataclass(frozen=True)
class VoiceSettings:
    backend: str
    command_template: str
    piper_binary: str
    piper_model: Path | None
    speaker_id: int | None
    elevenlabs_voice_id: str
    elevenlabs_model_id: str
    elevenlabs_output_format: str
    elevenlabs_stability: float
    elevenlabs_similarity_boost: float
    elevenlabs_style: float
    elevenlabs_use_speaker_boost: bool
    elevenlabs_api_key: str


@dataclass(frozen=True)
class AudioSettings:
    extension: str


@dataclass(frozen=True)
class BuildSettings:
    """Optional pacing between synthesized lines (helps ElevenLabs rate limits)."""

    delay_seconds_after_each_line: float


@dataclass(frozen=True)
class AnnouncerConfig:
    name: str
    game: str
    ootp: OotpSettings
    voice: VoiceSettings
    audio: AudioSettings
    build: BuildSettings


def _optional_float(value: object, default: float) -> float:
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    return float(text)


def _optional_bool(value: object, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off", ""}:
        return False
    return default


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _optional_path(value: object) -> Path | None:
    if value is None:
        return None
    text = str(value).strip()
    return Path(text).expanduser() if text else None


def load_config(path: Path) -> AnnouncerConfig:
    with path.open("rb") as handle:
        raw = tomllib.load(handle)

    project = raw.get("project", {})
    ootp = raw.get("ootp", {})
    voice = raw.get("voice", {})
    audio = raw.get("audio", {})
    build = raw.get("build", {})

    backend = str(voice.get("backend", "dry-run")).strip().lower()
    if backend not in {"dry-run", "piper", "command", "elevenlabs"}:
        raise ValueError(f"Unsupported voice backend: {backend}")

    speaker_value = voice.get("speaker_id")
    speaker_text = "" if speaker_value is None else str(speaker_value).strip()
    speaker_id = int(speaker_text) if speaker_text else None

    extension = str(audio.get("extension", "wav")).strip().lstrip(".").lower()
    if not extension:
        raise ValueError("audio.extension must not be empty")

    el_voice = str(voice.get("elevenlabs_voice_id", "")).strip()
    el_model = str(voice.get("elevenlabs_model_id", "eleven_multilingual_v2")).strip()
    el_format = str(voice.get("elevenlabs_output_format", "mp3_44100_128")).strip()
    el_key = str(voice.get("elevenlabs_api_key", "")).strip()

    el_stab = _clamp01(_optional_float(voice.get("elevenlabs_stability"), 0.5))
    el_sim = _clamp01(_optional_float(voice.get("elevenlabs_similarity_boost"), 0.75))
    el_style = _clamp01(_optional_float(voice.get("elevenlabs_style"), 0.25))
    el_boost = _optional_bool(voice.get("elevenlabs_use_speaker_boost"), True)

    delay = max(0.0, min(60.0, _optional_float(build.get("delay_seconds_after_each_line"), 0.0)))

    if backend == "elevenlabs":
        if not el_voice:
            raise ValueError("voice.elevenlabs_voice_id is required when backend is 'elevenlabs'")
        if extension != "mp3":
            raise ValueError(
                "audio.extension must be 'mp3' when using the ElevenLabs backend "
                "(API returns MPEG audio for mp3_* output formats)."
            )
        if not el_format.lower().startswith("mp3"):
            raise ValueError(
                "voice.elevenlabs_output_format must start with 'mp3_' when audio.extension is 'mp3'"
            )

    return AnnouncerConfig(
        name=str(project.get("name", "Realistic OOTP Announcer")),
        game=str(project.get("game", "OOTP 27")),
        ootp=OotpSettings(
            root=_optional_path(ootp.get("root")),
            pronunciation_file=str(
                ootp.get("pronunciation_file", "data/misc/pronunciation.txt")
            ),
        ),
        voice=VoiceSettings(
            backend=backend,
            command_template=str(voice.get("command_template", "")),
            piper_binary=str(voice.get("piper_binary", "piper")),
            piper_model=_optional_path(voice.get("piper_model")),
            speaker_id=speaker_id,
            elevenlabs_voice_id=el_voice,
            elevenlabs_model_id=el_model or "eleven_multilingual_v2",
            elevenlabs_output_format=el_format or "mp3_44100_128",
            elevenlabs_stability=el_stab,
            elevenlabs_similarity_boost=el_sim,
            elevenlabs_style=el_style,
            elevenlabs_use_speaker_boost=el_boost,
            elevenlabs_api_key=el_key,
        ),
        audio=AudioSettings(extension=extension),
        build=BuildSettings(delay_seconds_after_each_line=delay),
    )


def default_config_text(ootp_root: Path | None = None) -> str:
    root_value = "" if ootp_root is None else str(ootp_root)
    return f"""[project]
name = "Realistic OOTP Announcer"
game = "OOTP 27"

[ootp]
# Fill this in with the OOTP install or data folder discovered on the game PC.
root = {_toml_string(root_value)}
pronunciation_file = "data/misc/pronunciation.txt"

[voice]
# Options: dry-run, piper, command, elevenlabs
backend = "dry-run"

# Piper backend settings.
piper_binary = "piper"
piper_model = ""
speaker_id = ""

# Generic command backend. The command must create {{output}}.
command_template = ""

# ElevenLabs (https://elevenlabs.io) — set ELEVENLABS_API_KEY in the environment,
# or put the key in elevenlabs_api_key here (never commit a real key).
# elevenlabs_voice_id = "YOUR_VOICE_ID"
# elevenlabs_model_id = "eleven_multilingual_v2"
# elevenlabs_output_format = "mp3_44100_128"
# elevenlabs_stability = 0.5
# elevenlabs_similarity_boost = 0.75
# elevenlabs_style = 0.25
# elevenlabs_use_speaker_boost = true
# elevenlabs_api_key = ""

[audio]
extension = "wav"

[build]
# Pause after each line (except the last). Useful for ElevenLabs rate limits.
delay_seconds_after_each_line = 0.0
"""


def _toml_string(value: str) -> str:
    return json.dumps(value)
