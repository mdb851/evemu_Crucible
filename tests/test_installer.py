from pathlib import Path
import tempfile
import unittest

from ootp_announcer.installer import install_voice_pack, render_install_report


class InstallerTests(unittest.TestCase):
    def test_install_dry_run_does_not_copy_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            voice_pack = _voice_pack(root / "voice-pack")
            target = root / "target"

            report = install_voice_pack(voice_pack, target)
            rendered = render_install_report(report)

            self.assertFalse(report.applied)
            self.assertFalse((target / "manifest.json").exists())
            self.assertIn("DRY RUN", rendered)

    def test_install_apply_copies_files_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            voice_pack = _voice_pack(root / "voice-pack")
            target = root / "target"

            report = install_voice_pack(voice_pack, target, apply=True)

            self.assertTrue(report.applied)
            self.assertTrue((target / "manifest.json").exists())
            self.assertTrue((target / "audio" / "welcome.wav").exists())
            self.assertTrue((target / "ootp-announcer-install.json").exists())

    def test_install_apply_backs_up_existing_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            voice_pack = _voice_pack(root / "voice-pack")
            target = root / "target"
            audio = target / "audio"
            audio.mkdir(parents=True)
            (audio / "welcome.wav").write_text("old", encoding="utf-8")

            report = install_voice_pack(voice_pack, target, apply=True)

            backups = [action.backup for action in report.actions if action.backup is not None]
            self.assertEqual(len(backups), 1)
            self.assertTrue(backups[0].exists())
            self.assertEqual(backups[0].read_text(encoding="utf-8"), "old")


def _voice_pack(path: Path) -> Path:
    audio = path / "audio"
    audio.mkdir(parents=True)
    (path / "manifest.json").write_text("{}", encoding="utf-8")
    (audio / "welcome.wav").write_text("new", encoding="utf-8")
    return path


if __name__ == "__main__":
    unittest.main()
