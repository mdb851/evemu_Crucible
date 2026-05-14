from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path

from .config import AnnouncerConfig
from .packager import write_install_notes
from .script import ScriptLine
from .tts import synthesize


def build_voice_pack(
    config: AnnouncerConfig,
    lines: list[ScriptLine],
    output_dir: Path,
) -> Path:
    audio_dir = output_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    manifest_lines = []
    for line in lines:
        audio_path = audio_dir / line.filename
        synthesize(line.text, audio_path, config.voice)
        manifest_lines.append(
            {
                "id": line.cue_id,
                "category": line.category,
                "text": line.text,
                "audio": str(audio_path.relative_to(output_dir)),
            }
        )

    manifest = {
        "name": config.name,
        "game": config.game,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "voice_backend": config.voice.backend,
        "ootp": {
            "root": str(config.ootp.root) if config.ootp.root else "",
            "pronunciation_file": config.ootp.pronunciation_file,
        },
        "lines": manifest_lines,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    script_snapshot = output_dir / "script-lines.json"
    script_snapshot.write_text(
        json.dumps([asdict(line) for line in lines], indent=2),
        encoding="utf-8",
    )
    write_install_notes(output_dir)
    return manifest_path
