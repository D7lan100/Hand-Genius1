# app.py
import os
from flask import Flask, render_template
from flask_mysqldb import MySQL
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Mail 

from config import config
from src.models.ModelUser import ModelUser


def create_app():
    app = Flask(__name__, template_folder="src/templates", static_folder="src/static")
    app.config.from_object(config['development'])
    # -----------------------------
    # 🔒 Aseguramos SECRET_KEY para sesiones/CSRF
    # Si no tienes SECRET_KEY en config, la cogemos de env o usamos un fallback para dev.
    # En producción debes usar una variable de entorno fuerte y segura.
    # -----------------------------
    app.secret_key = os.environ.get('SECRET_KEY') or app.config.get('SECRET_KEY') or 'dev_fallback_secret_key_!change_me'

    # Extender tiempo de validez del token CSRF (segundos). Ajusta según necesites.
    # Por defecto Flask-WTF tiene 3600 (1h). Aquí lo aumentamos para pruebas a 24h.
    app.config['WTF_CSRF_TIME_LIMIT'] = 60 * 60 * 24

    # Opciones de cookie de sesión para que navegador mantenga la sesión correctamente
    app.config.setdefault('SESSION_COOKIE_HTTPONLY', True)
    app.config.setdefault('SESSION_COOKIE_SAMESITE', 'Lax')
    # ------------------ EXTENSIONES ------------------
    csrf = CSRFProtect(app)
    db = MySQL(app)
    login_manager = LoginManager(app)
    login_manager.login_view = 'auth_bp.login'
    login_manager.login_message = 'Por favor, inicia sesión para acceder a esta página.'
    login_manager.login_message_category = 'info'
    mail = Mail(app)  # Configurar correo

    SECRET_KEY_TOKEN = os.environ.get('SECRET_KEY_TOKEN') or app.config.get('SECRET_KEY', app.secret_key)
    s = URLSafeTimedSerializer(SECRET_KEY_TOKEN)

    # Guardar en la app para uso en otros módulos
    app.db = db
    app.csrf = csrf
    app.login_manager = login_manager
    app.mail = mail
    app.s = s

    # ------------------ LOGIN MANAGER ------------------
    @login_manager.user_loader
    def load_user(id_usuario):
        return ModelUser.get_by_id(app.db, id_usuario)

    # ------------------ BLUEPRINTS ------------------
    from src.routes.auth import auth_bp
    from src.routes.home import home_bp
    from src.routes.productos import productos_bp
    from src.routes.admin import admin_bp
    from src.routes.api import api_bp
    from src.routes.navbar import navbar_bp
    from src.routes.usuarios import usuarios_bp
    from src.routes.carrito import carrito_bp
    from src.routes.suscripciones import suscripciones_bp
    from src.routes.personalizacion import personalizacion_bp
    from src.routes.sugerencias import sugerencias_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(home_bp)
    app.register_blueprint(productos_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(navbar_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(carrito_bp)
    app.register_blueprint(suscripciones_bp, url_prefix="/suscripciones")
    app.register_blueprint(sugerencias_bp, url_prefix="/sugerencias")

    # ------------------ EXENCIONES CSRF ------------------
    csrf_exempt_endpoints = [
        'auth_bp.logout_redirect',
        'admin_bp.in_editar_usuario',
        'admin_bp.agregar_producto',
        'admin_bp.editar_producto',
        'admin_bp.eliminar_producto',
        'admin_bp.actualizar_pedido'
        'usuario_bp.actualizar_perfil',
        'api_bp.api_eventos',
        'api_bp.api_productos',
        'carrito_bp.agregar',
        'carrito_bp.vaciar',
        'carrito_bp.eliminar',
        'carrito_bp.checkout',
        'carrito_bp.subir_comprobante',
        'navbar_bp.calendario',
        'suscripciones_bp.subir_comprobante',
        'admin_bp.aprobar_suscripcion',
        'admin_bp.rechazar_suscripcion',
        'admin_bp.eliminar_usuario',
        'admin_bp.admin_editar_usuario',
        'productos_bp.guardar_texto_personalizado',
        'productos_bp.subir_boceto',
        'productos_bp.guardar_plantilla',
        'productos_bp.registrar_formulario',
        'admin_bp.actualizar_pedido'
    ]

    for ep in csrf_exempt_endpoints:
        view = app.view_functions.get(ep)
        if view:
            try:
                csrf.exempt(view)
            except Exception:
                pass

    # ------------------ DEPURACIÓN ------------------
    print("\n📌 Rutas registradas en la app:")
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint:25s} -> {rule.rule}")

    return app


if __name__ == '__main__':
    app = create_app()
    print("🏠 Sitio web: http://localhost:5000")
    print("👑 Dashboard admin: http://localhost:5000/admin")
    app.run(debug=True, port=5000)
