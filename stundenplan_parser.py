from bs4 import BeautifulSoup
from ics import Calendar, Event
from datetime import datetime
import pytz
import uuid

# HTML einlesen
with open("stundenplan.html", encoding="windows-1252") as f:
    soup = BeautifulSoup(f, "html.parser")

cal = Calendar()
tz = pytz.timezone("Europe/Berlin")  # korrekte Zeitzone

# Tabellen durchgehen
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
        if len(lines) < 1 or "-" not in lines[0]:
            continue

        try:
            start_str, end_str = lines[0].split("-")
            start = datetime.strptime(start_str, "%H:%M").time()
            end = datetime.strptime(end_str, "%H:%M").time()
        except ValueError:
            continue

        subject = lines[1] if len(lines) > 1 else "Unterricht"
        note = lines[2] if len(lines) > 2 else ""

        start_dt = tz.localize(datetime.combine(date, start))
        end_dt = tz.localize(datetime.combine(date, end))

        e = Event()
        e.name = subject
        e.begin = start_dt
        e.end = end_dt
        e.description = note
        e.uid = f"{uuid.uuid4()}@stundenplan"

        cal.events.add(e)

# Speichern
with open("stundenplan_export.ics", "w", encoding="utf-8") as f:
    f.writelines(cal.serialize_iter())
