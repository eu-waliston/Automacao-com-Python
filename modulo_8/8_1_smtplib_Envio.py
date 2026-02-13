import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(subject, body, to_email):
    msg = MIMEMultipart()
    msg['From'] = 'bot@empresa.com'
    msg['to'] = to_email
    msg['subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login("email", "senha")
        server.send_message(msg)