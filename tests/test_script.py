from pathlib import Path
import unittest

from ootp_announcer.script import load_script, sanitize_filename


class ScriptTests(unittest.TestCase):
    def test_sanitize_filename_adds_extension(self) -> None:
        self.assertEqual(sanitize_filename("Home Run Call!", "wav"), "home-run-call.wav")

    def test_load_script_defaults_optional_fields(self) -> None:
        with self._tmp_script("id,text\nfirst_pitch,Play ball!\n") as script:
            lines = load_script(script, "wav")

        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0].cue_id, "first_pitch")
        self.assertEqual(lines[0].category, "general")
        self.assertEqual(lines[0].filename, "first-pitch.wav")

    def test_load_script_rejects_duplicate_ids(self) -> None:
        with self._tmp_script(
            "id,text\nfirst_pitch,Play ball!\nfirst_pitch,Again!\n"
        ) as script:
            with self.assertRaisesRegex(ValueError, "Duplicate cue id"):
                load_script(script, "wav")

    def _tmp_script(self, text: str):
        return _TemporaryScript(text)


class _TemporaryScript:
    def __init__(self, text: str) -> None:
        self.text = text
        self.path: Path | None = None

    def __enter__(self) -> Path:
        import tempfile

        directory = tempfile.TemporaryDirectory()
        self._directory = directory
        self.path = Path(directory.name) / "lines.csv"
        self.path.write_text(self.text, encoding="utf-8")
        return self.path

    def __exit__(self, *args: object) -> None:
        self._directory.cleanup()


if __name__ == "__main__":
    unittest.main()
