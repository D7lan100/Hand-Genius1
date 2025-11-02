from flask import Blueprint, render_template, redirect, url_for, flash, current_app
from flask_login import login_required
from datetime import date

admin_suscripciones_bp = Blueprint('admin_suscripciones_bp', __name__)

# 📌 Ver todas las suscripciones
@admin_suscripciones_bp.route('/')
@login_required
def listar():
    cursor = current_app.db.connection.cursor()
    cursor.execute("""
        SELECT s.id_suscripcion, u.nombre_completo, t.nombre, s.fecha_inicio, s.fecha_fin, s.fecha_inicio, s.fecha_fin, s.id_usuario
        FROM suscripciones s
        JOIN tipo_suscripcion t ON s.id_tipo_suscripcion = t.id_tipo_suscripcion
        JOIN usuarios u ON s.id_usuario = u.id_usuario
    """)
    suscripciones = cursor.fetchall()
    cursor.close()
    return render_template('admin/suscripciones_admin.html', suscripciones=suscripciones)


# 📌 Aprobar suscripción
@admin_suscripciones_bp.route('/aprobar/<int:id_suscripcion>')
@login_required
def aprobar(id_suscripcion):
    cursor = current_app.db.connection.cursor()
    cursor.execute("""
        UPDATE suscripciones
        SET fecha_fin = %s
        WHERE id_suscripcion = %s
    """, (date.today() + timedelta(days=30), id_suscripcion))
    current_app.db.connection.commit()
    cursor.close()
    flash('Suscripción activada correctamente.', 'success')
    return redirect(url_for('admin_suscripciones_bp.listar'))


# 📌 Rechazar suscripción
@admin_suscripciones_bp.route('/rechazar/<int:id_suscripcion>')
@login_required
def rechazar(id_suscripcion):
    cursor = current_app.db.connection.cursor()
    cursor.execute("DELETE FROM suscripciones WHERE id_suscripcion = %s", (id_suscripcion,))
    current_app.db.connection.commit()
    cursor.close()
    flash('Suscripción rechazada y eliminada.', 'danger')
    return redirect(url_for('admin_suscripciones_bp.listar'))
