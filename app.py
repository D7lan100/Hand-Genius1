# app.py
import os
from flask import Flask, render_template
from flask_mysqldb import MySQL
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Mail  # 👈 Importamos Flask-Mail

from config import config
from src.models.ModelUser import ModelUser


def create_app():
    app = Flask(__name__, template_folder="src/templates", static_folder="src/static")
    app.config.from_object(config['development'])

    # Extensiones
    csrf = CSRFProtect(app)
    db = MySQL(app)
    login_manager = LoginManager(app)
    login_manager.login_view = 'auth_bp.login'
    login_manager.login_message = 'Por favor, inicia sesión para acceder a esta página.'
    login_manager.login_message_category = 'info'

    # Configuración de Flask-Mail
    mail = Mail(app)  # 👈 Inicializamos Flask-Mail

    # Generador de tokens seguros (para recuperación de contraseña con enlace/código)
    SECRET_KEY_TOKEN = os.environ.get('SECRET_KEY_TOKEN') or app.config.get('SECRET_KEY', 'clave_secreta_fallback')
    s = URLSafeTimedSerializer(SECRET_KEY_TOKEN)

    # Adjuntar en app para que los blueprints accedan con current_app.*
    app.db = db
    app.csrf = csrf
    app.login_manager = login_manager
    app.mail = mail     # 👈 Ahora tu app tiene mail accesible
    app.s = s           # 👈 Serializador disponible para reset de contraseña

    # loader de usuarios
    @login_manager.user_loader
    def load_user(id_usuario):
        return ModelUser.get_by_id(app.db, id_usuario)

    # Importar blueprints
    from src.routes.auth import auth_bp
    from src.routes.home import home_bp
    from src.routes.productos import productos_bp
    from src.routes.admin import admin_bp
    from src.routes.api import api_bp
    from src.routes.navbar import navbar_bp
    from src.routes.usuarios import usuarios_bp
    from src.routes.carrito import carrito_bp
    from src.routes.suscripciones import suscripciones_bp
    from src.routes.admin_suscripciones import admin_suscripciones_bp
    from src.routes.personalizacion import personalizacion_bp

    # Registrar blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(home_bp)
    app.register_blueprint(productos_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(navbar_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(carrito_bp)
    app.register_blueprint(suscripciones_bp, url_prefix="/suscripciones")
    app.register_blueprint(admin_suscripciones_bp, url_prefix="/admin/suscripciones")

    # Exenciones CSRF
    csrf_exempt_endpoints = [
    'auth_bp.logout_redirect',
    'admin_editar_usuario',
    'admin_eliminar_usuario',
    'admin_editar_producto',
    'admin_eliminar_producto',
    'admin_agregar_producto',
    'actualizar_perfil',
    'calendario',
    'api_eventos',
    'carrito_bp.agregar',      # POST agregar producto
    'carrito_bp.vaciar',       # POST vaciar carrito
    'carrito_bp.eliminar',     # POST eliminar producto
    'carrito_bp.checkout',     # POST checkout
    'productos_bp.guardar_texto_personalizado',
    'productos_bp.subir_boceto',
    'productos_bp.guardar_plantilla',
    'productos_bp.registrar_formulario' 
]


    for ep in csrf_exempt_endpoints:
        view = app.view_functions.get(ep)
        if view:
            try:
                csrf.exempt(view)
            except Exception:
                pass

    # Debug rutas registradas
    print("\n📌 Rutas registradas en la app:")
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint:25s} -> {rule.rule}")

    return app


if __name__ == '__main__':
    app = create_app()
    print("🏠 Sitio web: http://localhost:5000")
    print("👑 Dashboard admin: http://localhost:5000/admin")
    app.run(debug=True, port=5000)