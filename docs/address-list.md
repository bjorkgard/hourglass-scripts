# Adresslista

`create_address_list.py` skapar en svensk adresslista i PDF-format från en
CSV-export från Hourglass.

Adresslistan grupperar personer per grupptillsyningsman och visar namn, adress,
mobiltelefon, telefon, e-post och övriga markeringar.

## Kör skriptet

Grundkommando:

```bash
python3 create_address_list.py hourglass-contactlist.csv
```

Ange eget namn på PDF-filen:

```bash
python3 create_address_list.py hourglass-contactlist.csv --output adresslista.pdf
```

Kortform:

```bash
python3 create_address_list.py hourglass-contactlist.csv -o adresslista.pdf
```

## Parametrar

`csvfil`

Sökväg till CSV-filen från Hourglass. Detta är obligatoriskt.

Exempel:

```bash
python3 create_address_list.py ~/Downloads/hourglass-contactlist.csv
```

`-o`, `--output`

Valfritt namn eller sökväg för PDF-filen som skapas. Om parametern utelämnas
skapas filen i aktuell mapp med namnet `Adresslista_ÅÅÅÅ-MM-DD.pdf`.

Exempel:

```bash
python3 create_address_list.py hourglass-contactlist.csv --output ~/Desktop/adresslista.pdf
```

## Uppgifter som fylls i när skriptet körs

Efter att CSV-filen har lästs in frågar skriptet efter följande:

1. Layout
   - `1` = Modern
   - `2` = Kompakt, standardval om du bara trycker Enter
   - `3` = Premium

2. Ordning på grupper
   - Skriptet visar alla grupptillsyningsmän som hittas i CSV-filen.
   - Skriv alla nummer i den ordning grupperna ska visas i PDF-filen.
   - Exempel: `3,1,4,2`

3. Kontaktinformation för kretstillsyningsmannen
   - Namn
   - Adress
   - Postnummer
   - Ort
   - Mobiltelefon
   - Telefon
   - E-post

Lämna ett fält tomt om uppgiften saknas.

## Obligatoriska kolumner i CSV-filen

CSV-filen måste innehålla dessa kolumner:

- `lastname`
- `firstname`
- `fullname`
- `birth`
- `email`
- `cellphone`
- `homephone`
- `address_line1`
- `address_line2`
- `address_city`
- `address_postalcode`
- `appt`
- `status`
- `inactive`
- `group_overseer`

Om någon kolumn saknas avbryts körningen och skriptet skriver vilka kolumner som
behöver läggas till.

## Markeringar i kolumnen Övrigt

Skriptet fyller automatiskt i kolumnen `Övrigt` baserat på Hourglass-data:

- `appt = Elder` visas som `Ä`
- `appt = MS` visas som `FT`
- `status = Regular Pioneer` visas som `P`
- `inactive = 1` visas som `Overksam`

## Resultat

När skriptet är klart skrivs vald layout, sökvägen till den skapade PDF-filen
och sökvägen till TXT-rapporten ut i terminalen. Rapporten jämför med senaste
lokala historik och använder `fullname` + `birth` som personnyckel, där saknat
födelsedatum räknas som `0`.
