from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from datetime import date, timedelta
import os

suscripciones_bp = Blueprint('suscripciones_bp', __name__, url_prefix='/suscripciones')


# 📌 1️⃣ Ver todos los tipos de suscripción disponibles
@suscripciones_bp.route('/')
@login_required
def listar_planes():
    cursor = current_app.db.connection.cursor()
    cursor.execute("SELECT id_tipo_suscripcion, nombre, descripcion, precio_mensual FROM tipo_suscripcion")
    planes = cursor.fetchall()
    cursor.close()
    return render_template('suscripciones/suscripciones.html', planes=planes)


# 📌 2️⃣ Subir comprobante de pago para un plan
@suscripciones_bp.route('/pago/<int:id_tipo>', methods=['GET', 'POST'])
@login_required
def subir_comprobante(id_tipo):
    if request.method == 'POST':
        file = request.files.get('comprobante')
        if not file or file.filename == '':
            flash('Debes subir un comprobante de pago.', 'danger')
            return redirect(request.url)

        # Crear carpeta si no existe
        upload_folder = os.path.join('src', 'static', 'comprobantes')
        os.makedirs(upload_folder, exist_ok=True)

        # Guardar archivo
        filename = f"user_{current_user.id_usuario}_{file.filename}"
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)

        # Registrar suscripción (pendiente de validación)
        cursor = current_app.db.connection.cursor()
        cursor.execute("""
            INSERT INTO suscripciones (id_usuario, id_tipo_suscripcion, fecha_inicio, fecha_fin)
            VALUES (%s, %s, %s, %s)
        """, (current_user.id_usuario, id_tipo, date.today(), date.today() + timedelta(days=30)))
        current_app.db.connection.commit()
        cursor.close()

        flash('📤 Comprobante enviado correctamente. Espera la validación del administrador.', 'success')
        return redirect(url_for('suscripciones_bp.ver_suscripcion'))

    # Obtener información del plan seleccionado
    cursor = current_app.db.connection.cursor()
    cursor.execute("SELECT * FROM tipo_suscripcion WHERE id_tipo_suscripcion = %s", (id_tipo,))
    plan = cursor.fetchone()
    cursor.close()

    return render_template('suscripciones/subir_comprobante.html', plan=plan)


# 📌 3️⃣ Ver suscripción activa del usuario
@suscripciones_bp.route('/mi-suscripcion')
@login_required
def ver_suscripcion():
    cursor = current_app.db.connection.cursor()
    cursor.execute("""
        SELECT s.id_suscripcion, t.nombre, t.precio_mensual, s.fecha_inicio, s.fecha_fin
        FROM suscripciones s
        JOIN tipo_suscripcion t ON s.id_tipo_suscripcion = t.id_tipo_suscripcion
        WHERE s.id_usuario = %s
        ORDER BY s.fecha_inicio DESC
        LIMIT 1
    """, (current_user.id_usuario,))
    suscripcion = cursor.fetchone()
    cursor.close()

    if not suscripcion:
        flash('Aún no tienes una suscripción activa.', 'info')
        return redirect(url_for('suscripciones_bp.listar_planes'))

    hoy = date.today()
    estado = "Activa" if hoy <= suscripcion[4] else "Expirada"

    return render_template('suscripciones/mi_suscripcion.html', suscripcion=suscripcion, estado=estado)
