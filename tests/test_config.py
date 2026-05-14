from pathlib import Path
import tempfile
import unittest

from ootp_announcer.config import default_config_text, load_config


class ConfigTests(unittest.TestCase):
    def test_default_config_loads(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "announcer.toml"
            config_path.write_text(default_config_text(), encoding="utf-8")

            config = load_config(config_path)

        self.assertEqual(config.game, "OOTP 27")
        self.assertEqual(config.voice.backend, "dry-run")
        self.assertEqual(config.audio.extension, "wav")

    def test_rejects_unknown_backend(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "announcer.toml"
            config_path.write_text(
                '[voice]\nbackend = "robot"\n',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "Unsupported voice backend"):
                load_config(config_path)


if __name__ == "__main__":
    unittest.main()
