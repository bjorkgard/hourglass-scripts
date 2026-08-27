import csv
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from create_address_list import (
    adress,
    gruppera,
    las_csv,
    ovrligt,
    skapa_pdf,
    svensk_sortnyckel,
)


EXAMPLE_CSV = Path(__file__).resolve().parents[1] / "example_csv" / "hourglass-contactlist.csv"


class AddressListTests(unittest.TestCase):
    def test_history_path_uses_parent_when_output_is_in_out_directory(self):
        from create_address_list import history_path_for_output

        output = Path("/tmp/hourglass/out/adresslista.pdf")

        self.assertEqual(
            history_path_for_output(output),
            Path("/tmp/hourglass/history/contact_history.json"),
        )

    def test_history_path_uses_output_directory_when_output_is_not_in_out_directory(self):
        from create_address_list import history_path_for_output

        output = Path("/tmp/hourglass/adresslista.pdf")

        self.assertEqual(
            history_path_for_output(output),
            Path("/tmp/hourglass/history/contact_history.json"),
        )

    def test_formats_address_from_hourglass_columns(self):
        rad = {
            "address_line1": "Kabelgatan 37D",
            "address_line2": "",
            "address_postalcode": "414 57",
            "address_city": "Göteborg",
        }

        self.assertEqual(adress(rad), "Kabelgatan 37D<br/>414 57 Göteborg")

    def test_formats_other_markers(self):
        self.assertEqual(
            ovrligt({"appt": "Elder", "status": "Regular Pioneer", "inactive": "1"}),
            "Ä, P, Overksam",
        )
        self.assertEqual(ovrligt({"appt": "MS", "status": "", "inactive": ""}), "FT")

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
                        "birth",
                        "email",
                        "cellphone",
                        "homephone",
                        "address_line1",
                        "address_line2",
                        "address_city",
                        "address_postalcode",
                        "appt",
                        "status",
                        "inactive",
                        "group_overseer",
                    ],
                )
                writer.writeheader()

            self.assertEqual(las_csv(csv_path), [])

    def test_requires_birth_for_report_identity(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "contacts.csv"
            with csv_path.open("w", encoding="utf-8", newline="") as fil:
                writer = csv.DictWriter(
                    fil,
                    fieldnames=[
                        "lastname",
                        "firstname",
                        "fullname",
                        "email",
                        "cellphone",
                        "homephone",
                        "address_line1",
                        "address_line2",
                        "address_city",
                        "address_postalcode",
                        "appt",
                        "status",
                        "inactive",
                        "group_overseer",
                    ],
                )
                writer.writeheader()

            with self.assertRaisesRegex(ValueError, "birth"):
                las_csv(csv_path)

    def test_creates_pdf_when_no_contact_rows_exist(self):
        if shutil.which("pdftotext") is None:
            self.skipTest("pdftotext saknas")

        kt = {
            "namn": "Test Kretstillsyningsman",
            "adress": "Testgatan 1",
            "postnummer": "12345",
            "ort": "Teststad",
            "mobiltelefon": "070-000 00 00",
            "telefon": "",
            "epost": "test@example.com",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "adresslista.pdf"
            skapa_pdf([], output, "2", kt, [])

            text = subprocess.run(
                ["pdftotext", str(output), "-"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            self.assertIn("Adresslista", text)
            self.assertIn("Kretstillsyningsman", text)
            self.assertIn("Test Kretstillsyningsman", text)

    def test_main_creates_report_next_to_output_pdf(self):
        from create_address_list import main

        rows = [
            {
                "fullname": "Andersson, Anna",
                "birth": "1980-01-02",
                "group_overseer": "Björkgård, Nathanael",
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            csv_path = root / "contacts.csv"
            output = root / "out" / "adresslista.pdf"
            output.parent.mkdir()
            csv_path.write_text("fullname,birth,group_overseer\n", encoding="utf-8")

            svar = iter(["2", "1", "Test KT", "", "", "", "", "", "kt@example.com"])
            with (
                patch("sys.argv", ["create_address_list.py", str(csv_path), "-o", str(output)]),
                patch("builtins.input", side_effect=lambda _prompt="": next(svar)),
                patch("create_address_list.las_csv", return_value=rows),
                patch("create_address_list.skapa_pdf"),
                patch("create_address_list.skapa_rapport") as skapa_rapport,
                redirect_stdout(StringIO()),
            ):
                main()

            self.assertEqual(skapa_rapport.call_count, 1)
            self.assertEqual(skapa_rapport.call_args.args[0], rows)
            self.assertEqual(
                skapa_rapport.call_args.args[1].resolve(),
                (root / "history" / "contact_history.json").resolve(),
            )
            self.assertEqual(skapa_rapport.call_args.args[2].resolve(), output.parent.resolve())


@unittest.skipUnless(EXAMPLE_CSV.exists(), "example_csv/hourglass-contactlist.csv saknas")
class ExampleCsvAddressListTests(unittest.TestCase):
    def test_reads_current_hourglass_example_csv(self):
        poster = las_csv(EXAMPLE_CSV)

        self.assertEqual(len(poster), 142)
        self.assertEqual(
            {
                "lastname",
                "firstname",
                "fullname",
                "email",
                "cellphone",
                "homephone",
                "address_line1",
                "address_line2",
                "address_city",
                "address_postalcode",
                "appt",
                "status",
                "inactive",
                "group_overseer",
            }
            - set(poster[0]),
            set(),
        )

    def test_groups_current_example_csv_by_overseer(self):
        poster = las_csv(EXAMPLE_CSV)
        gruppordning = sorted(
            {rad.get("group_overseer", "").strip() for rad in poster},
            key=svensk_sortnyckel,
        )
        grupper = gruppera(poster, gruppordning)

        self.assertEqual(len(grupper), 7)
        self.assertEqual(grupper[0][0], "Björkgård, Nathanael")
        self.assertEqual(grupper[-1][0], "Sundberg, Joel")
        self.assertEqual(grupper[0][1][0]["fullname"], "Arrenäs, Gunvor")

    def test_creates_pdf_from_current_example_csv(self):
        if shutil.which("pdfinfo") is None or shutil.which("pdftotext") is None:
            self.skipTest("pdfinfo och pdftotext saknas")

        poster = las_csv(EXAMPLE_CSV)
        gruppordning = sorted(
            {rad.get("group_overseer", "").strip() for rad in poster},
            key=svensk_sortnyckel,
        )
        kt = {
            "namn": "Test Kretstillsyningsman",
            "adress": "Testgatan 1",
            "postnummer": "12345",
            "ort": "Teststad",
            "mobiltelefon": "070-000 00 00",
            "telefon": "",
            "epost": "test@example.com",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "adresslista.pdf"
            skapa_pdf(poster, output, "2", kt, gruppordning)

            self.assertTrue(output.exists())
            self.assertGreater(output.stat().st_size, 1000)

            pdfinfo = subprocess.run(
                ["pdfinfo", str(output)],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            self.assertIn("Pages:           5", pdfinfo)

            text = subprocess.run(
                ["pdftotext", str(output), "-"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            self.assertIn("Adresslista", text)
            self.assertIn("Tillgången är begränsad och sekretessbelagd.", text)
            self.assertIn("Grupptillsyningsman: Björkgård, Nathanael", text)
            self.assertIn("Arrenäs, Gunvor", text)
            self.assertIn("Test Kretstillsyningsman", text)


if __name__ == "__main__":
    unittest.main()
