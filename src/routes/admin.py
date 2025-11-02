# src/routes/admin.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime

from src.models.ModelProducto import ModelProducto
from src.models.ModelUser import ModelUser

admin_bp = Blueprint('admin_bp', __name__)

# Decorador admin (recrea el comportamiento original)
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Si no está autenticado, Flask-Login ya se encargará gracias a @login_required,
        # pero igual podemos reforzarlo:
        if not current_user.is_authenticated:
            return redirect(url_for('auth_bp.login', next=request.url))
        # Si no tiene rol de administrador
        if getattr(current_user, 'id_rol', None) != 2:
            flash("No tienes permisos para acceder al panel de administración.", "error")
            return redirect(url_for('home_bp.home'))  # 👈 o cualquier vista pública segura
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/admin', endpoint='admin')
@login_required
@admin_required
def admin_dashboard():
    try:
        cursor = current_app.db.connection.cursor()

        cursor.execute("SELECT COUNT(*) FROM usuarios")
        total_usuarios = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM productos WHERE disponible = 1")
        total_productos = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM pedidos")
        total_pedidos = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM pedidos WHERE estado = 'pendiente'")
        pedidos_pendientes = cursor.fetchone()[0] or 0

        cursor.execute("""
            SELECT COALESCE(SUM(precio_total), 0) 
            FROM detalle_pedido dp 
            JOIN pedidos p ON dp.id_pedido = p.id_pedido
            WHERE MONTH(p.fecha_pedido) = MONTH(NOW()) AND YEAR(p.fecha_pedido) = YEAR(NOW())
        """)
        ingresos_mes = float(cursor.fetchone()[0] or 0)

        cursor.execute("""
            SELECT pr.nombre, SUM(dp.cantidad) 
            FROM productos pr
            JOIN detalle_pedido dp ON pr.id_producto = dp.id_producto
            JOIN pedidos p ON dp.id_pedido = p.id_pedido
            WHERE p.fecha_pedido >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            GROUP BY pr.id_producto, pr.nombre
            ORDER BY SUM(dp.cantidad) DESC
            LIMIT 5
        """)
        productos_populares = cursor.fetchall()

        cursor.execute("""
            SELECT 'pedido', CONCAT('Nuevo pedido #', id_pedido), fecha_pedido
            FROM pedidos
            WHERE fecha_pedido >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            ORDER BY fecha_pedido DESC
            LIMIT 5
        """)
        actividad_pedidos = cursor.fetchall()

        cursor.execute("""
            SELECT 'usuario', CONCAT('Nuevo usuario: ', nombre_completo), fecha_registro
            FROM usuarios
            WHERE fecha_registro >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            ORDER BY fecha_registro DESC
            LIMIT 5
        """)
        actividad_usuarios = cursor.fetchall()

        actividad_reciente = list(actividad_pedidos) + list(actividad_usuarios)
        actividad_reciente.sort(key=lambda x: x[2] if x[2] else datetime.min, reverse=True)
        actividad_reciente = actividad_reciente[:10]

        cursor.close()

        estadisticas = {
            'total_usuarios': total_usuarios,
            'total_productos': total_productos,
            'total_pedidos': total_pedidos,
            'pedidos_pendientes': pedidos_pendientes,
            'ingresos_mes': ingresos_mes,
            'productos_populares': productos_populares,
            'actividad_reciente': actividad_reciente
        }

        return render_template('admin/dashboard.html', user=current_user, estadisticas=estadisticas)

    except Exception as e:
        print(f"Error en admin_dashboard: {e}")
        flash(f"Error al cargar el dashboard: {str(e)}", "danger")
        estadisticas = {
            'total_usuarios': 0,
            'total_productos': 0,
            'total_pedidos': 0,
            'pedidos_pendientes': 0,
            'ingresos_mes': 0.0,
            'productos_populares': [],
            'actividad_reciente': []
        }
        return render_template('admin/dashboard.html', user=current_user, estadisticas=estadisticas)

@admin_bp.route('/admin/usuarios', endpoint='admin_usuarios')
@login_required
@admin_required
def admin_usuarios():
    try:
        cursor = current_app.db.connection.cursor()
        cursor.execute("""
            SELECT u.id_usuario, u.nombre_completo, u.correo_electronico, u.telefono, u.fecha_registro, r.nombre
            FROM usuarios u
            LEFT JOIN roles r ON u.id_rol = r.id_rol
        """)
        usuarios = cursor.fetchall()
        cursor.close()
        return render_template('admin/usuarios.html', usuarios=usuarios, user=current_user)
    except Exception as e:
        flash(f"Error al cargar usuarios: {str(e)}", "danger")
        return render_template('admin/usuarios.html', usuarios=[], user=current_user)

