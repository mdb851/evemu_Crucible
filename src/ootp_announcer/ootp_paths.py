from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re
from pathlib import Path


@dataclass(frozen=True)
class OotpPathCandidate:
    path: Path
    kind: str
    exists: bool


def _env_path(name: str) -> Path | None:
    value = os.environ.get(name)
    return Path(value).expanduser() if value else None


# Steam / installs use the long folder name; some docs and older paths use the short name.
_OOTP_27_INSTALL_FOLDER_NAMES: tuple[str, ...] = (
    "Out of the Park Baseball 27",
    "OOTP Baseball 27",
)


_STEAM_VDF_PATH_KEY = re.compile(r'"path"\s+"([^"]*)"')


def library_roots_from_steam_libraryfolders_vdf(text: str) -> list[Path]:
    """
    Parse Steam config steamapps/libraryfolders.vdf (KeyValues or JSON) and
    return each library root (folder that contains a steamapps subdirectory).
    """
    raw_text = text.lstrip("\ufeff").strip()
    roots: list[Path] = []

    if raw_text.startswith("{"):
        try:
            blob = json.loads(raw_text)
        except json.JSONDecodeError:
            blob = None
        if isinstance(blob, dict):
            for v in blob.values():
                if isinstance(v, dict):
                    p = v.get("path")
                    if isinstance(p, str) and p.strip():
                        roots.append(Path(p))

    if not roots:
        for m in _STEAM_VDF_PATH_KEY.finditer(text):
            inner = (m.group(1) or "").replace("\\\\", "\\").replace("/", "\\").strip()
            if inner:
                roots.append(Path(inner))

    seen: set[str] = set()
    uniq: list[Path] = []
    for p in roots:
        key = str(p).casefold()
        if key in seen:
            continue
        seen.add(key)
        uniq.append(p)
    return uniq


def _steam_client_roots_windows() -> list[Path]:
    roots: list[Path] = []
    for base in (_env_path("PROGRAMFILES"), _env_path("PROGRAMFILES(X86)")):
        if base is None:
            continue
        steam = base / "Steam"
        if steam.is_dir():
            roots.append(steam)
    return sorted(set(roots), key=lambda p: str(p).casefold())


def _windows_steam_library_ootp_candidates() -> list[tuple[Path, str]]:
    """Extra Steam library disks (from libraryfolders.vdf) → OOTP 27 common path."""
    out: list[tuple[Path, str]] = []
    for steam in _steam_client_roots_windows():
        vdf = steam / "steamapps" / "libraryfolders.vdf"
        if not vdf.is_file():
            continue
        try:
            text = vdf.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lib_root in library_roots_from_steam_libraryfolders_vdf(text):
            for game_name in _OOTP_27_INSTALL_FOLDER_NAMES:
                game = lib_root / "steamapps" / "common" / game_name
                out.append((game, "steam-library"))
    return out


def _windows_candidates() -> list[tuple[Path, str]]:
    candidates: list[tuple[Path, str]] = []
    for env_name in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
        base = _env_path(env_name)
        if base is None:
            continue
        for game_name in _OOTP_27_INSTALL_FOLDER_NAMES:
            candidates.append((base / "Out of the Park Developments" / game_name, "install"))
            candidates.append((base / "Steam" / "steamapps" / "common" / game_name, "steam"))

    documents = _env_path("USERPROFILE")
    if documents is not None:
        for game_name in _OOTP_27_INSTALL_FOLDER_NAMES:
            candidates.append(
                (
                    documents
                    / "Documents"
                    / "Out of the Park Developments"
                    / game_name,
                    "user-data",
                )
            )

    for env_name in ("LOCALAPPDATA", "APPDATA"):
        base = _env_path(env_name)
        if base is None:
            continue
        for game_name in _OOTP_27_INSTALL_FOLDER_NAMES:
            candidates.append((base / "Out of the Park Developments" / game_name, "config"))

    return candidates


def _linux_candidates() -> list[tuple[Path, str]]:
    home = Path.home()
    out: list[tuple[Path, str]] = []
    for game_name in _OOTP_27_INSTALL_FOLDER_NAMES:
        out.extend(
            [
                (home / ".steam" / "steam" / "steamapps" / "common" / game_name, "steam"),
                (home / ".local" / "share" / "Steam" / "steamapps" / "common" / game_name, "steam"),
            ]
        )
    for game_name in _OOTP_27_INSTALL_FOLDER_NAMES:
        out.append(
            (
                home / "Documents" / "Out of the Park Developments" / game_name,
                "user-data",
            )
        )
    return out


def likely_candidates(extra_root: Path | None = None) -> list[OotpPathCandidate]:
    seen: set[Path] = set()
    raw = []
    if extra_root is not None:
        raw.append((extra_root.expanduser(), "provided"))
    raw.extend(_windows_candidates())
    raw.extend(_windows_steam_library_ootp_candidates())
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
