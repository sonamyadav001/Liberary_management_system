import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configure these with real SMTP credentials to enable actual emails
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SMTP_USER = ''   # e.g. 'your@gmail.com'
SMTP_PASS = ''   # App password

def send_email_notification(to_email, subject, body):
    """Send email notification. Falls back to console log if not configured."""
    print(f"\n📧 EMAIL NOTIFICATION")
    print(f"   To: {to_email}")
    print(f"   Subject: {subject}")
    print(f"   Body: {body}\n")

    if not SMTP_USER or not SMTP_PASS:
        return True  # Silently succeed when not configured

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f'Shabd Sangrah Library <{SMTP_USER}>'
        msg['To'] = to_email

        html_body = f"""
        <html><body style="font-family:Arial,sans-serif;background:#F5F5DC;padding:20px">
        <div style="max-width:600px;margin:auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.1)">
          <div style="background:linear-gradient(135deg,#6D3B07,#D47E30);padding:30px;text-align:center">
            <h1 style="color:#F5F5DC;margin:0;font-size:28px">📚 Shabd Sangrah</h1>
            <p style="color:#F5F5DC;margin:5px 0">Library Management System</p>
          </div>
          <div style="padding:30px">
            <h2 style="color:#6D3B07">{subject}</h2>
            <p style="color:#333;line-height:1.6">{body}</p>
            <hr style="border:1px solid #eee;margin:20px 0">
            <p style="color:#999;font-size:12px">Shabd Sangrah Library | Connecting Readers with Knowledge</p>
          </div>
        </div>
        </body></html>
        """
        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False
