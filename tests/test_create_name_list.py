import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from create_name_list import (
    STIL,
    bygg_familjer,
    formatera_familjenamn,
    las_csv,
    skapa_pdf,
    skapa_stilar,
    titelblock,
)


EXAMPLE_CSV = Path(__file__).resolve().parents[1] / "example_csv" / "hourglass-contactlist.csv"


class NameListTests(unittest.TestCase):
    def test_groups_families_by_address_and_orders_members(self):
        poster = [
            {
                "address_id": "200",
                "familycontact": "0",
                "lastname": "Berg",
                "firstname": "Yngve",
                "fullname": "Berg Yngve",
                "birth": "2012-03-01",
            },
            {
                "address_id": "100",
                "familycontact": "0",
                "lastname": "Andersson",
                "firstname": "Sara",
                "fullname": "Andersson Sara",
                "birth": "1980-04-01",
            },
            {
                "address_id": "100",
                "familycontact": "1",
                "lastname": "Andersson",
                "firstname": "Erik",
                "fullname": "Andersson Erik",
                "birth": "1978-01-01",
            },
            {
                "address_id": "100",
                "familycontact": "0",
                "lastname": "Andersson",
                "firstname": "Alma",
                "fullname": "Andersson Alma",
                "birth": "2010-05-01",
            },
            {
                "address_id": "200",
                "familycontact": "1",
                "lastname": "Berg",
                "firstname": "Anna",
                "fullname": "Berg Anna",
                "birth": "1975-08-20",
            },
        ]

        familjer = bygg_familjer(poster)

        self.assertEqual(
            [formatera_familjenamn(familj) for familj in familjer],
            [
                "<b>Andersson</b> Erik, Sara, Alma",
                "<b>Berg</b> Anna, Yngve",
            ],
        )

    def test_title_block_omits_privacy_text_for_compact_name_list(self):
        block = titelblock(skapa_stilar(), 500)
        plain_text = "\n".join(
            element.getPlainText()
            for element in block
            if hasattr(element, "getPlainText")
        )

        self.assertIn("Namnlista", plain_text)
        self.assertNotIn("Tillgången är begränsad och sekretessbelagd.", plain_text)
        self.assertNotIn("Personuppgifter på papper förvaras", plain_text)

    def test_name_list_uses_airier_single_page_layout(self):
        self.assertEqual(STIL["topp_mm"], 8)
        self.assertEqual(STIL["textstorlek"], 9.0)
        self.assertEqual(STIL["radavstand"], 11.0)
        self.assertEqual(STIL["radpadding"], 1.2)


@unittest.skipUnless(EXAMPLE_CSV.exists(), "example_csv/hourglass-contactlist.csv saknas")
class ExampleCsvNameListTests(unittest.TestCase):
    def test_reads_current_hourglass_example_csv(self):
        poster = las_csv(EXAMPLE_CSV)

        self.assertEqual(len(poster), 142)
        self.assertEqual(
            {"address_id", "familycontact", "lastname", "firstname", "fullname", "birth"}
            - set(poster[0]),
            set(),
        )

    def test_builds_expected_families_from_current_example_csv(self):
        familjer = bygg_familjer(las_csv(EXAMPLE_CSV))
        familjenamn = [formatera_familjenamn(familj) for familj in familjer]

        self.assertEqual(len(familjer), 103)
        self.assertEqual(familjenamn[0], "<b>Ahlberg</b> Wendela")
        self.assertEqual(familjenamn[-1], "<b>Österlid</b> Christian, Isabel")
        self.assertIn("<b>Björkgård</b> Nathanael, Elisabeth", familjenamn)

    def test_creates_single_page_pdf_from_current_example_csv(self):
        if shutil.which("pdfinfo") is None or shutil.which("pdftotext") is None:
            self.skipTest("pdfinfo och pdftotext saknas")

        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "namnlista.pdf"
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
            self.assertIn("Namnlista", text)
            self.assertIn("Ahlberg Wendela", text)
            self.assertIn("Österlid Christian, Isabel", text)
            self.assertNotIn("Tillgången är begränsad", text)


if __name__ == "__main__":
    unittest.main()
