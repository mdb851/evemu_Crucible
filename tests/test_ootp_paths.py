import unittest
from pathlib import Path

from ootp_announcer.ootp_paths import library_roots_from_steam_libraryfolders_vdf


class SteamLibraryfoldersTests(unittest.TestCase):
    def test_json_format_paths(self) -> None:
        text = '{"0": {"path": "D:/SteamLibrary", "label": ""}}'
        roots = library_roots_from_steam_libraryfolders_vdf(text)
        self.assertEqual(len(roots), 1)
        self.assertEqual(roots[0], Path("D:/SteamLibrary"))

    def test_vdf_keyvalues_path_lines(self) -> None:
        text = '\t"path"\t\t"D:\\\\Games\\\\SteamLib"\n\t"label"\t\t""\n'
        roots = library_roots_from_steam_libraryfolders_vdf(text)
        self.assertEqual(len(roots), 1)
        self.assertIn("SteamLib", str(roots[0]))

    def test_dedupes_identical_paths(self) -> None:
        text = '"path" "E:\\\\steam"\n"path" "E:\\\\steam"\n'
        roots = library_roots_from_steam_libraryfolders_vdf(text)
        self.assertEqual(len(roots), 1)


if __name__ == "__main__":
    unittest.main()
