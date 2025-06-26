from bs4 import BeautifulSoup
from ics import Calendar, Event
from datetime import datetime
import pytz
import hashlib

# Lade HTML-Datei
with open("stundenplan.html", "r", encoding="latin1") as f:
    soup = BeautifulSoup(f, "html.parser")

cal = Calendar()
timezone = pytz.timezone("Europe/Berlin")

# Liste aller Tabellen mit Datumskopf
tables = soup.find_all("table")
print(f"[DEBUG] Tabellen gefunden: {len(tables)}")

for table in tables:
    header = table.find("th")
    if not header:
        continue

    try:
        date_str = header.get_text(strip=True)
        date = datetime.strptime(date_str, "%d.%m.%Y").date()
    except:
        continue

    rows = table.find_all("tr")[1:]
    print(f"[DEBUG] {date.isoformat()}: {len(rows)} Einträge gefunden")

    for row in rows:
        cell = row.find("td")
        if not cell:
            continue

        parts = cell.find_all("font")
        if len(parts) < 1:
            continue

        time_text = parts[0].get_text(strip=True)

        # Versuche subject_text im zweiten font-Tag, wenn vorhanden
        subject_text = parts[1].get_text(strip=True) if len(parts) > 1 else ""

        # Wenn subject_text leer, prüfe ob kursiver Text im cell ist (für Sondertermine)
        if not subject_text:
            italic = cell.find("i")
            if italic and italic.get_text(strip=True):
                subject_text = italic.get_text(strip=True)

        if not time_text or not subject_text:
            print(f"[DEBUG] Zeit: {time_text}, Fach: {subject_text}")
            continue

        # Zeit extra
