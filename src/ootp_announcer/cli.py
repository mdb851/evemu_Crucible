from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

from .config import default_config_text, load_config
from .generator import build_voice_pack
from .ootp_paths import likely_candidates
from .ootp_sound_export import SoundExportError, export_sounds
from .pbp_harvest import (
    find_pbp_language_html,
    harvest_phrases_from_html,
    phrases_to_csv_rows,
    suggest_html_files_for_verbose,
    write_harvest_csv,
)
from .script import load_script
from .tts import (
    TtsError,
    describe_elevenlabs_api_key_source,
    fetch_elevenlabs_user_json,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ootp27-announcer",
        description="OOTP 27 Realistic Announcer — build voice packs from CSV (Piper, ElevenLabs, or custom TTS).",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    discover = subcommands.add_parser("discover", help="Show likely OOTP 27 folders")
    discover.add_argument("--ootp-root", type=Path, help="Additional folder to check")
    discover.set_defaults(func=_discover)

    init_config = subcommands.add_parser("init-config", help="Write a starter TOML config")
    init_config.add_argument("--output", type=Path, default=Path("announcer.toml"))
    init_config.add_argument("--ootp-root", type=Path)
    init_config.add_argument("--force", action="store_true", help="Overwrite an existing config")
    init_config.set_defaults(func=_init_config)

    build = subcommands.add_parser("build", help="Generate an announcer voice pack")
    build.add_argument("--config", type=Path, default=Path("announcer.toml"))
    build.add_argument("--script", type=Path, required=True)
    build.add_argument("--out", type=Path, default=Path("voice-pack"))
    build.add_argument(
        "--max-lines",
        type=int,
        default=None,
        metavar="N",
        help="Only generate the first N lines (quick test / save time and credits)",
    )
    build.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip lines whose output audio file already exists and is non-empty (resume after errors or quota)",
    )
    build.set_defaults(func=_build)

    verify = subcommands.add_parser(
        "verify-elevenlabs",
        help="Check that your ElevenLabs API key works (no audio generated)",
    )
    verify.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Optional TOML: read key from voice.elevenlabs_api_key if env/file unset (ELEVENLABS_API_KEY_FILE then ELEVENLABS_API_KEY win)",
    )
    verify.set_defaults(func=_verify_elevenlabs)

    harvest = subcommands.add_parser(
        "harvest-pbp",
        help="Extract candidate phrases from OOTP English markup (HTML or XML)",
    )
    harvest.add_argument(
        "--ootp-root",
        type=Path,
        default=None,
        help="OOTP 27 install folder, or a single .html/.htm/.xml file (e.g. data\\text\\english.xml)",
    )
    harvest.add_argument(
        "--out",
        type=Path,
        default=Path("build/harvested-pbp-lines.csv"),
        help="Output CSV (id, category, text) for merging into a voice script",
    )
    harvest.add_argument(
        "--min-chars",
        type=int,
        default=24,
        metavar="N",
        help="Drop very short snippets (UI labels, numbers)",
    )
    harvest.add_argument(
        "--max-chars",
        type=int,
        default=320,
        metavar="N",
        help="Drop very long blocks; split sentences already applied inside each HTML chunk",
    )
    harvest.add_argument(
        "--html-file",
        type=Path,
        action="append",
        default=None,
        metavar="PATH",
        help="Use this .html, .htm, or .xml file directly (repeat for multiple). Use when auto-discovery fails.",
    )
    harvest.add_argument(
        "--verbose",
        action="store_true",
        help="If discovery fails, print candidate HTML/XML paths under --ootp-root",
    )
    harvest.set_defaults(func=_harvest_pbp)

    export_sounds_cmd = subcommands.add_parser(
        "export-ootp-sounds",
        help="Copy or convert manifest cues into OOTP data/sounds-style .wav files (see docs/INTEGRATION.md)",
    )
    export_sounds_cmd.add_argument(
        "--voice-pack",
        type=Path,
        required=True,
        help="Directory that contains manifest.json and an audio/ subfolder",
    )
    export_sounds_cmd.add_argument(
        "--map",
        type=Path,
        required=True,
        help="TOML file with [[map]] rows: cue_id + ootp_filename (basename without .wav)",
    )
    export_sounds_cmd.add_argument(
        "--dest",
        type=Path,
        required=True,
        help="Output folder (use a staging path first; back up the game's sounds folder)",
    )
    export_sounds_cmd.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned copies/conversions without writing files",
    )
    export_sounds_cmd.add_argument(
        "--ffmpeg",
        default="ffmpeg",
        metavar="EXE",
        help="ffmpeg executable name when converting MP3 sources (default: ffmpeg)",
    )
    export_sounds_cmd.set_defaults(func=_export_ootp_sounds)

    return parser


