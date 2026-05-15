from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

from .config import default_config_text, load_config
from .generator import build_voice_pack
from .ootp_paths import likely_candidates
from .script import load_script
from .tts import (
    TtsError,
    describe_elevenlabs_api_key_source,
    fetch_elevenlabs_user_json,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ootp-announcer",
        description="Build a realistic announcer voice pack for OOTP 27.",
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
    manifest = build_voice_pack(config, lines, args.out)
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


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
