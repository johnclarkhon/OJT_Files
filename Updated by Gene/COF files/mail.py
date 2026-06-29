import smtplib
from email.mime.text import MIMEText

# ==========================
# SMTP CONFIGURATION
# ==========================

EMAIL = "YOUR_EMAIL@gmail.com"
PASSWORD = "YOUR_APP_PASSWORD"

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


# ==========================
# SEND EMAIL
# ==========================

def send_email(receiver, subject, body):

    try:

        message = MIMEText(body)

        message["Subject"] = subject
        message["From"] = EMAIL
        message["To"] = receiver

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)

        server.starttls()

        server.login(EMAIL, PASSWORD)

        server.sendmail(
            EMAIL,
            receiver,
            message.as_string()
        )

        server.quit()

        print("Email sent successfully.")

        return True

    except Exception as e:

        print("Email Error:", e)

        return False