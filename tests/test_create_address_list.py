import csv
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

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
