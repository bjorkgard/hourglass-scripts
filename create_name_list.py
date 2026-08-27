#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Skapa en svensk namnlista i PDF-format från en Hourglass-CSV.

Kör:
    python3 create_name_list.py hourglass-contactlist.csv

Beroende:
    python3 -m pip install reportlab
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.platypus import (
        LongTable,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        TableStyle,
    )
except ImportError:
    print("ReportLab saknas. Installera det med:")
    print("  python3 -m pip install reportlab")
    sys.exit(1)

STIL = {
    "marginal_mm": 8.5,
    "topp_mm": 8,
    "botten_mm": 11,
    "marginal": 8.5 * mm,
    "topp": 8 * mm,
    "botten": 11 * mm,
    "titelstorlek": 19,
    "textstorlek": 9.0,
    "radavstand": 10.6,
    "radpadding": 0.8,
    "footerstorlek": 7.2,
    "kolumngap": 6 * mm,
    "accent": colors.HexColor("#35536B"),
    "accent_mork": colors.HexColor("#233A4B"),
    "grid": colors.HexColor("#CDD4D9"),
    "text": colors.HexColor("#20272C"),
}

ANTAL_KOLUMNER = 2
RADER_PER_SIDA = 52


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
        falt = set(lasare.fieldnames or [])
        poster = [dict(rad) for rad in lasare]

    krav = {"address_id", "familycontact", "lastname", "firstname", "fullname", "birth"}
    saknas = sorted(krav - falt)
    if saknas:
        raise ValueError("CSV-filen saknar följande kolumner: " + ", ".join(saknas))
    return poster


def birth_sortnyckel(rad: Dict[str, str]) -> date:
    """Returnera födelsedatum för sortering, med okända datum sist."""
    varde = ren(rad.get("birth"))
    if not varde:
        return date.max

    for format_ in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y", "%Y%m%d"):
        try:
            return datetime.strptime(varde, format_).date()
        except ValueError:
            pass

    return date.max


def ar_familjekontakt(rad: Dict[str, str]) -> bool:
    return ren(rad.get("familycontact")) == "1"


def fornamn(rad: Dict[str, str]) -> str:
    if ren(rad.get("firstname")):
        return ren(rad.get("firstname"))
    fullname = ren(rad.get("fullname"))
    lastname = ren(rad.get("lastname"))
    if lastname and fullname.startswith(lastname):
        return fullname[len(lastname) :].strip()
    return fullname


def familj_sortnyckel(medlemmar: List[Dict[str, str]]):
    kontakt = next((rad for rad in medlemmar if ar_familjekontakt(rad)), medlemmar[0])
    return (
        svensk_sortnyckel(kontakt.get("lastname", "")),
        svensk_sortnyckel(fornamn(kontakt)),
    )


def medlem_sortnyckel(rad: Dict[str, str]):
    return (
        0 if ar_familjekontakt(rad) else 1,
        birth_sortnyckel(rad),
        svensk_sortnyckel(fornamn(rad)),
    )


def bygg_familjer(poster: Iterable[Dict[str, str]]) -> List[List[Dict[str, str]]]:
    grupper: Dict[str, List[Dict[str, str]]] = {}
    for index, rad in enumerate(poster):
        address_id = ren(rad.get("address_id")) or f"__utan_address_id_{index}"
        grupper.setdefault(address_id, []).append(rad)

    familjer = [sorted(medlemmar, key=medlem_sortnyckel) for medlemmar in grupper.values()]
    return sorted(familjer, key=familj_sortnyckel)


def formatera_familjenamn(familj: List[Dict[str, str]]) -> str:
    if not familj:
        return ""

    lastname = html_escape(familj[0].get("lastname", ""))
    namn = [html_escape(fornamn(rad)) for rad in familj if fornamn(rad)]

    if lastname and namn:
        return f"<b>{lastname}</b> " + ", ".join(namn)
    if lastname:
        return f"<b>{lastname}</b>"
    return ", ".join(namn)


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
    }


