# routes/usuarios.py
from flask import Blueprint, render_template
from flask_login import login_required, current_user

usuarios_bp = Blueprint('usuarios_bp', __name__, url_prefix="/usuarios")

# Ruta de perfil/configuración
@usuarios_bp.route('/perfil')
@login_required
def perfil():
    return render_template('usuarios/perfil.html', user=current_user)

# Si quieres que sea editable:
@usuarios_bp.route('/perfil/configuracion')
@login_required
def configuracion():
    return render_template('usuarios/configuracion.html', user=current_user)


