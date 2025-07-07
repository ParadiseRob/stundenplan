import os
import smtplib
import ssl
from email.message import EmailMessage
from ics import Calendar

OLD_ICS_PATH = "stundenplan_export_old.ics"
NEW_ICS_PATH = "stundenplan_export.ics"

def load_events(file_path):
    if not os.path.exists(file_path):
        print(f"[WARN] Datei {file_path} existiert nicht.")
        return set()
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        if not content.strip():
            print(f"[WARN] Datei {file_path} ist leer.")
            return set()
        c = Calendar(content)
    events = set()
    for e in c.events:
        day = e.begin.date().isoformat()
        events.add((e.uid, day, e.name))
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
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
            smtp.login(smtp_email, smtp_password)
            smtp.send_message(message)
        print("[INFO] E-Mail erfolgreich gesendet.")
    except Exception as e:
        print(f"[ERROR] Fehler beim Senden der E-Mail: {e}")

def main():
    smtp_email = os.getenv("SMTP_EMAIL")
    smtp_password = os.getenv("SMTP_PASSWORD")
    mail_recipient = os.getenv("MAIL_RECIPIENT")

    if not all([smtp_email, smtp_password, mail_recipient]):
        print("Bitte SMTP_EMAIL, SMTP_PASSWORD und MAIL_RECIPIENT als Secrets setzen!")
        return
    print("[INFO] SMTP und Mail-Empfänger sind gesetzt.")

    old_events = load_events(OLD_ICS_PATH)
    new_events = load_events(NEW_ICS_PATH)

    if not new_events:
        print("[WARN] Keine neuen Events geladen, Abbruch.")
        return

    if new_events != old_events:
        changed_days = extract_changed_days(old_events, new_events)
        if changed_days:
            print(f"Änderungen gefunden an Tagen: {changed_days}, sende Mail...")
            send_mail(changed_days, smtp_email, smtp_password, mail_recipient)
            try:
                with open(NEW_ICS_PATH, "r", encoding="utf-8") as f_new, \
                     open(OLD_ICS_PATH, "w", encoding="utf-8") as f_old:
                    f_old.write(f_new.read())
                print("[INFO] Alte ICS-Datei aktualisiert.")
            except Exception as e:
                print(f"[ERROR] Fehler beim Aktualisieren der alten ICS-Datei: {e}")
        else:
            print("Änderungen entdeckt, aber keine Tage zum Melden gefunden.")
    else:
        print("Keine Änderungen zum Stundenplan.")

if __name__ == "__main__":
    main()
