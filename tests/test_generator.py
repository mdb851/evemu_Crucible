from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ootp_announcer.config import default_config_text, load_config
from ootp_announcer.generator import build_voice_pack
from ootp_announcer.script import load_script


class GeneratorTests(unittest.TestCase):
    def test_build_voice_pack_dry_run_writes_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "announcer.toml"
            script_path = root / "lines.csv"
            output_dir = root / "voice-pack"
            config_path.write_text(default_config_text(), encoding="utf-8")
            script_path.write_text("id,text\nwelcome,Welcome to OOTP.\n", encoding="utf-8")

            config = load_config(config_path)
            lines = load_script(script_path, config.audio.extension)
            manifest = build_voice_pack(config, lines, output_dir)

            self.assertTrue(manifest.exists())
            self.assertTrue((output_dir / "audio" / "welcome.wav").exists())
            self.assertIn("Welcome to OOTP.", manifest.read_text(encoding="utf-8"))

    def test_build_sleep_between_lines_when_delay_set(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "announcer.toml"
            script_path = root / "lines.csv"
            output_dir = root / "voice-pack"
            config_path.write_text(
                default_config_text().replace(
                    "delay_seconds_after_each_line = 0.0",
                    "delay_seconds_after_each_line = 0.01",
                ),
                encoding="utf-8",
            )
            script_path.write_text(
                "id,text\na,One\nb,Two\nc,Three\n",
                encoding="utf-8",
            )
            config = load_config(config_path)
            lines = load_script(script_path, config.audio.extension)
            with patch("ootp_announcer.generator.time.sleep") as mock_sleep:
                build_voice_pack(config, lines, output_dir)
            self.assertEqual(mock_sleep.call_count, 2)


if __name__ == "__main__":
    unittest.main()
