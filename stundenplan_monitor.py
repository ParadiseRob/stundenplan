import os
import smtplib
import ssl
from email.message import EmailMessage
from datetime import datetime
import re

OLD_ICS_PATH = "stundenplan_export_old.ics"
NEW_ICS_PATH = "stundenplan_export.ics"

UID_RE = re.compile(r"^UID:(.*)$")
DTSTART_RE = re.compile(r"^DTSTART:(.*)$")
SUMMARY_RE = re.compile(r"^SUMMARY:(.*)$")


def parse_ics_events(path: str):
    """
    Minimal-Parser: liest UID, DTSTART, SUMMARY pro VEVENT.
    Gibt Set von (uid, day_iso, summary) zurück.
    """
    if not os.path.exists(path):
        return set()

    events = set()
    current = {}

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()

            if line == "BEGIN:VEVENT":
                current = {}
                continue

            if line == "END:VEVENT":
                uid = current.get("uid")
                dtstart = current.get("dtstart")
                summary = current.get("summary", "")
                if uid and dtstart:
                    # DTSTART ist UTC im Format YYYYMMDDTHHMMSSZ
                    try:
                        day = datetime.strptime(dtstart[:8], "%Y%m%d").date().isoformat()
                        events.add((uid, day, summary))
                    except:
                        pass
                current = {}
                continue

            m = UID_RE.match(line)
            if m:
                current["uid"] = m.group(1).strip()
                continue

            m = DTSTART_RE.match(line)
            if m:
                current["dtstart"] = m.group(1).strip()
                continue

            m = SUMMARY_RE.match(line)
            if m:
                # Unescape minimal
                s = m.group(1).replace("\\n", "\n").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")
                current["summary"] = s.strip()
                continue

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

    old_events = parse_ics_events(OLD_ICS_PATH)
    new_events = parse_ics_events(NEW_ICS_PATH)

    if new_events != old_events:
        changed_days = extract_changed_days(old_events, new_events)
        if changed_days:
            print(f"Änderungen gefunden an Tagen: {changed_days}, sende Mail...")
            send_mail(changed_days, smtp_email, smtp_password, mail_recipient)

            # Neue Datei als alt speichern
            with open(NEW_ICS_PATH, "r", encoding="utf-8", errors="ignore") as f_new, \
                 open(OLD_ICS_PATH, "w", encoding="utf-8") as f_old:
                f_old.write(f_new.read())
        else:
            print("Änderungen entdeckt, aber keine Tage zum Melden gefunden.")
    else:
        print("Keine Änderungen zum Stundenplan.")


if __name__ == "__main__":
    main()
