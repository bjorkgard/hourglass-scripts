#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Skapa en svensk röstlängd i PDF-format från en Hourglass-CSV.

Kör:
    python3 create_voting_list.py hourglass-contactlist.csv

Beroende:
    python3 -m pip install reportlab
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path
from typing import Dict, List

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.platypus import Flowable, LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle
except ImportError:
    print("ReportLab saknas. Installera det med:")
    print("  python3 -m pip install reportlab")
    sys.exit(1)


STIL = {
    "marginal": 8.5 * mm,
    "topp": 8 * mm,
    "botten": 11 * mm,
    "titelstorlek": 19,
    "textstorlek": 8.2,
    "radavstand": 11.0,
    "radpadding": 1.15,
    "footerstorlek": 7.2,
    "kolumngap": 4.8 * mm,
    "accent": colors.HexColor("#35536B"),
    "accent_mork": colors.HexColor("#233A4B"),
    "grid": colors.HexColor("#CDD4D9"),
    "text": colors.HexColor("#20272C"),
}


class NumreradCanvas(canvas.Canvas):
    """Canvas som skriver datum och 'Sida X av Y' i sidfoten."""

    def __init__(self, *args, footer_info=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._sidstatus = []
        self.footer_info = footer_info or {}

    def showPage(self):
        self._sidstatus.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        antal = len(self._sidstatus)
        for status in self._sidstatus:
            self.__dict__.update(status)
            self._rita_sidfot(antal)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def _rita_sidfot(self, antal_sidor: int):
        datum = self.footer_info["datum"]
        bredd, _ = A4
        y = 6.7 * mm
        self.saveState()
        self.setFont("Helvetica", STIL["footerstorlek"])
        self.setFillColor(colors.HexColor("#333333"))
        self.drawString(STIL["marginal"], y, datum)
        self.drawRightString(bredd - STIL["marginal"], y, f"Sida {self._pageNumber} av {antal_sidor}")
        self.restoreState()


class Kryssruta(Flowable):
    """En tom ruta som kan bockas i manuellt på utskriven PDF."""

    def __init__(self, storlek: float = 3.2 * mm):
        super().__init__()
        self.width = storlek
        self.height = storlek
        self.storlek = storlek

    def draw(self):
        self.canv.saveState()
        self.canv.setStrokeColor(STIL["text"])
        self.canv.setLineWidth(0.6)
        self.canv.rect(0, 0, self.storlek, self.storlek, stroke=1, fill=0)
        self.canv.restoreState()


def ren(varde: str | None) -> str:
    return (varde or "").strip()


def svensk_sortnyckel(text: str) -> str:
    """En stabil svensk sortnyckel där å, ä och ö kommer efter z."""
    text = ren(text).casefold()
    ersattningar = {
        "å": "{a",
        "ä": "{b",
        "ö": "{c",
        "é": "e",
        "è": "e",
        "ü": "u",
    }
    return "".join(ersattningar.get(tecken, tecken) for tecken in text)


def html_escape(text: str) -> str:
    return (
        ren(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def las_csv(sokvag: Path) -> List[Dict[str, str]]:
    if not sokvag.exists():
        raise FileNotFoundError(f"CSV-filen finns inte: {sokvag}")

    with sokvag.open("r", encoding="utf-8-sig", newline="") as fil:
        lasare = csv.DictReader(fil)
        poster = [dict(rad) for rad in lasare]

    krav = {"fullname", "baptism", "inactive"}
    saknas = sorted(krav - set(poster[0].keys() if poster else []))
    if saknas:
        raise ValueError("CSV-filen saknar följande kolumner: " + ", ".join(saknas))
    return poster


def filtrera_rostande(poster: List[Dict[str, str]]) -> List[Dict[str, str]]:
    rostande = [
        rad
        for rad in poster
        if ren(rad.get("fullname")) and ren(rad.get("baptism")) and not ren(rad.get("inactive"))
    ]
    return sorted(rostande, key=lambda rad: svensk_sortnyckel(rad.get("fullname", "")))


def narvaro_text(antal_rostande: int) -> str:
    return f"Av församlingens {antal_rostande} döpta medlemmar var ____ närvarande."


def skapa_stilar() -> Dict[str, ParagraphStyle]:
    return {
        "titel": ParagraphStyle(
            "Titel",
            fontName="Helvetica-Bold",
            fontSize=STIL["titelstorlek"],
            leading=STIL["titelstorlek"] + 2,
            alignment=TA_CENTER,
            textColor=STIL["accent_mork"],
            spaceAfter=3,
        ),
        "namn": ParagraphStyle(
            "Namn",
            fontName="Helvetica",
            fontSize=STIL["textstorlek"],
            leading=STIL["radavstand"],
            textColor=STIL["text"],
            spaceAfter=0,
            spaceBefore=0,
            splitLongWords=True,
        ),
        "summering": ParagraphStyle(
            "Summering",
            fontName="Helvetica",
            fontSize=9.2,
            leading=11.2,
            alignment=TA_CENTER,
            textColor=STIL["text"],
            spaceAfter=0,
            spaceBefore=0,
        ),
    }


def titelblock(stilar: Dict[str, ParagraphStyle], totalbredd: float):
    linje = LongTable([[""]], colWidths=[totalbredd], rowHeights=[0.7])
    linje.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), STIL["accent"])]))
    return [
        Paragraph("Röstlängd", stilar["titel"]),
        Spacer(1, 2.2 * mm),
        linje,
        Spacer(1, 1.8 * mm),
    ]


