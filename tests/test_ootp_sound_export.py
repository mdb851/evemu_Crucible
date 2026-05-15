from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ootp_announcer.cli import main
from ootp_announcer.ootp_sound_export import (
    SoundExportError,
    export_sounds,
    load_export_map,
    load_manifest,
)


class LoadManifestTests(unittest.TestCase):
    def test_requires_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(SoundExportError):
                load_manifest(Path(directory))

    def test_loads_lines(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "manifest.json").write_text(
                json.dumps({"lines": [{"id": "a", "audio": "audio/a.wav"}]}),
                encoding="utf-8",
            )
            m = load_manifest(root)
            self.assertIn("lines", m)


class ExportSoundsTests(unittest.TestCase):
    def test_copies_wav(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vp = root / "pack"
            audio = vp / "audio"
            audio.mkdir(parents=True)
            (audio / "a.wav").write_bytes(b"fake-wav")
            (vp / "manifest.json").write_text(
                json.dumps(
                    {
                        "lines": [
                            {
                                "id": "cue1",
                                "audio": "audio/a.wav",
                                "category": "x",
                                "text": "t",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            map_path = root / "map.toml"
            map_path.write_text(
                '[[map]]\ncue_id = "cue1"\nootp_filename = "hit_hard"\n',
                encoding="utf-8",
            )
            dest = root / "out"
            log = export_sounds(vp, map_path, dest, dry_run=False)
            out = dest / "hit_hard.wav"
            self.assertTrue(out.is_file())
            self.assertEqual(out.read_bytes(), b"fake-wav")
            self.assertTrue(any("copy" in line for line in log))

    def test_dry_run_does_not_create_dest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vp = root / "pack"
            audio = vp / "audio"
            audio.mkdir(parents=True)
            (audio / "a.wav").write_bytes(b"x")
            (vp / "manifest.json").write_text(
                json.dumps({"lines": [{"id": "cue1", "audio": "audio/a.wav"}]}),
                encoding="utf-8",
            )
            map_path = root / "map.toml"
            map_path.write_text(
                '[[map]]\ncue_id = "cue1"\nootp_filename = "hit_hard"\n',
                encoding="utf-8",
            )
            dest = root / "out"
            export_sounds(vp, map_path, dest, dry_run=True)
            self.assertFalse(dest.exists())

    def test_mp3_without_ffmpeg_errors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vp = root / "pack"
            audio = vp / "audio"
            audio.mkdir(parents=True)
            (audio / "a.mp3").write_bytes(b"\xff\xfb")
            (vp / "manifest.json").write_text(
                json.dumps({"lines": [{"id": "cue1", "audio": "audio/a.mp3"}]}),
                encoding="utf-8",
            )
            map_path = root / "map.toml"
            map_path.write_text(
                '[[map]]\ncue_id = "cue1"\nootp_filename = "hit_hard"\n',
                encoding="utf-8",
            )
            dest = root / "out"
            with patch("ootp_announcer.ootp_sound_export.which", return_value=None):
                with self.assertRaises(SoundExportError):
                    export_sounds(vp, map_path, dest, dry_run=False)

    def test_load_map_accepts_export_key(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "m.toml"
            p.write_text(
                '[[export]]\ncue_id = "x"\nootp_filename = "y"\n',
                encoding="utf-8",
            )
            rows = load_export_map(p)
            self.assertEqual(rows, [("x", "y")])


class CliExportTests(unittest.TestCase):
    def test_cli_export_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vp = root / "pack"
            audio = vp / "audio"
            audio.mkdir(parents=True)
            (audio / "a.wav").write_bytes(b"x")
            (vp / "manifest.json").write_text(
                json.dumps({"lines": [{"id": "cue1", "audio": "audio/a.wav"}]}),
                encoding="utf-8",
            )
            map_path = root / "map.toml"
            map_path.write_text(
                '[[map]]\ncue_id = "cue1"\nootp_filename = "hit_hard"\n',
                encoding="utf-8",
            )
            dest = root / "out"
            code = main(
                [
                    "export-ootp-sounds",
                    "--voice-pack",
                    str(vp),
                    "--map",
                    str(map_path),
                    "--dest",
                    str(dest),
                    "--dry-run",
                ]
            )
            self.assertEqual(code, 0)
            self.assertFalse(dest.exists())


if __name__ == "__main__":
    unittest.main()
