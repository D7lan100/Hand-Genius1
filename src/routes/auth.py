from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required
from werkzeug.security import check_password_hash
from datetime import datetime, timedelta
import random, string
from flask_mail import Message  # 👈 Usamos Flask-Mail

from src.models.ModelUser import ModelUser
from src.models.entities.User import User

auth_bp = Blueprint('auth_bp', __name__)

# ------------------------
# Helpers
# ------------------------
def _generate_code(length: int = 6) -> str:
    """Generar un código numérico de recuperación (OTP)."""
    return ''.join(random.choices(string.digits, k=length))


def _send_email(to_email: str, subject: str, body: str) -> bool:
    """Enviar correo usando Flask-Mail."""
    try:
        msg = Message(subject=subject,
                      sender=current_app.config.get("MAIL_USERNAME"),
                      recipients=[to_email])
        msg.body = body
        current_app.mail.send(msg)
        return True
    except Exception as ex:
        current_app.logger.exception("❌ Error enviando correo: %s", ex)
        return False


# ------------------------
# Login / Logout / Register
# ------------------------
@auth_bp.route('/login', methods=['GET', 'POST'], endpoint='login')
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash("Todos los campos son obligatorios", "error")
            return render_template('auth/login.html')

        user = User(0, email, password, '')
        logged_user = ModelUser.login(current_app.db, user)

        if logged_user and check_password_hash(logged_user.contraseña, password):
            login_user(logged_user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home_bp.home'))
        else:
            flash("Usuario o contraseña incorrectos", "error")

    return render_template('auth/login.html')

@auth_bp.route('/logout_redirect', methods=['POST'])
@login_required
def logout_redirect():
    logout_user()
    flash("Has cerrado sesión exitosamente", "success")
    return redirect(url_for('home_bp.index'))

@auth_bp.route('/register', methods=['GET', 'POST'], endpoint='register')
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        contact = request.form.get('contact', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')

        errors = []
        if not username:
            errors.append("El nombre de usuario es obligatorio")
        if not contact:
            errors.append("El contacto es obligatorio")
        if not email:
            errors.append("El email es obligatorio")
        if not password:
            errors.append("La contraseña es obligatoria")
        if len(password) < 6:
            errors.append("La contraseña debe tener al menos 6 caracteres")
        if password != password2:
            errors.append("Las contraseñas no coinciden")

        if email and ModelUser.get_by_email(current_app.db, email):
            errors.append("El correo electrónico ya está registrado")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template('auth/register.html')

        user = User(0, email, password, username)
        if ModelUser.register(current_app.db, user, contact):
            flash("Usuario registrado exitosamente. ¡Ya puedes iniciar sesión!", "success")
            return redirect(url_for('auth_bp.login'))
        else:
            flash("Error al registrar usuario. Intenta nuevamente.", "error")

    return render_template('auth/register.html')


# ------------------------
# Recuperación de contraseña con CÓDIGO (OTP)
# ------------------------
@auth_bp.route('/forgot_password', methods=['GET', 'POST'], endpoint='forgot_password')
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        if not email:
            flash("El email es obligatorio", "error")
            return render_template("auth/forgot_password.html")

        user = ModelUser.get_by_email(current_app.db, email)
        if not user:
            flash("Si el email está registrado, recibirás un código de recuperación", "info")
            return redirect(url_for('auth_bp.forgot_password'))

        # Generar código OTP
        codigo = _generate_code(6)
        expira = datetime.now() + timedelta(minutes=10)

        try:
            cursor = current_app.db.connection.cursor()
            cursor.execute("""
                UPDATE usuarios
                SET codigo_reset=%s, expira_reset=%s
                WHERE correo_electronico=%s
            """, (codigo, expira, email))
            current_app.db.connection.commit()
            cursor.close()
        except Exception as ex:
            current_app.logger.exception("❌ Error guardando código en BD: %s", ex)
            flash("Error interno. Intenta más tarde.", "error")
            return render_template("auth/forgot_password.html")

        subject = "Código de recuperación - Hand&Genius"
        body = (
            f"Hola,\n\n"
            f"Tu código de recuperación es: {codigo}\n\n"
            f"Este código expira en 10 minutos.\n\n"
            f"Si no solicitaste este código, ignora este mensaje."
        )

        enviado = _send_email(email, subject, body)
        if enviado:
            flash("Hemos enviado un código de recuperación a tu correo.", "info")
        else:
            current_app.logger.warning("⚠️ No se pudo enviar el correo; código generado: %s", codigo)
            flash("No se pudo enviar el correo. Intenta de nuevo más tarde.", "error")

        return redirect(url_for("auth_bp.verify_code", email=email))

    return render_template("auth/forgot_password.html")


@auth_bp.route('/verify_code', methods=['GET', 'POST'], endpoint='verify_code')
def verify_code():
    email = request.args.get('email') or request.form.get('email') or ''
    if request.method == 'POST':
        codigo = request.form.get('codigo', '').strip()
        email = request.form.get('email', '').strip().lower()

        if not email or not codigo:
            flash("Email y código son requeridos", "error")
            return render_template("auth/verify_code.html", email=email)

        try:
            cursor = current_app.db.connection.cursor()
            cursor.execute("""
                SELECT codigo_reset, expira_reset
                FROM usuarios
                WHERE correo_electronico = %s
            """, (email,))
            row = cursor.fetchone()
            cursor.close()

            if not row:
                flash("Código inválido o expirado", "error")
                return render_template("auth/verify_code.html", email=email)

            codigo_bd, expira_bd = row if not isinstance(row, dict) else (row.get('codigo_reset'), row.get('expira_reset'))

            if codigo_bd and str(codigo_bd) == codigo and expira_bd and datetime.now() < expira_bd:
                flash("Código válido. Ahora puedes cambiar tu contraseña.", "success")
                return redirect(url_for("auth_bp.reset_password_code", email=email))
            else:
                flash("Código inválido o expirado", "error")
        except Exception as ex:
            current_app.logger.exception("❌ Error validando código: %s", ex)
            flash("Error interno al validar el código", "error")

    return render_template("auth/verify_code.html", email=email)


@auth_bp.route('/reset_password_code', methods=['GET', 'POST'], endpoint='reset_password_code')
def reset_password_code():
    email = request.args.get('email') or request.form.get('email') or ''
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')

        if not email:
            flash("Email requerido", "error")
            return render_template("auth/reset_password_code.html", email=email)

        if not password or len(password) < 6:
            flash("La contraseña debe tener al menos 6 caracteres", "error")
            return render_template("auth/reset_password_code.html", email=email)

        if password != password2:
            flash("Las contraseñas no coinciden", "error")
            return render_template("auth/reset_password_code.html", email=email)

        try:
            cursor = current_app.db.connection.cursor()
            cursor.execute("""
                SELECT expira_reset
                FROM usuarios
                WHERE correo_electronico = %s
            """, (email,))
            row = cursor.fetchone()

            if not row:
                flash("Operación no permitida", "error")
                cursor.close()
                return render_template("auth/reset_password_code.html", email=email)

            expira_bd = row[0] if not isinstance(row, dict) else row.get('expira_reset')

            if not expira_bd or datetime.now() > expira_bd:
                flash("El código expiró. Solicita uno nuevo.", "error")
                cursor.close()
                return redirect(url_for("auth_bp.forgot_password"))

            if ModelUser.reset_password(current_app.db, email, password):
                cursor.execute("""
                    UPDATE usuarios
                    SET codigo_reset = NULL, expira_reset = NULL
                    WHERE correo_electronico = %s
                """, (email,))
                current_app.db.connection.commit()
                cursor.close()

                flash("Contraseña actualizada con éxito. Ya puedes iniciar sesión.", "success")
                return redirect(url_for("auth_bp.login"))
            else:
                cursor.close()
                flash("Error al actualizar la contraseña", "error")
        except Exception as ex:
            current_app.logger.exception("❌ Error actualizando contraseña: %s", ex)
            flash("Error interno", "error")

    return render_template("auth/reset_password_code.html", email=email)