def titelblock(stilar: Dict[str, ParagraphStyle], totalbredd: float):
    linje = LongTable([[""]], colWidths=[totalbredd], rowHeights=[0.7])
    linje.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), STIL["accent"])]))
    return [
        Paragraph("Namnlista", stilar["titel"]),
        Spacer(1, 2.2 * mm),
        linje,
        Spacer(1, 1.8 * mm),
    ]


def dela_upp_i_sidor(texter: List[str]) -> List[List[str]]:
    namn_per_sida = RADER_PER_SIDA * ANTAL_KOLUMNER
    if not texter:
        return [[]]
    return [texter[index : index + namn_per_sida] for index in range(0, len(texter), namn_per_sida)]


def dela_upp_i_kolumner(texter: List[str]) -> List[List[str]]:
    per_kolumn = (len(texter) + ANTAL_KOLUMNER - 1) // ANTAL_KOLUMNER
    if per_kolumn == 0:
        return [[] for _ in range(ANTAL_KOLUMNER)]
    return [texter[i * per_kolumn : (i + 1) * per_kolumn] for i in range(ANTAL_KOLUMNER)]


def skapa_tom_namntabell(stilar: Dict[str, ParagraphStyle], totalbredd: float):
    tabell = LongTable(
        [[Paragraph("Inga familjer hittades.", stilar["namn"])]],
        colWidths=[totalbredd],
        hAlign="LEFT",
    )
    tabell.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), STIL["radpadding"]),
                ("BOTTOMPADDING", (0, 0), (-1, -1), STIL["radpadding"]),
            ]
        )
    )
    return tabell


def skapa_namntabell(texter: List[str], stilar: Dict[str, ParagraphStyle], totalbredd: float):
    if not texter:
        return skapa_tom_namntabell(stilar, totalbredd)

    vanster, hoger = dela_upp_i_kolumner(texter)
    antal_rader = max(len(vanster), len(hoger))

    data = []
    for index in range(antal_rader):
        data.append(
            [
                Paragraph(vanster[index], stilar["namn"]) if index < len(vanster) else "",
                "",
                Paragraph(hoger[index], stilar["namn"]) if index < len(hoger) else "",
            ]
        )

    tabell = LongTable(
        data,
        colWidths=[
            (totalbredd - STIL["kolumngap"]) / 2,
            STIL["kolumngap"],
            (totalbredd - STIL["kolumngap"]) / 2,
        ],
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
            ]
        )
    )
    return tabell


def skapa_pdf(poster: List[Dict[str, str]], output: Path):
    stilar = skapa_stilar()
    bredd, _ = A4
    totalbredd = bredd - 2 * STIL["marginal"]
    familjer = bygg_familjer(poster)

    doc = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        rightMargin=STIL["marginal"],
        leftMargin=STIL["marginal"],
        topMargin=STIL["topp"],
        bottomMargin=STIL["botten"],
        title="Namnlista",
        author="Namnlistgenerator",
        subject="Namnlista",
    )

    story = []
    story.extend(titelblock(stilar, totalbredd))
    texter = [formatera_familjenamn(familj) for familj in familjer if formatera_familjenamn(familj)]
    for sidindex, sidtexter in enumerate(dela_upp_i_sidor(texter)):
        if sidindex:
            story.append(PageBreak())
        story.append(skapa_namntabell(sidtexter, stilar, totalbredd))

    idag = date.today().isoformat()
    footer_info = {"datum": idag}
    doc.build(story, canvasmaker=lambda *a, **kw: NumreradCanvas(*a, footer_info=footer_info, **kw))


def main():
    parser = argparse.ArgumentParser(
        description="Skapa en PDF-namnlista grupperad på familjer från en Hourglass-CSV."
    )
    parser.add_argument("csvfil", help="Sökväg till CSV-filen")
    parser.add_argument(
        "-o",
        "--output",
        help="Namn på PDF-filen. Standard: Namnlista_ÅÅÅÅ-MM-DD.pdf",
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
        else Path.cwd() / f"Namnlista_{date.today().isoformat()}.pdf"
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
