# src/routes/api.py
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from src.models.ModelProducto import ModelProducto
from src.models.ModelCalendario import ModelCalendario
from functools import wraps

api_bp = Blueprint('api_bp', __name__)

# admin_required (copia ligera)
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': 'No autorizado'}), 401
        if getattr(current_user, 'id_rol', None) != 2:
            return jsonify({'success': False, 'error': 'No tienes permisos'}), 403
        return f(*args, **kwargs)
    return decorated

@api_bp.route('/api/productos', methods=['GET'], endpoint='api_productos')
def api_productos():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        categoria_id = request.args.get('categoria_id', type=int)
        buscar = request.args.get('buscar', '').strip()

        per_page = min(per_page, 100)
        offset = (page - 1) * per_page

        cursor = current_app.db.connection.cursor()

        base_query = """
            SELECT p.*, c.nombre as categoria_nombre, u.nombre_completo as vendedor_nombre
            FROM productos p
            LEFT JOIN categorias c ON p.id_categoria = c.id_categoria
            LEFT JOIN usuarios u ON p.id_vendedor = u.id_usuario
            WHERE p.disponible = 1
        """

        params = []

        if categoria_id:
            base_query += " AND p.id_categoria = %s"
            params.append(categoria_id)

        if buscar:
            base_query += " AND (p.nombre LIKE %s OR p.descripcion LIKE %s)"
            params.extend([f'%{buscar}%', f'%{buscar}%'])

        count_query = base_query.replace(
            "SELECT p.*, c.nombre as categoria_nombre, u.nombre_completo as vendedor_nombre",
            "SELECT COUNT(*) as total"
        )
        cursor.execute(count_query, params)
        total = cursor.fetchone()['total']

        base_query += " ORDER BY p.id_producto DESC LIMIT %s OFFSET %s"
        params.extend([per_page, offset])

        cursor.execute(base_query, params)
        productos_raw = cursor.fetchall()
        cursor.close()

        productos = []
        for p in productos_raw:
            producto = dict(p)
            if producto.get('precio'):
                producto['precio'] = float(producto['precio'])
            if producto.get('calificacion_promedio'):
                producto['calificacion_promedio'] = float(producto['calificacion_promedio'])
            productos.append(producto)

        return jsonify({
            'success': True,
            'productos': productos,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': f'Error interno del servidor: {str(e)}'}), 500

@api_bp.route('/api/producto/<int:producto_id>', methods=['GET'], endpoint='api_producto_detalle')
def api_producto_detalle(producto_id):
    try:
        cursor = current_app.db.connection.cursor()
        cursor.execute("""
            SELECT p.*, c.nombre as categoria_nombre, u.nombre_completo as vendedor_nombre
            FROM productos p
            LEFT JOIN categorias c ON p.id_categoria = c.id_categoria
            LEFT JOIN usuarios u ON p.id_vendedor = u.id_usuario
            WHERE p.id_producto = %s AND p.disponible = 1
        """, (producto_id,))

        producto_raw = cursor.fetchone()
        if not producto_raw:
            cursor.close()
            return jsonify({'success': False, 'error': 'Producto no encontrado'}), 404

        producto = dict(producto_raw)
        if producto.get('precio'):
            producto['precio'] = float(producto['precio'])
        if producto.get('calificacion_promedio'):
            producto['calificacion_promedio'] = float(producto['calificacion_promedio'])

        cursor.execute("""
            SELECT c.puntuacion, c.comentario, c.fecha_calificacion, u.nombre_completo
            FROM calificaciones c
            LEFT JOIN usuarios u ON c.id_usuario = u.id_usuario
            WHERE c.id_producto = %s
            ORDER BY c.fecha_calificacion DESC
            LIMIT 10
        """, (producto_id,))

        calificaciones_raw = cursor.fetchall()
        calificaciones = []
        for c in calificaciones_raw:
            cal = dict(c)
            if cal.get('puntuacion'):
                cal['puntuacion'] = float(cal['puntuacion'])
            if cal.get('fecha_calificacion'):
                cal['fecha_calificacion'] = cal['fecha_calificacion'].isoformat()
            calificaciones.append(cal)

        cursor.execute("""
            SELECT tipo, url, descripcion
            FROM material_audiovisual
            WHERE id_producto = %s
            ORDER BY fecha_subida DESC
        """, (producto_id,))

        material_audiovisual = cursor.fetchall()
        cursor.close()

        return jsonify({'success': True, 'producto': producto, 'calificaciones': calificaciones, 'material_audiovisual': material_audiovisual}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error interno del servidor: {str(e)}'}), 500

@api_bp.route('/api/categorias', methods=['GET'], endpoint='api_categorias')
def api_categorias():
    try:
        cursor = current_app.db.connection.cursor()
        cursor.execute("""
            SELECT c.*, COUNT(p.id_producto) as total_productos
            FROM categorias c
            LEFT JOIN productos p ON c.id_categoria = p.id_categoria AND p.disponible = 1
            GROUP BY c.id_categoria
            ORDER BY c.nombre
        """)
        categorias = cursor.fetchall()
        cursor.close()
        return jsonify({'success': True, 'categorias': categorias}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error interno del servidor: {str(e)}'}), 500

@api_bp.route('/api/buscar', methods=['GET'], endpoint='api_buscar')
def api_buscar():
    try:
        query = request.args.get('q', '').strip()
        limite = request.args.get('limite', 20, type=int)

        if not query or len(query) < 2:
            return jsonify({'success': False, 'error': 'La búsqueda debe tener al menos 2 caracteres'}), 400

        limite = min(limite, 100)
        cursor = current_app.db.connection.cursor()

        cursor.execute("""
            SELECT p.id_producto, p.nombre, p.precio, p.descripcion, p.imagen,
                   c.nombre as categoria_nombre
            FROM productos p
            LEFT JOIN categorias c ON p.id_categoria = c.id_categoria
            WHERE p.disponible = 1 
            AND (p.nombre LIKE %s OR p.descripcion LIKE %s)
            ORDER BY p.nombre
            LIMIT %s
        """, (f'%{query}%', f'%{query}%', limite))

        productos_raw = cursor.fetchall()
        productos = []
        for p in productos_raw:
            producto = dict(p)
            if producto.get('precio'):
                producto['precio'] = float(producto['precio'])
            productos.append(producto)

        cursor.execute("""
            SELECT id_categoria, nombre, descripcion
            FROM categorias
            WHERE nombre LIKE %s OR descripcion LIKE %s
            ORDER BY nombre
            LIMIT 10
        """, (f'%{query}%', f'%{query}%'))

        categorias = cursor.fetchall()
        cursor.close()

        return jsonify({'success': True, 'query': query, 'resultados': {'productos': productos, 'categorias': categorias}}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error interno del servidor: {str(e)}'}), 500

@api_bp.route('/api/admin/stats', methods=['GET'], endpoint='api_admin_stats')
@login_required
@admin_required
def api_admin_stats():
    try:
        cursor = current_app.db.connection.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM usuarios")
        total_usuarios = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(*) as total FROM productos WHERE disponible = 1")
        total_productos = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(*) as total FROM pedidos")
        total_pedidos = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(*) as total FROM pedidos WHERE estado = 'pendiente'")
        pedidos_pendientes = cursor.fetchone()['total']

        cursor.execute("""
            SELECT COALESCE(SUM(dp.precio_total), 0) as ingresos 
            FROM pedidos p 
            JOIN detalle_pedido dp ON p.id_pedido = dp.id_pedido 
            WHERE MONTH(p.fecha_pedido) = MONTH(NOW()) 
            AND YEAR(p.fecha_pedido) = YEAR(NOW())
        """)
        ingresos_mes = cursor.fetchone()['ingresos'] or 0
        cursor.close()

        return jsonify({'success': True, 'estadisticas': {
            'total_usuarios': total_usuarios,
            'total_productos': total_productos,
            'total_pedidos': total_pedidos,
            'pedidos_pendientes': pedidos_pendientes,
            'ingresos_mes': float(ingresos_mes)
        }}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error interno del servidor: {str(e)}'}), 500

@api_bp.route('/api/eventos', endpoint='api_eventos')
@login_required
def api_eventos():
    eventos = ModelCalendario.get_all(current_app.db, current_user.id)
    return jsonify(eventos)
