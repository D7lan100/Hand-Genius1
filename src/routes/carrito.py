from flask import Blueprint, render_template, session, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from datetime import datetime
import os
from werkzeug.utils import secure_filename

carrito_bp = Blueprint('carrito_bp', __name__, template_folder="../templates/navbar")


# -----------------------------
# Agregar producto al carrito
# -----------------------------
@carrito_bp.route('/carrito/agregar/<int:id_producto>', methods=['POST'])
def agregar(id_producto):
    cantidad = int(request.form.get('cantidad', 1))

    if 'carrito' not in session:
        session['carrito'] = {}

    carrito = session['carrito']
    carrito[str(id_producto)] = carrito.get(str(id_producto), 0) + cantidad
    session['carrito'] = carrito

    flash("✅ Producto agregado correctamente al carrito", "success")
    return redirect(url_for('carrito_bp.ver'))


# -----------------------------
# Ver carrito (desde sesión)
# -----------------------------
@carrito_bp.route('/carrito')
def ver():
    carrito = session.get('carrito', {})
    productos_detalle = []
    total = 0.0

    # Si el carrito está vacío
    if not carrito:
        return render_template('navbar/carrito.html', productos=[], total=0)

    try:
        cur = current_app.db.connection.cursor()

        # Obtener los productos según los IDs guardados en sesión
        ids = tuple(map(int, carrito.keys()))
        cur.execute(f"""
            SELECT id_producto, nombre, precio, imagen
            FROM productos
            WHERE id_producto IN {ids}
        """)
        productos_db = cur.fetchall()
        cur.close()

        for p in productos_db:
            id_prod = str(p[0])
            cantidad = carrito.get(id_prod, 1)
            subtotal = float(p[2]) * cantidad

            productos_detalle.append({
                'id_producto': p[0],
                'nombre': p[1],
                'precio': float(p[2]),
                'imagen': p[3],
                'cantidad': cantidad,
                'subtotal': subtotal,
                'texto': None,
                'boceto': None,
                'plantilla': None,
                'formulario': None
            })

        total = sum(item['subtotal'] for item in productos_detalle)

    except Exception as e:
        print(f"❌ Error al cargar carrito: {e}")
        flash("Error al cargar el carrito", "danger")

    return render_template('navbar/carrito.html', productos=productos_detalle, total=total)

# -----------------------------
# Eliminar producto del carrito
# -----------------------------
@carrito_bp.route('/carrito/eliminar/<int:id_producto>', methods=['POST'])
def eliminar(id_producto):
    carrito = session.get('carrito', {})
    carrito.pop(str(id_producto), None)
    session['carrito'] = carrito

    flash("🗑️ Producto eliminado del carrito", "info")
    return redirect(url_for('carrito_bp.ver'))


# -----------------------------
# Vaciar todo el carrito
# -----------------------------
@carrito_bp.route('/carrito/vaciar', methods=['POST'])
def vaciar():
    session.pop('carrito', None)
    flash("🧹 Carrito vaciado correctamente", "info")
    return redirect(url_for('carrito_bp.ver'))


# -----------------------------
# Checkout / Crear pedido
# -----------------------------
@carrito_bp.route('/carrito/checkout', methods=['POST'])
@login_required
def checkout():
    carrito = session.get('carrito', {})
    if not carrito:
        flash("⚠️ Tu carrito está vacío.", "warning")
        return redirect(url_for('productos_bp.productos'))

    user_id = current_user.id_usuario
    fecha_pedido = datetime.now()

    try:
        cur = current_app.db.connection.cursor()

        # Crear pedido
        cur.execute("""
            INSERT INTO pedidos (id_usuario, fecha_pedido, estado)
            VALUES (%s, %s, %s)
        """, (user_id, fecha_pedido, 'pendiente'))
        id_pedido = cur.lastrowid

        # Insertar detalles
        for id_prod, cantidad in carrito.items():
            cur.execute("SELECT precio FROM productos WHERE id_producto=%s", (id_prod,))
            precio = cur.fetchone()[0]
            cur.execute("""
                INSERT INTO detalle_pedido (id_pedido, id_producto, cantidad, precio_total)
                VALUES (%s, %s, %s, %s)
            """, (id_pedido, id_prod, cantidad, precio * cantidad))

        current_app.db.connection.commit()
        cur.close()

        session.pop('carrito', None)
        flash("✅ Pedido creado correctamente. Sube el comprobante de pago.", "info")
        return redirect(url_for('carrito_bp.subir_comprobante', id_pedido=id_pedido))

    except Exception as e:
        print(f"❌ Error al realizar checkout: {e}")
        flash("Error al procesar el pedido", "danger")
        return redirect(url_for('carrito_bp.ver'))


# -----------------------------
# Subir comprobante de pago
# -----------------------------
@carrito_bp.route('/carrito/pago/<int:id_pedido>', methods=['GET', 'POST'])
@login_required
def subir_comprobante(id_pedido):
    if request.method == 'POST':
        file = request.files.get('comprobante')
        metodo_pago = request.form.get('metodo_pago')

        if not file or file.filename.strip() == '':
            flash('⚠️ Debes subir un comprobante de pago.', 'danger')
            return redirect(request.url)

        upload_folder = os.path.join('src', 'static', 'comprobantes')
        os.makedirs(upload_folder, exist_ok=True)

        filename = secure_filename(f"pedido_{id_pedido}_user_{current_user.id_usuario}_{file.filename}")
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)

        try:
            cur = current_app.db.connection.cursor()
            cur.execute("""
                UPDATE pedidos 
                SET comprobante_pago = %s, metodo_pago = %s, estado = 'en_revision'
                WHERE id_pedido = %s
            """, (filename, metodo_pago, id_pedido))
            current_app.db.connection.commit()
            cur.close()

            flash('📤 Comprobante enviado correctamente. Espera la validación del administrador.', 'success')
        except Exception as e:
            current_app.db.connection.rollback()
            print(f"❌ Error al guardar comprobante: {e}")
            flash('❌ Error al guardar el comprobante.', 'danger')

        return redirect(url_for('carrito_bp.ver_seguimiento', id_pedido=id_pedido))

    return render_template('navbar/subir_comprobante.html', id_pedido=id_pedido)


# -----------------------------
# Ver seguimiento del pedido
# -----------------------------
@carrito_bp.route('/carrito/seguimiento/<int:id_pedido>')
@login_required
def ver_seguimiento(id_pedido):
    pedido = None
    try:
        cur = current_app.db.connection.cursor()
        cur.execute("""
            SELECT p.id_pedido, p.estado, p.metodo_pago, p.comprobante_pago,
                   d.estado AS envio_estado, d.empresa_transportadora, d.fecha_envio
            FROM pedidos p
            LEFT JOIN domicilio d ON p.id_pedido = d.id_pedido
            WHERE p.id_pedido = %s
        """, (id_pedido,))
        pedido = cur.fetchone()
        cur.close()
    except Exception as e:
        print(f"❌ Error al obtener seguimiento: {e}")
        flash("Error al cargar seguimiento", "danger")

    return render_template('navbar/seguimiento.html', pedido=pedido)
