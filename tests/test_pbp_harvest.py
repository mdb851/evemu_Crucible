from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ootp_announcer.cli import main
from ootp_announcer.pbp_harvest import (
    find_pbp_language_html,
    harvest_phrases_from_html,
    phrases_to_csv_rows,
    write_harvest_csv,
)


class FindPbpHtmlTests(unittest.TestCase):
    def test_prefers_languages_english(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lang = root / "languages"
            lang.mkdir(parents=True)
            target = lang / "English.html"
            target.write_text("<html></html>", encoding="utf-8")
            found = find_pbp_language_html(root)
            self.assertEqual(found, [target.resolve()])


class HarvestPhrasesTests(unittest.TestCase):
    def test_extracts_sentence_from_paragraph(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "English.html"
            path.write_text(
                "<html><body><p>He slices one the other way for a base hit. "
                "The crowd loves this kind of inning.</p></body></html>",
                encoding="utf-8",
            )
            phrases = harvest_phrases_from_html(path, min_chars=12, max_chars=400)
            joined = " ".join(phrases)
            self.assertIn("base hit", joined)
            self.assertIn("crowd loves", joined)

    def test_skips_lines_that_still_contain_braces(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "English.html"
            path.write_text(
                "<p>Hello {unclosed template without a closing brace.</p>",
                encoding="utf-8",
            )
            phrases = harvest_phrases_from_html(path, min_chars=10, max_chars=200)
            self.assertEqual(phrases, [])

    def test_strips_known_placeholders(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "English.html"
            path.write_text(
                "<p>{batter} lines one into the corner for a double.</p>",
                encoding="utf-8",
            )
            phrases = harvest_phrases_from_html(path, min_chars=20, max_chars=200)
            self.assertTrue(any("corner" in p and "double" in p for p in phrases))


class PhrasesToCsvTests(unittest.TestCase):
    def test_dedupes_identical_text(self) -> None:
        rows = phrases_to_csv_rows(["Same line.", "Same line."])
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0][0].startswith("pbp_"))


class HarvestCliTests(unittest.TestCase):
    def test_cli_writes_csv(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lang = root / "languages"
            lang.mkdir(parents=True)
            (lang / "English.html").write_text(
                "<html><body><p>This is a long enough sample sentence for the harvester.</p></body></html>",
                encoding="utf-8",
            )
            out = root / "out.csv"
            code = main(
                [
                    "harvest-pbp",
                    "--ootp-root",
                    str(root),
                    "--out",
                    str(out),
                    "--min-chars",
                    "10",
                ]
            )
            self.assertEqual(code, 0)
            self.assertTrue(out.is_file())
            body = out.read_text(encoding="utf-8")
            self.assertIn("harvested_pbp", body)
            self.assertIn("sample sentence", body)

    def test_cli_fails_when_no_english_html(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            out = root / "out.csv"
            code = main(["harvest-pbp", "--ootp-root", str(root), "--out", str(out)])
            self.assertEqual(code, 2)


class WriteHarvestCsvTests(unittest.TestCase):
    def test_escapes_quotes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "x.csv"
            write_harvest_csv([("pbp_1", "harvested_pbp", 'He said "wow".')], out)
            text = out.read_text(encoding="utf-8")
            self.assertIn('""wow""', text)


if __name__ == "__main__":
    unittest.main()
