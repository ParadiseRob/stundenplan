from bs4 import BeautifulSoup
from ics import Calendar, Event
from datetime import datetime, timedelta
import uuid
import pytz

# Lokale Zeitzone definieren
berlin = pytz.timezone("Europe/Berlin")

# Lade die Stundenplan-HTML-Datei
with open("stundenplan.html", encoding="windows-1252") as f:
    soup = BeautifulSoup(f, "html.parser")

cal = Calendar()

for table in soup.find_all("table", {"border": "1"}):
    th = table.find("th")
    if not th:
        continue
    try:
        date = datetime.strptime(th.text.strip(), "%d.%m.%Y").date()
    except ValueError:
        continue

    for td in table.find_all("td"):
        lines = [line.strip() for line in td.stripped_strings]
        if not lines or len(lines) < 1:
            continue

        time_range = lines[0]
        if "-" not in time_range:
            continue

        try:
            start_str, end_str = time_range.split("-")
            start_time = datetime.strptime(start_str.strip(), "%H:%M").time()
            end_time = datetime.strptime(end_str.strip(), "%H:%M").time()
        except ValueError:
            continue

        # Finde sinnvollen Titel
        title = "Unterricht"
        for line in lines[1:]:
            if "/" in line and any(c.isdigit() for c in line):
                continue  # ignoriere Stundenanzahl wie "32/56"
            if line.lower().startswith("raum") or line.lower().startswith("frau") or line.lower().startswith("herr"):
                continue  # ignoriere Räume oder Namen
            title = line
            break

        start_dt = berlin.localize(datetime.combine(date, start_time))
        end_dt = berlin.localize(datetime.combine(date, end_time))

        event = Event()
        event.name = title
        event.begin = start_dt
        event.end = end_dt
        event.uid = f"{uuid.uuid4()}@stundenplan"
        cal.events.add(event)

# Speichere die ICS-Datei
with open("stundenplan_export.ics", "w", encoding="utf-8") as f:
    f.writelines(cal.serialize_iter())
