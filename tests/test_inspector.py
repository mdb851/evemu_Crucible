from pathlib import Path
import tempfile
import unittest

from ootp_announcer.inspector import (
    classify_file,
    classify_folder,
    inspect_ootp_root,
    render_markdown_report,
)


class InspectorTests(unittest.TestCase):
    def test_classifies_known_announcer_targets(self) -> None:
        self.assertEqual(classify_file("data/misc/pronunciation.txt"), "pronunciation")
        self.assertEqual(classify_file("data/pbp/english.xml"), "play-by-play")
        self.assertEqual(classify_file("app.cfg"), "game config")
        self.assertEqual(classify_folder("data/sounds"), "audio folder")

    def test_inspect_root_finds_candidate_files_and_folders(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            misc = root / "data" / "misc"
            pbp = root / "data" / "pbp"
            sounds = root / "sounds"
            misc.mkdir(parents=True)
            pbp.mkdir(parents=True)
            sounds.mkdir()
            (misc / "pronunciation.txt").write_text("Smith=Smihth\n", encoding="utf-8")
            (pbp / "english.xml").write_text("<pbp />\n", encoding="utf-8")
            (sounds / "crowd.wav").write_bytes(b"RIFF")

            report = inspect_ootp_root(root)
            markdown = render_markdown_report(report)

        self.assertTrue(report.exists)
        self.assertIn("pronunciation.txt", markdown)
        self.assertIn("data/pbp", markdown)
        self.assertIn("crowd.wav", markdown)

    def test_missing_root_returns_non_existing_report(self) -> None:
        report = inspect_ootp_root(Path("/definitely/not/ootp27"))

        self.assertFalse(report.exists)
        self.assertEqual(report.files, [])
        self.assertIn("does not exist", render_markdown_report(report))


if __name__ == "__main__":
    unittest.main()
