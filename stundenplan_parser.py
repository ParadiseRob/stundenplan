from bs4 import BeautifulSoup
from ics import Calendar, Event
from datetime import datetime
import pytz

# Fächerliste (optional zur Validierung)
faecher = [
    "Termin Ausbildung", "KFM", "RdG", "Verworga",
    "AVR", "Buchf", "HSK", "BGB", "Pers.R", "Lehrprobe"
]

# Lade HTML-Datei
with open("stundenplan.html", "r", encoding="latin-1") as f:
    soup = BeautifulSoup(f, "html.parser")

calendar = Calendar()
timezone = pytz.timezone("Europe/Berlin")

# Suche alle Tages-Tabellen
for table in soup.find_all("table"):
    header = table.find("th")
    if not header or not header.text.strip():
        continue
    try:
        datum = datetime.strptime(header.text.strip(), "%d.%m.%Y").date()
    except ValueError:
        continue

    # Einzelne Zellen durchgehen
    for td in table.find_all("td", bgcolor="#C0C0C0"):
        fonts = td.find_all("font")
        if len(fonts) < 2:
            continue

        zeitraum_text = fonts[0].text.strip()
        fach_text = fonts[1].text.strip()

        if not zeitraum_text or not fach_text:
            continue

        if not any(fach_text.startswith(fach) for fach in faecher):
            continue  # ignorieren, wenn kein Fach

        zeiten = zeitraum_text.split("|")[0].strip()
        try:
            von, bis = zeiten.split("-")
        except ValueError:
            continue  # ungültige Zeitangabe

        start_dt = datetime.strptime(f"{datum} {von}", "%Y-%m-%d %H:%M")
        end_dt = datetime.strptime(f"{datum} {bis}", "%Y-%m-%d %H:%M")

        event = Event()
        event.name = fach_text
        event.begin = timezone.localize(start_dt)
        event.end = timezone.localize(end_dt)
        calendar.events.add(event)

# Nur schreiben, wenn mindestens ein Termin gefunden wurde
if calendar.events:
    with open("stundenplan.ics", "w", encoding="utf-8") as f:
        f.writelines(calendar)
    print("ICS-Datei erfolgreich geschrieben.")
else:
    print("⚠️ Keine Termine gefunden – keine ICS-Datei geschrieben.")
