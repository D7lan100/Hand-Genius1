# src/routes/productos.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from src.models.ModelProducto import ModelProducto
from werkzeug.utils import secure_filename
import os

def get_cursor():
    """Devuelve un cursor nuevo asegurando que use la BD correcta"""
    db = current_app.db
    cursor = db.connection.cursor()
    cursor.execute(f"USE {current_app.config['MYSQL_DB']};")
    return cursor

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

@productos_bp.route('/personalizacion_panel/<int:id_producto>')
def panel_personalizacion(id_producto):
    """
    Muestra las 4 opciones de personalización:
    1. Personalización directa (dirige a la plantilla que ya tienes)
    2. Descripción en texto
    3. Subir boceto
    4. Formulario externo de Google
    """
    return render_template('producto/panel_personalizacion.html', id_producto=id_producto)

@productos_bp.route('/personalizar/<int:id_producto>')
def personalizar(id_producto):
    try:
        producto = ModelProducto.get_by_id(current_app.db, id_producto)
        if not producto:
            flash("Producto no encontrado", "error")
            return redirect(url_for('productos_bp.productos'))

        return render_template('producto/personalizar_producto.html', producto=producto)
    except Exception as e:
        print(f"Error en personalizar: {e}")
        flash("Error al cargar la personalización del producto", "danger")
        return redirect(url_for('productos_bp.productos'))


# connexion de las 4 opciones de personalizacion con la bd
@productos_bp.route('/guardar_texto_personalizado/<int:id_producto>', methods=['POST'])
def guardar_texto_personalizado(id_producto):
    db = current_app.db
    try:
        texto = request.form.get('texto_personalizado', '').strip()
        id_usuario = current_user.id_usuario

        if not texto:
            return jsonify(success=False, message="Por favor escribe una descripción antes de enviar."), 400

        cursor = db.connection.cursor()

        # Buscar pedido pendiente del usuario
        cursor.execute("""
            SELECT id_pedido FROM pedidos
            WHERE id_usuario = %s AND estado = 'pendiente' LIMIT 1
        """, (id_usuario,))
        pedido = cursor.fetchone()

        if not pedido:
            cursor.execute("""
                INSERT INTO pedidos (id_usuario, fecha_pedido, estado, metodo_pago)
                VALUES (%s, NOW(), 'pendiente', 'No definido')
            """, (id_usuario,))
            db.connection.commit()
            cursor.execute("SELECT LAST_INSERT_ID()")
            id_pedido = cursor.fetchone()[0]
        else:
            id_pedido = pedido[0]

        # Buscar si ya existe un detalle del mismo producto
        cursor.execute("""
            SELECT id_detalle FROM detalle_pedido
            WHERE id_pedido = %s AND id_producto = %s
        """, (id_pedido, id_producto))
        detalle_existente = cursor.fetchone()

        if detalle_existente:
            # 🔁 Actualizar el texto si ya hay un detalle
            cursor.execute("""
                UPDATE detalle_pedido
                SET texto_personalizado = %s
                WHERE id_detalle = %s
            """, (texto, detalle_existente[0]))
        else:
            # ➕ Insertar nuevo detalle
            cursor.execute("""
                INSERT INTO detalle_pedido (id_pedido, id_producto, cantidad, texto_personalizado)
                VALUES (%s, %s, 1, %s)
            """, (id_pedido, id_producto, texto))

        db.connection.commit()
        return jsonify(success=True)

    except Exception as e:
        db.connection.rollback()
        print(f"❌ ERROR SQL TEXTO: {e}")
        return jsonify(success=False, message=str(e)), 500
    

