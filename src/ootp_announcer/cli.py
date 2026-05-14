from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .config import default_config_text, load_config
from .doctor import render_doctor_report, run_doctor
from .generator import build_voice_pack
from .installer import install_voice_pack, render_install_report
from .inspector import inspect_ootp_root, write_json_report, write_markdown_report
from .ootp_paths import likely_candidates
from .packager import create_zip_package
from .pronunciation import (
    apply_pronunciations,
    load_pronunciations,
    render_pronunciation_report,
    write_prepared_script,
)
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

    inspect = subcommands.add_parser(
        "inspect",
        help="Inspect an OOTP 27 folder for likely announcer integration files",
    )
    inspect.add_argument("--ootp-root", type=Path, required=True)
    inspect.add_argument("--out", type=Path, default=Path("ootp-inspection.md"))
    inspect.add_argument("--json-out", type=Path)
    inspect.add_argument(
        "--max-files",
        type=int,
        default=5000,
        help="Maximum number of files to scan before stopping",
    )
    inspect.set_defaults(func=_inspect)

    doctor = subcommands.add_parser("doctor", help="Validate config, script, and TTS setup")
    doctor.add_argument("--config", type=Path, default=Path("announcer.toml"))
    doctor.add_argument("--script", type=Path)
    doctor.add_argument("--out", type=Path, default=Path("voice-pack"))
    doctor.set_defaults(func=_doctor)

    prepare_script = subcommands.add_parser(
        "prepare-script",
        help="Apply a pronunciation lexicon to a CSV announcer script",
    )
    prepare_script.add_argument("--script", type=Path, required=True)
    prepare_script.add_argument("--pronunciations", type=Path, required=True)
    prepare_script.add_argument("--out", type=Path, required=True)
    prepare_script.add_argument("--audio-extension", default="wav")
    prepare_script.add_argument("--report", type=Path)
    prepare_script.set_defaults(func=_prepare_script)

    build = subcommands.add_parser("build", help="Generate an announcer voice pack")
    build.add_argument("--config", type=Path, default=Path("announcer.toml"))
    build.add_argument("--script", type=Path, required=True)
    build.add_argument("--out", type=Path, default=Path("voice-pack"))
    build.add_argument("--pronunciations", type=Path)
    build.set_defaults(func=_build)

    package = subcommands.add_parser("package", help="Zip a generated voice pack")
    package.add_argument("--voice-pack", type=Path, default=Path("voice-pack"))
    package.add_argument("--out", type=Path, default=Path("voice-pack.zip"))
    package.set_defaults(func=_package)

    install = subcommands.add_parser(
        "install",
        help="Copy a generated voice pack to a chosen local target folder",
    )
    install.add_argument("--voice-pack", type=Path, default=Path("voice-pack"))
    install.add_argument("--target", type=Path, required=True)
    install.add_argument("--backup-dir", type=Path)
    install.add_argument(
        "--apply",
        action="store_true",
        help="Actually copy files; omitted means dry-run only",
    )
    install.set_defaults(func=_install)

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


def _inspect(args: argparse.Namespace) -> int:
    report = inspect_ootp_root(args.ootp_root, max_files=args.max_files)
    write_markdown_report(report, args.out)
    print(f"Wrote inspection report: {args.out}")
    if args.json_out:
        write_json_report(report, args.json_out)
        print(f"Wrote JSON report: {args.json_out}")
    if not report.exists:
        return 1
    print(f"Found {len(report.folders)} candidate folder(s)")
    print(f"Found {len(report.files)} candidate file(s)")
    return 0


def _doctor(args: argparse.Namespace) -> int:
    report = run_doctor(args.config, script_path=args.script, output_dir=args.out)
    print(render_doctor_report(report))
    return 1 if report.has_errors else 0


def _prepare_script(args: argparse.Namespace) -> int:
    lines = load_script(args.script, args.audio_extension)
    rules = load_pronunciations(args.pronunciations)
    prepared, changes = apply_pronunciations(lines, rules)
    write_prepared_script(lines, prepared, args.out)
    report = render_pronunciation_report(changes)
    print(report)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(report, encoding="utf-8")
        print(f"Wrote pronunciation report: {args.report}")
    print(f"Wrote prepared script: {args.out}")
    return 0


def _build(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    lines = load_script(args.script, config.audio.extension)
    if args.pronunciations:
        rules = load_pronunciations(args.pronunciations)
        lines, changes = apply_pronunciations(lines, rules)
        args.out.mkdir(parents=True, exist_ok=True)
        pronunciation_report = args.out / "pronunciation-report.md"
        pronunciation_report.write_text(render_pronunciation_report(changes), encoding="utf-8")
    manifest = build_voice_pack(config, lines, args.out)
    print(f"Generated {len(lines)} line(s)")
    if args.pronunciations:
        print(f"Pronunciation report: {pronunciation_report}")
    print(f"Manifest: {manifest}")
    return 0


def _package(args: argparse.Namespace) -> int:
    output = create_zip_package(args.voice_pack, args.out)
    print(f"Wrote package: {output}")
    return 0


def _install(args: argparse.Namespace) -> int:
    report = install_voice_pack(
        args.voice_pack,
        args.target,
        apply=args.apply,
        backup_dir=args.backup_dir,
    )
    print(render_install_report(report))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))
