from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil


INSTALL_MANIFEST = "ootp-announcer-install.json"


@dataclass(frozen=True)
class InstallAction:
    source: Path
    destination: Path
    backup: Path | None
    status: str


@dataclass(frozen=True)
class InstallReport:
    voice_pack: Path
    target: Path
    applied: bool
    actions: list[InstallAction]
    manifest_path: Path | None


def install_voice_pack(
    voice_pack: Path,
    target: Path,
    apply: bool = False,
    backup_dir: Path | None = None,
) -> InstallReport:
    source_root = voice_pack.expanduser()
    target_root = target.expanduser()
    if not source_root.exists():
        raise FileNotFoundError(f"Voice pack directory not found: {source_root}")
    if not (source_root / "manifest.json").exists():
        raise FileNotFoundError(f"Voice pack manifest not found: {source_root / 'manifest.json'}")

    files = [path for path in sorted(source_root.rglob("*")) if path.is_file()]
    actions: list[InstallAction] = []
    backup_root = backup_dir.expanduser() if backup_dir else target_root / "_backup"

    for source in files:
        relative = source.relative_to(source_root)
        destination = target_root / relative
        backup_path = backup_root / relative if destination.exists() else None
        actions.append(
            InstallAction(
                source=source,
                destination=destination,
                backup=backup_path,
                status="planned" if not apply else "copied",
            )
        )

    manifest_path: Path | None = None
    if apply:
        for action in actions:
            action.destination.parent.mkdir(parents=True, exist_ok=True)
            if action.backup is not None:
                action.backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(action.destination, action.backup)
            shutil.copy2(action.source, action.destination)

        manifest_path = target_root / INSTALL_MANIFEST
        manifest_path.write_text(
            json.dumps(_report_to_dict(source_root, target_root, True, actions), indent=2),
            encoding="utf-8",
        )

    return InstallReport(
        voice_pack=source_root,
        target=target_root,
        applied=apply,
        actions=actions,
        manifest_path=manifest_path,
    )


def render_install_report(report: InstallReport) -> str:
    mode = "APPLIED" if report.applied else "DRY RUN"
    lines = [
        f"OOTP announcer install report ({mode})",
        "",
        f"Voice pack: {report.voice_pack}",
        f"Target: {report.target}",
        f"Files: {len(report.actions)}",
        "",
    ]
    for action in report.actions:
        backup = f" backup={action.backup}" if action.backup else ""
        lines.append(f"- {action.status}: {action.source} -> {action.destination}{backup}")
    if report.manifest_path:
        lines.extend(["", f"Install manifest: {report.manifest_path}"])
    if not report.applied:
        lines.extend(["", "No files were copied. Re-run with --apply to perform this install."])
    return "\n".join(lines)


def _report_to_dict(
    voice_pack: Path,
    target: Path,
    applied: bool,
    actions: list[InstallAction],
) -> dict[str, object]:
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "voice_pack": str(voice_pack),
        "target": str(target),
        "applied": applied,
        "actions": [
            {
                "source": str(action.source),
                "destination": str(action.destination),
                "backup": str(action.backup) if action.backup else "",
                "status": action.status,
            }
            for action in actions
        ],
    }
