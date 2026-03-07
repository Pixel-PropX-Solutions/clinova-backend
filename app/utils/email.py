import smtplib
from email.message import EmailMessage
from app.config import settings

def send_email(to_email: str, subject: str, body: str):
    if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
        print(f"Mock sending email to {to_email}")
        print(f"Subject: {subject}")
        print(f"Body: {body}")
        return

    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = settings.SMTP_USERNAME
        msg['To'] = to_email

        server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
        server.starttls()
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"Successfully sent email to {to_email}")
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")
