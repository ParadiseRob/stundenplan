from bs4 import BeautifulSoup
from ics import Calendar, Event
from datetime import datetime, timedelta
import uuid
import pytz

# === Konfiguration ===
FACHNAMEN = {
    "Termin Ausbildung",
    "KFM",
    "RdG",
    "Verworga",
    "AVR",
    "Buchf",
    "HSK",
    "BGB",
    "Pers.R",
    "Lehrprobe",
}

# === HTML laden ===
with open("stundenplan.html", encoding="latin1") as f:
    soup = BeautifulSoup(f, "html.parser")

cal = Calendar()
timezone = pytz.timezone("Europe/Berlin")

# === Tabellen mit Datum verarbeiten ===
for table in soup.find_all("table", {"border": "1"}):
    header = table.find("th")
    if not header:
        continue

    try:
        datum = datetime.strptime(header.text.strip(), "%d.%m.%Y").date()
        print(f"Datum gefunden: {datum}")
    except ValueError:
        continue

    for td in table.find_all("td"):
        fonts = td.find_all("font")
        if len(fonts) < 2:
            continue

        zeit_raw = fonts[0].get_text(strip=True)
        fach = fonts[1].get_text(strip=True).strip()

        print(f"  Zeit: {zeit_raw}, Fach: '{fach}'")

        if not fach or fach not in FACHNAMEN:
            print(f"  -> übersprungen (Fach nicht relevant)")
            continue

        if "-" not in zeit_raw:
            continue

        try:
            start_str, end_str = zeit_raw.split("-")
            start_time = datetime.strptime(start_str.strip(), "%H:%M").time()
            end_time = datetime.strptime(end_str.strip(), "%H:%M").time()
        except ValueError:
            continue

        start_dt = timezone.localize(datetime.combine(datum, start_time))
        end_dt = timezone.localize(datetime.combine(datum, end_time))

        event = Event()
        event.name = fach
        event.begin = start_dt
        event.end = end_dt
        event.uid = f"{uuid.uuid4()}@stundenplan"
        cal.events.add(event)

# === Ausgabe ===
print(f"Erzeugte Events: {len(cal.events)}")

if len(cal.events) > 0:
    with open("stundenplan.ics", "w", encoding="utf-8") as f:
        f.writelines(cal.serialize_iter())
    print("ICS-Datei erfolgreich geschrieben.")
else:
    print("Keine Events erzeugt. ICS-Datei wurde nicht erstellt.")
