#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Skapa en svensk adresslista i PDF-format från en Hourglass-CSV.

Kör:
    python3 create_address_list.py hourglass-contactlist.csv

Beroende:
    python3 -m pip install reportlab
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from report_history import skapa_rapport

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        LongTable,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        TableStyle,
    )
    from reportlab.pdfgen import canvas
except ImportError:
    print("ReportLab saknas. Installera det med:")
    print("  python3 -m pip install reportlab")
    sys.exit(1)


KOLUMN_NAMN = ["Namn", "Adress", "Mobiltelefon", "Telefon", "E-post", "Övrigt"]
SEKRETESSRAD_1 = "Tillgången är begränsad och sekretessbelagd."
SEKRETESSRAD_2 = (
    "Personuppgifter på papper förvaras i låsta arkivskåp som bara "
    "auktoriserad personal har tillgång till. (CRPA-Z)"
)


DESIGNER = {
    "1": {
        "namn": "Modern",
        "marginal": 11 * mm,
        "topp": 12 * mm,
        "botten": 13 * mm,
        "titelstorlek": 20,
        "underradstorlek": 7.2,
        "textstorlek": 7.7,
        "radavstand": 9.2,
        "headerstorlek": 7.5,
        "cellpadding_v": 4.1,
        "grupp_v": 5.2,
        "footerstorlek": 7.2,
        "accent": colors.HexColor("#35536B"),
        "accent_mork": colors.HexColor("#233A4B"),
        "header_bg": colors.HexColor("#E8EEF2"),
        "grupp_bg": colors.HexColor("#DCE6EC"),
        "zebra": colors.HexColor("#F7F9FA"),
        "grid": colors.HexColor("#CDD4D9"),
        "text": colors.HexColor("#20272C"),
        "grupp_text": colors.HexColor("#1E313F"),
        "titel_linjer": True,
        "premium_band": False,
        "kolumner": [0.18, 0.225, 0.122, 0.108, 0.245, 0.12],
    },
    "2": {
        "namn": "Kompakt",
        "marginal": 8.5 * mm,
        "topp": 9 * mm,
        "botten": 12 * mm,
        "titelstorlek": 18,
        "underradstorlek": 6.7,
        "textstorlek": 7.15,
        "radavstand": 8.15,
        "headerstorlek": 7.15,
        "cellpadding_v": 2.8,
        "grupp_v": 3.8,
        "footerstorlek": 7.0,
        "accent": colors.HexColor("#3E4A52"),
        "accent_mork": colors.HexColor("#252C31"),
        "header_bg": colors.HexColor("#EDEDED"),
        "grupp_bg": colors.HexColor("#E3E3E3"),
        "zebra": colors.HexColor("#F8F8F8"),
        "grid": colors.HexColor("#D4D4D4"),
        "text": colors.HexColor("#222222"),
        "grupp_text": colors.HexColor("#111111"),
        "titel_linjer": False,
        "premium_band": False,
        "kolumner": [0.18, 0.215, 0.12, 0.11, 0.245, 0.13],
    },
    "3": {
        "namn": "Premium",
        "marginal": 12 * mm,
        "topp": 13 * mm,
        "botten": 14 * mm,
        "titelstorlek": 21,
        "underradstorlek": 7.2,
        "textstorlek": 7.8,
        "radavstand": 9.35,
        "headerstorlek": 7.6,
        "cellpadding_v": 4.4,
        "grupp_v": 5.8,
        "footerstorlek": 7.2,
        "accent": colors.HexColor("#243947"),
        "accent_mork": colors.HexColor("#17252E"),
        "header_bg": colors.HexColor("#E9ECEE"),
        "grupp_bg": colors.HexColor("#D8E0E4"),
        "zebra": colors.HexColor("#F6F7F8"),
        "grid": colors.HexColor("#C9D0D4"),
        "text": colors.HexColor("#1D2428"),
        "grupp_text": colors.HexColor("#17252E"),
        "titel_linjer": False,
        "premium_band": True,
        "kolumner": [0.19, 0.22, 0.12, 0.105, 0.245, 0.12],
    },
}

