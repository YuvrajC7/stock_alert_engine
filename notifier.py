import smtplib
from email.message import EmailMessage
from plyer import notification
import json
import os

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

def send_desktop_notification(title, message):
    try:
        notification.notify(
            title=title,
            message=message,
            app_name='SSL Alert System',
            timeout=10
        )
    except Exception as e:
        print(f"Failed to send desktop notification: {e}")

def send_email(subject, body):
    config = load_config()
    email_conf = config.get("email", {})
    sender = email_conf.get("sender")
    password = email_conf.get("password")
    receiver = email_conf.get("receiver")
    
    if not sender or not password or not receiver or sender == "your_email@gmail.com":
        print("Email configuration is missing or default. Skipping email notification.")
        return
        
    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = receiver
    
    try:
        # Assumes Gmail. Change smtp server if using another provider.
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender, password)
        server.send_message(msg)
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")