@admin_bp.route('/admin/usuario/<int:id>/editar', methods=['POST'], endpoint='admin_editar_usuario')
@login_required
@admin_required
def admin_editar_usuario(id):
    try:
        nombre_completo = request.form.get('nombre_completo')
        correo_electronico = request.form.get('correo_electronico')
        id_rol = request.form.get('id_rol')

        cursor = current_app.db.connection.cursor()

        sql = """
            UPDATE usuarios 
            SET nombre_completo = %s,
                correo_electronico = %s,
                id_rol = %s
            WHERE id_usuario = %s
        """
        cursor.execute(sql, (nombre_completo, correo_electronico, id_rol, id))
        current_app.db.connection.commit()
        cursor.close()

        flash("Usuario actualizado correctamente", "success")
        return redirect(url_for('admin_usuarios'))

    except Exception as e:
        current_app.db.connection.rollback()
        flash(f"Error al actualizar usuario: {str(e)}", "danger")
        return redirect(url_for('admin_usuarios'))

@admin_bp.route('/admin/usuario/<int:id>/eliminar', methods=['POST'], endpoint='admin_eliminar_usuario')
@login_required
@admin_required
def admin_eliminar_usuario(id):
    try:
        cursor = current_app.db.connection.cursor()

        cursor.execute("DELETE FROM sugerencias WHERE id_usuario=%s", (id,))
        cursor.execute("DELETE FROM suscripciones WHERE id_usuario=%s", (id,))
        cursor.execute("DELETE FROM detalle_pedido WHERE id_pedido IN (SELECT id_pedido FROM pedidos WHERE id_usuario=%s)", (id,))
        cursor.execute("DELETE FROM domicilio WHERE id_pedido IN (SELECT id_pedido FROM pedidos WHERE id_usuario=%s)", (id,))
        cursor.execute("DELETE FROM pedidos WHERE id_usuario=%s", (id,))
        cursor.execute("DELETE FROM usuarios WHERE id_usuario=%s", (id,))

        current_app.db.connection.commit()
        cursor.close()

        flash("Usuario y todos sus datos relacionados eliminados correctamente", "success")
    except Exception as e:
        current_app.db.connection.rollback()
        flash(f"Error al eliminar usuario: {str(e)}", "danger")

    return redirect(url_for('admin_usuarios'))

@admin_bp.route('/admin/productos', endpoint='admin_productos')
@login_required
@admin_required
def admin_productos():
    try:
        productos = ModelProducto.get_all(current_app.db)
        return render_template('admin/productos.html', productos=productos, user=current_user)
    except Exception as e:
        flash(f"Error al cargar productos: {str(e)}", "danger")
        return render_template('admin/productos.html', productos=[], user=current_user)

@admin_bp.route('/admin/producto/<int:id>/editar', methods=['POST'], endpoint='admin_editar_producto')
@login_required
@admin_required
def admin_editar_producto(id):
    try:
        nombre = request.form.get('nombre')
        precio = request.form.get('precio')
        disponible = 1 if request.form.get('disponible') == 'on' else 0
        es_personalizable = 1 if request.form.get('es_personalizable') == 'on' else 0
        id_categoria = request.form.get('id_categoria')
        imagen = request.form.get('imagen')

        if ModelProducto.update(current_app.db, id, nombre, precio, disponible, es_personalizable, id_categoria, imagen):
            flash("Producto actualizado correctamente", "success")
        else:
            flash("No se pudo actualizar el producto", "danger")
        return redirect(url_for('admin_productos'))
    except Exception as e:
        flash(f"Error al actualizar producto: {str(e)}", "danger")
        return redirect(url_for('admin_productos'))

@admin_bp.route('/admin/producto/<int:id>/eliminar', methods=['POST'], endpoint='admin_eliminar_producto')
@login_required
@admin_required
def admin_eliminar_producto(id):
    if ModelProducto.delete(current_app.db, id):
        flash("Producto eliminado correctamente", "success")
    else:
        flash("No se pudo eliminar el producto", "danger")
    return redirect(url_for('admin_productos'))

@admin_bp.route('/admin/producto/agregar', methods=['POST'], endpoint='admin_agregar_producto')
# en tu código original no tenía login_required/admin_required: lo dejamos igual para mantener la lógica original
def admin_agregar_producto():
    try:
        nombre = request.form['nombre']
        descripcion = request.form.get('descripcion')
        precio = float(request.form['precio'])
        disponible = int(request.form.get('disponible', 1))
        es_personalizable = int(request.form.get('es_personalizable', 0))
        id_categoria = request.form.get('id_categoria')
        imagen = request.form.get('imagen')

        cursor = current_app.db.connection.cursor()
        sql = """INSERT INTO productos 
                 (nombre, descripcion, precio, disponible, es_personalizable, id_categoria, imagen)
                 VALUES (%s,%s,%s,%s,%s,%s,%s)"""
        cursor.execute(sql, (nombre, descripcion, precio, disponible, es_personalizable, id_categoria, imagen))
        current_app.db.connection.commit()
        cursor.close()

        flash("Producto agregado exitosamente.", "success")
        return redirect(url_for('admin_productos'))

    except Exception as ex:
        flash(f"Error al agregar producto: {ex}", "danger")
        return redirect(url_for('admin_productos'))