HISTORY_FIL = "history/contact_history.json"


class NumreradCanvas(canvas.Canvas):
    """Canvas som kan skriva 'Sida X av Y' i sidfoten."""

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
        stil = self.footer_info["stil"]
        datum = self.footer_info["datum"]
        bredd, _ = A4
        y = 6.7 * mm
        self.saveState()
        self.setFont("Helvetica", stil["footerstorlek"])
        self.setFillColor(colors.HexColor("#333333"))
        self.drawString(stil["marginal"], y, datum)
        self.drawRightString(bredd - stil["marginal"], y, f"Sida {self._pageNumber} av {antal_sidor}")
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


def las_csv(sokvag: Path) -> List[Dict[str, str]]:
    if not sokvag.exists():
        raise FileNotFoundError(f"CSV-filen finns inte: {sokvag}")

    with sokvag.open("r", encoding="utf-8-sig", newline="") as fil:
        lasare = csv.DictReader(fil)
        falt = set(lasare.fieldnames or [])
        poster = [dict(rad) for rad in lasare]

    krav = {
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
    saknas = sorted(krav - falt)
    if saknas:
        raise ValueError("CSV-filen saknar följande kolumner: " + ", ".join(saknas))
    return poster


def valj_design() -> str:
    print("\nVälj layout:")
    print("  1. Modern")
    print("  2. Kompakt (standard)")
    print("  3. Premium")
    while True:
        svar = input("Val [2]: ").strip() or "2"
        if svar in DESIGNER:
            return svar
        print("Ange 1, 2 eller 3.")


def valj_gruppordning(poster: List[Dict[str, str]]) -> List[str]:
    grupper = sorted(
        {ren(rad.get("group_overseer")) or "Utan grupptillsyningsman" for rad in poster},
        key=svensk_sortnyckel,
    )

    print("\nORDNING PÅ GRUPPTILLSYNINGSMÄN")
    print("Följande grupptillsyningsmän hittades i CSV-filen:")
    for index, overseer in enumerate(grupper, start=1):
        print(f"  {index}. {overseer}")

    print("\nSkriv ALLA nummer i den ordning som grupperna ska visas i PDF-filen.")
    print("Exempel: 3,1,4,2")

    while True:
        svar = input("Önskad ordning: ").strip()
        if not svar:
            print("Du måste ange alla nummer exakt en gång.")
            continue

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


def fraga_epost(prompt: str = "E-post: ") -> str:
    """Läs e-post och hantera macOS-terminaler där Option+2 skickas som Esc+2."""
    svar = input(prompt).strip()
    # På svenskt Mac-tangentbord skrivs @ med Option+2. Om Terminal är inställd
    # att använda Option som Meta kan tangenttryckningen komma in som ESC + 2.
    svar = svar.replace("\x1b2", "@").replace("^[2", "@")
    return svar


def fraga_kretstillsyningsman() -> Dict[str, str]:
    print("\nKontaktinformation för kretstillsyningsmannen")
    print("Lämna ett fält tomt om uppgiften saknas.")
    return {
        "namn": input("Namn: ").strip(),
        "adress": input("Adress: ").strip(),
        "postnummer": input("Postnummer: ").strip(),
        "ort": input("Ort: ").strip(),
        "mobiltelefon": input("Mobiltelefon: ").strip(),
        "telefon": input("Telefon: ").strip(),
        "epost": fraga_epost(),
    }


def history_path_for_output(output: Path) -> Path:
    """Placera historiken bredvid out/ när adresslistan skrivs i en out-mapp."""
    root = output.parent.parent if output.parent.name == "out" else output.parent
    return root / HISTORY_FIL


def ovrligt(rad: Dict[str, str]) -> str:
    markeringar: List[str] = []
    appt = ren(rad.get("appt"))
    status = ren(rad.get("status"))
    inactive = ren(rad.get("inactive"))

    if appt == "Elder":
        markeringar.append("Ä")
    elif appt == "MS":
        markeringar.append("FT")

    if status == "Regular Pioneer":
        markeringar.append("P")

    if inactive == "1":
        markeringar.append("Overksam")

    return ", ".join(markeringar)


def adress(rad: Dict[str, str]) -> str:
    delar = []
    if ren(rad.get("address_line1")):
        delar.append(ren(rad.get("address_line1")))
    if ren(rad.get("address_line2")):
        delar.append(ren(rad.get("address_line2")))
    postort = " ".join(
        del_ for del_ in [ren(rad.get("address_postalcode")), ren(rad.get("address_city"))] if del_
    )
    if postort:
        delar.append(postort)
    return "<br/>".join(delar)


def gruppera(
    poster: Iterable[Dict[str, str]], gruppordning: List[str]
) -> List[Tuple[str, List[Dict[str, str]]]]:
    grupper: Dict[str, List[Dict[str, str]]] = {}
    for rad in poster:
        overseer = ren(rad.get("group_overseer")) or "Utan grupptillsyningsman"
        grupper.setdefault(overseer, []).append(rad)

    resultat = []
    for overseer in gruppordning:
        if overseer not in grupper:
            continue
        medlemmar = sorted(
            grupper[overseer],
            key=lambda r: (
                svensk_sortnyckel(r.get("lastname", "")),
                svensk_sortnyckel(r.get("firstname", "")),
                svensk_sortnyckel(r.get("fullname", "")),
            ),
        )
        resultat.append((overseer, medlemmar))
    return resultat


def p(text: str, stil: ParagraphStyle) -> Paragraph:
    safe = (
        ren(text)
        .replace("&", "&amp;")
        .replace("<br/>", "§BR§")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("§BR§", "<br/>")
    )
    return Paragraph(safe, stil)


def skapa_stilar(stil: Dict) -> Dict[str, ParagraphStyle]:
    grund = ParagraphStyle(
        "Grund",
        fontName="Helvetica",
        fontSize=stil["textstorlek"],
        leading=stil["radavstand"],
        textColor=stil["text"],
        spaceAfter=0,
        spaceBefore=0,
        splitLongWords=True,
    )
    return {
        "normal": grund,
        "namn": ParagraphStyle("Namn", parent=grund, fontName="Helvetica-Bold"),
        "header": ParagraphStyle(
            "Header",
            parent=grund,
            fontName="Helvetica-Bold",
            fontSize=stil["headerstorlek"],
            leading=stil["headerstorlek"] + 1,
            textColor=stil["accent_mork"],
        ),
        "grupp": ParagraphStyle(
            "Grupp",
            parent=grund,
            fontName="Helvetica-Bold",
            fontSize=stil["textstorlek"] + 0.25,
            leading=stil["radavstand"] + 0.2,
            textColor=stil["grupp_text"],
        ),
        "titel": ParagraphStyle(
            "Titel",
            fontName="Helvetica-Bold",
            fontSize=stil["titelstorlek"],
            leading=stil["titelstorlek"] + 2,
            alignment=TA_CENTER,
            textColor=stil["accent_mork"],
            spaceAfter=3,
        ),
        "sekretess": ParagraphStyle(
            "Sekretess",
            fontName="Helvetica-Oblique",
            fontSize=stil["underradstorlek"],
            leading=stil["underradstorlek"] + 2,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#666666"),
            spaceAfter=0,
        ),
        "premium_titel": ParagraphStyle(
            "PremiumTitel",
            fontName="Helvetica-Bold",
            fontSize=stil["titelstorlek"],
            leading=stil["titelstorlek"] + 2,
            alignment=TA_LEFT,
            textColor=colors.white,
        ),
        "premium_sub": ParagraphStyle(
            "PremiumSub",
            fontName="Helvetica-Oblique",
            fontSize=stil["underradstorlek"],
            leading=stil["underradstorlek"] + 2,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#E8EEF1"),
        ),
    }


def titelblock(stil: Dict, stilar: Dict[str, ParagraphStyle], totalbredd: float):
    if stil["premium_band"]:
        inre = [
            [Paragraph("Adresslista", stilar["premium_titel"])],
            [Paragraph(SEKRETESSRAD_1, stilar["premium_sub"])],
            [Paragraph(SEKRETESSRAD_2, stilar["premium_sub"])],
        ]
        block = LongTable(inre, colWidths=[totalbredd], hAlign="LEFT")
        block.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), stil["accent_mork"]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 9),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                    ("TOPPADDING", (0, 0), (-1, 0), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 1),
                    ("TOPPADDING", (0, 1), (-1, -1), 1),
                    ("BOTTOMPADDING", (0, 1), (-1, -2), 0),
                    ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
                ]
            )
        )
        return [block, Spacer(1, 5.5 * mm)]

    element = [
        Paragraph("Adresslista", stilar["titel"]),
        Paragraph(SEKRETESSRAD_1, stilar["sekretess"]),
        Paragraph(SEKRETESSRAD_2, stilar["sekretess"]),
        Spacer(1, 4.2 * mm if stil["namn"] == "Modern" else 3.2 * mm),
    ]
    if stil["titel_linjer"]:
        linje = LongTable([[""]], colWidths=[totalbredd], rowHeights=[0.7])
        linje.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), stil["accent"])]))
        element.append(linje)
        element.append(Spacer(1, 2.2 * mm))
    return element


