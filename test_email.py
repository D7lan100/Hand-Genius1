import smtplib
from email.mime.text import MIMEText
from email.header import Header

# 🔹 Cambia estos datos
REMITENTE = "handgenius21@gmail.com"
PASSWORD = "zcmbnrmgkjeqbsfc"  # contraseña de aplicación sin espacios
DESTINATARIO = "handgenius21@gmail.com"

try:
    # Crear mensaje con UTF-8
    mensaje = MIMEText("Hola, este es un test desde Python 🚀", "plain", "utf-8")
    mensaje["Subject"] = Header("Prueba de correo", "utf-8")
    mensaje["From"] = REMITENTE
    mensaje["To"] = DESTINATARIO

    # Conectar con el servidor SMTP de Gmail
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(REMITENTE, PASSWORD)

    # Enviar correo
    server.sendmail(REMITENTE, DESTINATARIO, mensaje.as_string())
    server.quit()

    print("✅ Correo enviado correctamente")

except Exception as e:
    print("❌ Error enviando correo:", e)
