from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from .config import AnnouncerConfig
from .script import ScriptLine
from .tts import synthesize


def build_voice_pack(
    config: AnnouncerConfig,
    lines: list[ScriptLine],
    output_dir: Path,
    *,
    skip_existing: bool = False,
) -> Path:
    audio_dir = output_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    manifest_lines = []
    delay = config.build.delay_seconds_after_each_line
    for index, line in enumerate(lines):
        audio_path = audio_dir / line.filename
        skip = (
            skip_existing
            and audio_path.is_file()
            and audio_path.stat().st_size > 0
        )
        if not skip:
            synthesize(line.text, audio_path, config.voice)
        manifest_lines.append(
            {
                "id": line.cue_id,
                "category": line.category,
                "text": line.text,
                "audio": str(audio_path.relative_to(output_dir)),
            }
        )
        if delay > 0.0 and index + 1 < len(lines):
            time.sleep(delay)

    manifest = {
        "name": config.name,
        "game": config.game,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "voice_backend": config.voice.backend,
        "build": {
            "delay_seconds_after_each_line": config.build.delay_seconds_after_each_line,
        },
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
    return manifest_path
