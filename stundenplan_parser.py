from bs4 import BeautifulSoup
from ics import Calendar, Event
from datetime import datetime
import uuid

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

        subject = lines[1] if len(lines) > 1 else "Unterricht"

        start_dt = datetime.combine(date, start_time)
        end_dt = datetime.combine(date, end_time)

        e = Event()
        e.name = subject
        e.begin = f"{start_dt.strftime('%Y%m%dT%H%M%S')}"
        e.end = f"{end_dt.strftime('%Y%m%dT%H%M%S')}"
        e.uid = f"{uuid.uuid4()}@stundenplan"
        cal.events.add(e)

with open("stundenplan_export.ics", "w", encoding="utf-8") as f:
    f.writelines(cal.serialize_iter())
