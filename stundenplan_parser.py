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

# Liste aller Tabellen mit Datumskopf
tables = soup.find_all("table")
print(f"[DEBUG] Tabellen gefunden: {len(tables)}")

for table in tables:
    header = table.find("th")
    if not header:
        continue

    try:
        date_str = header.get_text(strip=True)
        date = datetime.strptime(date_str, "%d.%m.%Y").date()
    except:
        continue

    rows = table.find_all("tr")[1:]
    print(f"[DEBUG] {date.isoformat()}: {len(rows)} Einträge gefunden")

    for row in rows:
        cell = row.find("td")
        if not cell:
            continue

        fonts = cell.find_all("font")

        time_text = fonts[0].get_text(strip=True) if len(fonts) > 0 else ""
        
        # Versuch, Fachtext aus zweitem font-Tag zu holen
        subject_text = fonts[1].get_text(strip=True) if len(fonts) > 1 else ""

        # Falls kein Fachtext, schaue, ob kursiver Text vorhanden ist (für Sondertermine)
        if not subject_text:
            italic = cell.find("i")
            if italic and italic.get_text(strip=True):
                subject_text = italic.get_text(strip=True)

        # Wenn Zeit oder Fach fehlt, überspringen
        if not time_text or not subject_text:
            print(f"[DEBUG] Überspringe Termin mit Zeit '{time_text}' und Fach '{subject_text}'")
            continue

        # Zeit extrahieren (z.B. "08:15-09:45 | 12/64")
        time_range = time_text.split("|")[0].strip() if "|" in time_text else time_text
        try:
            start_str, end_str = [t.strip() for t in time_range.split("-")]
            start_dt = timezone.localize(datetime.strptime(f"{date} {start_str}", "%Y-%m-%d %H:%M"))
            end_dt = timezone.localize(datetime.strptime(f"{date} {end_str}", "%Y-%m-%d %H:%M"))
        except Exception as e:
            print(f"[DEBUG] Fehler beim Parsen der Uhrzeit '{time_range}': {e}")
            continue

        # UID so bauen, dass Termine stabil erkannt werden (Datum+Zeit+Fach)
        uid_base = f"{date.isoformat()}_{start_str}_{end_str}_{subject_text}".replace(" ", "_")
        event_uid = f"{uid_base}@stundenplan"

        # Event erzeugen
        event = Event()
        event.name = subject_text
        event.begin = start_dt
        event.end = end_dt
        event.uid = event_uid
        cal.events.add(event)

        print(f"[DEBUG] Event hinzugefügt: {subject_text} von {start_str} bis {end_str}")

# ICS-Datei schreiben
with open("stundenplan_export.ics", "w", encoding="utf-8") as f:
    f.writelines(cal.serialize_iter())

print(f"✅ {len(cal.events)} Termine geschrieben in stundenplan_export.ics")
