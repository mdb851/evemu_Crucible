from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from shutil import which


class SoundExportError(RuntimeError):
    """Raised when OOTP sound export cannot complete."""


def load_manifest(voice_pack_dir: Path) -> dict[str, object]:
    path = voice_pack_dir / "manifest.json"
    if not path.is_file():
        raise SoundExportError(f"manifest.json not found under {voice_pack_dir}")
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SoundExportError(f"Invalid JSON in {path}") from exc
    if not isinstance(blob, dict):
        raise SoundExportError("manifest.json must contain a JSON object")
    return blob


def manifest_id_to_source_audio(voice_pack_dir: Path, manifest: dict[str, object]) -> dict[str, Path]:
    lines = manifest.get("lines")
    if not isinstance(lines, list):
        return {}
    out: dict[str, Path] = {}
    for row in lines:
        if not isinstance(row, dict):
            continue
        cid = row.get("id")
        rel = row.get("audio")
        if not isinstance(cid, str) or not isinstance(rel, str):
            continue
        src = (voice_pack_dir / rel).resolve()
        out[cid] = src
    return out


def load_export_map(path: Path) -> list[tuple[str, str]]:
    """Load [[map]] entries: cue_id -> OOTP sounds filename without extension."""
    import tomllib

    raw = path.read_bytes()
    try:
        data = tomllib.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise SoundExportError(f"Could not read map TOML {path}: {exc}") from exc

    entries: list[tuple[str, str]] = []
    for key in ("map", "export"):
        block = data.get(key)
        if isinstance(block, list):
            for item in block:
                if not isinstance(item, dict):
                    continue
                cue = item.get("cue_id")
                name = item.get("ootp_filename") or item.get("filename")
                if isinstance(cue, str) and isinstance(name, str) and cue.strip() and name.strip():
                    entries.append((cue.strip(), name.strip()))
    if not entries:
        raise SoundExportError(
            f"No [[map]] or [[export]] entries in {path}. "
            "Each row needs cue_id and ootp_filename (or filename)."
        )
    return entries


def _convert_mp3_to_wav(mp3: Path, wav: Path, *, ffmpeg_exe: str) -> None:
    exe = which(ffmpeg_exe) or which(f"{ffmpeg_exe}.exe")
    if not exe:
        raise SoundExportError(
            "Source is MP3 but ffmpeg was not found on PATH. "
            "Install ffmpeg, add it to PATH, or convert files to WAV manually."
        )
    wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [exe, "-hide_banner", "-loglevel", "error", "-y", "-i", str(mp3), str(wav)]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        raise SoundExportError(
            f"ffmpeg failed converting {mp3} -> {wav}: {exc.stderr or exc.stdout or exc}"
        ) from exc


def export_sounds(
    voice_pack_dir: Path,
    map_path: Path,
    dest_dir: Path,
    *,
    dry_run: bool = False,
    ffmpeg_exe: str = "ffmpeg",
) -> list[str]:
    """
    Copy or convert manifest cues into OOTP-style .wav files under dest_dir.
    Returns log lines (for CLI output).
    """
    manifest = load_manifest(voice_pack_dir)
    id_to_src = manifest_id_to_source_audio(voice_pack_dir, manifest)
    mappings = load_export_map(map_path)
    dest_dir = dest_dir.expanduser().resolve()
    if not dry_run:
        dest_dir.mkdir(parents=True, exist_ok=True)

    log: list[str] = []
    for cue_id, basename in mappings:
        src = id_to_src.get(cue_id)
        if src is None:
            log.append(f"skip  {cue_id}: not in manifest")
            continue
        if not src.is_file():
            log.append(f"skip  {cue_id}: missing file {src}")
            continue

        dest_wav = dest_dir / f"{basename}.wav"
        suf = src.suffix.lower()
        if dry_run:
            log.append(f"would {src.name} -> {dest_wav.name}  (cue {cue_id})")
            continue

        if suf == ".wav":
            shutil.copy2(src, dest_wav)
            log.append(f"copy  {cue_id} -> {dest_wav.name}")
        elif suf == ".mp3":
            _convert_mp3_to_wav(src, dest_wav, ffmpeg_exe=ffmpeg_exe)
            log.append(f"ffmpeg {cue_id} -> {dest_wav.name}")
        else:
            raise SoundExportError(
                f"Unsupported audio extension {src.suffix!r} for cue {cue_id}; use .wav or .mp3"
            )
    return log
