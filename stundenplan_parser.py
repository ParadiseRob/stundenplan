from bs4 import BeautifulSoup
from ics import Calendar, Event
from datetime import datetime
import uuid

# Lade die Stundenplan-HTML-Datei
with open("stundenplan.html", encoding="windows-1252") as f:
    soup = BeautifulSoup(f, "html.parser")

cal = Calendar()

# Füge VTIMEZONE-Definition hinzu (für Europe/Berlin)
cal.extra.append("""
BEGIN:VTIMEZONE
TZID:Europe/Berlin
X-LIC-LOCATION:Europe/Berlin
BEGIN:DAYLIGHT
TZOFFSETFROM:+0100
TZOFFSETTO:+0200
TZNAME:CEST
DTSTART:19700329T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:+0200
TZOFFSETTO:+0100
TZNAME:CET
DTSTART:19701025T030000
RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
END:STANDARD
END:VTIMEZONE
""")

# Verarbeite alle Tages-Tabellen (jeweils ein Tag pro Spalte)
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
        note = lines[2] if len(lines) > 2 else ""

        start_dt = datetime.combine(date, start_time)
