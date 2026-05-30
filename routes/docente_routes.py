import base64
import os
from datetime import date
from flask import render_template, request, redirect, url_for, session, flash, jsonify, send_file

from database import get_db_connection
from helpers import obtener_usuario_sesion, get_roles_persona_schema, get_active_role_clause
from pdf_utils import generar_pdf_asistencia, enviar_pdf_por_correo


def register_docente_routes(app):
    @app.route('/docente')
    def dashboard_docente():
        if session.get('rol') != 'catedratico':
            return redirect(url_for('login'))
        usuario = obtener_usuario_sesion()
        if not usuario:
            flash('Debe iniciar sesión.', 'danger')
            return redirect(url_for('login'))
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT id_persona FROM usuarios WHERE id_usuario = %s', (session.get('user_id'),))
        fila = cursor.fetchone()
        if not fila:
            cursor.close()
            conn.close()
            flash('No se encontró el usuario.', 'danger')
            return redirect(url_for('login'))
        id_catedratico = fila['id_persona']
        cursor.close()
        cursor = conn.cursor(dictionary=True)
        rp_cols = get_roles_persona_schema()
        if 'id_rol' in rp_cols:
            activo_clause = get_active_role_clause('r')
            cursor.execute(f"""
    SELECT DISTINCT
           c.id_curso,
           c.nombre AS nombre_curso,
           c.codigo,
           ca.nombre AS carrera,
           s.nombre AS seccion,
           sa.nombre AS salon,
           sed.nombre AS sede,
           j.nombre AS jornada,
           ac.ciclo,
           ac.anio
    FROM cursos c
    JOIN asignacion_cursos ac
        ON c.id_curso = ac.id_curso
    JOIN roles_persona r
        ON ac.id_rol_persona = r.id_rol_persona
    JOIN roles ro
        ON r.id_rol = ro.id_rol
    JOIN secciones s
        ON ac.id_seccion = s.id_seccion
    JOIN sede_carrera sc
        ON c.id_sede_carrera = sc.id_sede_carrera
    JOIN carreras ca
        ON sc.id_carrera = ca.id_carrera
    LEFT JOIN salones sa
        ON ac.id_salon = sa.id_salon
    LEFT JOIN sedes sed
        ON sa.id_sede = sed.id_sede
    LEFT JOIN jornadas j
        ON ac.id_jornada = j.id_jornada
    WHERE r.id_persona = %s
      AND ro.nombre = 'catedratico'
      {activo_clause}
    ORDER BY c.nombre
""", (id_catedratico,))
        cursos = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('catedratico/mis_cursos.html', cursos=cursos, usuario=usuario)
