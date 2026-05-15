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


def find_pbp_language_html(install_root: Path) -> list[Path]:
    """Return likely play-by-play HTML files under an OOTP install root."""
    root = install_root.expanduser()
    if not root.is_dir():
        return []

    direct: list[Path] = []
    for rel in (
        Path("languages") / "English.html",
        Path("Languages") / "English.html",
        Path("languages") / "english.html",
        Path("Languages") / "english.html",
        Path("english.html"),
        Path("English.html"),
    ):
        p = root / rel
        if p.is_file():
            direct.append(p.resolve())

    if direct:
        return sorted(set(direct), key=lambda x: str(x).lower())

    found: list[Path] = []
    for name in ("English.html", "english.html"):
        for p in root.rglob(name):
            if p.is_file():
                found.append(p.resolve())
    return sorted(set(found), key=lambda x: str(x).lower())


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
