from bs4 import BeautifulSoup
from ics import Calendar, Event
from datetime import datetime
import pytz

berlin = pytz.timezone("Europe/Berlin")

with open("stundenplan.html", encoding="ISO-8859-1") as f:
    soup = BeautifulSoup(f, "html.parser")

cal = Calendar()

for row in soup.select("tr")[1:]:
    cols = row.find_all("td")
    if len(cols) < 5:
        continue

    date_str = cols[0].text.strip()
    time_str = cols[1].text.strip()
    subject = cols[2].text.strip()

    try:
        start_time, end_time = time_str.split(" - ")
        start_dt = berlin.localize(datetime.strptime(f"{date_str} {start_time}", "%d.%m.%Y %H:%M"))
        end_dt = berlin.localize(datetime.strptime(f"{date_str} {end_time}", "%d.%m.%Y %H:%M"))

        e = Event()
        e.name = subject
        e.begin = start_dt
        e.end = end_dt
        cal.events.add(e)

    except Exception as e:
        print("Fehler beim Parsen:", e)

with open("stundenplan_export.ics", "w", encoding="utf-8") as f:
    f.writelines(cal)
