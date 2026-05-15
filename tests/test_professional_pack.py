from __future__ import annotations

from pathlib import Path
import unittest

from ootp_announcer.script import load_script


class ProfessionalPackTests(unittest.TestCase):
    def test_professional_csv_loads_with_unique_ids(self) -> None:
        root = Path(__file__).resolve().parents[1]
        csv_path = root / "packs" / "professional_broadcast" / "lines.csv"
        lines = load_script(csv_path, "wav")
        self.assertGreaterEqual(len(lines), 80)
        ids = [line.cue_id for line in lines]
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
