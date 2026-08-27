import csv
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from create_service_group_list import dela_upp_i_sidor, skapa_stilar
from create_service_group_list import gruppera, las_csv, skapa_pdf, skapa_tjanstegruppstabell


class ServiceGroupListTests(unittest.TestCase):
    def test_groups_active_people_by_address_list_order_and_sorts_people_by_name(self):
        rows = [
            {
                "fullname": "Person, Aktiv",
                "lastname": "Person",
                "firstname": "Aktiv",
                "inactive": "",
                "group_overseer": "Ledare, Beta",
            },
            {
                "fullname": "Ledare, Beta",
                "lastname": "Ledare",
                "firstname": "Beta",
                "inactive": "",
                "group_overseer": "Ledare, Beta",
            },
            {
                "fullname": "Person, Overksam",
                "lastname": "Person",
                "firstname": "Overksam",
                "inactive": "1",
                "group_overseer": "Ledare, Beta",
            },
            {
                "fullname": "Ledare, Alfa",
                "lastname": "Ledare",
                "firstname": "Alfa",
                "inactive": "",
                "group_overseer": "Ledare, Alfa",
            },
        ]

        grupper = gruppera(rows, ["Ledare, Alfa", "Ledare, Beta"])

        self.assertEqual([namn for namn, _ in grupper], ["Ledare, Alfa", "Ledare, Beta"])
        self.assertEqual([rad["fullname"] for rad in grupper[1][1]], ["Ledare, Beta", "Person, Aktiv"])

    def test_does_not_force_overseer_before_alphabetical_name_order(self):
        rows = [
            {
                "fullname": "Öhman, Grupp",
                "lastname": "Öhman",
                "firstname": "Grupp",
                "inactive": "",
                "group_overseer": "Öhman, Grupp",
            },
            {
                "fullname": "Andersson, Anna",
                "lastname": "Andersson",
                "firstname": "Anna",
                "inactive": "",
                "group_overseer": "Öhman, Grupp",
            },
        ]

        grupper = gruppera(rows, ["Öhman, Grupp"])

        self.assertEqual(
            [rad["fullname"] for rad in grupper[0][1]],
            ["Andersson, Anna", "Öhman, Grupp"],
        )

    def test_paginates_groups_in_two_top_aligned_rows_of_four_columns(self):
        grupper = [
            (f"Ledare {index}", [{"fullname": f"Ledare {index}", "group_overseer": f"Ledare {index}"}])
            for index in range(1, 10)
        ]

        sidor = dela_upp_i_sidor(grupper)
        tabell = skapa_tjanstegruppstabell(sidor[0], 1, skapa_stilar(), 400)

        self.assertEqual([len(sida) for sida in sidor], [8, 1])
        self.assertEqual(len(tabell._cellvalues), 2)
        self.assertEqual([len(rad) for rad in tabell._cellvalues], [4, 4])
        self.assertEqual(tabell._colWidths, [100, 100, 100, 100])

    def test_reads_header_only_csv_as_empty_export(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "contacts.csv"
            with csv_path.open("w", encoding="utf-8", newline="") as fil:
                writer = csv.DictWriter(
                    fil,
                    fieldnames=[
                        "lastname",
                        "firstname",
                        "fullname",
                        "inactive",
                        "group_overseer",
                    ],
                )
                writer.writeheader()

            self.assertEqual(las_csv(csv_path), [])

    def test_creates_pdf_with_numbered_group_headers(self):
        if shutil.which("pdftotext") is None:
            self.skipTest("pdftotext saknas")

        rows = [
            {
                "fullname": "Ledare, Alfa",
                "lastname": "Ledare",
                "firstname": "Alfa",
                "inactive": "",
                "group_overseer": "Ledare, Alfa",
            },
            {
                "fullname": "Person, Aktiv",
                "lastname": "Person",
                "firstname": "Aktiv",
                "inactive": "",
                "group_overseer": "Ledare, Alfa",
            },
            {
                "fullname": "Person, Overksam",
                "lastname": "Person",
                "firstname": "Overksam",
                "inactive": "1",
                "group_overseer": "Ledare, Alfa",
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "tjanstegrupper.pdf"
            skapa_pdf(rows, output, ["Ledare, Alfa"])

            text = subprocess.run(
                ["pdftotext", str(output), "-"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout

        self.assertIn("Tjänstegrupper", text)
        self.assertIn("1. Ledare, Alfa", text)
        self.assertIn("Person, Aktiv", text)
        self.assertNotIn("Person, Overksam", text)

    def test_main_prompts_for_group_order(self):
        from create_service_group_list import main

        rows = [
            {"fullname": "Ledare, Alfa", "group_overseer": "Ledare, Alfa"},
            {"fullname": "Ledare, Beta", "group_overseer": "Ledare, Beta"},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "contacts.csv"
            output = Path(tmpdir) / "tjanstegrupper.pdf"
            csv_path.write_text("fullname,inactive,group_overseer\n", encoding="utf-8")

            with (
                patch("sys.argv", ["create_service_group_list.py", str(csv_path), "-o", str(output)]),
                patch("builtins.input", return_value="2,1"),
                patch("create_service_group_list.las_csv", return_value=rows),
                patch("create_service_group_list.skapa_pdf") as skapa_pdf_mock,
            ):
                main()

            self.assertEqual(
                skapa_pdf_mock.call_args.args[2],
                ["Ledare, Beta", "Ledare, Alfa"],
            )


if __name__ == "__main__":
    unittest.main()
