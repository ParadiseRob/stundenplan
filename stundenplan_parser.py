from bs4 import BeautifulSoup
from ics import Calendar, Event
from datetime import datetime, timedelta
import uuid
import pytz

berlin = pytz.timezone("Europe/Berlin")

# Lade HTML-Datei
with open("stundenplan.html", encoding="windows-1252") as f:
    soup = BeautifulSoup(f, "html.parser")

cal = Calendar()

# Tabellen mit Terminen durchgehen
for table in soup.find_all("table", {"border": "1"}):
    th = table.find("th")
    if not th:
        continue
    try:
        date = datetime.strptime(th.text.strip(), "%d.%m.%Y").date()
    except ValueError:
        continue

    for td in table.find_all("td"):
        lines = list(td.stripped_strings)
        if not lines or "-" not in lines[0]:
            continue

        try:
            time_range = lines[0]
            start_str, end_str = time_range.split("-")
            start_time = datetime.strptime(start_str.strip(), "%H:%M").time()
            end_time = datetime.strptime(end_str.strip(), "%H:%M").time()
        except ValueError:
            continue

        # 💡 Jetzt holen wir uns den Fachnamen (Zeile 2) und ggf. Lehrkraft/Ort (Zeile 3)
        subject = lines[1] if len(lines) > 1 else "Unterricht"
        note = lines[2] if len(lines) > 2 else ""

        start_dt = berlin.localize(datetime.combine(date, start_time))
        end_dt = berlin.localize(datetime.combine(date, end_time))

        e = Event()
        e.name = subject  # ➜ AVR, Verworga etc.
        if note:
            e.description = note  # ➜ z. B. "Frau Mustermann, Raum 103"
        e.begin = start_dt
        e.end = end_dt
        e.uid = f"{uuid.uuid4()}@stundenplan"
        cal.events.add(e)

# Speichern
with open("stundenplan_export.ics", "w", encoding="utf-8") as f:
    f.writelines(cal.serialize_iter())
