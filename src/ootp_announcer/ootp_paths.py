from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class OotpPathCandidate:
    path: Path
    kind: str
    exists: bool


def _env_path(name: str) -> Path | None:
    value = os.environ.get(name)
    return Path(value).expanduser() if value else None


def _windows_candidates() -> list[tuple[Path, str]]:
    candidates: list[tuple[Path, str]] = []
    for env_name in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
        base = _env_path(env_name)
        if base is not None:
            candidates.extend(
                [
                    (base / "Out of the Park Developments" / "OOTP Baseball 27", "install"),
                    (base / "Steam" / "steamapps" / "common" / "OOTP Baseball 27", "steam"),
                ]
            )

    documents = _env_path("USERPROFILE")
    if documents is not None:
        candidates.append(
            (
                documents
                / "Documents"
                / "Out of the Park Developments"
                / "OOTP Baseball 27",
                "user-data",
            )
        )

    for env_name in ("LOCALAPPDATA", "APPDATA"):
        base = _env_path(env_name)
        if base is not None:
            candidates.append((base / "Out of the Park Developments" / "OOTP Baseball 27", "config"))

    return candidates


def _linux_candidates() -> list[tuple[Path, str]]:
    home = Path.home()
    return [
        (home / ".steam" / "steam" / "steamapps" / "common" / "OOTP Baseball 27", "steam"),
        (home / ".local" / "share" / "Steam" / "steamapps" / "common" / "OOTP Baseball 27", "steam"),
        (home / "Documents" / "Out of the Park Developments" / "OOTP Baseball 27", "user-data"),
    ]


def likely_candidates(extra_root: Path | None = None) -> list[OotpPathCandidate]:
    seen: set[Path] = set()
    raw = []
    if extra_root is not None:
        raw.append((extra_root.expanduser(), "provided"))
    raw.extend(_windows_candidates())
    raw.extend(_linux_candidates())

    candidates: list[OotpPathCandidate] = []
    for path, kind in raw:
        normalized = path.expanduser()
        if normalized in seen:
            continue
        seen.add(normalized)
        candidates.append(
            OotpPathCandidate(path=normalized, kind=kind, exists=normalized.exists())
        )
    return candidates
