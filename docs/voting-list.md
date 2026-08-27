# Röstlängd

`create_voting_list.py` skapar en röstlängd i PDF-format från en CSV-export från
Hourglass.

Röstlängden tar med alla personer som har `baptism` ifyllt och där `inactive`
är tomt. Namnen sorteras på `fullname` och visas på A4 i tre kolumner. Till
vänster om varje namn finns en tom kryssruta som kan bockas av vid närvaro.
Längst ner skrivs en närvarorad med det totala antalet namn i röstlängden.

## Kör skriptet

Grundkommando:

```bash
python3 create_voting_list.py hourglass-contactlist.csv
```

Ange eget namn på PDF-filen:

```bash
python3 create_voting_list.py hourglass-contactlist.csv --output rostlangd.pdf
```

Kortform:

```bash
python3 create_voting_list.py hourglass-contactlist.csv -o rostlangd.pdf
```

## Parametrar

`csvfil`

Sökväg till CSV-filen från Hourglass. Detta är obligatoriskt.

Exempel:

```bash
python3 create_voting_list.py ~/Downloads/hourglass-contactlist.csv
```

`-o`, `--output`

Valfritt namn eller sökväg för PDF-filen som skapas. Om parametern utelämnas
skapas filen i aktuell mapp med namnet `Röstlängd_ÅÅÅÅ-MM-DD.pdf`.

Exempel:

```bash
python3 create_voting_list.py hourglass-contactlist.csv --output ~/Desktop/rostlangd.pdf
```

## Obligatoriska kolumner i CSV-filen

CSV-filen måste innehålla dessa kolumner:

- `fullname`
- `baptism`
- `inactive`

Om någon kolumn saknas avbryts körningen och skriptet skriver vilka kolumner som
behöver läggas till.

## Urval och sortering

En person tas med i röstlängden när:

- `baptism` är ifyllt
- `inactive` är tomt

Namnen sorteras på `fullname`, vilket i Hourglass-exporten normalt är på formen
`Lastname, Firstname`.

## Resultat

Längst ner i PDF-filen skrivs:

```text
Av församlingens X döpta medlemmar var ____ närvarande.
```

`X` byts automatiskt ut mot antalet personer som finns med i röstlängden.

När skriptet är klart skrivs sökvägen till den skapade PDF-filen ut i terminalen.
