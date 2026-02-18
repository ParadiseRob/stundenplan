from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import requests
import re
import os
import sys
from typing import List, Dict, Tuple

URL = "https://studieninstitute.org/Duisburg/kursauswahl.php?KursName=Stg25FiSoH&abc=S"
OUT_PATH = "stundenplan_export.ics"
TZ = pytz.timezone("Europe/Berlin")

DATE_RE = re.compile(r"\b(\d{2}\.\d{2}\.\d{4})\b")
TIME_RE = re.compile(r"(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})")


def read_old_event_count(path: str) -> int:
    if not os.path.exists(path):
        return 0
    cnt = 0
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.startswith("UID:"):
                cnt += 1
    return cnt


def safe_fetch(url: str) -> str:
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "stundenplan-bot/1.0"})
        r.raise_for_status()
        # Seite ist häufig latin1/iso-8859-1 – wir decodieren robust:
        if not r.encoding:
            r.encoding = "latin1"
        return r.text
    except Exception as e:
        print(f"[WARN] Konnte HTML-Seite nicht laden ({e}). ICS wird NICHT überschrieben.")
        return ""


def extract_subject(cell) -> str:
    fonts = cell.find_all("font")
    subject_text = ""
    if len(fonts) > 1:
        subject_text = fonts[1].get_text(strip=True)

    if not subject_text:
        italic = cell.find("i")
        if italic and italic.get_text(strip=True):
            subject_text = italic.get_text(strip=True)

    # Fallback: nimm den gesamten Text und entferne Zeit/Ort-Reste
    if not subject_text:
        raw = cell.get_text(" ", strip=True)
        # Entferne Zeitbereich, Raumangaben nach | etc.
        raw = raw.split("|")[-1].strip() if "|" in raw else raw
        # Wenn raw noch Zeit enthält, entfernen
        raw = TIME_RE.sub("", raw).strip(" -|")
        subject_text = raw.strip()

    return subject_text.strip()


def parse_tables(html: str) -> List[Dict]:
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    print(f"[DEBUG] Tabellen gefunden: {len(tables)}")

    events: List[Dict] = []

    for table in tables:
        # Datum irgendwo im Tabellenkopf / erster Zeile finden
        table_text_head = ""
        first_tr = table.find("tr")
        if first_tr:
            table_text_head = first_tr.get_text(" ", strip=True)

        m = DATE_RE.search(table_text_head)
        if not m:
            # Fallback: suche in th/td generell
            header = table.find(["th", "td"])
            if header:
                m = DATE_RE.search(header.get_text(" ", strip=True))
        if not m:
            continue

        date_str = m.group(1)
        try:
            day = datetime.strptime(date_str, "%d.%m.%Y").date()
        except:
            continue

        rows = table.find_all("tr")[1:]
        print(f"[DEBUG] {day.isoformat()}: {len(rows)} Einträge gefunden")

        for row in rows:
            cell = row.find("td")
            if not cell:
                continue

            # Zeitbereich finden (egal wo in der Zelle)
            cell_text = cell.get_text(" ", strip=True)
            tm = TIME_RE.search(cell_text)
            if not tm:
                # Wenn keine Zeit, überspringen
                print(f"[DEBUG] Überspringe Termin ohne Uhrzeit: '{cell_text[:60]}'")
                continue

            start_str, end_str = tm.group(1), tm.group(2)
            subject = extract_subject(cell)

            if not subject:
                print(f"[DEBUG] Überspringe Termin mit Zeit '{start_str}-{end_str}' und leerem Fach")
                continue

            try:
                start_dt = TZ.localize(datetime.strptime(f"{day.isoformat()} {start_str}", "%Y-%m-%d %H:%M"))
                end_dt = TZ.localize(datetime.strptime(f"{day.isoformat()} {end_str}", "%Y-%m-%d %H:%M"))
            except Exception as e:
                print(f"[DEBUG] Fehler beim Parsen der Uhrzeit '{start_str}-{end_str}': {e}")
                continue

            # stabile UID (Datum + Start + Ende + Fach)
            uid_base = f"{day.isoformat()}_{start_str}_{end_str}_{subject}".replace(" ", "_")
            uid_base = re.sub(r"[^A-Za-z0-9_.-]", "_", uid_base)
            uid = f"{uid_base}@stundenplan"

            events.append({
                "uid": uid,
                "summary": subject,
                "start": start_dt,
                "end": end_dt,
            })

            print(f"[DEBUG] Event hinzugefügt: {subject} von {start_str} bis {end_str}")

    return events


def fmt_dt_utc(dt_local) -> str:
    dt_utc = dt_local.astimezone(pytz.utc)
    return dt_utc.strftime("%Y%m%dT%H%M%SZ")


def write_ics(path: str, events: List[Dict]) -> None:
    lines = []
    lines.append("BEGIN:VCALENDAR")
    lines.append("VERSION:2.0")
    lines.append("PRODID:-//stundenplan//parser//DE")

    for e in events:
        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{e['uid']}")
        lines.append(f"DTSTART:{fmt_dt_utc(e['start'])}")
        lines.append(f"DTEND:{fmt_dt_utc(e['end'])}")
        # SUMMARY escapen minimal
        summary = e["summary"].replace("\\", "\\\\").replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")
        lines.append(f"SUMMARY:{summary}")
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    html = safe_fetch(URL)
    if not html.strip():
        # Seite nicht erreichbar/leer -> nicht überschreiben, aber Workflow nicht “rot” machen
        sys.exit(0)

    old_count = read_old_event_count(OUT_PATH)
    events = parse_tables(html)
    new_count = len(events)

    # Schutz gegen “Server zeigt Seite ohne Termine”
    # - gar keine Events -> NICHT überschreiben
    # - oder drastisch weniger als vorher -> NICHT überschreiben
    if new_count == 0:
        print("Warning: Keine Termine gefunden! ICS wird NICHT überschrieben.")
        sys.exit(0)

    if old_count > 0 and new_count < max(5, int(old_count * 0.6)):
        print(f"Warning: Verdächtig wenige Termine gefunden ({new_count} statt vorher {old_count}). ICS wird NICHT überschrieben.")
        sys.exit(0)

    write_ics(OUT_PATH, events)
    print(f"✅ {new_count} Termine geschrieben in {OUT_PATH}")


if __name__ == "__main__":
    main()
