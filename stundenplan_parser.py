from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import requests
import sys
import os
import re

URL = "https://studieninstitute.org/Duisburg/kursauswahl.php?KursName=Stg25FiSoG&abc=S"
OUTFILE = "stundenplan_export.ics"
TIMEZONE = pytz.timezone("Europe/Berlin")

# Wenn die neue Seite "leer" ist, aber vorher gab es Termine:
# -> NICHT überschreiben (Schutz gegen Server-Ausfall/Leer-Seite)
MIN_EVENTS_IF_PREVIOUS_EXISTS = 1          # "0 Termine" gilt als Ausfall
DROP_RATIO_THRESHOLD = 0.25                # optional: wenn plötzlich <25% der alten Termine -> verdächtig

def safe_ics_text(s: str) -> str:
    """Minimal escapings für ICS TEXT (SUMMARY etc.)."""
    s = s.replace("\\", "\\\\")
    s = s.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n")
    s = s.replace(",", "\\,").replace(";", "\\;")
    return s.strip()

def dt_to_utc_z(dt_local: datetime) -> str:
    dt_utc = dt_local.astimezone(pytz.utc)
    return dt_utc.strftime("%Y%m%dT%H%M%SZ")

def count_vevents(path: str) -> int:
    if not os.path.exists(path):
        return 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            txt = f.read()
        return len(re.findall(r"BEGIN:VEVENT", txt))
    except Exception:
        return 0

def build_uid(date_iso: str, start_str: str, end_str: str, subject: str) -> str:
    uid_base = f"{date_iso}_{start_str}_{end_str}_{subject}".replace(" ", "_")
    uid_base = re.sub(r"[^A-Za-z0-9_\-\.]", "_", uid_base)
    return f"{uid_base}@stundenplan"

def fetch_html(url: str) -> str:
    resp = requests.get(
        url,
        timeout=20,
        headers={"User-Agent": "stundenplan-bot/1.0 (+github-actions)"}
    )
    resp.raise_for_status()
    return resp.text

def parse_events(html: str):
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    print(f"[DEBUG] Tabellen gefunden: {len(tables)}")

    events = []
    for table in tables:
        header = table.find("th")
        if not header:
            continue

        try:
            date_str = header.get_text(strip=True)
            date = datetime.strptime(date_str, "%d.%m.%Y").date()
        except Exception:
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

            # Sondertermine stehen bei dir teils kursiv
            if not subject_text:
                italic = cell.find("i")
                if italic and italic.get_text(strip=True):
                    subject_text = italic.get_text(strip=True)

            if not time_text or not subject_text:
                print(f"[DEBUG] Überspringe Termin mit Zeit '{time_text}' und Fach '{subject_text}'")
                continue

            time_range = time_text.split("|")[0].strip() if "|" in time_text else time_text
            try:
                start_str, end_str = [t.strip() for t in time_range.split("-")]
                start_dt = TIMEZONE.localize(datetime.strptime(f"{date} {start_str}", "%Y-%m-%d %H:%M"))
                end_dt = TIMEZONE.localize(datetime.strptime(f"{date} {end_str}", "%Y-%m-%d %H:%M"))
            except Exception as e:
                print(f"[DEBUG] Fehler beim Parsen der Uhrzeit '{time_range}': {e}")
                continue

            uid = build_uid(date.isoformat(), start_str, end_str, subject_text)
            events.append({
                "uid": uid,
                "summary": subject_text,
                "dtstart": start_dt,
                "dtend": end_dt,
            })
            print(f"[DEBUG] Event hinzugefügt: {subject_text} von {start_str} bis {end_str}")

    return events

def write_ics(events, path: str):
    lines = []
    lines.append("BEGIN:VCALENDAR")
    lines.append("VERSION:2.0")
    lines.append("PRODID:-//stundenplan//parser//DE")
    lines.append("CALSCALE:GREGORIAN")

    # stabile Sortierung, damit diff sauber ist
    events_sorted = sorted(events, key=lambda e: (e["dtstart"], e["uid"]))

    for e in events_sorted:
        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{safe_ics_text(e['uid'])}")
        lines.append(f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}")
        lines.append(f"DTSTART:{dt_to_utc_z(e['dtstart'])}")
        lines.append(f"DTEND:{dt_to_utc_z(e['dtend'])}")
        lines.append(f"SUMMARY:{safe_ics_text(e['summary'])}")
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    content = "\r\n".join(lines) + "\r\n"

    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content)

def main():
    prev_count = count_vevents(OUTFILE)

    try:
        html = fetch_html(URL)
    except Exception as e:
        print(f"[ERROR] Konnte HTML-Seite nicht laden: {e}")
        # wichtig: Exit != 0, damit Workflow klar zeigt "Parser kaputt"
        sys.exit(1)

    events = parse_events(html)
    new_count = len(events)

    # Schutz: wenn plötzlich gar keine Termine -> NICHT überschreiben
    if prev_count > 0 and new_count < MIN_EVENTS_IF_PREVIOUS_EXISTS:
        print(f"[WARN] Neue Seite liefert {new_count} Termine, vorher waren es {prev_count}. "
              f"Vermutlich Ausfall/Leer-Seite -> ICS wird NICHT überschrieben.")
        sys.exit(0)

    # Optionaler zusätzlicher Schutz: starker Drop
    if prev_count > 0 and new_count / max(prev_count, 1) < DROP_RATIO_THRESHOLD:
        print(f"[WARN] Sehr starker Rückgang: vorher {prev_count}, jetzt {new_count} "
              f"(<{int(DROP_RATIO_THRESHOLD*100)}%). Verdächtig -> ICS wird NICHT überschrieben.")
        sys.exit(0)

    write_ics(events, OUTFILE)
    print(f"✅ {new_count} Termine geschrieben in {OUTFILE}")

if __name__ == "__main__":
    main()
