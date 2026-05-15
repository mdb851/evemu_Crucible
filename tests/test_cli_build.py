from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from ootp_announcer.cli import main
from ootp_announcer.config import default_config_text


class CliBuildMaxLinesTests(unittest.TestCase):
    def test_build_max_lines_via_cli(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "announcer.toml"
            script_path = root / "lines.csv"
            out_dir = root / "pack"
            config_path.write_text(default_config_text(), encoding="utf-8")
            script_path.write_text(
                "id,text\na,One\nb,Two\nc,Three\n",
                encoding="utf-8",
            )
            code = main(
                [
                    "build",
                    "--config",
                    str(config_path),
                    "--script",
                    str(script_path),
                    "--out",
                    str(out_dir),
                    "--max-lines",
                    "2",
                ]
            )
            self.assertEqual(code, 0)
            self.assertTrue((out_dir / "audio" / "a.wav").exists())
            self.assertTrue((out_dir / "audio" / "b.wav").exists())
            self.assertFalse((out_dir / "audio" / "c.wav").exists())


if __name__ == "__main__":
    unittest.main()
