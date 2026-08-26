# Namnlista

`create_name_list.py` skapar en namnlista i PDF-format från en CSV-export från
Hourglass.

Namnlistan grupperar personer per familj med hjälp av `address_id` och visar
familjerna i en luftig tvåkolumnslayout på A4.

## Kör skriptet

Grundkommando:

```bash
python3 create_name_list.py hourglass-contactlist.csv
```

Ange eget namn på PDF-filen:

```bash
python3 create_name_list.py hourglass-contactlist.csv --output namnlista.pdf
```

Kortform:

```bash
python3 create_name_list.py hourglass-contactlist.csv -o namnlista.pdf
```

## Parametrar

`csvfil`

Sökväg till CSV-filen från Hourglass. Detta är obligatoriskt.

Exempel:

```bash
python3 create_name_list.py ~/Downloads/hourglass-contactlist.csv
```

`-o`, `--output`

Valfritt namn eller sökväg för PDF-filen som skapas. Om parametern utelämnas
skapas filen i aktuell mapp med namnet `Namnlista_ÅÅÅÅ-MM-DD.pdf`.

Exempel:

```bash
python3 create_name_list.py hourglass-contactlist.csv --output ~/Desktop/namnlista.pdf
```

## Obligatoriska kolumner i CSV-filen

CSV-filen måste innehålla dessa kolumner:

- `address_id`
- `familycontact`
- `lastname`
- `firstname`
- `fullname`
- `birth`

Personer som har samma `address_id` räknas som samma familj. Inom varje familj
placeras personen med `familycontact = 1` först. Övriga familjemedlemmar sorteras
efter `birth` med äldst först. Tomt eller okänt födelsedatum hamnar sist.

Varje familj visas på formen:

```text
Lastname Firstname, Firstname, Firstname
```

I PDF-filen skrivs efternamnet med fet stil och förnamnen med normal stil.

## Resultat

När skriptet är klart skrivs sökvägen till den skapade PDF-filen ut i terminalen.