@productos_bp.route('/subir_boceto/<int:id_producto>', methods=['POST'])
def subir_boceto(id_producto):
    db = current_app.db
    try:
        archivo = request.files.get('imagen_personalizada')
        if not archivo or archivo.filename == "":
            return jsonify(success=False, message="Por favor selecciona un archivo válido."), 400

        filename = secure_filename(archivo.filename)
        ruta_carpeta = os.path.join('src', 'static', 'personalizacion', 'bocetos_usuarios')
        os.makedirs(ruta_carpeta, exist_ok=True)
        ruta_archivo = os.path.join(ruta_carpeta, filename)
        archivo.save(ruta_archivo)

        id_usuario = current_user.id_usuario
        cursor = db.connection.cursor()

        # Buscar pedido pendiente
        cursor.execute("""
            SELECT id_pedido FROM pedidos
            WHERE id_usuario = %s AND estado = 'pendiente' LIMIT 1
        """, (id_usuario,))
        pedido = cursor.fetchone()

        if not pedido:
            cursor.execute("""
                INSERT INTO pedidos (id_usuario, fecha_pedido, estado, metodo_pago)
                VALUES (%s, NOW(), 'pendiente', 'No definido')
            """, (id_usuario,))
            db.connection.commit()
            cursor.execute("SELECT LAST_INSERT_ID()")
            id_pedido = cursor.fetchone()[0]
        else:
            id_pedido = pedido[0]

        # Buscar si ya existe un detalle del mismo producto
        cursor.execute("""
            SELECT id_detalle FROM detalle_pedido
            WHERE id_pedido = %s AND id_producto = %s
        """, (id_pedido, id_producto))
        detalle_existente = cursor.fetchone()

        if detalle_existente:
            # 🔁 Actualizar boceto existente
            cursor.execute("""
                UPDATE detalle_pedido
                SET imagen_personalizada = %s
                WHERE id_detalle = %s
            """, (ruta_archivo, detalle_existente[0]))
        else:
            # ➕ Insertar nuevo si no existe
            cursor.execute("""
                INSERT INTO detalle_pedido (id_pedido, id_producto, cantidad, imagen_personalizada)
                VALUES (%s, %s, 1, %s)
            """, (id_pedido, id_producto, ruta_archivo))

        db.connection.commit()
        print(f"✅ Boceto guardado en {ruta_archivo} para usuario {id_usuario}")
        return jsonify(success=True, ruta=ruta_archivo)

    except Exception as e:
        db.connection.rollback()
        print(f"❌ ERROR SQL BOCETO: {e}")
        return jsonify(success=False, message=str(e)), 500
    
@productos_bp.route('/guardar_plantilla/<int:id_producto>', methods=['POST'])
def guardar_plantilla(id_producto):
    db = current_app.db
    try:
        data = request.get_json()
        id_usuario = current_user.id_usuario

        if not data:
            return jsonify(success=False, message="No se recibieron datos de la plantilla."), 400

        cursor = db.connection.cursor()

        # Buscar o crear pedido pendiente
        cursor.execute("""
            SELECT id_pedido FROM pedidos
            WHERE id_usuario = %s AND estado = 'pendiente' LIMIT 1
        """, (id_usuario,))
        pedido = cursor.fetchone()

        if not pedido:
            cursor.execute("""
                INSERT INTO pedidos (id_usuario, fecha_pedido, estado, metodo_pago)
                VALUES (%s, NOW(), 'pendiente', 'No definido')
            """, (id_usuario,))
            db.connection.commit()
            cursor.execute("SELECT LAST_INSERT_ID()")
            id_pedido = cursor.fetchone()[0]
        else:
            id_pedido = pedido[0]

        # Verificar si ya existe un detalle para este producto
        cursor.execute("""
            SELECT id_detalle FROM detalle_pedido
            WHERE id_pedido = %s AND id_producto = %s LIMIT 1
        """, (id_pedido, id_producto))
        detalle = cursor.fetchone()

        plantilla_json = str(data)

        if detalle:
            cursor.execute("""
                UPDATE detalle_pedido
                SET plantilla_seleccionada = %s
                WHERE id_detalle = %s
            """, (plantilla_json, detalle[0]))
        else:
            cursor.execute("""
                INSERT INTO detalle_pedido (id_pedido, id_producto, cantidad, plantilla_seleccionada)
                VALUES (%s, %s, 1, %s)
            """, (id_pedido, id_producto, plantilla_json))

        db.connection.commit()
        return jsonify(success=True, message="Plantilla guardada correctamente")

    except Exception as e:
        db.connection.rollback()
        print(f"❌ ERROR SQL PLANTILLA: {e}")
        return jsonify(success=False, message=str(e)), 500
    
@productos_bp.route('/registrar_formulario/<int:id_producto>', methods=['POST'])
@login_required
def registrar_formulario(id_producto):
    try:
        conn = current_app.db.connection  # Conexión válida
        cursor = conn.cursor()

        # Buscar pedido pendiente del usuario
        cursor.execute("""
            SELECT id_pedido 
            FROM pedidos 
            WHERE id_usuario = %s AND estado = 'pendiente'
            ORDER BY fecha_pedido DESC 
            LIMIT 1
        """, (current_user.id_usuario,))
        pedido = cursor.fetchone()

        if not pedido:
            return jsonify(success=False, message="No se encontró un pedido activo o pendiente.")

        id_pedido = pedido[0]  # ✅ ahora accedemos como tupla

        # Actualizar registro en detalle_pedido
        cursor.execute("""
            UPDATE detalle_pedido 
            SET formulario_seleccionado = %s
            WHERE id_pedido = %s AND id_producto = %s
        """, ("Formulario guiado de Google completado", id_pedido, id_producto))
        conn.commit()

        return jsonify(success=True)

    except Exception as e:
        print(f"❌ Error al registrar formulario: {e}")
        return jsonify(success=False, message=str(e)), 500
