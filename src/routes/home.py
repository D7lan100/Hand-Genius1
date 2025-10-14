# src/routes/home.py
from flask import Blueprint, render_template, flash, current_app
from flask_login import login_required, current_user
from src.models.ModelProducto import ModelProducto

home_bp = Blueprint('home_bp', __name__)

@home_bp.route('/', endpoint='index')
def index():
    try:
        productos_lista = ModelProducto.get_all(current_app.db)
        return render_template('home/index.html', productos=productos_lista)
    except Exception as e:
        flash("Error al cargar los productos: " + str(e), "danger")
        return render_template('home/index.html', productos=[])

@home_bp.route('/home', endpoint='home')
@login_required
def home():
    try:
        productos_lista = ModelProducto.get_all(current_app.db)
        return render_template('home/home.html', user=current_user, productos=productos_lista)
    except Exception as e:
        flash("Error al cargar los productos: " + str(e), "danger")
        return render_template('home/home.html', user=current_user, productos=[])
