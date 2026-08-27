import csv
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from create_voting_list import RADER_PER_SIDA, STIL, dela_upp_i_sidor, filtrera_rostande, las_csv, narvaro_text, skapa_pdf


EXAMPLE_CSV = Path(__file__).resolve().parents[1] / "example_csv" / "hourglass-contactlist.csv"


class VotingListTests(unittest.TestCase):
    def test_filters_baptized_active_publishers_and_sorts_by_fullname(self):
        poster = [
            {"fullname": "Österlid, Isabel", "baptism": "2003-07-21", "inactive": ""},
            {"fullname": "Ahlberg, Wendela", "baptism": "1993-07-17", "inactive": ""},
            {"fullname": "Bentzen, John", "baptism": "", "inactive": ""},
            {"fullname": "Arrenäs, Gunvor", "baptism": "1975-09-21", "inactive": "1"},
        ]

        rostande = filtrera_rostande(poster)

        self.assertEqual([rad["fullname"] for rad in rostande], ["Ahlberg, Wendela", "Österlid, Isabel"])

    def test_presence_summary_uses_number_of_voters(self):
        self.assertEqual(
            narvaro_text(117),
            "Av församlingens 117 döpta medlemmar var ____ närvarande.",
        )

    def test_voting_list_uses_airier_row_spacing(self):
        self.assertEqual(STIL["radavstand"], 11.0)
        self.assertEqual(STIL["radpadding"], 1.15)

    def test_page_chunks_preserve_sorted_ranges(self):
        namn = [f"Person {nummer:03d}" for nummer in range(1, RADER_PER_SIDA * 3 + 5)]

        sidor = dela_upp_i_sidor(namn)

        self.assertEqual(sidor[0], namn[: RADER_PER_SIDA * 3])
        self.assertEqual(sidor[1], namn[RADER_PER_SIDA * 3 :])

    def test_creates_pdf_when_no_rows_match_voter_filter(self):
        if shutil.which("pdftotext") is None:
            self.skipTest("pdftotext saknas")

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "contacts.csv"
            output = Path(tmpdir) / "rostlangd.pdf"
            with csv_path.open("w", encoding="utf-8", newline="") as fil:
                writer = csv.DictWriter(fil, fieldnames=["fullname", "baptism", "inactive"])
                writer.writeheader()
                writer.writerow({"fullname": "Ahlberg, Wendela", "baptism": "", "inactive": ""})
                writer.writerow({"fullname": "Österlid, Isabel", "baptism": "2003-07-21", "inactive": "1"})

            skapa_pdf(las_csv(csv_path), output)

            text = subprocess.run(
                ["pdftotext", str(output), "-"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            self.assertIn("Inga röstberättigade personer hittades.", text)
            self.assertIn("Av församlingens 0 döpta medlemmar var ____ närvarande.", text)


@unittest.skipUnless(EXAMPLE_CSV.exists(), "example_csv/hourglass-contactlist.csv saknas")
class ExampleCsvVotingListTests(unittest.TestCase):
    def test_reads_and_filters_current_example_csv(self):
        rostande = filtrera_rostande(las_csv(EXAMPLE_CSV))

        self.assertEqual(len(rostande), 117)
        self.assertEqual(rostande[0]["fullname"], "Ahlberg, Wendela")
        self.assertEqual(rostande[-1]["fullname"], "Österlid, Isabel")
        self.assertTrue(all(rad["baptism"].strip() for rad in rostande))
        self.assertTrue(all(not rad["inactive"].strip() for rad in rostande))

    def test_creates_single_page_pdf_from_current_example_csv(self):
        if shutil.which("pdfinfo") is None or shutil.which("pdftotext") is None:
            self.skipTest("pdfinfo och pdftotext saknas")

        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "rostlangd.pdf"
            skapa_pdf(las_csv(EXAMPLE_CSV), output)

            self.assertTrue(output.exists())
            self.assertGreater(output.stat().st_size, 1000)

            pdfinfo = subprocess.run(
                ["pdfinfo", str(output)],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            self.assertIn("Pages:           1", pdfinfo)

            text = subprocess.run(
                ["pdftotext", str(output), "-"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            self.assertIn("Röstlängd", text)
            self.assertIn("Ahlberg, Wendela", text)
            self.assertIn("Österlid, Isabel", text)
            self.assertIn("Av församlingens 117 döpta medlemmar var ____ närvarande.", text)


if __name__ == "__main__":
    unittest.main()
