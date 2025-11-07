# app.py
import os
from flask import Flask
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

    # ------------------ EXTENSIONES ------------------
    csrf = CSRFProtect(app)
    db = MySQL(app)
    login_manager = LoginManager(app)
    login_manager.login_view = 'auth_bp.login'
    login_manager.login_message = 'Por favor, inicia sesión para acceder a esta página.'
    login_manager.login_message_category = 'info'
    mail = Mail(app)  # Configurar correo

    SECRET_KEY_TOKEN = os.environ.get('SECRET_KEY_TOKEN') or app.config.get('SECRET_KEY', 'clave_secreta_fallback')
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

    app.register_blueprint(auth_bp)
    app.register_blueprint(home_bp)
    app.register_blueprint(productos_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(navbar_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(carrito_bp)
    app.register_blueprint(suscripciones_bp, url_prefix="/suscripciones")

    # ------------------ EXENCIONES CSRF ------------------
    csrf_exempt_endpoints = [
        'admin_bp.in_editar_usuario',
        'admin_bp.admin_eliminar_usuario',
        'admin_bp.admin_editar_producto',
        'admin_bp.admin_eliminar_producto',
        'admin_bp.admin_agregar_producto',
        'usuario_bp.actualizar_perfil',
        'api_bp.api_eventos',
        'carrito_bp.agregar',
        'carrito_bp.vaciar',
        'carrito_bp.eliminar',
        'carrito_bp.checkout',
        'navbar_bp.calendario',
        'suscripciones_bp.subir_comprobante',
        'admin_bp.aprobar_suscripcion',
        'admin_bp.rechazar_suscripcion',
        'admin_bp.eliminar_usuario',
        'admin_bp.editar_usuario'
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
