#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Skapa TXT-rapport och lokal historik för Hourglass-kontakter."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


KONTAKTFALT = [
    "address_line1",
    "address_line2",
    "address_postalcode",
    "address_city",
    "cellphone",
    "homephone",
    "email",
]


def ren(varde: str | None) -> str:
    return (varde or "").strip()


def svensk_sortnyckel(text: str) -> str:
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


def normalisera_birth(varde: str | None) -> str:
    return ren(varde) or "0"


def personnyckel(rad: Dict[str, str]) -> str:
    return f"{ren(rad.get('fullname')).casefold()}\0{normalisera_birth(rad.get('birth'))}"


def visningsnamn(person: Dict[str, Any]) -> str:
    namn = ren(person.get("fullname"))
    birth = ren(person.get("birth"))
    if birth:
        return f"{namn} ({birth})"
    return namn


def skapa_snapshot(poster: Iterable[Dict[str, str]]) -> Dict[str, Dict[str, Any]]:
    personer: Dict[str, Dict[str, Any]] = {}
    for rad in poster:
        if not ren(rad.get("fullname")):
            raise ValueError("Alla personer i rapporten måste ha fullname.")
        nyckel = personnyckel(rad)
        personer[nyckel] = {
            "fullname": ren(rad.get("fullname")),
            "birth": normalisera_birth(rad.get("birth")),
            "kontakt": {falt: ren(rad.get(falt)) for falt in KONTAKTFALT},
        }
    return personer


def las_historik(history_path: Path) -> Dict[str, Any] | None:
    if not history_path.exists():
        return None

    with history_path.open("r", encoding="utf-8") as fil:
        historik = json.load(fil)
    if not isinstance(historik, dict):
        raise ValueError("Historikfilen måste innehålla ett JSON-objekt.")
    return historik


def spara_historik(history_path: Path, datum: str, personer: Dict[str, Dict[str, Any]]) -> None:
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("w", encoding="utf-8") as fil:
        json.dump({"datum": datum, "personer": personer}, fil, ensure_ascii=False, indent=2)
        fil.write("\n")


def sortera_personer(personer: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        personer,
        key=lambda person: (
            svensk_sortnyckel(str(person.get("fullname", ""))),
            ren(str(person.get("birth", ""))),
        ),
    )


def jamfor(
    gamla: Dict[str, Dict[str, Any]],
    aktuella: Dict[str, Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    gamla_nycklar = set(gamla)
    aktuella_nycklar = set(aktuella)

    nya = [aktuella[nyckel] for nyckel in aktuella_nycklar - gamla_nycklar]
    borttagna = [gamla[nyckel] for nyckel in gamla_nycklar - aktuella_nycklar]
    uppdaterade = [
        aktuella[nyckel]
        for nyckel in aktuella_nycklar & gamla_nycklar
        if aktuella[nyckel].get("kontakt") != gamla[nyckel].get("kontakt")
    ]

    return sortera_personer(nya), sortera_personer(uppdaterade), sortera_personer(borttagna)


def lagg_till_lista(rader: List[str], rubrik: str, personer: List[Dict[str, Any]]) -> None:
    rader.append(f"{rubrik}: {len(personer)}")
    if personer:
        rader.extend(f"- {visningsnamn(person)}" for person in personer)
    rader.append("")


def rapporttext(
    rapportdatum: str,
    jamforelsedatum: str | None,
    nya: List[Dict[str, Any]],
    uppdaterade: List[Dict[str, Any]],
    borttagna: List[Dict[str, Any]],
) -> str:
    rader = [
        "Hourglass ändringsrapport",
        f"Rapportdatum: {rapportdatum}",
        f"Jämför med: {jamforelsedatum or 'Ingen tidigare körning'}",
        "",
    ]
    lagg_till_lista(rader, "Nya namn", nya)
    lagg_till_lista(rader, "Uppdaterade kontaktuppgifter", uppdaterade)
    lagg_till_lista(rader, "Borttagna namn", borttagna)
    return "\n".join(rader).rstrip() + "\n"


def skapa_rapport(
    poster: Iterable[Dict[str, str]],
    history_path: Path,
    out_dir: Path,
    datum: str | None = None,
) -> Path:
    rapportdatum = datum or date.today().isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)

    aktuella = skapa_snapshot(poster)
    historik = las_historik(history_path)
    gamla = historik.get("personer", {}) if historik else {}
    if not isinstance(gamla, dict):
        raise ValueError("Historikfilens personlista måste vara ett JSON-objekt.")

    nya, uppdaterade, borttagna = jamfor(gamla, aktuella)
    jamforelsedatum = ren(str(historik.get("datum", ""))) if historik else None

    report_path = out_dir / f"Rapport_{rapportdatum}.txt"
    report_path.write_text(
        rapporttext(rapportdatum, jamforelsedatum, nya, uppdaterade, borttagna),
        encoding="utf-8",
    )
    spara_historik(history_path, rapportdatum, aktuella)
    return report_path
