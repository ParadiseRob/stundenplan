from bs4 import BeautifulSoup
from ics import Calendar, Event
from datetime import datetime, timedelta
import uuid
import pytz

# Lokale Zeitzone definieren
berlin = pytz.timezone("Europe/Berlin")

# HTML laden
with open("stundenplan.html", encoding="windows-1252") as f:
    soup = BeautifulSoup(f, "html.parser")

cal = Calendar()

# Tabellen mit Tagesdaten durchgehen
for table in soup.find_all("table", {"border": "1"}):
    th = table.find("th")
    if not th:
        continue
    try:
        date = datetime.strptime(th.text.strip(), "%d.%m.%Y").date()
    except ValueError:
        continue

    # Alle Unterrichtszellen verarbeiten
    for td in table.find_all("td"):
        lines = list(td.stripped_strings)
        if not lines or "-" not in lines[0]:
            continue

        try:
            time_range = lines[0]
            start_str, end_str = [t.strip() for t in time_range.split("-")]
            start_time = datetime.strptime(start_str, "%H:%M").time()
            end_time = datetime.strptime(end_str, "%H:%M").time()
        except ValueError:
            continue

        subject = lines[1] if len(lines) > 1 else "Unterricht"
        note = lines[2] if len(lines) > 2 else ""

        start_dt = berlin.localize(datetime.combine(date, start_time))
        end_dt = berlin.localize(datetime.combine(date, end_time))

        e = Event()
        e.name = subject if subject else "Unterricht"
        e.begin = start_dt
        e.end = end_dt
        e.uid = f"{uuid.uuid4()}@stundenplan"
        cal.events.add(e)

# Datei speichern
with open("stundenplan_export.ics", "w", encoding="utf-8") as f:
    f.writelines(cal.serialize_iter())
