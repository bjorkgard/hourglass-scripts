import json
import tempfile
import unittest
from datetime import date
from pathlib import Path


class ReportHistoryTests(unittest.TestCase):
    def test_creates_first_report_and_history_without_previous_comparison(self):
        from report_history import skapa_rapport

        rows = [
            {
                "fullname": "Andersson, Anna",
                "birth": "1980-01-02",
                "email": "anna@example.com",
                "cellphone": "070-111 11 11",
                "homephone": "",
                "address_line1": "Gatan 1",
                "address_line2": "",
                "address_postalcode": "12345",
                "address_city": "Teststad",
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            report_path = skapa_rapport(rows, root / "history" / "contact_history.json", root / "out")

            text = report_path.read_text(encoding="utf-8")
            self.assertIn(f"Rapportdatum: {date.today().isoformat()}", text)
            self.assertIn("Jämför med: Ingen tidigare körning", text)
            self.assertIn("Nya namn: 1", text)
            self.assertIn("- Andersson, Anna (1980-01-02)", text)
            self.assertIn("Uppdaterade kontaktuppgifter: 0", text)
            self.assertIn("Borttagna namn: 0", text)

            history = json.loads((root / "history" / "contact_history.json").read_text(encoding="utf-8"))
            self.assertEqual(history["datum"], date.today().isoformat())
            self.assertEqual(len(history["personer"]), 1)

    def test_reports_new_updated_and_removed_contacts_against_previous_history(self):
        from report_history import skapa_rapport

        previous_rows = [
            {
                "fullname": "Andersson, Anna",
                "birth": "1980-01-02",
                "email": "old@example.com",
                "cellphone": "070-111 11 11",
                "homephone": "",
                "address_line1": "Gatan 1",
                "address_line2": "",
                "address_postalcode": "12345",
                "address_city": "Teststad",
            },
            {
                "fullname": "Bengtsson, Bertil",
                "birth": "1975-03-04",
                "email": "bertil@example.com",
                "cellphone": "",
                "homephone": "",
                "address_line1": "Vägen 2",
                "address_line2": "",
                "address_postalcode": "54321",
                "address_city": "Annanstad",
            },
        ]
        current_rows = [
            {
                "fullname": "Andersson, Anna",
                "birth": "1980-01-02",
                "email": "new@example.com",
                "cellphone": "070-111 11 11",
                "homephone": "",
                "address_line1": "Gatan 1",
                "address_line2": "",
                "address_postalcode": "12345",
                "address_city": "Teststad",
            },
            {
                "fullname": "Carlsson, Cecilia",
                "birth": "1990-05-06",
                "email": "cecilia@example.com",
                "cellphone": "",
                "homephone": "",
                "address_line1": "Torget 3",
                "address_line2": "",
                "address_postalcode": "67890",
                "address_city": "Nystad",
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            history_path = root / "history" / "contact_history.json"
            out_dir = root / "out"

            skapa_rapport(previous_rows, history_path, out_dir, datum="2026-08-20")
            report_path = skapa_rapport(current_rows, history_path, out_dir, datum="2026-08-27")

            text = report_path.read_text(encoding="utf-8")
            self.assertIn("Rapportdatum: 2026-08-27", text)
            self.assertIn("Jämför med: 2026-08-20", text)
            self.assertIn("Nya namn: 1", text)
            self.assertIn("- Carlsson, Cecilia (1990-05-06)", text)
            self.assertIn("Uppdaterade kontaktuppgifter: 1", text)
            self.assertIn("- Andersson, Anna (1980-01-02)", text)
            self.assertIn("Borttagna namn: 1", text)
            self.assertIn("- Bengtsson, Bertil (1975-03-04)", text)

    def test_uses_zero_for_rows_without_birth(self):
        from report_history import skapa_rapport

        rows = [
            {
                "fullname": "Andersson, Anna",
                "birth": "",
                "email": "anna@example.com",
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            history_path = root / "history" / "contact_history.json"

            report_path = skapa_rapport(rows, history_path, root / "out", datum="2026-08-29")

            text = report_path.read_text(encoding="utf-8")
            self.assertIn("- Andersson, Anna (0)", text)

            history = json.loads(history_path.read_text(encoding="utf-8"))
            self.assertEqual(
                history["personer"]["andersson, anna\0" + "0"],
                {
                    "fullname": "Andersson, Anna",
                    "birth": "0",
                    "kontakt": {
                        "address_line1": "",
                        "address_line2": "",
                        "address_postalcode": "",
                        "address_city": "",
                        "cellphone": "",
                        "homephone": "",
                        "email": "anna@example.com",
                    },
                },
            )

    def test_rejects_rows_without_fullname_before_updating_history(self):
        from report_history import skapa_rapport

        rows = [
            {
                "fullname": "",
                "birth": "1980-01-02",
                "email": "anna@example.com",
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            history_path = root / "history" / "contact_history.json"

            with self.assertRaisesRegex(ValueError, "fullname"):
                skapa_rapport(rows, history_path, root / "out")

            self.assertFalse(history_path.exists())


if __name__ == "__main__":
    unittest.main()