def _discover(args: argparse.Namespace) -> int:
    candidates = likely_candidates(args.ootp_root)
    for candidate in candidates:
        marker = "FOUND" if candidate.exists else "missing"
        print(f"{marker:7} {candidate.kind:10} {candidate.path}")
    return 0


def _init_config(args: argparse.Namespace) -> int:
    if args.output.exists() and not args.force:
        print(f"{args.output} already exists; use --force to overwrite", file=sys.stderr)
        return 2
    args.output.write_text(default_config_text(args.ootp_root), encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


def _build(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    lines = load_script(args.script, config.audio.extension)
    if args.max_lines is not None:
        if args.max_lines < 1:
            print("--max-lines must be at least 1", file=sys.stderr)
            return 2
        lines = lines[: args.max_lines]
    manifest = build_voice_pack(
        config,
        lines,
        args.out,
        skip_existing=args.skip_existing,
    )
    print(f"Generated {len(lines)} line(s)")
    print(f"Manifest: {manifest}")
    return 0


def _verify_elevenlabs(args: argparse.Namespace) -> int:
    if args.config is not None:
        voice = load_config(args.config).voice
        key, source = describe_elevenlabs_api_key_source(voice)
        if source.startswith("voice."):
            source = f"{source} ({args.config})"
        elif source:
            source = f"{source} (overrides TOML from {args.config})"
    else:
        key, source = describe_elevenlabs_api_key_source(None)

    if not key:
        print(
            "No API key found. Set ELEVENLABS_API_KEY in this PowerShell window, "
            "or ELEVENLABS_API_KEY_FILE to a path containing the key on one line, "
            "or run with --config path\\to\\announcer.toml that contains voice.elevenlabs_api_key.",
            file=sys.stderr,
        )
        return 2

    try:
        user = fetch_elevenlabs_user_json(key)
    except TtsError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print("ElevenLabs accepted your API key.")
    print(f"Key source checked: {source}")
    print(f"Key length after cleanup: {len(key)} characters")
    sub = user.get("subscription")
    if isinstance(sub, dict):
        tier = sub.get("tier", sub.get("tier_display_name", "?"))
        print(f"Subscription info from API: tier = {tier!r}")
    return 0


def _harvest_pbp(args: argparse.Namespace) -> int:
    if args.min_chars < 1 or args.max_chars < args.min_chars:
        print("--min-chars must be >= 1 and --max-chars must be >= --min-chars", file=sys.stderr)
        return 2

    all_files: list[Path] = []
    html_files: list[Path] = list(args.html_file or [])

    if html_files:
        for f in html_files:
            p = f.expanduser()
            if p.is_file():
                all_files.append(p.resolve())
            else:
                print(f"Not a file: {p}", file=sys.stderr)
        all_files = sorted(set(all_files), key=lambda x: str(x).casefold())
        if not all_files:
            print(
                "No valid --html-file paths. In Explorer, search the OOTP install folder for "
                "english.xml (under data\\text) or English.html, then pass the full path.",
                file=sys.stderr,
            )
            return 2
    else:
        ootp_arg = args.ootp_root.expanduser() if args.ootp_root is not None else None

        if ootp_arg is not None:
            if not ootp_arg.exists():
                print(
                    f"Path does not exist: {ootp_arg}\n"
                    "In PowerShell prefer single quotes around paths with (x86) or spaces, e.g. "
                    r"--ootp-root 'C:\Program Files (x86)\Steam\steamapps\common\Out of the Park Baseball 27'",
                    file=sys.stderr,
                )
                return 2
            if ootp_arg.is_file():
                suf = ootp_arg.suffix.casefold()
                if suf in (".html", ".htm", ".xml"):
                    all_files = [ootp_arg.resolve()]
                else:
                    print(
                        f"Unsupported file type {ootp_arg.suffix!r}: use .html, .htm, or .xml, "
                        "or pass the game install folder.",
                        file=sys.stderr,
                    )
                    return 2
            else:
                roots = [ootp_arg]
                for root in roots:
                    r = root.expanduser().resolve()
                    if r.is_dir():
                        all_files.extend(find_pbp_language_html(r))
                all_files = sorted(set(all_files), key=lambda x: str(x).casefold())
        else:
            roots = [c.path for c in likely_candidates(None) if c.exists]
            for root in roots:
                r = root.expanduser().resolve()
                if r.is_dir():
                    all_files.extend(find_pbp_language_html(r))
            all_files = sorted(set(all_files), key=lambda x: str(x).casefold())

        if not all_files:
            if args.ootp_root is not None:
                root = args.ootp_root.expanduser()
                if root.is_dir():
                    if args.verbose:
                        hints = suggest_html_files_for_verbose(root)
                        if hints:
                            print("HTML/XML files that might be language/PBP (first batch):", file=sys.stderr)
                            for h in hints:
                                print(f"  {h}", file=sys.stderr)
                        else:
                            print(
                                f"No matching *.html / english.xml under {root.resolve()}. "
                                "Is this the full game folder (not a shortcut)?",
                                file=sys.stderr,
                            )
                    else:
                        print(
                            f"No English.html or english.xml under {root.resolve()}. "
                            "Re-run with --verbose to list candidates, or pass --html-file with a full path.",
                            file=sys.stderr,
                        )
            else:
                print(
                    "No English markup found under known paths. Install OOTP 27, run "
                    "`python -m ootp_announcer discover`, then pass --ootp-root to a FOUND folder. "
                    "Steam often uses 'Out of the Park Baseball 27' under steamapps\\common. "
                    "Use single quotes in PowerShell for paths that contain (x86). "
                    "You can also pass --html-file with the path to data\\text\\english.xml.",
                    file=sys.stderr,
                )
            return 2

    dedupe_text: set[str] = set()
    rows: list[tuple[str, str, str]] = []
    for html_path in all_files:
        phrases = harvest_phrases_from_html(
            html_path,
            min_chars=args.min_chars,
            max_chars=args.max_chars,
        )
        for row in phrases_to_csv_rows(phrases):
            text_key = row[2].casefold()
            if text_key in dedupe_text:
                continue
            dedupe_text.add(text_key)
            rows.append(row)

    if not rows:
        print(
            "Parsed markup but found no usable phrases. Try lowering --min-chars (e.g. 12).",
            file=sys.stderr,
        )
        return 3

    write_harvest_csv(rows, args.out)
    print(f"Sources ({len(all_files)} file(s)):")
    for path in all_files:
        print(f"  {path}")
    print(f"Wrote {len(rows)} unique phrase(s) to {args.out}")
    print("Merge or cherry-pick rows into your script CSV, then run build.")
    return 0


def _export_ootp_sounds(args: argparse.Namespace) -> int:
    try:
        lines = export_sounds(
            args.voice_pack.expanduser().resolve(),
            args.map.expanduser().resolve(),
            args.dest.expanduser().resolve(),
            dry_run=bool(args.dry_run),
            ffmpeg_exe=str(args.ffmpeg),
        )
    except SoundExportError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    for line in lines:
        print(line)
    return 0


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) == 1 and argv[0] in ("--version", "-V"):
        from . import __version__

        print(f"ootp27-announcer {__version__}")
        return 0

    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
