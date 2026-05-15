from __future__ import annotations

import json
from dataclasses import replace
from io import BytesIO
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from ootp_announcer.config import VoiceSettings, load_config
from ootp_announcer.tts import (
    TtsError,
    synthesize,
    _elevenlabs_api_key_from_env_or_keyfile,
    _normalize_elevenlabs_api_key,
)
from urllib.error import HTTPError


def _default_elevenlabs_voice() -> VoiceSettings:
    return VoiceSettings(
        backend="elevenlabs",
        command_template="",
        piper_binary="piper",
        piper_model=None,
        speaker_id=None,
        elevenlabs_voice_id="voice123",
        elevenlabs_model_id="eleven_multilingual_v2",
        elevenlabs_output_format="mp3_44100_128",
        elevenlabs_stability=0.5,
        elevenlabs_similarity_boost=0.75,
        elevenlabs_style=0.25,
        elevenlabs_use_speaker_boost=True,
        elevenlabs_api_key="",
    )


class ElevenLabsTtsTests(unittest.TestCase):
    def test_missing_api_key_raises(self) -> None:
        voice = _default_elevenlabs_voice()
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "line.mp3"
            with patch.dict("os.environ", {}, clear=True):
                with self.assertRaisesRegex(TtsError, "API key missing"):
                    synthesize("Hello ballpark", out, voice)

    def test_writes_response_bytes(self) -> None:
        voice = replace(_default_elevenlabs_voice(), elevenlabs_api_key="test-key")
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "line.mp3"
            mock_resp = MagicMock()
            mock_resp.read.return_value = b"\xff\xfb\x90\x00"
            mock_ctx = MagicMock()
            mock_ctx.__enter__.return_value = mock_resp
            mock_ctx.__exit__.return_value = False

            with patch("ootp_announcer.tts.urlopen", return_value=mock_ctx):
                synthesize("Play ball!", out, voice)

            self.assertEqual(out.read_bytes(), b"\xff\xfb\x90\x00")

    def test_elevenlabs_payload_includes_style_settings(self) -> None:
        voice = replace(_default_elevenlabs_voice(), elevenlabs_api_key="test-key")
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "line.mp3"
            mock_resp = MagicMock()
            mock_resp.read.return_value = b"x"
            mock_ctx = MagicMock()
            mock_ctx.__enter__.return_value = mock_resp
            mock_ctx.__exit__.return_value = False

            with patch("ootp_announcer.tts.urlopen", return_value=mock_ctx) as mock_urlopen:
                synthesize("On the air", out, voice)

            req = mock_urlopen.call_args[0][0]
            body = json.loads(req.data.decode("utf-8"))
            self.assertEqual(body["voice_settings"]["style"], 0.25)
            self.assertTrue(body["voice_settings"]["use_speaker_boost"])

    def test_http_error_includes_body(self) -> None:
        voice = replace(_default_elevenlabs_voice(), elevenlabs_api_key="test-key")
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "line.mp3"
            err = HTTPError(
                "https://api.elevenlabs.io/v1/text-to-speech/x",
                401,
                "Unauthorized",
                {},
                BytesIO(b'{"detail":"invalid"}'),
            )
            with patch("ootp_announcer.tts.urlopen", side_effect=err):
                with self.assertRaisesRegex(TtsError, "ElevenLabs HTTP 401"):
                    synthesize("Hi", out, voice)


class ElevenLabsKeyfileTests(unittest.TestCase):
    def test_keyfile_env_reads_normalized_key(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            key_path = Path(directory) / "key.txt"
            key_path.write_text("  abc123xyz  \n", encoding="utf-8")
            with patch.dict(
                os.environ,
                {"ELEVENLABS_API_KEY": "", "ELEVENLABS_API_KEY_FILE": str(key_path)},
            ):
                self.assertEqual(_elevenlabs_api_key_from_env_or_keyfile(), "abc123xyz")

    def test_keyfile_wins_over_env_when_both_set(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            key_path = Path(directory) / "key.txt"
            key_path.write_text("fromfile\n", encoding="utf-8")
            with patch.dict(
                os.environ,
                {
                    "ELEVENLABS_API_KEY": "wrong-env-key-should-not-win",
                    "ELEVENLABS_API_KEY_FILE": str(key_path),
                },
            ):
                self.assertEqual(_elevenlabs_api_key_from_env_or_keyfile(), "fromfile")


class NormalizeElevenLabsKeyTests(unittest.TestCase):
    def test_multiline_uses_first_line(self) -> None:
        self.assertEqual(
            _normalize_elevenlabs_api_key("  first\nsecond\n"),
            "first",
        )

    def test_strips_common_label_prefix(self) -> None:
        self.assertEqual(
            _normalize_elevenlabs_api_key('API Key: "skabc"'),
            "skabc",
        )


class ElevenLabsConfigTests(unittest.TestCase):
    def test_loads_elevenlabs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "announcer.toml"
            path.write_text(
                '\n'.join(
                    [
                        "[voice]",
                        'backend = "elevenlabs"',
                        'elevenlabs_voice_id = "abc"',
                        "",
                        "[audio]",
                        'extension = "mp3"',
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            cfg = load_config(path)
            self.assertEqual(cfg.voice.backend, "elevenlabs")
            self.assertEqual(cfg.voice.elevenlabs_voice_id, "abc")

    def test_requires_mp3_extension(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "announcer.toml"
            path.write_text(
                '\n'.join(
                    [
                        "[voice]",
                        'backend = "elevenlabs"',
                        'elevenlabs_voice_id = "abc"',
                        "",
                        "[audio]",
                        'extension = "wav"',
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "audio.extension must be 'mp3'"):
                load_config(path)


if __name__ == "__main__":
    unittest.main()
