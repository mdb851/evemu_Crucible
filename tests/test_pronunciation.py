from pathlib import Path
import tempfile
import unittest

from ootp_announcer.pronunciation import (
    apply_pronunciations,
    load_pronunciations,
    render_pronunciation_report,
    write_prepared_script,
)
from ootp_announcer.script import ScriptLine


class PronunciationTests(unittest.TestCase):
    def test_load_pronunciations_sorts_longest_first(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pronunciations.csv"
            path.write_text(
                "term,replacement\nleft,left\nleft field,left-field\n",
                encoding="utf-8",
            )

            rules = load_pronunciations(path)

        self.assertEqual([rule.term for rule in rules], ["left field", "left"])

    def test_apply_pronunciations_rewrites_script_text(self) -> None:
        lines = [
            ScriptLine(
                cue_id="home_run",
                text="That ball is deep to left field in OOTP.",
                category="hit",
                filename="home_run.wav",
            )
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pronunciations.csv"
            path.write_text(
                "term,replacement\nleft field,left-field\nOOTP,Out of the Park\n",
                encoding="utf-8",
            )
            rules = load_pronunciations(path)

        prepared, changes = apply_pronunciations(lines, rules)
        report = render_pronunciation_report(changes)

        self.assertEqual(
            prepared[0].text,
            "That ball is deep to left-field in Out of the Park.",
        )
        self.assertIn("left field", report)
        self.assertIn("OOTP", report)

    def test_write_prepared_script_preserves_original_text(self) -> None:
        original = [
            ScriptLine("welcome", "Welcome to OOTP.", "intro", "welcome.wav"),
        ]
        prepared = [
            ScriptLine("welcome", "Welcome to Out of the Park.", "intro", "welcome.wav"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "prepared.csv"
            write_prepared_script(original, prepared, output)

            text = output.read_text(encoding="utf-8")

        self.assertIn("original_text", text)
        self.assertIn("Welcome to OOTP.", text)


if __name__ == "__main__":
    unittest.main()
