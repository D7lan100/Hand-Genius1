# src/routes/carrito.py
from flask import Blueprint, render_template, session, request, redirect, url_for, flash, current_app
from datetime import datetime

# Usamos la carpeta "navbar" para guardar carrito.html
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

    flash("Producto agregado al carrito", "success")
    # Redirige directamente al carrito en vez de productos
    return redirect(url_for('carrito_bp.ver'))

# -----------------------------
# Ver carrito
# -----------------------------
@carrito_bp.route('/carrito')
def ver():
    carrito = session.get('carrito', {})
    productos_detalle = []

    if carrito:
        cur = current_app.db.connection.cursor()
        for id_prod, cantidad in carrito.items():
            cur.execute("""
                SELECT id_producto, nombre, precio, imagen 
                FROM productos 
                WHERE id_producto=%s
            """, (id_prod,))
            prod = cur.fetchone()
            if prod:
                productos_detalle.append({
                    'id_producto': prod[0],
                    'nombre': prod[1],
                    'precio': float(prod[2]),
                    'cantidad': cantidad,
                    'subtotal': float(prod[2]) * cantidad,
                    'imagen': prod[3]
                })
        cur.close()

    total = sum(item['subtotal'] for item in productos_detalle)
    return render_template('navbar/carrito.html', productos=productos_detalle, total=total)

# -----------------------------
# Eliminar un producto del carrito
# -----------------------------
@carrito_bp.route('/carrito/eliminar/<int:id_producto>', methods=['POST'])
def eliminar(id_producto):
    carrito = session.get('carrito', {})
    if str(id_producto) in carrito:
        carrito.pop(str(id_producto))
        session['carrito'] = carrito
        flash("Producto eliminado del carrito", "info")
    return redirect(url_for('carrito_bp.ver'))

# -----------------------------
# Vaciar todo el carrito
# -----------------------------
@carrito_bp.route('/carrito/vaciar', methods=['POST'])
def vaciar():
    session.pop('carrito', None)
    flash("Carrito vaciado", "info")
    return redirect(url_for('carrito_bp.ver'))

# -----------------------------
# Checkout / Crear pedido
# -----------------------------
@carrito_bp.route('/carrito/checkout', methods=['POST'])
def checkout():
    if 'user_id' not in session or 'carrito' not in session:
        flash("Debe iniciar sesión y agregar productos al carrito", "danger")
        return redirect(url_for('productos_bp.productos'))

    carrito = session['carrito']
    user_id = session['user_id']
    fecha_pedido = datetime.now()

    cur = current_app.db.connection.cursor()

    # Crear pedido
    cur.execute("""
        INSERT INTO pedidos (id_usuario, fecha_pedido, estado) 
        VALUES (%s, %s, %s)
    """, (user_id, fecha_pedido, 'pendiente'))
    id_pedido = cur.lastrowid

    # Insertar detalle del pedido
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
    flash("Pedido realizado con éxito", "success")
    return redirect(url_for('productos_bp.productos'))
