# src/routes/productos.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from src.models.ModelProducto import ModelProducto

productos_bp = Blueprint('productos_bp', __name__)

@productos_bp.route('/productos', endpoint='productos')
def productos():
    try:
        productos_lista = ModelProducto.get_all(current_app.db)
        print(f"Se cargaron {len(productos_lista)} productos")  # Debug

        if productos_lista:
            primer_producto = productos_lista[0]
            print(f"Primer producto - ID: {primer_producto.id}, Nombre: {primer_producto.nombre}")
            print(f"Atributos disponibles: {list(vars(primer_producto).keys())}")

        return render_template('producto/productos.html', productos=productos_lista)
    except Exception as e:
        print(f"Error en ruta /productos: {e}")
        flash(f"Error al cargar los productos: {str(e)}", "danger")
        return render_template('producto/productos.html', productos=[])

@productos_bp.route('/producto/<int:id>', endpoint='detalle_producto')
def detalle_producto(id):
    try:
        print(f"Buscando producto con ID: {id}")
        producto = ModelProducto.get_by_id(current_app.db, id)

        if not producto:
            flash("Producto no encontrado", "error")
            return redirect(url_for('productos'))

        print(f"Producto encontrado: {producto.nombre}")
        return render_template('producto/detalle_producto.html', producto=producto)

    except Exception as e:
        print(f"Error en detalle_producto: {e}")
        flash(f"Error al cargar el producto: {str(e)}", "error")
        return redirect(url_for('productos'))

@productos_bp.route('/productos/categoria/<int:id_categoria>', endpoint='productos_por_categoria')
def productos_por_categoria(id_categoria):
    try:
        productos_lista = ModelProducto.get_by_categoria(current_app.db, id_categoria)
        return render_template('producto/productos.html', productos=productos_lista, categoria_id=id_categoria)
    except Exception as e:
        print(f"Error en productos_por_categoria: {e}")
        flash(f"Error al cargar productos de la categoría: {str(e)}", "danger")
        return render_template('producto/productos.html', productos=[])

@productos_bp.route('/productos/buscar', endpoint='buscar_productos')
def buscar_productos():
    try:
        termino = request.args.get('q', '').strip()
        if not termino:
            flash("Ingresa un término de búsqueda", "info")
            return redirect(url_for('productos'))

        productos_lista = ModelProducto.search(current_app.db, termino)
        return render_template('producto/productos.html', productos=productos_lista, termino_busqueda=termino)
    except Exception as e:
        print(f"Error en buscar_productos: {e}")
        flash(f"Error al buscar productos: {str(e)}", "danger")
        return render_template('producto/productos.html', productos=[])

@productos_bp.route('/protected', endpoint='protected')
@login_required
def protected():
    return render_template('usuarios/base.html', user=current_user)
