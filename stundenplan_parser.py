import re
import uuid
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from ics import Calendar, Event

FACHNAMEN = {
    "Termin Ausbildung", "KFM", "RdG", "Verworga", "AVR",
    "Buchf", "HSK", "BGB", "Pers.R", "Lehrprobe"
}

def parse_time(tstr):
    """Wandelt z.B. '08:15-09:45' in (start_dt, end_dt) um"""
    start, end = tstr.split('-')
    return start.strip(), end.strip()

def parse_html_to_ics(html_path, ics_path):
    with open(html_path, "r", encoding="latin1") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    cal = Calendar()

    # Finde alle Datumstabellen
    for table in soup.find_all("table"):
        header = table.find("th")
        if header and re.match(r"\d{2}\.\d{2}\.\d{4}", header.text.strip()):
            datum_str = header.text.strip()
            datum = datetime.strptime(datum_str, "%d.%m.%Y").date()

            for cell in table.find_all("td"):
                fonts = cell.find_all("font")
                if len(fonts) >= 2:
                    zeitinfo = fonts[0].get_text(strip=True)
                    fach = fonts[1].get_text(strip=True)

                    if not fach or fach not in FACHNAMEN:
                        continue

                    # Zeit auslesen und zusammensetzen
                    zeit_match = re.search(r"\d{2}:\d{2}-\d{2}:\d{2}", zeitinfo)
                    if not zeit_match:
                        continue
                    start_str, end_str = parse_time(zeit_match.group())
                    start_dt = datetime.strptime(f"{datum} {start_str}", "%Y-%m-%d %H:%M")
                    end_dt = datetime.strptime(f"{datum} {end_str}", "%Y-%m-%d %H:%M")

                    # Event erzeugen
                    e = Event()
                    e.begin = start_dt
                    e.end = end_dt
                    e.name = fach
                    e.uid = str(uuid.uuid4()) + "@stundenplan"
                    cal.events.add(e)

    # Speichern
    with open(ics_path, "w", encoding="utf-8") as f:
        f.writelines(cal.serialize_iter())
