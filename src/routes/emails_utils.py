import smtplib
from email.mime.text import MIMEText
from flask import current_app

def send_reset_code(to_email, code):
    msg = MIMEText(f"Tu código de recuperación es: {code}\nEste código expira en 10 minutos.")
    msg['Subject'] = 'Recuperación de contraseña'
    msg['From'] = current_app.config['MAIL_USERNAME']
    msg['To'] = to_email

    with smtplib.SMTP(current_app.config['MAIL_SERVER'], current_app.config['MAIL_PORT']) as server:
        server.starttls()
        server.login(current_app.config['MAIL_USERNAME'], current_app.config['MAIL_PASSWORD'])
        server.sendmail(msg['From'], [to_email], msg.as_string())
