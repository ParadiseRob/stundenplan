from bs4 import BeautifulSoup
from ics import Calendar, Event
from datetime import datetime, timedelta
import pytz
import uuid

# --- Einstellungen ---
input_file = "stundenplan.html"  # Deine HTML-Datei
output_file = "stundenplan.ics"  # Ausgabe-ICS-Datei
timezone = pytz.timezone("Europe/Berlin")

# --- Einlesen und Parsen ---
with open(input_file, "r", encoding="windows-1252") as f:
    soup = BeautifulSoup(f, "html.parser")

cal = Calendar()

# Alle Tabellen im Dokument
tables = soup.find_all("table")

for table in tables:
    # Suche das Datum im <th>
    th = table.find("th")
    if not th:
        continue
    try:
        datum = datetime.strptime(th.text.strip(), "%d.%m.%Y").date()
    except ValueError:
        continue  # Kein valides Datum, überspringen

    # Finde alle Unterrichtszellen (<td> mit bgcolor C0C0C0)
    tds = table.find_all("td", bgcolor="#C0C0C0")

    for td in tds:
        fonts = td.find_all("font")
        if len(fonts) < 2:
            continue  # unvollständig

        zeit_text = fonts[0].text.strip()
        fach = fonts[1].text.strip()

        if not zeit_text or not fach:
            continue  # leeres Feld

        # Zeiten parsen
        try:
            start_str, end_str = zeit_text.split("-")
            start_time = datetime.strptime(start_str.strip(), "%H:%M").time()
            end_time = datetime.strptime(end_str.strip(), "%H:%M").time()
        except ValueError:
            continue  # Formatfehler

        # Lokales Start- und Endzeit-Datum kombinieren
        start_dt = timezone.localize(datetime.combine(datum, start_time))
        end_dt = timezone.localize(datetime.combine(datum, end_time))

        # Event erzeugen
        event = Event()
        event.name = fach
        event.begin = start_dt.astimezone(pytz.utc)
        event.end = end_dt.astimezone(pytz.utc)
        event.uid = f"{uuid.uuid4()}@stundenplan"

        cal.events.add(event)

# --- Speichern ---
with open(output_file, "w", encoding="utf-8") as f:
    f.writelines(cal.serialize_iter())
