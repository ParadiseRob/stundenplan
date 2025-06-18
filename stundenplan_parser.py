from bs4 import BeautifulSoup
from ics import Calendar, Event
from datetime import datetime, timedelta
import uuid

with open("stundenplan.html", encoding="ISO-8859-1") as f:
    soup = BeautifulSoup(f, "html.parser")

cal = Calendar()

for row in soup.select("table > tr")[1:]:
    cells = row.find_all("td")
    if len(cells) < 6:
        continue

    datum = cells[0].text.strip()
    uhrzeit = cells[1].text.strip()
    thema = cells[2].text.strip()

    try:
        start_datum = datetime.strptime(f"{datum} {uhrzeit}", "%d.%m.%Y %H:%M")
    except ValueError:
        continue

    end_datum = start_datum + timedelta(minutes=90)

    e = Event()
    e.name = thema
    e.begin = start_datum
    e.end = end_datum
    e.uid = str(uuid.uuid4())
    cal.events.add(e)

with open("stundenplan_export.ics", "w", encoding="utf-8") as f:
    f.writelines(cal)
