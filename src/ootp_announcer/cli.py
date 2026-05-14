from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .config import default_config_text, load_config
from .generator import build_voice_pack
from .ootp_paths import likely_candidates
from .script import load_script


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
    build.set_defaults(func=_build)

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
    manifest = build_voice_pack(config, lines, args.out)
    print(f"Generated {len(lines)} line(s)")
    print(f"Manifest: {manifest}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))
