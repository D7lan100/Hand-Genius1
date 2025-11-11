# src/routes/personalizacion.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
import os

personalizacion_bp = Blueprint('personalizacion_bp', __name__)

@personalizacion_bp.route('/personalizar', methods=['GET', 'POST'])
def personalizar():
    if request.method == 'POST':
        tipo = request.form.get('tipo')

        if tipo == 'plantilla':
            return redirect(url_for('productos_bp.plantilla_personalizacion'))
        
        elif tipo == 'texto':
            descripcion = request.form.get('descripcion')
            # Aquí podrías guardar en la BD la descripción
            flash('Descripción enviada correctamente.', 'success')
            return redirect(url_for('personalizacion_bp.personalizar'))
        
        elif tipo == 'boceto':
            imagen = request.files.get('boceto')
            if imagen:
                upload_folder = os.path.join(current_app.root_path, 'src', 'static', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                imagen.save(os.path.join(upload_folder, imagen.filename))
                flash('Boceto subido correctamente.', 'success')
            return redirect(url_for('personalizacion_bp.personalizar'))

        elif tipo == 'formulario':
            return redirect("https://docs.google.com/forms/d/tu_formulario_aquí")

    return render_template('personalizacion/panel.html')