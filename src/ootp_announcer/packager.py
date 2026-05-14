from __future__ import annotations

from pathlib import Path
import zipfile


def write_install_notes(voice_pack_dir: Path) -> Path:
    manifest = voice_pack_dir / "manifest.json"
    notes = voice_pack_dir / "INSTALL.md"
    notes.write_text(
        "# OOTP Announcer Voice Pack\n\n"
        "This folder contains generated announcer assets.\n\n"
        "## Contents\n\n"
        "- `manifest.json`: cue IDs, text, and generated audio paths\n"
        "- `script-lines.json`: source line snapshot used for the build\n"
        "- `audio/`: generated audio files\n\n"
        "## Local integration checklist\n\n"
        "1. Run `ootp-announcer inspect --ootp-root \"PATH_TO_OOTP\" --out ootp-report.md`.\n"
        "2. Review the report for play-by-play, pronunciation, audio, and mod folders.\n"
        "3. Back up any OOTP file before editing it.\n"
        "4. Copy or reference files from `audio/` only after confirming the target folder.\n\n"
        f"Manifest present: `{manifest.exists()}`\n",
        encoding="utf-8",
    )
    return notes


def create_zip_package(voice_pack_dir: Path, output_zip: Path) -> Path:
    if not voice_pack_dir.exists():
        raise FileNotFoundError(f"Voice pack directory not found: {voice_pack_dir}")

    write_install_notes(voice_pack_dir)
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(voice_pack_dir.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(voice_pack_dir))
    return output_zip
