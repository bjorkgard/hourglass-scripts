#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Skapa alla PDF-listor från en Hourglass-CSV i in/ till out/.

Kör:
    python3 create_all.py

För att skapa om config-filen:
    python3 create_all.py --reconfigure
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Tuple

from create_address_list import (
    DESIGNER,
    fraga_epost,
    las_csv as address_las_csv,
    skapa_pdf as skapa_adress_pdf,
    svensk_sortnyckel,
)
from create_name_list import las_csv as name_las_csv
from create_name_list import skapa_pdf as skapa_namn_pdf
from create_service_group_list import skapa_pdf as skapa_tjanstegrupper_pdf
from create_voting_list import las_csv as voting_las_csv
from create_voting_list import skapa_pdf as skapa_rost_pdf
from report_history import skapa_rapport


CONFIG_FIL = "config.json"
HISTORY_FIL = "history/contact_history.json"
IN_MAPP = "in"
OUT_MAPP = "out"
KT_FALT = ["namn", "adress", "postnummer", "ort", "mobiltelefon", "telefon", "epost"]


def ren(varde: str | None) -> str:
    return (varde or "").strip()


def hitta_csv(in_dir: Path) -> Path:
    if not in_dir.exists():
        raise FileNotFoundError(f"In-mappen finns inte: {in_dir}")

    csv_filer = sorted(in_dir.glob("*.csv"), key=lambda path: svensk_sortnyckel(path.name))
    if not csv_filer:
        raise FileNotFoundError(f"Lägg en CSV-fil i {in_dir} och kör igen.")
    if len(csv_filer) == 1:
        return csv_filer[0]

    print("\nFlera CSV-filer hittades i in-mappen:")
    for index, csv_fil in enumerate(csv_filer, start=1):
        print(f"  {index}. {csv_fil.name}")

    while True:
        svar = input("Vilken CSV-fil ska användas? ").strip()
        try:
            nummer = int(svar)
        except ValueError:
            print("Ange ett nummer från listan.")
            continue

        if 1 <= nummer <= len(csv_filer):
            return csv_filer[nummer - 1]
        print(f"Ange ett nummer mellan 1 och {len(csv_filer)}.")


def las_config(config_path: Path) -> Dict[str, Any]:
    if not config_path.exists():
        return {}

    with config_path.open("r", encoding="utf-8") as fil:
        try:
            config = json.load(fil)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Config-filen kunde inte läsas som JSON: {exc}") from exc

    if not isinstance(config, dict):
        raise ValueError("Config-filen måste innehålla ett JSON-objekt.")
    return config


def spara_config(config_path: Path, config: Dict[str, Any]) -> None:
    with config_path.open("w", encoding="utf-8") as fil:
        json.dump(config, fil, ensure_ascii=False, indent=2)
        fil.write("\n")


def aktuella_grupper(poster: List[Dict[str, str]]) -> List[str]:
    return sorted(
        {ren(rad.get("group_overseer")) or "Utan grupptillsyningsman" for rad in poster},
        key=svensk_sortnyckel,
    )


def valj_design() -> str:
    print("\nVälj layout för adresslistan:")
    print("  1. Modern")
    print("  2. Kompakt (standard)")
    print("  3. Premium")
    while True:
        svar = input("Val [2]: ").strip() or "2"
        if svar in DESIGNER:
            return svar
        print("Ange 1, 2 eller 3.")


def valj_gruppordning(grupper: List[str]) -> List[str]:
    if not grupper:
        return []

    print("\nORDNING PÅ GRUPPTILLSYNINGSMÄN")
    print("Följande grupptillsyningsmän hittades i CSV-filen:")
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


def komplett_kt(kt: Any) -> bool:
    return isinstance(kt, dict) and all(falt in kt for falt in KT_FALT)


def komplett_gruppordning(gruppordning: Any, grupper: List[str]) -> bool:
    return (
        isinstance(gruppordning, list)
        and len(gruppordning) == len(grupper)
        and len(set(gruppordning)) == len(gruppordning)
        and set(gruppordning) == set(grupper)
    )


def hamta_adress_config(
    config: Dict[str, Any],
    poster: List[Dict[str, str]],
    reconfigure: bool = False,
) -> Tuple[Dict[str, Any], bool]:
    grupper = aktuella_grupper(poster)
    adress_config = {} if reconfigure else dict(config.get("adresslista") or {})
    changed = reconfigure or "adresslista" not in config

    if adress_config.get("designval") not in DESIGNER:
        adress_config["designval"] = valj_design()
        changed = True

    if not komplett_gruppordning(adress_config.get("gruppordning"), grupper):
        adress_config["gruppordning"] = valj_gruppordning(grupper)
        changed = True

    if not komplett_kt(adress_config.get("kretstillsyningsman")):
        adress_config["kretstillsyningsman"] = fraga_kretstillsyningsman()
        changed = True

    return adress_config, changed


def run_all(root: Path | None = None, reconfigure: bool = False) -> List[Path]:
    root = (root or Path(__file__).resolve().parent).resolve()
    in_dir = root / IN_MAPP
    out_dir = root / OUT_MAPP
    config_path = root / CONFIG_FIL

    in_dir.mkdir(exist_ok=True)
    out_dir.mkdir(exist_ok=True)

    csv_path = hitta_csv(in_dir)
    config = {} if reconfigure else las_config(config_path)

    print(f"\nLäser CSV: {csv_path}")
    adress_poster = address_las_csv(csv_path)
    namn_poster = name_las_csv(csv_path)
    rost_poster = voting_las_csv(csv_path)

    adress_config, changed = hamta_adress_config(config, adress_poster, reconfigure=reconfigure)
    if changed:
        config["adresslista"] = adress_config
        spara_config(config_path, config)
        print(f"Config sparad: {config_path}")

    idag = date.today().isoformat()
    outputs = [
        out_dir / f"Adresslista_{idag}.pdf",
        out_dir / f"Namnlista_{idag}.pdf",
        out_dir / f"Röstlängd_{idag}.pdf",
        out_dir / f"Tjänstegrupper_{idag}.pdf",
    ]

    skapa_adress_pdf(
        adress_poster,
        outputs[0],
        adress_config["designval"],
        adress_config["kretstillsyningsman"],
        adress_config["gruppordning"],
    )
    skapa_namn_pdf(namn_poster, outputs[1])
    skapa_rost_pdf(rost_poster, outputs[2])
    skapa_tjanstegrupper_pdf(adress_poster, outputs[3], adress_config["gruppordning"])
    skapa_rapport(adress_poster, root / HISTORY_FIL, out_dir)

    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Skapa adresslista, namnlista, röstlängd och tjänstegrupper från en CSV-fil i in/."
    )
    parser.add_argument(
        "--reconfigure",
        action="store_true",
        help="Fråga om alla configvärden igen och skriv över config.json.",
    )
    args = parser.parse_args()

    try:
        outputs = run_all(reconfigure=args.reconfigure)
    except Exception as exc:
        print(f"\nKunde inte skapa listorna: {exc}")
        sys.exit(1)

    print("\nKlart.")
    for output in outputs:
        print(f"PDF skapad: {output}")


if __name__ == "__main__":
    main()
