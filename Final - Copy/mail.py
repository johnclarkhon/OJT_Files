import os
import json
import smtplib
from email.mime.text import MIMEText

# Always locate database.json in the same folder as this file
DB_FILE = os.path.join(os.path.dirname(__file__), "database.json")


def load_settings():

    with open(DB_FILE, "r") as f:
        db = json.load(f)

    return db["notification_settings"]


def send_email(subject, message):

    settings = load_settings()

    smtp_server = settings["smtp_server"]
    smtp_port = settings["smtp_port"]

    from_address = settings["from_address"]
    recipients = settings["to_addresses"]

    smtp_username = settings.get("smtp_username", "")
    smtp_password = settings.get("smtp_password", "")
    use_tls = settings.get("use_tls", False)

    if recipients.strip() == "":
        return False

    recipient_list = [
        email.strip()
        for email in recipients.split(",")
        if email.strip()
    ]

    msg = MIMEText(message)

    msg["Subject"] = subject
    msg["From"] = from_address
    msg["To"] = ", ".join(recipient_list)

    try:

        smtp = smtplib.SMTP(smtp_server, smtp_port, timeout=30)

        smtp.ehlo()

        if use_tls:
            smtp.starttls()
            smtp.ehlo()

        if smtp_username and smtp_password:
            smtp.login(smtp_username, smtp_password)

        smtp.sendmail(
            from_address,
            recipient_list,
            msg.as_string()
        )

        smtp.quit()

        return True

    except Exception as e:

        print("Email Error:", e)

        return False