from __future__ import annotations

import hashlib
import html as html_module
import re
from html.parser import HTMLParser
from pathlib import Path


_PLACEHOLDER_BRACES = re.compile(r"\{[^{}]+\}")
_PLACEHOLDER_PERCENT = re.compile(r"%[A-Za-z0-9_]+%")
_WS = re.compile(r"\s+")


class _VisibleTextCollector(HTMLParser):
    """Collect visible text chunks; ignore script/style."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self.chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in ("script", "style"):
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in ("script", "style") and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        chunk = data.strip()
        if chunk:
            self.chunks.append(chunk)


def _pbp_source_sort_key(path: Path) -> tuple[int, str]:
    """Prefer data/text language files, then language folders, then stable path order."""
    s = str(path).casefold()
    if "data" in s and "text" in s and "english" in s:
        return (0, s)
    if path.suffix.casefold() == ".xml" and "english" in path.name.casefold():
        return (1, s)
    if "language" in s or "\\lang\\" in s or "/lang/" in s or "languagetext" in s:
        return (2, s)
    if "localization" in s or "gamedata" in s:
        return (3, s)
    return (4, s)


def _name_is_exact_english_html(path: Path) -> bool:
    return path.is_file() and path.name.casefold() in ("english.html", "english.htm")


def _name_is_exact_english_xml(path: Path) -> bool:
    return path.is_file() and path.name.casefold() == "english.xml"


def _looks_like_ootp_english_xml(path: Path) -> bool:
    if not path.is_file() or path.suffix.casefold() != ".xml":
        return False
    low_name = path.name.casefold()
    low_full = str(path).casefold()
    if "english" not in low_name:
        return False
    hints = (
        "text",
        "language",
        "languagetext",
        "localization",
        "data",
        "gamedata",
        "pbp",
        "playbyplay",
    )
    return any(h in low_full for h in hints)


def _looks_like_ootp_pbp_english(path: Path) -> bool:
    """Heuristic when the game ships a nonstandard HTML filename."""
    if not path.is_file():
        return False
    low_name = path.name.casefold()
    low_full = str(path).casefold()
    if path.suffix.casefold() not in (".html", ".htm"):
        return False
    if "english" not in low_name:
        return False
    hints = (
        "language",
        "languagetext",
        "\\lang\\",
        "/lang/",
        "localization",
        "gamedata",
        "textdata",
        "pbp",
        "playbyplay",
        "commentary",
    )
    return any(h in low_full for h in hints)


def find_pbp_language_html(install_root: Path) -> list[Path]:
    """Return likely English PBP/UI markup files (.html, .htm, .xml) under an OOTP install root."""
    root = install_root.expanduser().resolve()
    if not root.is_dir():
        return []

    found: set[Path] = set()
    for rel in (
        Path("languages") / "English.html",
        Path("Languages") / "English.html",
        Path("languages") / "english.html",
        Path("Languages") / "english.html",
        Path("english.html"),
        Path("English.html"),
        Path("data") / "text" / "english.xml",
        Path("Data") / "Text" / "english.xml",
    ):
        p = root / rel
        if p.is_file():
            found.add(p.resolve())

    for pattern in ("*.html", "*.htm"):
        try:
            for p in root.rglob(pattern):
                if _name_is_exact_english_html(p):
                    found.add(p.resolve())
        except OSError:
            continue

    try:
        for p in root.rglob("*.xml"):
            if _name_is_exact_english_xml(p):
                found.add(p.resolve())
    except OSError:
        pass

    if not found:
        for pattern in ("*.html", "*.htm"):
            try:
                for p in root.rglob(pattern):
                    if _looks_like_ootp_pbp_english(p):
                        found.add(p.resolve())
            except OSError:
                continue

    if not found:
        try:
            for p in root.rglob("*.xml"):
                if _looks_like_ootp_english_xml(p):
                    found.add(p.resolve())
        except OSError:
            pass

    return sorted(found, key=_pbp_source_sort_key)


def suggest_html_files_for_verbose(install_root: Path, *, limit: int = 60) -> list[Path]:
    """List HTML/XML paths that may be language/PBP text (for troubleshooting)."""
    root = install_root.expanduser().resolve()
    if not root.is_dir():
        return []
    needles = (
        "english",
        "language",
        "languagetext",
        "localization",
        "pbp",
        "playbyplay",
        "commentary",
        "gamedata",
        "text",
    )
    out: list[Path] = []
    try:
        for pattern in ("*.html", "*.xml"):
            for p in root.rglob(pattern):
                if not p.is_file():
                    continue
                low = str(p).casefold()
                if any(n in low for n in needles):
                    out.append(p.resolve())
                    if len(out) >= limit:
                        return sorted(set(out), key=lambda x: str(x).casefold())
    except OSError:
        return out[:limit]
    return sorted(set(out), key=lambda x: str(x).casefold())


def _strip_markup_to_plain(raw: str) -> str:
    """Strip XML/HTML tags (and simple CDATA) for loose text extraction."""
    t = re.sub(r"(?is)<\?xml[^>]*\?>", " ", raw)
    t = re.sub(r"(?is)<!\[CDATA\[(.*?)\]\]>", r"\1", t)
    t = re.sub(r"(?is)<script.*?>.*?</script>", " ", t)
    t = re.sub(r"(?is)<style.*?>.*?</style>", " ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html_module.unescape(t)
    return _WS.sub(" ", t).strip()


def _flatten_placeholders(text: str) -> str:
    t = _PLACEHOLDER_BRACES.sub(" ", text)
    t = _PLACEHOLDER_PERCENT.sub(" ", t)
    return _WS.sub(" ", t).strip()


def _is_usable_phrase(
    text: str,
    *,
    min_chars: int,
    max_chars: int,
) -> bool:
    if "{" in text or "}" in text:
        return False
    if "%" in text and "_" in text:
        return False
    if len(text) < min_chars or len(text) > max_chars:
        return False
    if not re.search(r"[a-zA-Z]", text):
        return False
    if " " not in text:
        return False
    lowered = text.lower()
    if lowered in {"ok", "yes", "no", "save", "cancel", "close", "help"}:
        return False
    if text.isupper() and len(text) < 20:
        return False
    return True


def harvest_phrases_from_html(
    path: Path,
    *,
    min_chars: int = 24,
    max_chars: int = 320,
) -> list[str]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    collector = _VisibleTextCollector()
    if path.suffix.casefold() == ".xml":
        plain = _strip_markup_to_plain(raw)
        collector.chunks = [plain] if plain else []
    else:
        try:
            collector.feed(raw)
            collector.close()
        except Exception:
            collector = _VisibleTextCollector()
            stripped = re.sub(r"(?is)<script.*?>.*?</script>", " ", raw)
            stripped = re.sub(r"(?is)<style.*?>.*?</style>", " ", stripped)
            stripped = re.sub(r"<[^>]+>", " ", stripped)
            collector.chunks = [c.strip() for c in _WS.split(stripped) if c.strip()]

    phrases: list[str] = []
    for chunk in collector.chunks:
        piece = html_module.unescape(chunk)
        piece = _flatten_placeholders(piece)
        piece = _WS.sub(" ", piece).strip()
        if not piece:
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", piece):
            s = sentence.strip()
            if _is_usable_phrase(s, min_chars=min_chars, max_chars=max_chars):
                phrases.append(s)
    return phrases


def phrases_to_csv_rows(phrases: list[str]) -> list[tuple[str, str, str]]:
    """Return (id, category, text) rows with stable ids from phrase text."""
    seen: set[str] = set()
    rows: list[tuple[str, str, str]] = []
    for text in phrases:
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        hid = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
        rows.append((f"pbp_{hid}", "harvested_pbp", text))
    return rows


def write_harvest_csv(
    rows: list[tuple[str, str, str]],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ["id,category,text"]
    for cue_id, category, text in rows:
        escaped = text.replace('"', '""')
        if any(c in text for c in (",", '"', "\n", "\r")):
            field = f'"{escaped}"'
        else:
            field = text
        lines.append(f"{cue_id},{category},{field}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
