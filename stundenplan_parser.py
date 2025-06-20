from bs4 import BeautifulSoup
from ics import Calendar, Event
from datetime import datetime, timedelta
import uuid

with open("stundenplan.html", encoding="ISO-8859-1") as f:
    soup = BeautifulSoup(f, "html.parser")

cal = Calendar()

# Jede Tages-Spalte ist eine eigene Tabelle
tabellen = soup.find_all("table", attrs={"border": "1"})

for tabelle in tabellen:
    datum_zelle = tabelle.find("th")
    if not datum_zelle:
        continue
    datum_text = datum_zelle.get_text(strip=True)
    try:
        datum = datetime.strptime(datum_text, "%d.%m.%Y").date()
    except ValueError:
        continue

    zellen = tabelle.find_all("td")
    for zelle in zellen:
        inhalt = zelle.get_text(separator="\n", strip=True)
        zeilen = inhalt.split("\n")
        if not zeilen or len(zeilen) < 2:
            continue

        zeit_str = zeilen[0]
        fach = zeilen[1]
        if not fach:
            continue

        try:
            start_str, _ = zeit_str.split("-")
            startzeit = datetime.strptime(start_str.strip(), "%H:%M").time()
            start_dt = datetime.combine(datum, startzeit)
            end_dt = start_dt + timedelta(minutes=90)
        except Exception:
            continue

        event = Event()
        event.name = fach
        event.begin = start_dt
        event.end = end_dt
        event.uid = str(uuid.uuid4())
        cal.events.add(event)

with open("stundenplan_export.ics", "w", encoding="utf-8") as f:
    f.writelines(cal)
