print("DEBUG: HTML-Datei öffne und zeile 1–10 anzeigen")
with open("stundenplan.html", encoding="windows-1252") as f:
    for i in range(10):
        print(repr(f.readline()))
# und ab hier der Rest deines Codes...


from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from ics import Calendar, Event

with open("stundenplan.html", encoding="windows-1252") as f:
    soup = BeautifulSoup(f, "html.parser")

cal = Calendar()

# Jeder Tag ist eine Tabelle
tables = soup.find_all("table", {"border": "1"})
for table in tables:
    rows = table.find_all("tr")
    if not rows:
        continue

    # Datum aus erster Zeile (z. B. "07.07.2025")
    date_cell = rows[0].find("th")
    if not date_cell:
        continue
    try:
        day = datetime.strptime(date_cell.text.strip(), "%d.%m.%Y")
    except ValueError:
        continue

    # Danach folgen Blöcke mit Terminen
    for row in rows[1:]:
        cell = row.find("td")
        if not cell:
            continue
        lines = [line.strip() for line in cell.stripped_strings]
        if not lines or len(lines) < 2:
            continue
        time_range = lines[0]  # z. B. "08:15-09:45"
        title = lines[1]       # z. B. "AVR"

        try:
            start_str, end_str = time_range.split("-")
            start_time = datetime.strptime(start_str.strip(), "%H:%M").time()
            end_time = datetime.strptime(end_str.strip(), "%H:%M").time()
        except ValueError:
            continue  # Falls Zeitangabe ungültig ist

        start_dt = datetime.combine(day.date(), start_time)
        end_dt = datetime.combine(day.date(), end_time)

        event = Event()
        event.name = title or "Unterricht"
        event.begin = start_dt.isoformat()
        event.end = end_dt.isoformat()
        cal.events.add(event)

# Speichern
with open("stundenplan_export.ics", "w", encoding="utf-8") as f:
    f.writelines(cal)
