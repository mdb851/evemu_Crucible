from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


INTERESTING_EXTENSIONS = {
    ".cfg",
    ".csv",
    ".dat",
    ".ini",
    ".json",
    ".mp3",
    ".ogg",
    ".txt",
    ".wav",
    ".xml",
}

SKIP_DIRECTORIES = {
    "__pycache__",
    ".git",
    ".pytest_cache",
    "cache",
    "debug",
    "logs",
    "saved_games",
    "temp",
    "tmp",
}


@dataclass(frozen=True)
class FileFinding:
    path: Path
    relative_path: str
    kind: str
    size_bytes: int


@dataclass(frozen=True)
class FolderFinding:
    path: Path
    relative_path: str
    kind: str


@dataclass(frozen=True)
class InspectionReport:
    root: Path
    exists: bool
    files: list[FileFinding]
    folders: list[FolderFinding]
    skipped_directories: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "root": str(self.root),
            "exists": self.exists,
            "files": [
                {
                    "path": str(finding.path),
                    "relative_path": finding.relative_path,
                    "kind": finding.kind,
                    "size_bytes": finding.size_bytes,
                }
                for finding in self.files
            ],
            "folders": [
                {
                    "path": str(finding.path),
                    "relative_path": finding.relative_path,
                    "kind": finding.kind,
                }
                for finding in self.folders
            ],
            "skipped_directories": self.skipped_directories,
        }


def inspect_ootp_root(root: Path, max_files: int = 5000) -> InspectionReport:
    expanded = root.expanduser()
    if not expanded.exists():
        return InspectionReport(
            root=expanded,
            exists=False,
            files=[],
            folders=[],
            skipped_directories=[],
        )

    files: list[FileFinding] = []
    folders: list[FolderFinding] = []
    skipped: set[str] = set()
    visited = 0

    for current, dirnames, filenames in _walk(expanded):
        relative_current = _relative(current, expanded)
        for dirname in sorted(list(dirnames)):
            child = current / dirname
            child_relative = _relative(child, expanded)
            folder_kind = classify_folder(child_relative)
            if folder_kind:
                folders.append(
                    FolderFinding(path=child, relative_path=child_relative, kind=folder_kind)
                )

            if dirname.lower() in SKIP_DIRECTORIES:
                dirnames.remove(dirname)
                skipped.add(child_relative)

        for filename in sorted(filenames):
            if visited >= max_files:
                skipped.add(f"{relative_current}/... (max file scan reached)")
                return InspectionReport(
                    root=expanded,
                    exists=True,
                    files=files,
                    folders=folders,
                    skipped_directories=sorted(skipped),
                )

            path = current / filename
            visited += 1
            if path.suffix.lower() not in INTERESTING_EXTENSIONS:
                continue

            relative = _relative(path, expanded)
            kind = classify_file(relative)
            if not kind:
                continue
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            files.append(
                FileFinding(path=path, relative_path=relative, kind=kind, size_bytes=size)
            )

    return InspectionReport(
        root=expanded,
        exists=True,
        files=files,
        folders=folders,
        skipped_directories=sorted(skipped),
    )


def classify_file(relative_path: str) -> str | None:
    normalized = relative_path.replace("\\", "/").lower()
    name = Path(normalized).name

    if name == "app.cfg":
        return "game config"
    if "pronunciation" in normalized:
        return "pronunciation"
    if "play_by_play" in normalized or "/pbp" in normalized or name.startswith("pbp"):
        return "play-by-play"
    if "commentary" in normalized or "announcer" in normalized:
        return "announcer text"
    if normalized.endswith((".wav", ".mp3", ".ogg")):
        if any(token in normalized for token in ("sound", "audio", "voice", "media")):
            return "audio asset"
    if "/data/" in normalized and normalized.endswith((".xml", ".txt", ".csv", ".dat")):
        return "game data"
    if normalized.endswith((".cfg", ".ini", ".json")):
        return "configuration"
    return None


def classify_folder(relative_path: str) -> str | None:
    normalized = relative_path.replace("\\", "/").lower()
    name = Path(normalized).name
    if name in {"sounds", "sound", "audio", "voice", "voices"}:
        return "audio folder"
    if name in {"mods", "addons", "workshop"}:
        return "mod folder"
    if "play_by_play" in normalized or name == "pbp":
        return "play-by-play folder"
    if name == "misc":
        return "misc data folder"
    if name == "data":
        return "game data folder"
    return None


def write_markdown_report(report: InspectionReport, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_markdown_report(report), encoding="utf-8")


def write_json_report(report: InspectionReport, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")


def render_markdown_report(report: InspectionReport) -> str:
    lines = [
        "# OOTP 27 Announcer Inspection Report",
        "",
        f"- Root: `{report.root}`",
        f"- Exists: `{report.exists}`",
        f"- Matching folders: `{len(report.folders)}`",
        f"- Matching files: `{len(report.files)}`",
        "",
    ]

    if not report.exists:
        lines.extend(
            [
                "The folder does not exist on this machine.",
                "",
                "Run `ootp-announcer discover` on the game PC and retry with an existing path.",
                "",
            ]
        )
        return "\n".join(lines)

    lines.extend(["## Candidate folders", ""])
    if report.folders:
        lines.extend(["| kind | path |", "| --- | --- |"])
        for folder in report.folders:
            lines.append(f"| {folder.kind} | `{folder.relative_path}` |")
    else:
        lines.append("No candidate folders found.")

    lines.extend(["", "## Candidate files", ""])
    if report.files:
        lines.extend(["| kind | size | path |", "| --- | ---: | --- |"])
        for finding in report.files:
            lines.append(
                f"| {finding.kind} | {finding.size_bytes} | `{finding.relative_path}` |"
            )
    else:
        lines.append("No candidate files found.")

    if report.skipped_directories:
        lines.extend(["", "## Skipped directories", ""])
        for skipped in report.skipped_directories:
            lines.append(f"- `{skipped}`")

    lines.extend(
        [
            "",
            "## Suggested next step",
            "",
            "Review the pronunciation, play-by-play, audio, and mod folder candidates above.",
            "Use the generated voice pack manifest to decide whether OOTP can reference audio",
            "assets directly or whether the game's play-by-play text should be rewritten to",
            "route through an external announcer tool.",
            "",
        ]
    )
    return "\n".join(lines)


def _walk(root: Path):
    import os

    for current, dirnames, filenames in os.walk(root):
        yield Path(current), dirnames, filenames


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()
