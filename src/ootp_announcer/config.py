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


@dataclass(frozen=True)
class AudioSettings:
    extension: str


@dataclass(frozen=True)
class AnnouncerConfig:
    name: str
    game: str
    ootp: OotpSettings
    voice: VoiceSettings
    audio: AudioSettings


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

    backend = str(voice.get("backend", "dry-run")).strip().lower()
    if backend not in {"dry-run", "piper", "command"}:
        raise ValueError(f"Unsupported voice backend: {backend}")

    speaker_value = voice.get("speaker_id")
    speaker_text = "" if speaker_value is None else str(speaker_value).strip()
    speaker_id = int(speaker_text) if speaker_text else None

    extension = str(audio.get("extension", "wav")).strip().lstrip(".").lower()
    if not extension:
        raise ValueError("audio.extension must not be empty")

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
        ),
        audio=AudioSettings(extension=extension),
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
# Options: dry-run, piper, command
backend = "dry-run"

# Piper backend settings.
piper_binary = "piper"
piper_model = ""
speaker_id = ""

# Generic command backend. The command must create {{output}}.
command_template = ""

[audio]
extension = "wav"
"""


def _toml_string(value: str) -> str:
    return json.dumps(value)
