# hourglass-scripts

Små Python-skript för att skapa PDF-listor från en CSV-export från Hourglass.

Projektet innehåller:

- [Adresslista](docs/address-list.md) - skapar en svensk adresslista grupperad
  per grupptillsyningsman.
- [Namnlista](docs/name-list.md) - skapar en namnlista grupperad per familj.
- [Röstlängd](docs/voting-list.md) - skapar en lista över döpta aktiva personer
  med kryssrutor för närvaro.
- [Tjänstegrupper](docs/service-group-list.md) - skapar en fyrkolumnslista över
  aktiva personer grupperade per tjänstegrupp.

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

## Skapa alla listor

Lägg CSV-exporten från Hourglass i `in/` och kör:

```bash
python3 create_all.py
```

PDF-filerna skapas i `out/`.
Samtidigt skapas en TXT-rapport, `Rapport_ÅÅÅÅ-MM-DD.txt`, som jämför
kontaktuppgifterna med senaste körningen och visar nya, uppdaterade och
borttagna namn. Jämförelsen använder `fullname` + `birth` som personnyckel.
Den lokala historiken sparas i `history/contact_history.json` och ignoreras av
git.

Första gången frågar kommandot efter de uppgifter som behövs för adresslistan
och tjänstegrupperna och sparar dem i en lokal `config.json`. Tjänstegrupperna
använder samma gruppordning som adresslistan. Nästa gång används config-filen
automatiskt. Om du vill skapa om config-filen kör du:

```bash
python3 create_all.py --reconfigure
```

Om `in/` innehåller flera CSV-filer frågar kommandot vilken som ska användas.

När du kör adresslistan direkt med `create_address_list.py` skapas samma typ av
rapport bredvid PDF-filen.

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
