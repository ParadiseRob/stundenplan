import os
import re
import smtplib
import ssl
from email.message import EmailMessage
from datetime import datetime
import pytz

PREV_ICS_PATH = "stundenplan_export_prev.ics"
NEW_ICS_PATH = "stundenplan_export.ics"
TZ = pytz.timezone("Europe/Berlin")

def parse_ics_events(file_path):
    """
    Extrahiert minimal:
      UID, DTSTART (UTC Z), SUMMARY
    Rückgabe: set((uid, day_iso, summary))
    """
    if not os.path.exists(file_path):
        return set()

    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    # sehr simples VEVENT parsing
    blocks = re.split(r"BEGIN:VEVENT\r?\n", text)
    events = set()

    for b in blocks[1:]:
        # Block endet vor END:VEVENT
        b = b.split("END:VEVENT", 1)[0]

        uid = None
        dtstart = None
        summary = None

        for line in b.splitlines():
            line = line.strip()
            if line.startswith("UID:"):
                uid = line[4:].strip()
            elif line.startswith("DTSTART:"):
                dtstart = line[len("DTSTART:"):].strip()
            elif line.startswith("SUMMARY:"):
                summary = line[len("SUMMARY:"):].strip()

        if not (uid and dtstart and summary):
            continue

        # DTSTART ist im Parser als UTC Z geschrieben: YYYYMMDDTHHMMSSZ
        try:
            dt_utc = datetime.strptime(dtstart, "%Y%m%dT%H%M%SZ").replace(tzinfo=pytz.utc)
            dt_local = dt_utc.astimezone(TZ)
            day = dt_local.date().isoformat()
        except Exception:
            continue

        events.add((uid, day, summary))

    return events

def extract_changed_days(old_events, new_events):
    old_ids = {e[0] for e in old_events}
    new_ids = {e[0] for e in new_events}

    added = new_ids - old_ids
    removed = old_ids - new_ids

    changed_days = set()
    for e in new_events:
        if e[0] in added:
            changed_days.add(e[1])
    for e in old_events:
        if e[0] in removed:
            changed_days.add(e[1])

    return sorted(changed_days)

def send_mail(changed_days, smtp_email, smtp_password, mail_recipient):
    message = EmailMessage()
    message["From"] = smtp_email
    message["To"] = mail_recipient
    message["Subject"] = "Stundenplan-Update: Änderungen entdeckt"

    body = "Es wurden Änderungen im Stundenplan festgestellt an folgenden Tagen:\n\n"
    for d in changed_days:
        body += f"- {d}\n"
    body += "\nBitte prüfe den aktualisierten Kalender.\n"

    message.set_content(body)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
        smtp.login(smtp_email, smtp_password)
        smtp.send_message(message)

def main():
    smtp_email = os.getenv("SMTP_EMAIL")
    smtp_password = os.getenv("SMTP_PASSWORD")
    mail_recipient = os.getenv("MAIL_RECIPIENT")

    if not all([smtp_email, smtp_password, mail_recipient]):
        print("Bitte SMTP_EMAIL, SMTP_PASSWORD und MAIL_RECIPIENT als Secrets setzen!")
        return

    old_events = parse_ics_events(PREV_ICS_PATH)
    new_events = parse_ics_events(NEW_ICS_PATH)

    if not old_events:
        print("Kein vorheriger Stand vorhanden (erste Ausführung?) – keine Mail.")
        return

    if new_events != old_events:
        changed_days = extract_changed_days(old_events, new_events)
        if changed_days:
            print(f"Änderungen gefunden an Tagen: {changed_days}, sende Mail...")
            send_mail(changed_days, smtp_email, smtp_password, mail_recipient)
        else:
            print("Änderungen entdeckt, aber keine Tage zum Melden gefunden.")
    else:
        print("Keine Änderungen zum Stundenplan.")

if __name__ == "__main__":
    main()