def skapa_tabell(
    grupper: List[Tuple[str, List[Dict[str, str]]]],
    kt: Dict[str, str],
    stil: Dict,
    stilar: Dict[str, ParagraphStyle],
    totalbredd: float,
) -> LongTable:
    kolumnbredder = [totalbredd * andel for andel in stil["kolumner"]]

    data = [[p(rubrik, stilar["header"]) for rubrik in KOLUMN_NAMN]]
    radtyper = ["header"]

    for overseer, medlemmar in grupper:
        data.append([p(f"Grupptillsyningsman: {overseer}", stilar["grupp"]), "", "", "", "", ""])
        radtyper.append("grupp")
        for rad in medlemmar:
            fullname = ren(rad.get("fullname")) or ", ".join(
                x for x in [ren(rad.get("lastname")), ren(rad.get("firstname"))] if x
            )
            data.append(
                [
                    p(fullname, stilar["namn"]),
                    p(adress(rad), stilar["normal"]),
                    p(ren(rad.get("cellphone")), stilar["normal"]),
                    p(ren(rad.get("homephone")), stilar["normal"]),
                    p(ren(rad.get("email")), stilar["normal"]),
                    p(ovrligt(rad), stilar["normal"]),
                ]
            )
            radtyper.append("person")

    data.append([p("Kretstillsyningsman", stilar["grupp"]), "", "", "", "", ""])
    radtyper.append("kretstillsyningsman")
    kt_adress = "<br/>".join(
        del_ for del_ in [ren(kt["adress"]), " ".join(x for x in [ren(kt["postnummer"]), ren(kt["ort"])] if x)] if del_
    )
    data.append(
        [
            p(kt["namn"], stilar["namn"]),
            p(kt_adress, stilar["normal"]),
            p(kt["mobiltelefon"], stilar["normal"]),
            p(kt["telefon"], stilar["normal"]),
            p(kt["epost"], stilar["normal"]),
            p("", stilar["normal"]),
        ]
    )
    radtyper.append("kt_person")

    tabell = LongTable(
        data,
        colWidths=kolumnbredder,
        repeatRows=1,
        hAlign="LEFT",
        splitByRow=1,
    )

    kommandon = [
        ("BACKGROUND", (0, 0), (-1, 0), stil["header_bg"]),
        ("LINEABOVE", (0, 0), (-1, 0), 0.9, stil["accent_mork"]),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, stil["accent_mork"]),
        ("GRID", (0, 0), (-1, -1), 0.35, stil["grid"]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4.2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4.2),
        ("TOPPADDING", (0, 0), (-1, -1), stil["cellpadding_v"]),
        ("BOTTOMPADDING", (0, 0), (-1, -1), stil["cellpadding_v"]),
    ]

    person_index = 0
    for i, typ in enumerate(radtyper):
        if typ in {"grupp", "kretstillsyningsman"}:
            kommandon.extend(
                [
                    ("SPAN", (0, i), (-1, i)),
                    ("BACKGROUND", (0, i), (-1, i), stil["grupp_bg"]),
                    ("LINEABOVE", (0, i), (-1, i), 1.05, stil["accent_mork"]),
                    ("TOPPADDING", (0, i), (-1, i), stil["grupp_v"]),
                    ("BOTTOMPADDING", (0, i), (-1, i), stil["grupp_v"]),
                ]
            )
            person_index = 0
        elif typ in {"person", "kt_person"}:
            if person_index % 2 == 1:
                kommandon.append(("BACKGROUND", (0, i), (-1, i), stil["zebra"]))
            person_index += 1

    tabell.setStyle(TableStyle(kommandon))
    return tabell