# para paneñl del docente, mostrar cursos asignados, ver asistencia, confirmar asistencia
    @app.route('/mis_cursos')
    def mis_cursos():
        if session.get('rol') != 'catedratico':
            return redirect(url_for('login'))
        usuario = obtener_usuario_sesion()
        if not usuario:
            flash('Debe iniciar sesión.', 'danger')
            return redirect(url_for('login'))
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT id_persona FROM usuarios WHERE id_usuario = %s', (session.get('user_id'),))
        fila = cursor.fetchone()
        if not fila:
            cursor.close()
            conn.close()
            flash('No se encontró el usuario.', 'danger')
            return redirect(url_for('login'))
        id_catedratico = fila['id_persona']
        cursor.close()
        cursor = conn.cursor(dictionary=True)
        rp_cols = get_roles_persona_schema()
        if 'id_rol' in rp_cols:
            activo_clause = get_active_role_clause('r')
            cursor.execute(f"""
                SELECT DISTINCT c.id_curso,
                       c.nombre AS nombre_curso,
                       ca.nombre AS carrera,
                       s.nombre AS seccion
                FROM cursos c
                JOIN asignacion_cursos ac ON c.id_curso = ac.id_curso
                JOIN roles_persona r ON ac.id_rol_persona = r.id_rol_persona
                JOIN roles ro ON r.id_rol = ro.id_rol
                JOIN secciones s ON ac.id_seccion = s.id_seccion
                JOIN sede_carrera sc ON c.id_sede_carrera = sc.id_sede_carrera
                JOIN carreras ca ON sc.id_carrera = ca.id_carrera
                WHERE r.id_persona = %s
                  AND ro.nombre = 'catedratico'
                  {activo_clause}
                ORDER BY c.nombre
            """, (id_catedratico,))
        else:
            cursor.execute("""
                SELECT DISTINCT c.id_curso,
                       c.nombre AS nombre_curso,
                       ca.nombre AS carrera,
                       s.nombre AS seccion
                FROM cursos c
                JOIN asignacion_cursos ac ON c.id_curso = ac.id_curso
                JOIN roles_persona r ON ac.id_rol_persona = r.id_rol_persona
                JOIN secciones s ON ac.id_seccion = s.id_seccion
                JOIN sede_carrera sc ON c.id_sede_carrera = sc.id_sede_carrera
                JOIN carreras ca ON sc.id_carrera = ca.id_carrera
                WHERE r.id_persona = %s
                  AND r.tipo_persona = 'catedratico'
                  AND r.activo = 1
                ORDER BY c.nombre
            """, (id_catedratico,))
        cursos = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('catedratico/mis_cursos.html', cursos=cursos, usuario=usuario)

    @app.route('/curso/<int:id_curso>/asistencia', methods=['GET'])
    def ver_asistencia_curso(id_curso):
        if session.get('rol') != 'catedratico':
            flash('Debe iniciar sesión como catedrático.', 'danger')
            return redirect(url_for('login'))
        usuario = obtener_usuario_sesion()
        if not usuario:
            flash('Debe iniciar sesión.', 'danger')
            return redirect(url_for('login'))
        id_catedratico = usuario['id_persona']
        fecha_hoy = date.today()
        conexion = get_db_connection()
        cursor = conexion.cursor(dictionary=True)
        rp_cols = get_roles_persona_schema()
        if 'id_rol' in rp_cols:
            activo_clause = get_active_role_clause('r')
            cursor.execute(f"""
                SELECT c.id_curso,
                       c.nombre AS nombre_curso,
                       ca.nombre AS carrera,
                       s.nombre AS seccion
                FROM cursos c
                JOIN asignacion_cursos ac ON c.id_curso = ac.id_curso
                JOIN roles_persona r ON ac.id_rol_persona = r.id_rol_persona
                JOIN roles ro ON r.id_rol = ro.id_rol
                JOIN secciones s ON ac.id_seccion = s.id_seccion
                JOIN sede_carrera sc ON c.id_sede_carrera = sc.id_sede_carrera
                JOIN carreras ca ON sc.id_carrera = ca.id_carrera
                WHERE c.id_curso = %s
                  AND r.id_persona = %s
                  AND ro.nombre = 'catedratico'
                  {activo_clause}
                LIMIT 1
            """, (id_curso, id_catedratico))
        else:
            cursor.execute("""
                SELECT c.id_curso,
                       c.nombre AS nombre_curso,
                       ca.nombre AS carrera,
                       s.nombre AS seccion
                FROM cursos c
                JOIN asignacion_cursos ac ON c.id_curso = ac.id_curso
                JOIN roles_persona r ON ac.id_rol_persona = r.id_rol_persona
                JOIN secciones s ON ac.id_seccion = s.id_seccion
                JOIN sede_carrera sc ON c.id_sede_carrera = sc.id_sede_carrera
                JOIN carreras ca ON sc.id_carrera = ca.id_carrera
                WHERE c.id_curso = %s
                  AND r.id_persona = %s
                  AND r.tipo_persona = 'catedratico'
                  AND r.activo = 1
                LIMIT 1
            """, (id_curso, id_catedratico))
        curso = cursor.fetchone()
        if not curso:
            cursor.close()
            conexion.close()
            flash('No tiene acceso a este curso.', 'danger')
            return redirect(url_for('mis_cursos'))
        cursor.execute("""
            SELECT p.id_persona, p.nombre, p.apellido, COALESCE(p.correo_institucional, p.correo_personal) AS correo, p.foto, p.carnet
            FROM inscripciones i
            JOIN roles_persona r ON i.id_rol_persona = r.id_rol_persona
            JOIN personas p ON r.id_persona = p.id_persona
            JOIN asignacion_cursos ac ON i.id_asignacion = ac.id_asignacion
            WHERE ac.id_curso = %s
            ORDER BY p.nombre, p.apellido
        """, (id_curso,))
        estudiantes_db = cursor.fetchall()
        estudiantes = []
        for e in estudiantes_db:
            cursor.execute("""
                SELECT id_acceso, tipo_acceso,fecha_hora, resultado
                FROM accesos_biometricos
                WHERE id_persona = %s AND date(fecha_hora) = %s
                ORDER BY fecha_hora DESC
                LIMIT 1
            """, (e['id_persona'], fecha_hoy))
            registro = cursor.fetchone()
            presente = registro is not None
            foto_base64 = None
            if e['foto']:
                if isinstance(e['foto'], (bytes, bytearray)):
                    foto_base64 = base64.b64encode(e['foto']).decode('utf-8')
            estudiantes.append({
                'id_persona': e['id_persona'],
                'nombre_completo': f"{e['nombre']} {e['apellido']}",
                'correo': e['correo'],
                'carnet': e['carnet'],
                'foto': foto_base64,
                'presente': presente,
                'tipo_acceso': registro['tipo_acceso'] if registro else None,
                'fecha_hora': registro['fecha_hora'] if registro else None,
                'resultado': registro['resultado'] if registro else None
            })
        cursor.close()
        conexion.close()
        return render_template('catedratico/arbol_asistencia.html', curso=curso, estudiantes=estudiantes, usuario=usuario)

    @app.route('/curso/<int:id_curso>/confirmar_asistencia', methods=['POST'])
    def confirmar_asistencia(id_curso):
        if session.get('rol') != 'catedratico':
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Debe iniciar sesión como catedrático.', 'redirect_url': url_for('login')}), 401
            flash('Debe iniciar sesión como catedrático.', 'danger')
            return redirect(url_for('login'))
        usuario = obtener_usuario_sesion()
        if not usuario:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Debe iniciar sesión.', 'redirect_url': url_for('login')}), 401
            flash('Debe iniciar sesión.', 'danger')
            return redirect(url_for('login'))
        fecha_hoy = date.today()
        conexion = get_db_connection()
        cursor = conexion.cursor(dictionary=True)
        try:
            rp_cols = get_roles_persona_schema()
            if 'id_rol' in rp_cols:
                activo_clause = get_active_role_clause('r')
                cursor.execute(f"""
                    SELECT c.id_curso,
                           c.nombre AS nombre_curso,
                           ca.nombre AS carrera,
                           s.nombre AS seccion
                    FROM cursos c
                    JOIN asignacion_cursos ac ON c.id_curso = ac.id_curso
                    JOIN roles_persona r ON ac.id_rol_persona = r.id_rol_persona
                    JOIN roles ro ON r.id_rol = ro.id_rol
                    JOIN secciones s ON ac.id_seccion = s.id_seccion
                    JOIN sede_carrera sc ON c.id_sede_carrera = sc.id_sede_carrera
                    JOIN carreras ca ON sc.id_carrera = ca.id_carrera
                    WHERE c.id_curso = %s
                      AND r.id_persona = %s
                      AND ro.nombre = 'catedratico'
                      {activo_clause}
                    LIMIT 1
                """, (id_curso, usuario['id_persona']))
            else:
                cursor.execute("""
                    SELECT c.id_curso,
                           c.nombre AS nombre_curso,
                           ca.nombre AS carrera,
                           s.nombre AS seccion
                    FROM cursos c
                    JOIN asignacion_cursos ac ON c.id_curso = ac.id_curso
                    JOIN roles_persona r ON ac.id_rol_persona = r.id_rol_persona
                    JOIN secciones s ON ac.id_seccion = s.id_seccion
                    JOIN sede_carrera sc ON c.id_sede_carrera = sc.id_sede_carrera
                    JOIN carreras ca ON sc.id_carrera = ca.id_carrera
                    WHERE c.id_curso = %s
                      AND r.id_persona = %s
                      AND r.tipo_persona = 'catedratico'
                      AND r.activo = 1
                    LIMIT 1
                """, (id_curso, usuario['id_persona']))
            curso = cursor.fetchone()
            if not curso:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'No tiene acceso a este curso.', 'redirect_url': url_for('mis_cursos')}), 403
                flash('No tiene acceso a este curso.', 'danger')
                return redirect(url_for('mis_cursos'))
            cursor.execute('SELECT id_persona, nombre, apellido, COALESCE(correo_institucional, correo_personal) AS correo FROM personas WHERE id_persona = %s', (usuario['id_persona'],))
            docente = cursor.fetchone()
            cursor.execute("""
                SELECT p.id_persona, p.nombre, p.apellido, COALESCE(p.correo_institucional, p.correo_personal) AS correo, p.carnet
                FROM inscripciones i
                JOIN roles_persona r ON i.id_rol_persona = r.id_rol_persona
                JOIN personas p ON r.id_persona = p.id_persona
                JOIN asignacion_cursos ac ON i.id_asignacion = ac.id_asignacion
                WHERE ac.id_curso = %s
                ORDER BY p.nombre, p.apellido
            """, (id_curso,))
            estudiantes_db = cursor.fetchall()
            estudiantes_pdf = []
            for e in estudiantes_db:
                cursor.execute("""
                    SELECT id_registro, ubicacion, hora
                    FROM registros_entrada
                    WHERE id_persona = %s AND fecha = %s
                    ORDER BY hora DESC
                    LIMIT 1
                """, (e['id_persona'], fecha_hoy))
                registro = cursor.fetchone()
                presente = registro is not None
                estado = 'presente' if presente else 'ausente'
                cursor.execute('SELECT id_asistencia FROM asistencias WHERE id_estudiante = %s AND id_curso = %s AND fecha = %s', (e['id_persona'], id_curso, fecha_hoy))
                existe = cursor.fetchone()
                if not existe:
                    cursor.execute('INSERT INTO asistencias (id_estudiante, id_curso, fecha, estado) VALUES (%s, %s, %s, %s)', (e['id_persona'], id_curso, fecha_hoy, estado))
                estudiantes_pdf.append({
                    'id_persona': e['id_persona'],
                    'nombre_completo': f"{e['nombre']} {e['apellido']}",
                    'correo': e['correo'],
                    'carnet': e['carnet'],
                    'presente': presente
                })
            conexion.commit()
            ruta_pdf, nombre_archivo = generar_pdf_asistencia(curso, docente, estudiantes_pdf, fecha_hoy)
            try:
                enviar_pdf_por_correo(docente['correo'], ruta_pdf, curso)
            except Exception as e:
                print('Error enviando correo:', e)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': True,
                    'message': 'La asistencia fue confirmada, el PDF fue generado y el correo enviado.',
                    'download_url': url_for('descargar_reporte_asistencia', nombre_archivo=nombre_archivo),
                    'redirect_url': url_for('mis_cursos')
                })
            flash('La asistencia fue confirmada correctamente.', 'success')
            return redirect(url_for('mis_cursos'))
        except Exception as e:
            conexion.rollback()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': f'Ocurrió un error: {str(e)}'}), 500
            flash(f'Ocurrió un error: {str(e)}', 'danger')
            return redirect(url_for('mis_cursos'))
        finally:
            cursor.close()
            conexion.close()

    @app.route('/descargar_reporte_asistencia/<nombre_archivo>')
    def descargar_reporte_asistencia(nombre_archivo):
        carpeta_reportes = 'static/reportes'
        ruta_pdf = f'{carpeta_reportes}/{nombre_archivo}'
        if not os.path.exists(ruta_pdf):
            flash('El archivo PDF no existe.', 'danger')
            return redirect(url_for('mis_cursos'))
        return send_file(ruta_pdf, as_attachment=True)
