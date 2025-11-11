from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory
from flask_login import login_required, current_user
from functools import wraps
from datetime import date, timedelta
from src.models.ModelUser import ModelUser
from src.models.entities.User import User
from src.models.ModelSugerencia import ModelSugerencia
from src.database.db import get_connection
import os

admin_bp = Blueprint('admin_bp', __name__, url_prefix='/admin', template_folder='../../templates/admin')

# ---------------------------
# Decorador: solo administradores
# ---------------------------
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Debes iniciar sesión para acceder.", "warning")
            return redirect(url_for('auth_bp.login'))
        if getattr(current_user, 'id_rol', None) not in (1, 2):
            flash("No tienes permisos para acceder al panel de administración.", "danger")
            return redirect(url_for('home_bp.home'))
        return f(*args, **kwargs)
    return decorated_function


# ---------------------------
# Helpers
# ---------------------------
def fetchall_dict(cursor):
    cols = [d[0] for d in cursor.description] if cursor.description else []
    return [dict(zip(cols, row)) for row in cursor.fetchall()]

def fetchone_dict(cursor):
    cols = [d[0] for d in cursor.description] if cursor.description else []
    row = cursor.fetchone()
    return dict(zip(cols, row)) if row else None


# ---------------------------
# Dashboard principal
# ---------------------------
@admin_bp.route('/')
@login_required
@admin_required
def index():
    db = current_app.db
    estadisticas = {
        "total_usuarios": 0,
        "total_productos": 0,
        "total_pedidos": 0,
        "pedidos_pendientes": 0,
        "ingresos_mes": 0,
        "productos_populares": [],
        "actividad_reciente": []
    }

    try:
        cur = db.connection.cursor()

        cur.execute("SELECT COUNT(*) FROM usuarios")
        estadisticas["total_usuarios"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM productos")
        estadisticas["total_productos"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM pedidos")
        estadisticas["total_pedidos"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM pedidos WHERE estado='pendiente'")
        estadisticas["pedidos_pendientes"] = cur.fetchone()[0]

        cur.execute("""
            SELECT COALESCE(SUM(total),0)
            FROM pedidos 
            WHERE MONTH(fecha_pedido)=MONTH(CURDATE()) AND YEAR(fecha_pedido)=YEAR(CURDATE())
        """)
        estadisticas["ingresos_mes"] = float(cur.fetchone()[0] or 0)

        cur.execute("""
            SELECT p.nombre AS nombre, SUM(dp.cantidad) AS ventas
            FROM detalle_pedido dp
            JOIN productos p ON dp.id_producto=p.id_producto
            GROUP BY p.id_producto, p.nombre
            ORDER BY ventas DESC
            LIMIT 5
        """)
        estadisticas["productos_populares"] = fetchall_dict(cur)

        cur.execute("""
            SELECT 'Pedido #' AS tipo, CONCAT('Pedido #', id_pedido) AS descripcion, fecha_pedido AS fecha
            FROM pedidos
            ORDER BY fecha_pedido DESC
            LIMIT 5
        """)
        actividad = fetchall_dict(cur)

        estadisticas["actividad_reciente"] = actividad
        cur.close()
    except Exception as e:
        print(f"Error en dashboard: {e}")

    return render_template('admin/dashboard.html', estadisticas=estadisticas, user=current_user)


# ---------------------------
# USUARIOS
# ---------------------------
@admin_bp.route('/usuarios')
@login_required
@admin_required
def usuarios():
    db = get_connection()
    usuarios = ModelUser.listar_todos(db)
    return render_template('admin/usuarios.html', usuarios=usuarios)


@admin_bp.route('/usuario/<int:id>/eliminar', methods=['POST'])
@login_required
@admin_required
def eliminar_usuario(id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM usuarios WHERE id_usuario=%s", (id,))
        conn.commit()
        flash("✅ Usuario eliminado correctamente", "success")
    except Exception as e:
        conn.rollback()
        print(e)
        flash("❌ Error al eliminar usuario", "danger")
    finally:
        conn.close()
    return redirect(url_for('admin_bp.usuarios'))


@admin_bp.route('/usuario/<int:id_usuario>/editar', methods=['POST'])
@login_required
@admin_required
def admin_editar_usuario(id_usuario):
    nombre = request.form.get('nombre')
    correo = request.form.get('correo')
    telefono = request.form.get('telefono')
    direccion = request.form.get('direccion')

    if not nombre or not correo:
        flash('❌ Nombre y correo son obligatorios.', 'warning')
        return redirect(url_for('admin_bp.usuarios'))

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE usuarios SET nombre_completo=%s, correo_electronico=%s,
            telefono=%s, direccion=%s WHERE id_usuario=%s
        """, (nombre, correo, telefono, direccion, id_usuario))
        conn.commit()
        flash("✅ Usuario actualizado correctamente.", "success")
    except Exception as e:
        conn.rollback()
        flash("❌ Error al editar usuario.", "danger")
        print(e)
    finally:
        conn.close()
    return redirect(url_for('admin_bp.usuarios'))


# ---------------------------
# PRODUCTOS
# ---------------------------
@admin_bp.route('/productos')
@login_required
@admin_required
def productos():
    db = current_app.db
    try:
        cur = db.connection.cursor()
        cur.execute("SELECT * FROM productos ORDER BY id_producto DESC")
        productos = fetchall_dict(cur)
        cur.close()
    except Exception as e:
        productos = []
        flash("Error al cargar productos.", "danger")
        print(e)
    return render_template('admin/productos.html', productos=productos, user=current_user)

@admin_bp.route('/productos/agregar', methods=['POST'])
@login_required
@admin_required
def agregar_producto():
    db = current_app.db
    nombre = request.form.get('nombre')
    precio = request.form.get('precio')
    descripcion = request.form.get('descripcion', '')
    disponible = request.form.get('disponible', 1)
    es_personalizable = request.form.get('es_personalizable', 0)
    id_categoria = request.form.get('id_categoria') or None
    imagen = request.form.get('imagen', None)

    if not nombre or not precio:
        flash("❌ El nombre y el precio son obligatorios", "warning")
        return redirect(url_for('admin_bp.productos'))

    try:
        cursor = db.connection.cursor()

        # 🚀 NO insertamos el id_producto, dejamos que MySQL lo asigne automáticamente.
        cursor.execute("""
            INSERT INTO productos (nombre, descripcion, precio, imagen, id_categoria, disponible, es_personalizable)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (nombre, descripcion, precio, imagen, id_categoria, disponible, es_personalizable))

        db.connection.commit()
        cursor.close()
        flash("✅ Producto agregado correctamente", "success")

    except Exception as e:
        db.connection.rollback()
        current_app.logger.exception("Error agregando producto: %s", e)
        flash("❌ Error al agregar el producto", "danger")

    return redirect(url_for('admin_bp.productos'))

@admin_bp.route('/producto/<int:id_producto>/editar', methods=['POST'])
@login_required
@admin_required
def editar_producto(id_producto):
    nombre = request.form.get('nombre')
    descripcion = request.form.get('descripcion')
    precio = request.form.get('precio')
    imagen = request.form.get('imagen')
    categoria = request.form.get('id_categoria')
    disponible = int(request.form.get('disponible', 0))
    personalizable = int(request.form.get('es_personalizable', 0))

    if not nombre or not precio:
        flash("❌ El nombre y el precio son obligatorios", "warning")
        return redirect(url_for('admin_bp.productos'))

    try:
        cur = current_app.db.connection.cursor()
        cur.execute("""
            UPDATE productos
            SET nombre=%s,
                descripcion=%s,
                precio=%s,
                imagen=%s,
                id_categoria=%s,
                disponible=%s,
                es_personalizable=%s
            WHERE id_producto=%s
        """, (nombre, descripcion, precio, imagen, categoria, disponible, personalizable, id_producto))
        current_app.db.connection.commit()
        cur.close()
        flash("✅ Producto actualizado correctamente", "success")
    except Exception as e:
        current_app.db.connection.rollback()
        current_app.logger.exception("Error al editar producto: %s", e)
        flash("❌ Error al editar el producto", "danger")

    return redirect(url_for('admin_bp.productos'))

@admin_bp.route('/producto/<int:id_producto>/eliminar', methods=['POST'])
@login_required
@admin_required
def eliminar_producto(id_producto):
    try:
        cur = current_app.db.connection.cursor()
        cur.execute("DELETE FROM productos WHERE id_producto = %s", (id_producto,))
        current_app.db.connection.commit()
        cur.close()
        flash("🗑️ Producto eliminado correctamente", "info")
    except Exception as e:
        current_app.db.connection.rollback()
        current_app.logger.exception("Error al eliminar producto: %s", e)
        flash("❌ No se pudo eliminar el producto", "danger")

    return redirect(url_for('admin_bp.productos'))

# ---------------------------
# SUGERENCIAS
# ---------------------------
@admin_bp.route('/sugerencias', endpoint='admin_sugerencias')
@login_required
@admin_required
def admin_sugerencias():
    try:
        db = current_app.db
        sugerencias = ModelSugerencia.obtener_todas(db)
    except Exception as e:
        print(f"❌ Error al cargar sugerencias: {e}")
        sugerencias = []
    return render_template('admin/sugerencias.html', sugerencias=sugerencias, user=current_user)


# ---------------------------
# PEDIDOS
# ---------------------------
@admin_bp.route('/pedidos')
@login_required
@admin_required
def pedidos():
    db = current_app.db
    try:
        cur = db.connection.cursor()
        cur.execute("""
            SELECT p.id_pedido, u.nombre_completo AS usuario, p.fecha_pedido,
                   p.metodo_pago, p.estado, p.comprobante_pago,
                   d.empresa_transportadora, d.fecha_envio, d.estado AS envio_estado
            FROM pedidos p
            LEFT JOIN usuarios u ON p.id_usuario=u.id_usuario
            LEFT JOIN domicilio d ON p.id_pedido=d.id_pedido
            ORDER BY p.fecha_pedido DESC
        """)
        pedidos = fetchall_dict(cur)
        cur.close()
    except Exception as e:
        pedidos = []
        flash("Error al cargar pedidos", "danger")
        print(e)
    return render_template('admin/pedidos.html', pedidos=pedidos, user=current_user)


@admin_bp.route('/pedidos/actualizar/<int:id_pedido>', methods=['POST'])
@login_required
@admin_required
def actualizar_pedido(id_pedido):
    estado = request.form.get('estado')
    empresa = request.form.get('empresa_transportadora')
    fecha_envio = request.form.get('fecha_envio')
    try:
        cur = current_app.db.connection.cursor()
        cur.execute("UPDATE pedidos SET estado=%s WHERE id_pedido=%s", (estado, id_pedido))
        if estado in ('enviado', 'entregado'):
            cur.execute("""
                INSERT INTO domicilio (id_pedido, empresa_transportadora, fecha_envio, estado)
                VALUES (%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE empresa_transportadora=%s, fecha_envio=%s, estado=%s
            """, (id_pedido, empresa, fecha_envio, estado, empresa, fecha_envio, estado))
        current_app.db.connection.commit()
        cur.close()
        flash("✅ Pedido actualizado correctamente", "success")
    except Exception as e:
        current_app.db.connection.rollback()
        flash("❌ Error al actualizar pedido", "danger")
        print(e)
    return redirect(url_for('admin_bp.pedidos'))


# ---------------------------
# SUSCRIPCIONES
# ---------------------------
@admin_bp.route('/suscripciones')
@login_required
@admin_required
def suscripciones():
    db = current_app.db
    try:
        cur = db.connection.cursor()
        cur.execute("""
            SELECT s.id_suscripcion, u.nombre_completo AS usuario, ts.nombre AS tipo,
                   s.fecha_inicio, s.fecha_fin, s.comprobante, s.estado
            FROM suscripciones s
            LEFT JOIN usuarios u ON s.id_usuario=u.id_usuario
            LEFT JOIN tipo_suscripcion ts ON s.id_tipo_suscripcion=ts.id_tipo_suscripcion
            ORDER BY s.fecha_inicio DESC
        """)
        suscripciones = fetchall_dict(cur)
        cur.close()
    except Exception as e:
        suscripciones = []
        flash("Error al cargar suscripciones", "danger")
        print(e)
    return render_template('admin/suscripciones.html', suscripciones=suscripciones, user=current_user)


@admin_bp.route('/suscripciones/aprobar/<int:id_suscripcion>', methods=['POST'])
@login_required
@admin_required
def aprobar_suscripcion(id_suscripcion):
    try:
        cur = current_app.db.connection.cursor()
        inicio = date.today()
        fin = inicio + timedelta(days=30)
        cur.execute("UPDATE suscripciones SET estado='Aprobada', fecha_inicio=%s, fecha_fin=%s WHERE id_suscripcion=%s",
                    (inicio, fin, id_suscripcion))
        current_app.db.connection.commit()
        cur.close()
        flash("✅ Suscripción aprobada correctamente", "success")
    except Exception as e:
        current_app.db.connection.rollback()
        flash("❌ Error al aprobar suscripción", "danger")
        print(e)
    return redirect(url_for('admin_bp.suscripciones'))


@admin_bp.route('/suscripciones/rechazar/<int:id_suscripcion>', methods=['POST'])
@login_required
@admin_required
def rechazar_suscripcion(id_suscripcion):
    try:
        cur = current_app.db.connection.cursor()
        cur.execute("UPDATE suscripciones SET estado='Rechazada' WHERE id_suscripcion=%s", (id_suscripcion,))
        current_app.db.connection.commit()
        cur.close()
        flash("❌ Suscripción rechazada", "info")
    except Exception as e:
        current_app.db.connection.rollback()
        flash("❌ Error al rechazar suscripción", "danger")
        print(e)
    return redirect(url_for('admin_bp.suscripciones'))


@admin_bp.route('/suscripciones/comprobante/<path:filename>')
@login_required
@admin_required
def ver_comprobante(filename):
    upload_path = os.path.join(current_app.root_path, 'static', 'comprobantes')
    return send_from_directory(upload_path, filename)
