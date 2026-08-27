#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Skapa en svensk tjänstegruppslista i PDF-format från en Hourglass-CSV.

Kör:
    python3 create_service_group_list.py hourglass-contactlist.csv

Beroende:
    python3 -m pip install reportlab
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.platypus import LongTable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, TableStyle
except ImportError:
    print("ReportLab saknas. Installera det med:")
    print("  python3 -m pip install reportlab")
    sys.exit(1)


STIL = {
    "marginal": 8.5 * mm,
    "topp": 8 * mm,
    "botten": 11 * mm,
    "titelstorlek": 19,
    "rubrikstorlek": 8.6,
    "textstorlek": 8.2,
    "radavstand": 10.0,
    "radpadding": 1.25,
    "grupprubrik_padding": 3.2,
    "footerstorlek": 7.2,
    "kolumngap": 4.8 * mm,
    "accent": colors.HexColor("#35536B"),
    "accent_mork": colors.HexColor("#233A4B"),
    "header_bg": colors.HexColor("#E8EEF2"),
    "grid": colors.HexColor("#CDD4D9"),
    "text": colors.HexColor("#20272C"),
}

ANTAL_KOLUMNER = 4
RADER_PER_SIDA = 2
GRUPPER_PER_SIDA = ANTAL_KOLUMNER * RADER_PER_SIDA


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

    krav = {"fullname", "inactive", "group_overseer"}
    saknas = sorted(krav - falt)
    if saknas:
        raise ValueError("CSV-filen saknar följande kolumner: " + ", ".join(saknas))
    return poster


def aktiv(rad: Dict[str, str]) -> bool:
    return not ren(rad.get("inactive"))


def fullname(rad: Dict[str, str]) -> str:
    return ren(rad.get("fullname")) or ", ".join(
        x for x in [ren(rad.get("lastname")), ren(rad.get("firstname"))] if x
    )


def person_sortnyckel(rad: Dict[str, str]):
    return (
        svensk_sortnyckel(rad.get("lastname", "")),
        svensk_sortnyckel(rad.get("firstname", "")),
        svensk_sortnyckel(rad.get("fullname", "")),
    )


def aktuella_grupper(poster: List[Dict[str, str]]) -> List[str]:
    return sorted(
        {ren(rad.get("group_overseer")) or "Utan grupptillsyningsman" for rad in poster if aktiv(rad)},
        key=svensk_sortnyckel,
    )


def valj_gruppordning(grupper: List[str]) -> List[str]:
    if not grupper:
        return []

    print("\nORDNING PÅ GRUPPTILLSYNINGSMÄN")
    print("Följande grupptillsyningsmän hittades bland aktiva personer i CSV-filen:")
    for index, overseer in enumerate(grupper, start=1):
        print(f"  {index}. {overseer}")

    print("\nSkriv ALLA nummer i den ordning som grupperna ska visas i PDF-filen.")
    print("Exempel: 3,1,4,2")

    while True:
        svar = input("Önskad ordning: ").strip()
        delar = [del_.strip() for del_ in svar.replace(";", ",").split(",") if del_.strip()]
        try:
            nummer = [int(del_) for del_ in delar]
        except ValueError:
            print("Använd endast nummer separerade med kommatecken.")
            continue

        giltiga = set(range(1, len(grupper) + 1))
        if len(nummer) != len(grupper) or set(nummer) != giltiga:
            print(f"Ange varje nummer från 1 till {len(grupper)} exakt en gång.")
            continue

        return [grupper[nr - 1] for nr in nummer]


def gruppera(
    poster: Iterable[Dict[str, str]], gruppordning: List[str]
) -> List[Tuple[str, List[Dict[str, str]]]]:
    grupper: Dict[str, List[Dict[str, str]]] = {}
    for rad in poster:
        if not aktiv(rad):
            continue
        overseer = ren(rad.get("group_overseer")) or "Utan grupptillsyningsman"
        grupper.setdefault(overseer, []).append(rad)

    resultat = []
    for overseer in gruppordning:
        if overseer not in grupper:
            continue

        medlemmar = sorted(grupper[overseer], key=person_sortnyckel)
        if medlemmar:
            resultat.append((overseer, medlemmar))
    return resultat


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
        "rubrik": ParagraphStyle(
            "Rubrik",
            fontName="Helvetica-Bold",
            fontSize=STIL["rubrikstorlek"],
            leading=STIL["rubrikstorlek"] + 1.4,
            textColor=STIL["accent_mork"],
            spaceAfter=0,
            spaceBefore=0,
            splitLongWords=True,
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
        "namn_fet": ParagraphStyle(
            "NamnFet",
            fontName="Helvetica-Bold",
            fontSize=STIL["textstorlek"],
            leading=STIL["radavstand"],
            textColor=STIL["text"],
            spaceAfter=0,
            spaceBefore=0,
            splitLongWords=True,
        ),
    }


def titelblock(stilar: Dict[str, ParagraphStyle], totalbredd: float):
    linje = LongTable([[""]], colWidths=[totalbredd], rowHeights=[0.7], hAlign="LEFT")
    linje.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), STIL["accent"])]))
    return [
        Paragraph("Tjänstegrupper", stilar["titel"]),
        Spacer(1, 2.2 * mm),
        linje,
        Spacer(1, 1.8 * mm),
    ]


