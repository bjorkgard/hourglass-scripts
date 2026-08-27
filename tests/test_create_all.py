import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from io import StringIO
from pathlib import Path
from unittest.mock import patch


class CreateAllTests(unittest.TestCase):
    def test_selects_only_csv_from_in_directory(self):
        from create_all import hitta_csv

        with tempfile.TemporaryDirectory() as tmpdir:
            in_dir = Path(tmpdir) / "in"
            in_dir.mkdir()
            csv_path = in_dir / "hourglass.csv"
            csv_path.write_text("fullname\n", encoding="utf-8")

            self.assertEqual(hitta_csv(in_dir), csv_path)

    def test_asks_which_csv_to_use_when_multiple_exist(self):
        from create_all import hitta_csv

        with tempfile.TemporaryDirectory() as tmpdir:
            in_dir = Path(tmpdir) / "in"
            in_dir.mkdir()
            first = in_dir / "a.csv"
            second = in_dir / "b.csv"
            first.write_text("fullname\n", encoding="utf-8")
            second.write_text("fullname\n", encoding="utf-8")

            with (
                patch("builtins.input", return_value="2"),
                redirect_stdout(StringIO()),
            ):
                self.assertEqual(hitta_csv(in_dir), second)

    def test_reuses_complete_config_without_prompting(self):
        from create_all import hamta_adress_config

        poster = [
            {"group_overseer": "Björkgård, Nathanael"},
            {"group_overseer": "Sundberg, Joel"},
        ]
        config = {
            "adresslista": {
                "designval": "2",
                "gruppordning": ["Björkgård, Nathanael", "Sundberg, Joel"],
                "kretstillsyningsman": {
                    "namn": "Test Kretstillsyningsman",
                    "adress": "Testgatan 1",
                    "postnummer": "12345",
                    "ort": "Teststad",
                    "mobiltelefon": "070-000 00 00",
                    "telefon": "",
                    "epost": "test@example.com",
                },
            }
        }

        with patch("builtins.input", side_effect=AssertionError("Ska inte fråga")):
            adress_config, changed = hamta_adress_config(config, poster)

        self.assertFalse(changed)
        self.assertEqual(adress_config["designval"], "2")
        self.assertEqual(
            adress_config["gruppordning"],
            ["Björkgård, Nathanael", "Sundberg, Joel"],
        )

    def test_creates_config_when_missing(self):
        from create_all import hamta_adress_config

        poster = [
            {"group_overseer": "Björkgård, Nathanael"},
            {"group_overseer": "Sundberg, Joel"},
        ]

        svar = iter(
            [
                "2",
                "2,1",
                "Test Kretstillsyningsman",
                "Testgatan 1",
                "12345",
                "Teststad",
                "070-000 00 00",
                "",
                "test@example.com",
            ]
        )
        with (
            patch("builtins.input", side_effect=lambda _prompt="": next(svar)),
            redirect_stdout(StringIO()),
        ):
            adress_config, changed = hamta_adress_config({}, poster)

        self.assertTrue(changed)
        self.assertEqual(adress_config["designval"], "2")
        self.assertEqual(
            adress_config["gruppordning"],
            ["Sundberg, Joel", "Björkgård, Nathanael"],
        )
        self.assertEqual(
            adress_config["kretstillsyningsman"]["epost"],
            "test@example.com",
        )

    def test_prompts_when_cached_group_order_contains_duplicates(self):
        from create_all import hamta_adress_config

        poster = [
            {"group_overseer": "Björkgård, Nathanael"},
            {"group_overseer": "Sundberg, Joel"},
        ]
        config = {
            "adresslista": {
                "designval": "2",
                "gruppordning": [
                    "Björkgård, Nathanael",
                    "Björkgård, Nathanael",
                    "Sundberg, Joel",
                ],
                "kretstillsyningsman": {
                    "namn": "Test Kretstillsyningsman",
                    "adress": "Testgatan 1",
                    "postnummer": "12345",
                    "ort": "Teststad",
                    "mobiltelefon": "070-000 00 00",
                    "telefon": "",
                    "epost": "test@example.com",
                },
            }
        }

        with (
            patch("builtins.input", return_value="2,1"),
            redirect_stdout(StringIO()),
        ):
            adress_config, changed = hamta_adress_config(config, poster)

        self.assertTrue(changed)
        self.assertEqual(
            adress_config["gruppordning"],
            ["Sundberg, Joel", "Björkgård, Nathanael"],
        )

    def test_reconfigure_ignores_existing_config(self):
        from create_all import hamta_adress_config

        poster = [{"group_overseer": "Björkgård, Nathanael"}]
        config = {
            "adresslista": {
                "designval": "1",
                "gruppordning": ["Björkgård, Nathanael"],
                "kretstillsyningsman": {
                    "namn": "Gammalt Namn",
                    "adress": "",
                    "postnummer": "",
                    "ort": "",
                    "mobiltelefon": "",
                    "telefon": "",
                    "epost": "",
                },
            }
        }
        svar = iter(["3", "1", "Nytt Namn", "", "", "", "", "", "ny@example.com"])

        with (
            patch("builtins.input", side_effect=lambda _prompt="": next(svar)),
            redirect_stdout(StringIO()),
        ):
            adress_config, changed = hamta_adress_config(config, poster, reconfigure=True)

        self.assertTrue(changed)
        self.assertEqual(adress_config["designval"], "3")
        self.assertEqual(adress_config["kretstillsyningsman"]["namn"], "Nytt Namn")

    def test_run_all_creates_three_pdfs_and_saves_config(self):
        from create_all import run_all

        rows = [{"group_overseer": "Björkgård, Nathanael"}]

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            in_dir = root / "in"
            out_dir = (root / "out").resolve()
            in_dir.mkdir()
            csv_path = in_dir / "hourglass.csv"
            csv_path.write_text("fullname\n", encoding="utf-8")

            svar = iter(["2", "1", "Test KT", "", "", "", "", "", "kt@example.com"])
            with (
                patch("builtins.input", side_effect=lambda _prompt="": next(svar)),
                patch("create_all.address_las_csv", return_value=rows),
                patch("create_all.name_las_csv", return_value=rows),
                patch("create_all.voting_las_csv", return_value=rows),
                patch("create_all.skapa_adress_pdf") as skapa_adress_pdf,
                patch("create_all.skapa_namn_pdf") as skapa_namn_pdf,
                patch("create_all.skapa_rost_pdf") as skapa_rost_pdf,
                patch("create_all.skapa_rapport") as skapa_rapport,
                redirect_stdout(StringIO()),
            ):
                outputs = run_all(root=root)

            idag = date.today().isoformat()
            self.assertEqual(
                {output.name for output in outputs},
                {
                    f"Adresslista_{idag}.pdf",
                    f"Namnlista_{idag}.pdf",
                    f"Röstlängd_{idag}.pdf",
                },
            )
            self.assertTrue((root / "config.json").exists())
            saved = json.loads((root / "config.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["adresslista"]["designval"], "2")
            self.assertEqual(skapa_adress_pdf.call_args.args[1].parent.resolve(), out_dir)
            self.assertEqual(skapa_namn_pdf.call_args.args[1].parent.resolve(), out_dir)
            self.assertEqual(skapa_rost_pdf.call_args.args[1].parent.resolve(), out_dir)
            self.assertEqual(skapa_rapport.call_count, 1)
            self.assertEqual(skapa_rapport.call_args.args[0], rows)
            self.assertEqual(
                skapa_rapport.call_args.args[1].resolve(),
                (root / "history" / "contact_history.json").resolve(),
            )
            self.assertEqual(skapa_rapport.call_args.args[2].resolve(), out_dir)


if __name__ == "__main__":
    unittest.main()
