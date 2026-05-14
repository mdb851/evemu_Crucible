from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
import re


_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9_.-]+")


@dataclass(frozen=True)
class ScriptLine:
    cue_id: str
    text: str
    category: str
    filename: str


def sanitize_filename(value: str, extension: str) -> str:
    stem = _SAFE_FILENAME.sub("-", value.strip()).strip("-._").lower()
    if not stem:
        raise ValueError("Cannot build a filename from an empty value")
    suffix = extension if extension.startswith(".") else f".{extension}"
    return f"{stem}{suffix}"


def load_script(path: Path, extension: str) -> list[ScriptLine]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"id", "text"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise ValueError(f"Script is missing required column(s): {missing_text}")

        lines: list[ScriptLine] = []
        seen_ids: set[str] = set()
        for row_number, row in enumerate(reader, start=2):
            cue_id = (row.get("id") or "").strip()
            text = (row.get("text") or "").strip()
            if not cue_id:
                raise ValueError(f"Row {row_number} has an empty id")
            if not text:
                raise ValueError(f"Row {row_number} has empty text")
            if cue_id in seen_ids:
                raise ValueError(f"Duplicate cue id: {cue_id}")
            seen_ids.add(cue_id)

            filename = (row.get("filename") or "").strip()
            if not filename:
                filename = sanitize_filename(cue_id, extension)
            elif Path(filename).suffix == "":
                filename = sanitize_filename(filename, extension)

            lines.append(
                ScriptLine(
                    cue_id=cue_id,
                    text=text,
                    category=(row.get("category") or "general").strip() or "general",
                    filename=filename,
                )
            )

    return lines