def skapa_pdf(
    poster: List[Dict[str, str]],
    output: Path,
    designval: str,
    kt: Dict[str, str],
    gruppordning: List[str],
):
    grupper = gruppera(poster, gruppordning)
    stil = DESIGNER[designval]
    stilar = skapa_stilar(stil)

    bredd, _ = A4
    totalbredd = bredd - 2 * stil["marginal"]

    doc = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        rightMargin=stil["marginal"],
        leftMargin=stil["marginal"],
        topMargin=stil["topp"],
        bottomMargin=stil["botten"],
        title="Adresslista",
        author="Adresslistgenerator",
        subject="Adresslista",
    )

    story = []
    story.extend(titelblock(stil, stilar, totalbredd))
    story.append(skapa_tabell(grupper, kt, stil, stilar, totalbredd))

    idag = date.today().isoformat()
    footer_info = {"stil": stil, "datum": idag}
    doc.build(story, canvasmaker=lambda *a, **kw: NumreradCanvas(*a, footer_info=footer_info, **kw))


def main():
    parser = argparse.ArgumentParser(
        description="Skapa en PDF-adresslista från en Hourglass-CSV."
    )
    parser.add_argument("csvfil", help="Sökväg till CSV-filen")
    parser.add_argument(
        "-o",
        "--output",
        help="Namn på PDF-filen. Standard: Adresslista_ÅÅÅÅ-MM-DD.pdf",
    )
    args = parser.parse_args()

    csv_sokvag = Path(args.csvfil).expanduser().resolve()

    try:
        poster = las_csv(csv_sokvag)
    except Exception as exc:
        print(f"\nKunde inte läsa CSV-filen: {exc}")
        sys.exit(1)

    designval = valj_design()
    gruppordning = valj_gruppordning(poster)
    kt = fraga_kretstillsyningsman()

    output = (
        Path(args.output).expanduser().resolve()
        if args.output
        else Path.cwd() / f"Adresslista_{date.today().isoformat()}.pdf"
    )

    try:
        skapa_pdf(poster, output, designval, kt, gruppordning)
        rapport = skapa_rapport(poster, history_path_for_output(output), output.parent)
    except Exception as exc:
        print(f"\nKunde inte skapa PDF-filen: {exc}")
        sys.exit(1)

    print("\nKlart.")
    print(f"Layout: {DESIGNER[designval]['namn']}")
    print(f"PDF skapad: {output}")
    print(f"Rapport skapad: {rapport}")


if __name__ == "__main__":
    main()
