from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from src.models.ModelProducto import ModelProducto
from src.models.ModelCalendario import ModelCalendario
from functools import wraps
from werkzeug.utils import secure_filename
import os

# ====================================================
# CONFIGURACIÓN GENERAL
# ====================================================
api_bp = Blueprint('api_bp', __name__)

# 📁 Carpeta de imágenes (usa la carpeta que ya tienes: static/img/productos)
def get_upload_folder():
    base_dir = os.path.dirname(os.path.abspath(__file__))  # src/routes/
    static_folder = os.path.join(base_dir, '..', '..', 'static', 'img', 'productos')
    static_folder = os.path.abspath(static_folder)
    os.makedirs(static_folder, exist_ok=True)
    return static_folder

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ====================================================
# DECORADOR: admin_required
# ====================================================
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': 'No autorizado'}), 401
        if getattr(current_user, 'id_rol', None) != 2:
            return jsonify({'success': False, 'error': 'No tienes permisos'}), 403
        return f(*args, **kwargs)
    return decorated


# ====================================================
# API PRODUCTOS
# ====================================================
@api_bp.route('/api/productos', methods=['GET', 'POST'])
@login_required
def api_productos():
    try:
        # ----------------------------
        # MÉTODO GET
        # ----------------------------
        if request.method == 'GET':
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            categoria_id = request.args.get('categoria_id', type=int)
            buscar = request.args.get('buscar', '').strip()

            per_page = min(per_page, 100)
            offset = (page - 1) * per_page

            cursor = current_app.db.connection.cursor(dictionary=True)

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

        # ----------------------------
        # MÉTODO POST
        # ----------------------------
        elif request.method == 'POST':
            if getattr(current_user, 'id_rol', None) not in [1, 2]:
                return jsonify({'success': False, 'error': 'No tienes permisos para agregar productos'}), 403

            nombre = request.form.get('nombre')
            descripcion = request.form.get('descripcion', '')
            precio = request.form.get('precio')
            id_categoria = request.form.get('id_categoria')
            disponible = 1 if request.form.get('disponible') else 0
            es_personalizable = 1 if request.form.get('es_personalizable') else 0

            if not nombre or not precio or not id_categoria:
                return jsonify({'success': False, 'error': 'Faltan campos obligatorios (nombre, precio, categoría)'}), 400

            imagen = None
            if 'imagen' in request.files:
                file = request.files['imagen']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    upload_folder = get_upload_folder()
                    file_path = os.path.join(upload_folder, filename)
                    file.save(file_path)
                    # ✅ Ruta pública correcta
                    imagen = f"img/productos/{filename}"

            cursor = current_app.db.connection.cursor()
            cursor.execute("""
                INSERT INTO productos (nombre, descripcion, precio, id_categoria, id_vendedor, disponible, es_personalizable, imagen)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (nombre, descripcion, precio, id_categoria, current_user.id_usuario, disponible, es_personalizable, imagen))
            current_app.db.connection.commit()
            nuevo_id = cursor.lastrowid
            cursor.close()

            return jsonify({
                'success': True,
                'mensaje': '✅ Producto agregado correctamente',
                'id_producto': nuevo_id,
                'imagen': imagen
            }), 201

    except Exception as e:
        print(f"Error en /api/productos: {e}")
        return jsonify({'success': False, 'error': f'Error al agregar producto: {str(e)}'}), 500


# ====================================================
# DETALLE DE PRODUCTO
# ====================================================
@api_bp.route('/api/producto/<int:producto_id>', methods=['GET'])
def api_producto_detalle(producto_id):
    try:
        cursor = current_app.db.connection.cursor(dictionary=True)
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
        cursor.close()
        return jsonify({'success': True, 'producto': producto}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ====================================================
# CATEGORÍAS
# ====================================================
@api_bp.route('/api/categorias', methods=['GET'])
def api_categorias():
    try:
        cursor = current_app.db.connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT c.*, COUNT(p.id_producto) AS total_productos
            FROM categorias c
            LEFT JOIN productos p ON c.id_categoria = p.id_categoria AND p.disponible = 1
            GROUP BY c.id_categoria
            ORDER BY c.nombre
        """)
        categorias = cursor.fetchall()
        cursor.close()
        return jsonify({'success': True, 'categorias': categorias}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ====================================================
# BÚSQUEDA GLOBAL
# ====================================================
@api_bp.route('/api/buscar', methods=['GET'])
def api_buscar():
    try:
        query = request.args.get('q', '').strip()
        limite = request.args.get('limite', 20, type=int)

        if not query or len(query) < 2:
            return jsonify({'success': False, 'error': 'La búsqueda debe tener al menos 2 caracteres'}), 400

        cursor = current_app.db.connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT p.id_producto, p.nombre, p.precio, p.descripcion, p.imagen,
                   c.nombre AS categoria_nombre
            FROM productos p
            LEFT JOIN categorias c ON p.id_categoria = c.id_categoria
            WHERE p.disponible = 1 AND (p.nombre LIKE %s OR p.descripcion LIKE %s)
            ORDER BY p.nombre
            LIMIT %s
        """, (f'%{query}%', f'%{query}%', limite))
        productos = cursor.fetchall()
        cursor.close()
        return jsonify({'success': True, 'query': query, 'productos': productos}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ====================================================
# ESTADÍSTICAS ADMIN
# ====================================================
@api_bp.route('/api/admin/stats', methods=['GET'])
@login_required
@admin_required
def api_admin_stats():
    try:
        cursor = current_app.db.connection.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) AS total FROM usuarios")
        total_usuarios = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(*) AS total FROM productos WHERE disponible = 1")
        total_productos = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(*) AS total FROM pedidos")
        total_pedidos = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(*) AS total FROM pedidos WHERE estado = 'pendiente'")
        pedidos_pendientes = cursor.fetchone()['total']
        cursor.close()

        return jsonify({'success': True, 'estadisticas': {
            'total_usuarios': total_usuarios,
            'total_productos': total_productos,
            'total_pedidos': total_pedidos,
            'pedidos_pendientes': pedidos_pendientes
        }}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ====================================================
# EVENTOS (CALENDARIO)
# ====================================================
@api_bp.route('/api/eventos')
@login_required
def api_eventos():
    try:
        eventos = ModelCalendario.get_all(current_app.db, current_user.id)
        return jsonify(eventos), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