def skapa_gruppblock(
    nummer: int,
    overseer: str,
    medlemmar: List[Dict[str, str]],
    stilar: Dict[str, ParagraphStyle],
    kolumnbredd: float,
):
    data = [[Paragraph(f"{nummer}. {html_escape(overseer)}", stilar["rubrik"])]]
    for rad in medlemmar:
        namn = fullname(rad)
        stil = stilar["namn_fet"] if namn == overseer else stilar["namn"]
        data.append([Paragraph(html_escape(namn), stil)])

    block = LongTable(data, colWidths=[kolumnbredd], hAlign="LEFT", splitByRow=1)
    block.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), STIL["header_bg"]),
                ("LINEABOVE", (0, 0), (-1, 0), 0.7, STIL["accent_mork"]),
                ("LINEBELOW", (0, 0), (-1, 0), 0.45, STIL["accent_mork"]),
                ("BOX", (0, 0), (-1, -1), 0.35, STIL["grid"]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3.4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3.4),
                ("TOPPADDING", (0, 0), (-1, 0), STIL["grupprubrik_padding"]),
                ("BOTTOMPADDING", (0, 0), (-1, 0), STIL["grupprubrik_padding"]),
                ("TOPPADDING", (0, 1), (-1, -1), STIL["radpadding"]),
                ("BOTTOMPADDING", (0, 1), (-1, -1), STIL["radpadding"]),
            ]
        )
    )
    return block


def dela_upp_i_sidor(grupper: List[Tuple[str, List[Dict[str, str]]]]):
    if not grupper:
        return [[]]
    return [grupper[index : index + GRUPPER_PER_SIDA] for index in range(0, len(grupper), GRUPPER_PER_SIDA)]


def skapa_tjanstegruppstabell(
    grupper: List[Tuple[str, List[Dict[str, str]]]],
    startnummer: int,
    stilar: Dict[str, ParagraphStyle],
    totalbredd: float,
):
    if not grupper:
        tabell = LongTable(
            [[Paragraph("Inga aktiva personer hittades.", stilar["namn"])]],
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

    kolumnbredd = totalbredd / ANTAL_KOLUMNER
    data = []
    for radstart in range(0, len(grupper), ANTAL_KOLUMNER):
        tabellrad = []
        for kolumnindex in range(ANTAL_KOLUMNER):
            gruppindex = radstart + kolumnindex
            if gruppindex < len(grupper):
                overseer, medlemmar = grupper[gruppindex]
                tabellrad.append(
                    skapa_gruppblock(
                        startnummer + gruppindex,
                        overseer,
                        medlemmar,
                        stilar,
                        kolumnbredd,
                    )
                )
            else:
                tabellrad.append("")
        data.append(tabellrad)

    tabell = LongTable(
        data,
        colWidths=[kolumnbredd] * ANTAL_KOLUMNER,
        hAlign="LEFT",
        splitByRow=1,
    )
    tabell.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 1), (-1, -1), STIL["kolumngap"]),
            ]
        )
    )
    return tabell


def skapa_pdf(poster: List[Dict[str, str]], output: Path, gruppordning: List[str]):
    stilar = skapa_stilar()
    bredd, _ = A4
    totalbredd = bredd - 2 * STIL["marginal"]
    grupper = gruppera(poster, gruppordning)

    doc = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        rightMargin=STIL["marginal"],
        leftMargin=STIL["marginal"],
        topMargin=STIL["topp"],
        bottomMargin=STIL["botten"],
        title="Tjänstegrupper",
        author="Tjänstegruppsgenerator",
        subject="Tjänstegrupper",
    )

    story = []
    story.extend(titelblock(stilar, totalbredd))
    for sidindex, sidgrupper in enumerate(dela_upp_i_sidor(grupper)):
        if sidindex:
            story.append(PageBreak())
        story.append(skapa_tjanstegruppstabell(sidgrupper, sidindex * GRUPPER_PER_SIDA + 1, stilar, totalbredd))

    idag = date.today().isoformat()
    footer_info = {"datum": idag}
    doc.build(story, canvasmaker=lambda *a, **kw: NumreradCanvas(*a, footer_info=footer_info, **kw))


def main():
    parser = argparse.ArgumentParser(
        description="Skapa en PDF-lista över tjänstegrupper från en Hourglass-CSV."
    )
    parser.add_argument("csvfil", help="Sökväg till CSV-filen")
    parser.add_argument(
        "-o",
        "--output",
        help="Namn på PDF-filen. Standard: Tjänstegrupper_ÅÅÅÅ-MM-DD.pdf",
    )
    args = parser.parse_args()

    csv_sokvag = Path(args.csvfil).expanduser().resolve()

    try:
        poster = las_csv(csv_sokvag)
    except Exception as exc:
        print(f"\nKunde inte läsa CSV-filen: {exc}")
        sys.exit(1)

    grupper = aktuella_grupper(poster)
    gruppordning = valj_gruppordning(grupper)
    output = (
        Path(args.output).expanduser().resolve()
        if args.output
        else Path.cwd() / f"Tjänstegrupper_{date.today().isoformat()}.pdf"
    )

    try:
        skapa_pdf(poster, output, gruppordning)
    except Exception as exc:
        print(f"\nKunde inte skapa PDF-filen: {exc}")
        sys.exit(1)

    print("\nKlart.")
    print(f"PDF skapad: {output}")


if __name__ == "__main__":
    main()
