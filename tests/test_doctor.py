from pathlib import Path
import tempfile
import unittest

from ootp_announcer.config import default_config_text
from ootp_announcer.doctor import render_doctor_report, run_doctor


class DoctorTests(unittest.TestCase):
    def test_doctor_passes_with_dry_run_warning(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "announcer.toml"
            script_path = root / "lines.csv"
            config_path.write_text(default_config_text(root), encoding="utf-8")
            script_path.write_text("id,text\nwelcome,Welcome!\n", encoding="utf-8")

            report = run_doctor(config_path, script_path=script_path, output_dir=root / "out")
            rendered = render_doctor_report(report)

        self.assertFalse(report.has_errors)
        self.assertIn("[OK] config", rendered)
        self.assertIn("[WARNING] voice", rendered)

    def test_doctor_reports_missing_config(self) -> None:
        report = run_doctor(Path("/missing/announcer.toml"))

        self.assertTrue(report.has_errors)
        self.assertIn("Config file not found", render_doctor_report(report))

    def test_doctor_reports_bad_script(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "announcer.toml"
            script_path = root / "lines.csv"
            config_path.write_text(default_config_text(), encoding="utf-8")
            script_path.write_text("id\nwelcome\n", encoding="utf-8")

            report = run_doctor(config_path, script_path=script_path)

        self.assertTrue(report.has_errors)
        self.assertIn("Could not load script", render_doctor_report(report))


if __name__ == "__main__":
    unittest.main()