def rostrad(namn: str, stil: ParagraphStyle, kolumnbredd: float):
    checkbox_bredd = 4.5 * mm
    rad = LongTable(
        [[Kryssruta(), Paragraph(namn, stil)]],
        colWidths=[checkbox_bredd, kolumnbredd - checkbox_bredd],
        hAlign="LEFT",
    )
    rad.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return rad


def skapa_rosttabell(rostande: List[Dict[str, str]], stilar: Dict[str, ParagraphStyle], totalbredd: float):
    namn = [html_escape(rad["fullname"]) for rad in rostande]
    per_kolumn = (len(namn) + 2) // 3
    kolumner = [namn[i * per_kolumn : (i + 1) * per_kolumn] for i in range(3)]
    antal_rader = max((len(kolumn) for kolumn in kolumner), default=0)
    kolumnbredd = (totalbredd - 2 * STIL["kolumngap"]) / 3

    data = []
    for index in range(antal_rader):
        rad = []
        for kolumn in kolumner:
            if index < len(kolumn):
                rad.append(rostrad(kolumn[index], stilar["namn"], kolumnbredd))
            else:
                rad.append("")
        data.append(rad)

    tabell = LongTable(
        data,
        colWidths=[kolumnbredd, kolumnbredd, kolumnbredd],
        hAlign="LEFT",
        splitByRow=1,
    )
    tabell.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), STIL["radpadding"]),
                ("BOTTOMPADDING", (0, 0), (-1, -1), STIL["radpadding"]),
                ("LINEBEFORE", (1, 0), (1, -1), 0.35, STIL["grid"]),
                ("LINEBEFORE", (2, 0), (2, -1), 0.35, STIL["grid"]),
                ("LEFTPADDING", (1, 0), (1, -1), STIL["kolumngap"]),
                ("LEFTPADDING", (2, 0), (2, -1), STIL["kolumngap"]),
            ]
        )
    )
    return tabell


def skapa_pdf(poster: List[Dict[str, str]], output: Path):
    stilar = skapa_stilar()
    bredd, _ = A4
    totalbredd = bredd - 2 * STIL["marginal"]
    rostande = filtrera_rostande(poster)

    doc = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        rightMargin=STIL["marginal"],
        leftMargin=STIL["marginal"],
        topMargin=STIL["topp"],
        bottomMargin=STIL["botten"],
        title="Röstlängd",
        author="Röstlängdsgenerator",
        subject="Röstlängd",
    )

    story = []
    story.extend(titelblock(stilar, totalbredd))
    story.append(skapa_rosttabell(rostande, stilar, totalbredd))
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph(narvaro_text(len(rostande)), stilar["summering"]))

    idag = date.today().isoformat()
    footer_info = {"datum": idag}
    doc.build(story, canvasmaker=lambda *a, **kw: NumreradCanvas(*a, footer_info=footer_info, **kw))


def main():
    parser = argparse.ArgumentParser(
        description="Skapa en PDF-röstlängd från en Hourglass-CSV."
    )
    parser.add_argument("csvfil", help="Sökväg till CSV-filen")
    parser.add_argument(
        "-o",
        "--output",
        help="Namn på PDF-filen. Standard: Röstlängd_ÅÅÅÅ-MM-DD.pdf",
    )
    args = parser.parse_args()

    csv_sokvag = Path(args.csvfil).expanduser().resolve()

    try:
        poster = las_csv(csv_sokvag)
    except Exception as exc:
        print(f"\nKunde inte läsa CSV-filen: {exc}")
        sys.exit(1)

    output = (
        Path(args.output).expanduser().resolve()
        if args.output
        else Path.cwd() / f"Röstlängd_{date.today().isoformat()}.pdf"
    )

    try:
        skapa_pdf(poster, output)
    except Exception as exc:
        print(f"\nKunde inte skapa PDF-filen: {exc}")
        sys.exit(1)

    print("\nKlart.")
    print(f"PDF skapad: {output}")


if __name__ == "__main__":
    main()
