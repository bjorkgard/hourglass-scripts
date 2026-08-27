# hourglass-scripts

Små Python-skript för att skapa PDF-listor från en CSV-export från Hourglass.

Projektet innehåller:

- [Adresslista](docs/address-list.md) - skapar en svensk adresslista grupperad
  per grupptillsyningsman.
- [Namnlista](docs/name-list.md) - skapar en namnlista grupperad per familj.
- [Röstlängd](docs/voting-list.md) - skapar en lista över döpta aktiva personer
  med kryssrutor för närvaro.

## Kom igång lokalt

Klona repot och gå in i projektmappen:

```bash
git clone git@github.com:bjorkgard/hourglass-scripts.git
cd hourglass-scripts
```

Skapa gärna en virtuell Python-miljö:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Installera beroenden:

```bash
python3 -m pip install reportlab
```

Läs respektive skriptdokumentation för hur skripten körs och vilka fält som
behövs i CSV-filen.

## Tester

Kör alla tester:

```bash
python3 -m unittest discover
```

Vissa integrationstester använder `example_csv/hourglass-contactlist.csv` om den
finns lokalt. Mappen `example_csv/` ignoreras av git eftersom den kan innehålla
personuppgifter.

## Hjälp till

Bidrag är välkomna. Håll ändringar små och fokuserade:

1. Skapa eller uppdatera tester för ändringen.
2. Kör `python3 -m unittest discover`.
3. Kontrollera att inga CSV-filer, PDF:er, cachefiler eller lokala miljöfiler
   följer med i `git status`.
4. Skriv en kort commit som beskriver ändringen.
