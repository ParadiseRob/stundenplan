from bs4 import BeautifulSoup
from ics import Calendar, Event
from datetime import datetime
import pytz

faecher = [
    "Termin Ausbildung", "KFM", "RdG", "Verworga",
    "AVR", "Buchf", "HSK", "BGB", "Pers.R", "Lehrprobe"
]

with open("stundenplan.html", "r", encoding="latin-1") as f:
    soup = BeautifulSoup(f, "html.parser")

calendar = Calendar()
timezone = pytz.timezone("Europe/Berlin")
event_count = 0

tables = soup.find_all("table")
print(f"[DEBUG] Tabellen gefunden: {len(tables)}")

for table in tables:
    header = table.find("th")
    if not header:
        continue
    try:
        datum = datetime.strptime(header.text.strip(), "%d.%m.%Y").date()
    except ValueError:
        continue

    stunden = table.find_all("td", bgcolor="#C0C0C0")
    print(f"[DEBUG] {datum}: {len(stunden)} Einträge gefunden")

    for td in stunden:
        fonts = td.find_all("font")
        if len(fonts) < 2:
            print("[DEBUG] Zu wenige <font>-Tags in Zelle, übersprungen.")
            continue

        zeitraum_text = fonts[0].text.strip()
        fach_text = fonts[1].text.strip()
        print(f"[DEBUG] Zeit: {zeitraum_text}, Fach: {fach_text}")

        if not zeitraum_text or not fach_text:
            continue

        zeiten = zeitraum_text.split("|")[0].strip()
        try:
            von, bis = zeiten.split("-")
        except ValueError:
            print("[DEBUG] Zeitformat ungültig:", zeiten)
            continue

        start_dt = datetime.strptime(f"{datum} {von.strip()}", "%Y-%m-%d %H:%M")
        end_dt = datetime.strptime(f"{datum} {bis.strip()}", "%Y-%m-%d %H:%M")

        event = Event()
        event.name = fach_text
        event.begin = timezone.localize(start_dt)
        event.end = timezone.localize(end_dt)
        calendar.events.add(event)
        event_count += 1
        print(f"[DEBUG] Event hinzugefügt: {fach_text} von {von} bis {bis}")

if event_count > 0:
    with open("stundenplan.ics", "w", encoding="utf-8") as f:
        f.writelines(calendar)
    print(f"✅ {event_count} Termine geschrieben in stundenplan.ics")
else:
    print("⚠️ Keine gültigen Termine gefunden.")
