from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import requests
import sys
import os

URL = "https://studieninstitute.org/Duisburg/kursauswahl.php?KursName=Stg25FiSoG&abc=S"
OUTPUT_FILE = "stundenplan_export.ics"

timezone = pytz.timezone("Europe/Berlin")
events = []

# ----------------------------------------
# HTML laden
# ----------------------------------------
try:
    response = requests.get(URL, timeout=15)
    response.raise_for_status()
    html_content = response.text
except Exception as e:
    print(f"[ERROR] Konnte HTML-Seite nicht laden: {e}")
    sys.exit(1)

soup = BeautifulSoup(html_content, "html.parser")

tables = soup.find_all("table")
print(f"[DEBUG] Tabellen gefunden: {len(tables)}")

# ----------------------------------------
# Termine parsen
# ----------------------------------------
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

        fonts = cell.find_all("font")
        time_text = fonts[0].get_text(strip=True) if len(fonts) > 0 else ""
        subject_text = fonts[1].get_text(strip=True) if len(fonts) > 1 else ""

        if not subject_text:
            italic = cell.find("i")
            if italic and italic.get_text(strip=True):
                subject_text = italic.get_text(strip=True)

        if not time_text or not subject_text:
            continue

        time_range = time_text.split("|")[0].strip() if "|" in time_text else time_text

        try:
            start_str, end_str = [t.strip() for t in time_range.split("-")]
            start_dt = timezone.localize(datetime.strptime(f"{date} {start_str}", "%Y-%m-%d %H:%M"))
            end_dt = timezone.localize(datetime.strptime(f"{date} {end_str}", "%Y-%m-%d %H:%M"))
        except:
            continue

        uid = f"{date.isoformat()}_{start_str}_{end_str}_{subject_text}".replace(" ", "_")

        events.append({
            "uid": uid,
            "summary": subject_text,
            "start": start_dt,
            "end": end_dt
        })

# ----------------------------------------
# Sicherheitsmechanismus:
# Wenn 0 Events gefunden → NICHT überschreiben
# ----------------------------------------
if len(events) == 0:
    print("[WARNING] Keine Termine gefunden! ICS wird NICHT überschrieben.")
    sys.exit(1)

# ----------------------------------------
# ICS-Datei manuell schreiben
# ----------------------------------------
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write("BEGIN:VCALENDAR\n")
    f.write("VERSION:2.0\n")
    f.write("PRODID:-//Stundenplan//EN\n")

    for event in events:
        f.write("BEGIN:VEVENT\n")
        f.write(f"UID:{event['uid']}@stundenplan\n")
        f.write(f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}\n")
        f.write(f"DTSTART:{event['start'].strftime('%Y%m%dT%H%M%S')}\n")
        f.write(f"DTEND:{event['end'].strftime('%Y%m%dT%H%M%S')}\n")
        f.write(f"SUMMARY:{event['summary']}\n")
        f.write("END:VEVENT\n")

    f.write("END:VCALENDAR\n")

print(f"✅ {len(events)} Termine geschrieben in {OUTPUT_FILE}")
