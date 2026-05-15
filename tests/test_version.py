from __future__ import annotations

import sys
import unittest
from io import StringIO
from unittest.mock import patch

from ootp_announcer import __version__
from ootp_announcer.cli import main


class VersionCliTests(unittest.TestCase):
    def test_version_matches_package(self) -> None:
        self.assertRegex(__version__, r"^\d+\.\d+\.\d+$")

    def test_version_flag_prints_and_exits_zero(self) -> None:
        buf = StringIO()
        with patch.object(sys, "stdout", buf):
            code = main(["--version"])
        self.assertEqual(code, 0)
        out = buf.getvalue()
        self.assertIn(__version__, out)
        self.assertIn("ootp27-announcer", out)

    def test_short_version_flag(self) -> None:
        buf = StringIO()
        with patch.object(sys, "stdout", buf):
            code = main(["-V"])
        self.assertEqual(code, 0)
        self.assertIn(__version__, buf.getvalue())


if __name__ == "__main__":
    unittest.main()
