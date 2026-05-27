import base64
import json
import os
import re
from datetime import date, datetime

import cv2
import face_recognition
from flask import render_template, request, redirect, url_for, session, flash

from database import get_db_connection
from helpers import (
    get_carrera_options,
    get_seccion_options,
    get_sede_options,
    get_carrera_id,
    get_seccion_id,
    generar_carnet_unico,
    is_valid_carrera,
    is_valid_seccion,
    is_valid_sede,
    limpiar_nombre,
    obtener_usuario_sesion,
    get_roles_persona_schema,
    get_rol_id_by_name,
    get_jornadas_options,
)
from pdf_utils import generate_id_card_pdf, send_email_with_pdf


def register_registro_routes(app):
    @app.route('/registrar', methods=['GET', 'POST'])
    def registrar_persona():
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT p.nombre, p.apellido, p.foto
            FROM usuarios u
            JOIN personas p ON u.id_persona = p.id_persona
            WHERE u.id_usuario = %s
        """, (session.get('user_id'),))
        usuario = cursor.fetchone()
        cursor.close()
        conn.close()
        if usuario and usuario.get('foto'):
            if isinstance(usuario['foto'], (bytes, bytearray)):
                usuario['foto'] = usuario['foto'].decode('utf-8')
        else:
            if usuario:
                usuario['foto'] = None

        if request.method == 'POST':
            nombre = request.form['nombre'].strip()
            apellido = request.form['apellido'].strip()
            telefono = request.form['telefono'].strip()
            correo = request.form['correo'].strip().lower()
            tipo_persona = request.form['tipo_persona']
            carrera = request.form.get('carrera', '')
            seccion = request.form.get('seccion', '')
            id_jornada = request.form.get('id_jornada', '')
            imagen_base64 = request.form.get('fotografia')
            firma = request.form.get('firma', '').strip()
            form_data = request.form.to_dict(flat=True)
            seccion_options = get_seccion_options(carrera) if carrera else []
            sede_options = get_sede_options()
            jornadas_options = get_jornadas_options()

            if not is_valid_carrera(carrera):
                flash('Carrera inválida. Seleccione una opción válida.', 'danger')
                form_data['fotografia'] = imagen_base64 or ''
                return render_template('registrar.html', form_data=form_data, retake_photo=True, usuario=usuario, carrera_options=[], seccion_options=seccion_options, sede_options=sede_options)
            if not is_valid_seccion(seccion, carrera):
                flash('Sección inválida. Seleccione una opción válida.', 'danger')
                form_data['fotografia'] = imagen_base64 or ''
                return render_template('registrar.html', form_data=form_data, retake_photo=True, usuario=usuario, carrera_options=[], seccion_options=seccion_options, sede_options=sede_options)
            sede = request.form.get('sede')
            if not is_valid_sede(sede):
                flash('Sede inválida. Seleccione una opción válida.', 'danger')
                form_data['fotografia'] = imagen_base64 or ''
                return render_template('registrar.html', form_data=form_data, retake_photo=True, usuario=usuario, carrera_options=[], seccion_options=seccion_options, sede_options=sede_options, jornadas_options=jornadas_options)
            if not correo.endswith('@miumg.edu.gt'):
                flash('Debe usar correo institucional @miumg.edu.gt', 'danger')
                return redirect(url_for('registrar_persona'))
            if not imagen_base64:
                flash('Debe capturar la fotografía', 'danger')
                form_data['fotografia'] = ''
                return render_template('registrar.html', form_data=form_data, retake_photo=True, usuario=usuario, carrera_options=[], seccion_options=get_seccion_options(carrera), sede_options=sede_options)
            try:
                _, encoded = imagen_base64.split(',', 1)
                imagen_bytes = base64.b64decode(encoded)
            except Exception:
                flash('Error procesando la imagen. Vuelva a tomar la fotografía.', 'danger')
                form_data['fotografia'] = ''
                return render_template('registrar.html', form_data=form_data, retake_photo=True, usuario=usuario, carrera_options=[], seccion_options=get_seccion_options(carrera))

            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                'SELECT COUNT(*) AS total FROM personas WHERE correo_personal = %s OR correo_institucional = %s',
                (correo, correo)
            )
            if cursor.fetchone()['total'] > 0:
                cursor.close()
                conn.close()
                flash('El correo ya está registrado', 'warning')
                return redirect(url_for('registrar_persona'))

            carnet = generar_carnet_unico()
            cursor.close()
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO personas (nombre, apellido, telefono, correo_institucional, carnet, foto, firma) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                (nombre, apellido, telefono, correo, carnet, imagen_bytes, firma)
            )
            id_persona = cursor.lastrowid
            conn.commit()
            id_carrera = get_carrera_id(carrera)
            id_seccion = get_seccion_id(seccion, id_carrera) if id_carrera else None
            id_sede = int(request.form.get('sede')) if request.form.get('sede') else None
            id_jornada_int = int(id_jornada) if id_jornada else None
            rp_cols = get_roles_persona_schema()
            if 'id_rol' in rp_cols:
                id_rol = get_rol_id_by_name(tipo_persona)
                if not id_rol:
                    raise ValueError(f"Rol desconocido: {tipo_persona}")
                if id_jornada_int:
                    cursor.execute('INSERT INTO roles_persona (id_persona, id_rol, id_jornada) VALUES (%s, %s, %s)', (id_persona, id_rol, id_jornada_int))
                else:
                    cursor.execute('INSERT INTO roles_persona (id_persona, id_rol) VALUES (%s, %s)', (id_persona, id_rol))
            else:
                cursor.execute(
                    'INSERT INTO roles_persona (id_persona, tipo_persona, carnet, id_carrera, id_seccion, id_sede, id_jornada, fecha_inicio) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
                    (id_persona, tipo_persona, carnet, id_carrera, id_seccion, id_sede, id_jornada_int, date.today())
                )
            conn.commit()

            nombre_limpio = limpiar_nombre(f"{nombre}_{apellido}")
            carpeta_persona = os.path.join('static', 'rostros', f'{id_persona}_{nombre_limpio}')
            os.makedirs(carpeta_persona, exist_ok=True)
            nombre_archivo = f'{nombre_limpio}_1.png'
            ruta_foto = os.path.join(carpeta_persona, nombre_archivo)
            with open(ruta_foto, 'wb') as f:
                f.write(imagen_bytes)

            try:
                img = cv2.imread(ruta_foto)
                if img is None:
                    raise ValueError('No se pudo leer la imagen')
                rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                encodings = face_recognition.face_encodings(rgb_img, model='large')
                if not encodings:
                    raise ValueError('No se detectó un rostro válido')
                encoding_json = json.dumps(encodings[0].tolist())
                cursor.execute('UPDATE personas SET encoding_facial = %s WHERE id_persona = %s', (encoding_json, id_persona))
                conn.commit()
            except Exception as e:
                print('Error encoding:', e)
                try:
                    cursor.execute('DELETE FROM roles_persona WHERE id_persona = %s', (id_persona,))
                    conn.commit()
                except Exception:
                    pass
                try:
                    cursor.execute('DELETE FROM personas WHERE id_persona = %s', (id_persona,))
                    conn.commit()
                except Exception:
                    pass
                try:
                    if os.path.exists(ruta_foto):
                        os.remove(ruta_foto)
                except Exception:
                    pass
                try:
                    if os.path.isdir(carpeta_persona) and len(os.listdir(carpeta_persona)) == 0:
                        os.rmdir(carpeta_persona)
                except Exception:
                    pass
                cursor.close()
                conn.close()
                flash('No se detectó un rostro válido. Vuelva a tomar la fotografía.', 'danger')
                form_data['fotografia'] = ''
                return render_template(
                    'registrar.html',
                    form_data=form_data,
                    retake_photo=True,
                    usuario=usuario,
                    carrera_options=[],
                    seccion_options=get_seccion_options(carrera),
                    sede_options=get_sede_options(),
                    jornadas_options=get_jornadas_options()
                )

            try:
                pdf_bytes = generate_id_card_pdf(nombre, apellido, correo, imagen_bytes, carnet, id_persona, firma)
                if pdf_bytes:
                    send_ok, send_err = send_email_with_pdf(correo, pdf_bytes, f'carnet_{id_persona}.pdf')
                    if send_ok:
                        flash('Persona registrada y carnet enviado por correo.', 'success')
                    else:
                        flash(f'Persona registrada, pero error enviando carnet: {send_err}', 'warning')
                else:
                    flash('Persona registrada, pero no se pudo generar el carnet PDF.', 'warning')
            except Exception as e:
                flash(f'Persona registrada, pero error al enviar carnet: {e}', 'warning')

            cursor.close()
            conn.close()
            return redirect(url_for('registrar_persona'))

        sede_options = get_sede_options()
        jornadas_options = get_jornadas_options()
        return render_template('registrar.html', usuario=usuario, carrera_options=[], seccion_options=[], sede_options=sede_options, jornadas_options=jornadas_options)
