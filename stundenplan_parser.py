from bs4 import BeautifulSoup
from ics import Calendar, Event
from datetime import datetime
import pytz
import uuid

# Lade HTML-Datei
with open("stundenplan.html", "r", encoding="latin1") as f:
    soup = BeautifulSoup(f, "html.parser")

cal = Calendar()
timezone = pytz.timezone("Europe/Berlin")

# Alle Tabellen mit Datumskopf finden
tables = soup.find_all("table")
print(f"[DEBUG] Tabellen gefunden: {len(tables)}")

for table in tables:
    header = table.find("th")
    if not header:
        continue

    try:
        date_str = header.get_text(strip=True)
        date = datetime.strptime(date_str, "%d.%m.%Y").date()
    except Exception as e:
        print(f"[DEBUG] Fehler beim Parsen des Datums: {e}")
        continue

    rows = table.find_all("tr")[1:]  # Skip header row
    print(f"[DEBUG] {date.isoformat()}: {len(rows)} Einträge gefunden")

    for row in rows:
        cell = row.find("td")
        if not cell:
            continue

        parts = cell.find_all("font")
        if len(parts) < 2:
            continue

        time_text = parts[0].get_text(strip=True)
        subject_text = parts[1].get_text(strip=True)

        if not time_text:
            print(f"[DEBUG] Keine Zeitangabe in Zeile, überspringe.")
            continue

        if not subject_text:
            # Falls kein Fach angegeben ist, z.B. leere Stunden, überspringen oder "Unterricht" setzen
            subject_text = "Unterricht"

        # Zeit extrahieren (z.B. "08:15-09:45 | 12/64")
        time_range = time_text.split("|")[0].strip() if "|" in time_text else time_text
        try:
            start_str, end_str = [t.strip() for t in time_range.split("-")]
            start_dt = timezone.localize(datetime.strptime(f"{date} {start_str}", "%Y-%m-%d %H:%M"))
            end_dt = timezone.localize(datetime.strptime(f"{date} {end_str}", "%Y-%m-%d %H:%M"))
        except Exception as e:
            print(f"[DEBUG] Fehler beim Parsen der Uhrzeit '{time_range}': {e}")
            continue

        # Event erzeugen
        event = Event()
        event.name = subject_text
        event.begin = start_dt
        event.end = end_dt
        event.uid = str(uuid.uuid4()) + "@stundenplan"
        cal.events.add(event)

        print(f"[DEBUG] Event hinzugefügt: {subject_text} von {start_str} bis {end_str}")

# ICS-Datei schreiben
with open("stundenplan_export.ics", "w", encoding="utf-8") as f:
    f.writelines(cal.serialize_iter())

print(f"✅ {len(cal.events)} Termine geschrieben in stundenplan_export.ics")
