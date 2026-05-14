from pathlib import Path
import tempfile
import unittest
import zipfile

from ootp_announcer.packager import create_zip_package, write_install_notes


class PackagerTests(unittest.TestCase):
    def test_write_install_notes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            voice_pack = Path(directory)
            (voice_pack / "manifest.json").write_text("{}", encoding="utf-8")

            notes = write_install_notes(voice_pack)

            self.assertTrue(notes.exists())
            self.assertIn("Local integration checklist", notes.read_text(encoding="utf-8"))

    def test_create_zip_package_includes_install_notes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            voice_pack = root / "voice-pack"
            audio = voice_pack / "audio"
            audio.mkdir(parents=True)
            (voice_pack / "manifest.json").write_text("{}", encoding="utf-8")
            (audio / "welcome.wav").write_text("dry run", encoding="utf-8")
            output = root / "voice-pack.zip"

            create_zip_package(voice_pack, output)

            with zipfile.ZipFile(output) as archive:
                names = set(archive.namelist())

        self.assertIn("INSTALL.md", names)
        self.assertIn("audio/welcome.wav", names)


if __name__ == "__main__":
    unittest.main()
