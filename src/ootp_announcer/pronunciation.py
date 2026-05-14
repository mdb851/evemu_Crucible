from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
import re

from .script import ScriptLine


@dataclass(frozen=True)
class PronunciationRule:
    term: str
    replacement: str
    notes: str = ""


@dataclass(frozen=True)
class PronunciationChange:
    cue_id: str
    term: str
    replacement: str


def load_pronunciations(path: Path) -> list[PronunciationRule]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"term", "replacement"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise ValueError(f"Pronunciation lexicon is missing required column(s): {missing_text}")

        rules: list[PronunciationRule] = []
        seen: set[str] = set()
        for row_number, row in enumerate(reader, start=2):
            term = (row.get("term") or "").strip()
            replacement = (row.get("replacement") or "").strip()
            if not term:
                raise ValueError(f"Row {row_number} has an empty term")
            if not replacement:
                raise ValueError(f"Row {row_number} has an empty replacement")
            key = term.casefold()
            if key in seen:
                raise ValueError(f"Duplicate pronunciation term: {term}")
            seen.add(key)
            rules.append(
                PronunciationRule(
                    term=term,
                    replacement=replacement,
                    notes=(row.get("notes") or "").strip(),
                )
            )

    return sorted(rules, key=lambda rule: len(rule.term), reverse=True)


def apply_pronunciations(
    lines: list[ScriptLine],
    rules: list[PronunciationRule],
) -> tuple[list[ScriptLine], list[PronunciationChange]]:
    prepared: list[ScriptLine] = []
    changes: list[PronunciationChange] = []

    for line in lines:
        text = line.text
        for rule in rules:
            text, count = _replace_term(text, rule)
            if count:
                changes.extend(
                    PronunciationChange(
                        cue_id=line.cue_id,
                        term=rule.term,
                        replacement=rule.replacement,
                    )
                    for _ in range(count)
                )

        prepared.append(
            ScriptLine(
                cue_id=line.cue_id,
                text=text,
                category=line.category,
                filename=line.filename,
            )
        )

    return prepared, changes


def write_prepared_script(
    original: list[ScriptLine],
    prepared: list[ScriptLine],
    output: Path,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["id", "category", "text", "filename", "original_text"],
        )
        writer.writeheader()
        for original_line, prepared_line in zip(original, prepared, strict=True):
            writer.writerow(
                {
                    "id": prepared_line.cue_id,
                    "category": prepared_line.category,
                    "text": prepared_line.text,
                    "filename": prepared_line.filename,
                    "original_text": original_line.text,
                }
            )


def render_pronunciation_report(changes: list[PronunciationChange]) -> str:
    lines = ["Pronunciation preparation report", ""]
    if not changes:
        lines.append("No pronunciation replacements were applied.")
        return "\n".join(lines)

    counts: dict[tuple[str, str], int] = {}
    for change in changes:
        key = (change.term, change.replacement)
        counts[key] = counts.get(key, 0) + 1

    lines.extend(["| term | replacement | count |", "| --- | --- | ---: |"])
    for (term, replacement), count in sorted(counts.items()):
        lines.append(f"| {term} | {replacement} | {count} |")
    return "\n".join(lines)


def _replace_term(text: str, rule: PronunciationRule) -> tuple[str, int]:
    pattern = re.compile(
        rf"(?<![A-Za-z0-9]){re.escape(rule.term)}(?![A-Za-z0-9])",
        flags=re.IGNORECASE,
    )
    return pattern.subn(rule.replacement, text)
