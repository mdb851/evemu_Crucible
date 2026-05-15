from __future__ import annotations

import json
import os
import unittest
from unittest.mock import MagicMock, patch

from ootp_announcer.cli import main
from ootp_announcer.tts import fetch_elevenlabs_user_json


class FetchElevenLabsUserTests(unittest.TestCase):
    def test_fetch_parses_json(self) -> None:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"subscription": {"tier": "free"}}).encode("utf-8")
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = mock_resp
        mock_ctx.__exit__.return_value = False

        with patch("ootp_announcer.tts.urlopen", return_value=mock_ctx):
            data = fetch_elevenlabs_user_json("sk-test-key-please-mock")

        self.assertEqual(data.get("subscription", {}).get("tier"), "free")


class VerifyCliTests(unittest.TestCase):
    def test_verify_cli_success(self) -> None:
        with patch("ootp_announcer.cli.fetch_elevenlabs_user_json", return_value={"subscription": {"tier": "free"}}):
            with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "a" * 48}, clear=False):
                code = main(["verify-elevenlabs"])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
