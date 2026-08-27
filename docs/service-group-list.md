# Tjänstegrupper

`create_service_group_list.py` skapar en PDF med församlingens aktiva personer
sorterade per tjänstegrupp.

PDF:en använder samma visuella grundstil som de övriga rapporterna. Grupperna
läggs i fyra kolumner från vänster till höger och därefter på nästa rad, så upp
till åtta grupper får plats per sida. Varje grupp har en rubrik med löpnummer
och grupptillsyningsmannens namn, till exempel:

```text
1. Efternamn, Förnamn
```

Personerna sorteras alfabetiskt inom varje grupp. Grupptillsyningsmannen visas
med fet stil där namnet hamnar i sorteringen. Personer som är markerade som
overksamma i CSV-filen tas inte med.

## Kör manuellt

```bash
python3 create_service_group_list.py hourglass-contactlist.csv
```

Skriptet frågar efter ordningen på grupptillsyningsmännen. Ange alla nummer en
gång, separerade med kommatecken, till exempel:

```text
3,1,4,2
```

Du kan välja utdatafil med `-o`:

```bash
python3 create_service_group_list.py hourglass-contactlist.csv -o out/Tjänstegrupper.pdf
```

## CSV-fält

Skriptet kräver dessa fält:

- `fullname`
- `inactive`
- `group_overseer`

Om `lastname` och `firstname` finns används de som stöd för sortering inom varje
grupp.
