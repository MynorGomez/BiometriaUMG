from datetime import datetime, date
from flask import render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash

from database import get_db_connection
from helpers import (
    obtener_usuario_sesion,
    get_carrera_options,
    get_seccion_options,
    get_carreras_for_sede,
    get_cursos_for_sede_carrera,
    get_sede_carrera_id,
    get_seccion_id,
    get_carrera_id,
    get_sede_options,
    get_jornadas_options,
    get_rol_id_by_name,
    is_valid_carrera_in_sede
)
import models


def register_admin_routes(app):
    @app.route('/admin')
    def dashboard_admin():
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))
        
        usuario = obtener_usuario_sesion()
        stats = models.get_dashboard_stats()
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT p.id_persona, p.nombre, p.apellido, p.carnet, p.estado, p.fecha_registro
            FROM personas p
            WHERE p.estado = 'activo'
            ORDER BY p.fecha_registro DESC
            LIMIT 15
        """)
        recent_personas = cursor.fetchall()
        
        # Obtener roles de cada persona
        for p in recent_personas:
            cursor.execute("""
                SELECT DISTINCT r.id_rol, r.nombre as tipo_persona
                FROM roles_persona rp
                JOIN roles r ON rp.id_rol = r.id_rol
                WHERE rp.id_persona = %s
            """, (p['id_persona'],))
            p['roles'] = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template(
            'admin.html',
            usuario=usuario,
            stats=stats,
            recent_personas=recent_personas,
            carrera_options=get_carrera_options()
        )

    @app.route('/personas/<int:id_persona>/promover', methods=['POST'])
    def promover_persona(id_persona):
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))

        nuevo_rol = request.form.get('nuevo_rol')
        crear_usuario = request.form.get('crear_usuario') == '1'
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            rp_cols = get_roles_persona_schema()
            if 'activo' in rp_cols:
                cursor.execute("UPDATE roles_persona SET activo=0, fecha_fin=%s WHERE id_persona=%s AND activo=1", (date.today(), id_persona))

            if 'id_rol' in rp_cols:
                id_rol = get_rol_id_by_name(nuevo_rol)
                if not id_rol:
                    raise ValueError(f"Rol desconocido: {nuevo_rol}")
                cursor.execute(
                    "INSERT INTO roles_persona (id_persona, id_rol) VALUES (%s, %s)",
                    (id_persona, id_rol)
                )
            else:
                cursor.execute(
                    "INSERT INTO roles_persona (id_persona, tipo_persona, carnet, id_carrera, id_seccion, id_sede, fecha_inicio, activo) VALUES (%s, %s, %s, %s, %s, %s, %s, 1)",
                    (id_persona, nuevo_rol, None, None, None, None, date.today())
                )

            if crear_usuario and nuevo_rol in ('catedratico', 'administrativo'):
                if not username:
                    cursor.execute(
                        "SELECT COALESCE(correo_institucional, correo_personal) AS correo FROM personas WHERE id_persona=%s",
                        (id_persona,)
                    )
                    rr = cursor.fetchone()
                    username = rr[0] if rr else f'user{id_persona}'
                if not password:
                    password = '123456'
                password_hash = generate_password_hash(password)
                cursor.execute(
                    'INSERT INTO usuarios (id_persona, username, password) VALUES (%s, %s, %s)',
                    (id_persona, username, password_hash)
                )
            conn.commit()
            flash('Persona promovida correctamente.', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error promoviendo persona: {e}', 'danger')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('admin_roles'))

    @app.route('/personas/<int:id_persona>/roles/add', methods=['POST'])
    def add_role_persona(id_persona):
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))

        tipo_persona = request.form.get('tipo_persona')
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            rp_cols = get_roles_persona_schema()
            if 'id_rol' in rp_cols:
                id_rol = get_rol_id_by_name(tipo_persona)
                if not id_rol:
                    raise ValueError(f"Rol desconocido: {tipo_persona}")
                cursor.execute('INSERT INTO roles_persona (id_persona, id_rol) VALUES (%s, %s)', (id_persona, id_rol))
            else:
                cursor.execute(
                    'INSERT INTO roles_persona (id_persona, tipo_persona, carnet, id_carrera, id_seccion, id_sede, fecha_inicio, activo) VALUES (%s, %s, %s, %s, %s, %s, %s, 1)',
                    (id_persona, tipo_persona, None, None, None, None, datetime.now())
                )
            conn.commit()
            flash('Rol añadido correctamente.', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error añadiendo rol: {e}', 'danger')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('admin_roles'))

    @app.route('/personas/<int:id_persona>/roles/<int:id_rol>/end', methods=['POST'])
    def end_role_persona(id_persona, id_rol):
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            rp_cols = get_roles_persona_schema()
            if 'activo' in rp_cols:
                cursor.execute('UPDATE roles_persona SET activo=0, fecha_fin=%s WHERE id_rol_persona=%s AND id_persona=%s', (datetime.now(), id_rol, id_persona))
            else:
                cursor.execute('DELETE FROM roles_persona WHERE id_rol_persona=%s AND id_persona=%s', (id_rol, id_persona))
            conn.commit()
            flash('Rol finalizado correctamente.', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error finalizando rol: {e}', 'danger')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('admin_roles'))

    @app.route('/admin/usuarios/nuevo', methods=['GET', 'POST'])
    def admin_crear_usuario():
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        if request.method == 'POST':
            id_persona = request.form.get('id_persona')
            rol = request.form.get('rol')
            username = request.form.get('username')
            password = request.form.get('password')
            if id_persona and not rol:
                rol = get_role_name(id_persona)
            if not (id_persona and rol and username and password):
                flash('Todos los campos son obligatorios.', 'warning')
                cursor.close()
                conn.close()
                return redirect(url_for('admin_crear_usuario'))
            try:
                password_hash = generate_password_hash(password)
                cursor.execute('INSERT INTO usuarios (id_persona, username, password) VALUES (%s, %s, %s)', (id_persona, username, password_hash))
                rp_cols = get_roles_persona_schema()
                if 'activo' in rp_cols:
                    cursor.execute('UPDATE roles_persona SET activo=0, fecha_fin=%s WHERE id_persona=%s AND activo=1', (date.today(), id_persona))
                if 'id_rol' not in rp_cols:
                    cursor.execute('SELECT carnet FROM personas WHERE id_persona=%s', (id_persona,))
                    rr = cursor.fetchone()
                    carnet = rr['carnet'] if rr else None
                    cursor.execute('INSERT INTO roles_persona (id_persona, tipo_persona, carnet, fecha_inicio, activo) VALUES (%s, %s, %s, %s, 1)', (id_persona, rol, carnet, date.today()))
                conn.commit()
                flash('Usuario y rol creados correctamente.', 'success')
                cursor.close()
                conn.close()
                return redirect(url_for('dashboard_admin'))
            except Exception as e:
                conn.rollback()
                flash(f'Error creando usuario: {e}', 'danger')
                cursor.close()
                conn.close()
                return redirect(url_for('admin_crear_usuario'))

        rp_cols = get_roles_persona_schema()
        if 'id_rol' in rp_cols:
            activo_clause = 'AND rp.activo = 1' if 'activo' in rp_cols else ''
            cursor.execute(f"""
                SELECT DISTINCT p.id_persona, p.nombre, p.apellido, p.carnet, r.nombre AS rol_activo
                FROM personas p
                LEFT JOIN usuarios u ON p.id_persona = u.id_persona
                JOIN roles_persona rp ON p.id_persona = rp.id_persona {activo_clause}
                JOIN roles r ON rp.id_rol = r.id_rol
                WHERE u.id_usuario IS NULL AND p.estado = 'activo' AND r.nombre != 'estudiante'
                ORDER BY p.nombre, p.apellido
            """)
        else:
            cursor.execute("""
                SELECT DISTINCT p.id_persona, p.nombre, p.apellido, p.carnet, r.tipo_persona AS rol_activo
                FROM personas p
                LEFT JOIN usuarios u ON p.id_persona = u.id_persona
                JOIN roles_persona r ON p.id_persona = r.id_persona AND r.activo = 1
                WHERE u.id_usuario IS NULL AND p.estado = 'activo' AND r.tipo_persona != 'estudiante'
                ORDER BY p.nombre, p.apellido
            """)
        personas = cursor.fetchall()
        cursor.close()
        conn.close()

        return render_template('admin_create_user.html', personas=personas, carrera_options=get_carrera_options())

    @app.route('/admin/roles', methods=['GET'])
    def admin_roles():
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))

        q = request.args.get('q', '').strip()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        results = []
        if q:
            like = f"%{q}%"
            cursor.execute("SELECT id_persona, nombre, apellido, carnet FROM personas WHERE (nombre LIKE %s OR apellido LIKE %s) AND estado='activo' ORDER BY nombre, apellido", (like, like))
            results = cursor.fetchall()
            rp_cols = get_roles_persona_schema()
            for p in results:
                cursor2 = conn.cursor(dictionary=True)
                if 'id_rol' in rp_cols:
                    activo_clause = 'AND rp.activo = 1' if 'activo' in rp_cols else ''
                    cursor2.execute(f"""
                        SELECT rp.id_persona AS id_rol_persona, r.nombre AS tipo_persona, NULL AS id_carrera, NULL AS id_seccion,
                               NULL AS carrera_nombre, NULL AS seccion_nombre, NULL AS sede_nombre
                        FROM roles_persona rp
                        JOIN roles r ON rp.id_rol = r.id_rol
                        WHERE rp.id_persona=%s {activo_clause}
                    """, (p['id_persona'],))
                else:
                    cursor2.execute("""
                        SELECT r.id_rol_persona, r.tipo_persona, r.id_carrera, r.id_seccion,
                               c.nombre AS carrera_nombre, s.nombre AS seccion_nombre, sd.nombre AS sede_nombre
                        FROM roles_persona r
                        LEFT JOIN carreras c ON r.id_carrera = c.id_carrera
                        LEFT JOIN secciones s ON r.id_seccion = s.id_seccion
                        LEFT JOIN sedes sd ON r.id_sede = sd.id_sede
                        WHERE r.id_persona=%s AND r.activo=1
                    """, (p['id_persona'],))
                roles = cursor2.fetchall()
                cursor2.close()
                p['active_roles'] = roles if roles else []
        cursor.close()
        conn.close()
        return render_template('admin_roles.html', results=results)

    @app.route('/admin/roles/<int:id_persona>', methods=['GET'])
    def admin_role_detail(id_persona):
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            'SELECT p.*, COALESCE(p.correo_institucional, p.correo_personal) AS correo '
            'FROM personas p WHERE p.id_persona=%s',
            (id_persona,)
        )
        persona = cursor.fetchone()
        if not persona:
            cursor.close()
            conn.close()
            flash('Persona no encontrada', 'warning')
            return redirect(url_for('admin_roles'))

        rp_cols = get_roles_persona_schema()
        if 'id_rol' in rp_cols:
            activo_clause = 'AND rp.activo = 1' if 'activo' in rp_cols else ''
            cursor.execute(f"""
                SELECT rp.id_persona AS id_rol_persona, r.nombre AS tipo_persona, NULL AS id_carrera, NULL AS id_seccion,
                       NULL AS carrera_nombre, NULL AS seccion_nombre, NULL AS sede_nombre
                FROM roles_persona rp
                JOIN roles r ON rp.id_rol = r.id_rol
                WHERE rp.id_persona=%s {activo_clause}
            """, (id_persona,))
        else:
            cursor.execute("""
                SELECT r.id_rol_persona, r.tipo_persona, r.id_carrera, r.id_seccion,
                       c.nombre AS carrera_nombre, s.nombre AS seccion_nombre, sd.nombre AS sede_nombre
                FROM roles_persona r
                LEFT JOIN carreras c ON r.id_carrera = c.id_carrera
                LEFT JOIN secciones s ON r.id_seccion = s.id_seccion
                LEFT JOIN sedes sd ON r.id_sede = sd.id_sede
                WHERE r.id_persona=%s AND r.activo=1
            """, (id_persona,))
        roles = cursor.fetchall()

        cursor.execute('SELECT id_sede, nombre FROM sedes ORDER BY nombre')
        sedes = cursor.fetchall()
        cursor.close()
        conn.close()

        return render_template('admin_role_detail.html', persona=persona, active_roles=roles, carrera_options=get_carrera_options(), sedes=sedes)

    # -------------------- Cámaras CRUD --------------------
    @app.route('/admin/camaras')
    def admin_camaras():
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT cam_id, nombre, source, id_sede, descripcion FROM camaras ORDER BY cam_id')
        cams = cursor.fetchall()
        cursor.close(); conn.close()
        return render_template('admin_camaras.html', camaras=cams)

    @app.route('/admin/camaras/nuevo', methods=['GET', 'POST'])
    def admin_camaras_nuevo():
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))
        conn = get_db_connection(); cursor = conn.cursor()
        if request.method == 'POST':
            cam_id = request.form.get('cam_id')
            nombre = request.form.get('nombre')
            source = request.form.get('source')
            id_sede = request.form.get('id_sede') or None
            descripcion = request.form.get('descripcion')
            if not cam_id or not source:
                flash('`cam_id` y `source` son obligatorios.', 'warning')
                return redirect(url_for('admin_camaras_nuevo'))
            try:
                cursor.execute('INSERT INTO camaras (cam_id, nombre, source, id_sede, descripcion) VALUES (%s,%s,%s,%s,%s)', (cam_id, nombre, source, id_sede, descripcion))
                conn.commit()
                flash('Cámara creada.', 'success')
                return redirect(url_for('admin_camaras'))
            except Exception as e:
                conn.rollback(); flash(f'Error: {e}', 'danger')
        # GET
        cursor.execute('SELECT id_sede, nombre FROM sedes ORDER BY nombre')
        sedes = cursor.fetchall()
        cursor.close(); conn.close()
        return render_template('admin_camara_form.html', sedes=sedes)

    @app.route('/admin/camaras/<cam_id>/editar', methods=['GET', 'POST'])
    def admin_camaras_editar(cam_id):
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))
        conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
        if request.method == 'POST':
            nombre = request.form.get('nombre')
            source = request.form.get('source')
            id_sede = request.form.get('id_sede') or None
            descripcion = request.form.get('descripcion')
            try:
                cursor.execute('UPDATE camaras SET nombre=%s, source=%s, id_sede=%s, descripcion=%s WHERE cam_id=%s', (nombre, source, id_sede, descripcion, cam_id))
                conn.commit(); flash('Cámara actualizada.', 'success')
                return redirect(url_for('admin_camaras'))
            except Exception as e:
                conn.rollback(); flash(f'Error: {e}', 'danger')
        cursor.execute('SELECT cam_id, nombre, source, id_sede, descripcion FROM camaras WHERE cam_id=%s', (cam_id,))
        cam = cursor.fetchone()
        cursor.execute('SELECT id_sede, nombre FROM sedes ORDER BY nombre')
        sedes = cursor.fetchall()
        cursor.close(); conn.close()
        if not cam:
            flash('Cámara no encontrada.', 'warning'); return redirect(url_for('admin_camaras'))
        return render_template('admin_camara_form.html', cam=cam, sedes=sedes)

    @app.route('/admin/camaras/<cam_id>/eliminar', methods=['POST'])
    def admin_camaras_eliminar(cam_id):
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))
        conn = get_db_connection(); cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM camera_mappings WHERE cam_id=%s', (cam_id,))
            cursor.execute('DELETE FROM camaras WHERE cam_id=%s', (cam_id,))
            conn.commit(); flash('Cámara eliminada.', 'success')
        except Exception as e:
            conn.rollback(); flash(f'Error eliminando: {e}', 'danger')
        finally:
            cursor.close(); conn.close()
        return redirect(url_for('admin_camaras'))

    # -------------------- Salones CRUD --------------------
    @app.route('/admin/salones')
    def admin_salones():
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))
        conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT s.*, se.nombre AS sede_nombre, ca.nombre AS carrera_nombre, j.nombre AS jornada_nombre
            FROM salones s
            JOIN sedes se ON s.id_sede = se.id_sede
            LEFT JOIN carreras ca ON s.id_carrera = ca.id_carrera
            LEFT JOIN jornadas j ON s.id_jornada = j.id_jornada
            ORDER BY s.nombre
        ''')
        salones = cursor.fetchall()
        cursor.close(); conn.close()
        return render_template('admin_salones.html', salones=salones)

    @app.route('/admin/salones/nuevo', methods=['GET', 'POST'])
    def admin_salones_nuevo():
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))
        conn = get_db_connection(); cursor = conn.cursor()
        if request.method == 'POST':
            nombre = request.form.get('nombre')
            codigo = request.form.get('codigo')
            ubicacion = request.form.get('ubicacion')
            descripcion = request.form.get('descripcion')
            id_sede = request.form.get('id_sede') or None
            carrera = request.form.get('carrera') or None
            id_jornada = request.form.get('id_jornada') or None
            
            if not nombre or not id_sede or not carrera or not id_jornada:
                flash('Nombre, sede, carrera y jornada son obligatorios.', 'warning'); return redirect(url_for('admin_salones_nuevo'))
            
            id_carrera = get_carrera_id(carrera)
            if not id_carrera or not is_valid_carrera_in_sede(id_sede, carrera):
                flash('La carrera seleccionada no es válida para la sede indicada.', 'warning'); return redirect(url_for('admin_salones_nuevo'))
            
            try:
                id_jornada = int(id_jornada) if id_jornada else None
                cursor.execute('INSERT INTO salones (nombre, codigo, id_sede, id_carrera, id_jornada, ubicacion, descripcion) VALUES (%s,%s,%s,%s,%s,%s,%s)', (nombre, codigo, id_sede, id_carrera, id_jornada, ubicacion, descripcion))
                conn.commit(); flash('Salón creado.', 'success'); return redirect(url_for('admin_salones'))
            except Exception as e:
                conn.rollback(); flash(f'Error: {e}', 'danger')
        cursor.close(); conn.close()
        return render_template('admin_salon_form.html', sedes=get_sede_options(), carreras=[], jornadas=get_jornadas_options())

    @app.route('/admin/salones/<int:id_salon>/editar', methods=['GET', 'POST'])
    def admin_salones_editar(id_salon):
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))
        conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
        if request.method == 'POST':
            nombre = request.form.get('nombre')
            codigo = request.form.get('codigo')
            ubicacion = request.form.get('ubicacion')
            descripcion = request.form.get('descripcion')
            id_sede = request.form.get('id_sede') or None
            carrera = request.form.get('carrera') or None
            id_jornada = request.form.get('id_jornada') or None
            
            if not nombre or not id_sede or not carrera or not id_jornada:
                flash('Nombre, sede, carrera y jornada son obligatorios.', 'warning'); return redirect(url_for('admin_salones_editar', id_salon=id_salon))
            
            id_carrera = get_carrera_id(carrera)
            if not id_carrera or not is_valid_carrera_in_sede(id_sede, carrera):
                flash('La carrera seleccionada no es válida para la sede indicada.', 'warning'); return redirect(url_for('admin_salones_editar', id_salon=id_salon))
            
            try:
                id_jornada = int(id_jornada) if id_jornada else None
                cursor.execute('UPDATE salones SET nombre=%s, codigo=%s, ubicacion=%s, descripcion=%s, id_sede=%s, id_carrera=%s, id_jornada=%s WHERE id_salon=%s', (nombre, codigo, ubicacion, descripcion, id_sede, id_carrera, id_jornada, id_salon))
                conn.commit(); flash('Salón actualizado.', 'success'); return redirect(url_for('admin_salones'))
            except Exception as e:
                conn.rollback(); flash(f'Error: {e}', 'danger')
        cursor.execute('SELECT s.id_salon, s.nombre, s.codigo, s.ubicacion, s.descripcion, s.id_sede, s.id_carrera, s.id_jornada, ca.nombre as carrera_nombre, j.nombre as jornada_nombre FROM salones s LEFT JOIN carreras ca ON s.id_carrera = ca.id_carrera LEFT JOIN jornadas j ON s.id_jornada = j.id_jornada WHERE s.id_salon=%s', (id_salon,))
        salon = cursor.fetchone()
        cursor.close(); conn.close()
        if not salon:
            flash('Salón no encontrado.', 'warning'); return redirect(url_for('admin_salones'))
        return render_template('admin_salon_form.html', salon=salon, sedes=get_sede_options(), carreras=get_carreras_for_sede(salon['id_sede']) if salon['id_sede'] else [], jornadas=get_jornadas_options())

    @app.route('/admin/salones/<int:id_salon>/eliminar', methods=['POST'])
    def admin_salones_eliminar(id_salon):
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))
        conn = get_db_connection(); cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM salones WHERE id_salon=%s', (id_salon,))
            conn.commit(); flash('Salón eliminado.', 'success')
        except Exception as e:
            conn.rollback(); flash(f'Error eliminando: {e}', 'danger')
        finally:
            cursor.close(); conn.close()
        return redirect(url_for('admin_salones'))

    # -------------------- Camera Mappings CRUD --------------------
    @app.route('/admin/camera_mappings')
    def admin_camera_mappings():
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))
        conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT cm.id, cm.cam_id, c.nombre AS cam_nombre,
                   cm.id_salon, s.nombre AS salon_nombre,
                   cm.id_sede_carrera,
                   se.nombre AS sede_nombre, ca.nombre AS carrera_nombre,
                   cm.id_seccion, sec.nombre AS seccion_nombre,
                   cm.id_jornada, j.nombre AS jornada_nombre,
                   cm.activo
            FROM camera_mappings cm
            LEFT JOIN camaras c ON cm.cam_id = c.cam_id
            LEFT JOIN salones s ON cm.id_salon = s.id_salon
            LEFT JOIN sede_carrera sc ON cm.id_sede_carrera = sc.id_sede_carrera
            LEFT JOIN sedes se ON sc.id_sede = se.id_sede
            LEFT JOIN carreras ca ON sc.id_carrera = ca.id_carrera
            LEFT JOIN secciones sec ON cm.id_seccion = sec.id_seccion
            LEFT JOIN jornadas j ON cm.id_jornada = j.id_jornada
            ORDER BY cm.id
        ''')
        maps = cursor.fetchall()
        cursor.close(); conn.close()
        return render_template('admin_camera_mappings.html', maps=maps)

    @app.route('/admin/camera_mappings/nuevo', methods=['GET', 'POST'])
    def admin_camera_mappings_nuevo():
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))
        conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
        selected_sede = None
        selected_carrera = None
        carreras = []
        if request.method == 'POST':
            cam_id = request.form.get('cam_id')
            selected_sede = request.form.get('id_sede') or None
            selected_carrera = request.form.get('carrera') or None
            id_salon = request.form.get('id_salon') or None
            # id_jornada will be derived from the selected salon to prevent manual override
            id_jornada = None
            activo = 1 if request.form.get('activo') == '1' else 0
            if selected_sede:
                carreras = get_carreras_for_sede(selected_sede)
            if selected_sede and selected_carrera:
                # keep carreras list populated for re-render
                pass
            id_sede_carrera = get_sede_carrera_id(selected_sede, selected_carrera) if selected_sede and selected_carrera else None
            id_seccion = None
            # derive jornada from salon if salon selected
            if id_salon:
                try:
                    cursor.execute('SELECT id_jornada FROM salones WHERE id_salon=%s', (id_salon,))
                    row = cursor.fetchone()
                    id_jornada = row['id_jornada'] if row and 'id_jornada' in row else None
                except Exception:
                    id_jornada = None
            if not selected_sede:
                flash('Debe seleccionar una sede.', 'warning')
            elif not selected_carrera:
                flash('Debe seleccionar una carrera.', 'warning')
            elif not id_sede_carrera:
                flash('La combinación de sede y carrera no es válida.', 'warning')
            elif not id_salon:
                flash('Debe seleccionar un salón.', 'warning')
            elif not id_jornada:
                flash('El salón seleccionado no tiene jornada asignada.', 'warning')
            elif not cam_id:
                flash('Debe seleccionar una cámara.', 'warning')
            else:
                try:
                    cursor.execute('INSERT INTO camera_mappings (cam_id, id_salon, id_sede_carrera, id_seccion, id_jornada, activo) VALUES (%s,%s,%s,%s,%s,%s)', (cam_id, id_salon, id_sede_carrera, id_seccion, id_jornada, activo))
                    conn.commit(); flash('Mapping creado.', 'success')
                    cursor.close(); conn.close()
                    return redirect(url_for('admin_camera_mappings'))
                except Exception as e:
                    conn.rollback(); flash(f'Error: {e}', 'danger')
        cursor.execute('SELECT cam_id, nombre FROM camaras ORDER BY cam_id')
        cams = cursor.fetchall()
        cursor.execute('''
            SELECT s.id_salon, s.nombre, s.id_jornada, j.nombre AS jornada_nombre
            FROM salones s
            LEFT JOIN jornadas j ON s.id_jornada = j.id_jornada
            ORDER BY s.nombre
        ''')
        salones = cursor.fetchall()
        cursor.close(); conn.close()
        return render_template(
            'admin_camera_mapping_form.html',
            cams=cams,
            salones=salones,
            sedes=get_sede_options(),
            carreras=carreras,
            selected_sede=selected_sede,
            selected_carrera=selected_carrera
        )

    @app.route('/admin/api/carreras_por_sede')
    def api_carreras_por_sede():
        id_sede = request.args.get('id_sede')
        return jsonify({'carreras': get_carreras_for_sede(id_sede) if id_sede else []})

    @app.route('/admin/api/cursos_por_sede_carrera')
    def api_cursos_por_sede_carrera():
        id_sede = request.args.get('id_sede')
        carrera = request.args.get('carrera')
        cursos = get_cursos_for_sede_carrera(id_sede, carrera) if id_sede and carrera else []
        return jsonify({'cursos': [{'id_curso': c[0], 'nombre': c[1]} for c in cursos]})

    @app.route('/admin/api/secciones_por_sede_carrera')
    def api_secciones_por_sede_carrera():
        id_sede = request.args.get('id_sede')
        carrera = request.args.get('carrera')
        secciones = get_seccion_options(id_sede, carrera) if id_sede and carrera else []
        return jsonify({'secciones': secciones})

    @app.route('/admin/api/salones_por_sede_carrera')
    def api_salones_por_sede_carrera():
        id_sede = request.args.get('id_sede')
        carrera = request.args.get('carrera')
        conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
        salones = []
        if id_sede and carrera:
            id_carrera = get_carrera_id(carrera)
            if id_carrera:
                cursor.execute('''
                    SELECT s.id_salon, s.nombre, s.id_jornada, j.nombre AS jornada_nombre
                    FROM salones s
                    LEFT JOIN jornadas j ON s.id_jornada = j.id_jornada
                    WHERE s.id_sede=%s AND s.id_carrera=%s
                    ORDER BY s.nombre
                ''', (id_sede, id_carrera))
                salones = [{'id_salon': s['id_salon'], 'nombre': s['nombre'], 'id_jornada': s.get('id_jornada'), 'jornada_nombre': s.get('jornada_nombre')} for s in cursor.fetchall()]
        cursor.close(); conn.close()
        return jsonify({'salones': salones})

    @app.route('/admin/camera_mappings/<int:id>/eliminar', methods=['POST'])
    def admin_camera_mappings_eliminar(id):
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))
        conn = get_db_connection(); cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM camera_mappings WHERE id=%s', (id,))
            conn.commit(); flash('Mapping eliminado.', 'success')
        except Exception as e:
            conn.rollback(); flash(f'Error eliminando: {e}', 'danger')
        finally:
            cursor.close(); conn.close()
        return redirect(url_for('admin_camera_mappings'))

    # -------------------- Sedes-Carreras-Jornadas CRUD --------------------
    @app.route('/admin/sedes_carreras_jornadas')
    def admin_sedes_carreras_jornadas():
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))
        conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT scj.id_sede_carrera_jornada, se.nombre AS sede, ca.nombre AS carrera, j.id_jornada, j.nombre AS jornada
            FROM sedes_carreras_jornadas scj
            JOIN sede_carrera sc ON scj.id_sede_carrera = sc.id_sede_carrera
            JOIN sedes se ON sc.id_sede = se.id_sede
            JOIN carreras ca ON sc.id_carrera = ca.id_carrera
            JOIN jornadas j ON scj.id_jornada = j.id_jornada
            ORDER BY se.nombre, ca.nombre, j.nombre
        ''')
        rows = cursor.fetchall()
        cursor.close(); conn.close()
        return render_template('admin_sedes_carreras_jornadas.html', rows=rows)

    @app.route('/admin/sedes_carreras_jornadas/nuevo', methods=['GET', 'POST'])
    def admin_scj_nuevo():
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))
        conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
        if request.method == 'POST':
            id_sede = request.form.get('id_sede')
            carrera = request.form.get('carrera')
            id_jornada = request.form.get('id_jornada')
            if not id_sede or not carrera or not id_jornada:
                flash('Sede, carrera y jornada son obligatorios.', 'warning')
                cursor.close(); conn.close(); return redirect(url_for('admin_scj_nuevo'))
            id_sede_carrera = get_sede_carrera_id(id_sede, carrera)
            if not id_sede_carrera:
                flash('La combinación sede-carrera no es válida.', 'warning')
                cursor.close(); conn.close(); return redirect(url_for('admin_scj_nuevo'))
            try:
                cursor.execute('INSERT INTO sedes_carreras_jornadas (id_sede_carrera, id_jornada) VALUES (%s,%s)', (id_sede_carrera, id_jornada))
                conn.commit(); flash('Mapping guardado.', 'success')
                cursor.close(); conn.close(); return redirect(url_for('admin_sedes_carreras_jornadas'))
            except Exception as e:
                conn.rollback(); flash(f'Error: {e}', 'danger')
                cursor.close(); conn.close(); return redirect(url_for('admin_scj_nuevo'))
        # GET
        cursor.execute('SELECT id_sede, nombre FROM sedes ORDER BY nombre')
        sedes = cursor.fetchall()
        cursor.close(); conn.close()
        return render_template('admin_sede_carrera_jornada_form.html', sedes=sedes, jornadas=get_jornadas_options(), carreras=[])

    @app.route('/admin/sedes_carreras_jornadas/<int:id_scj>/editar', methods=['GET', 'POST'])
    def admin_scj_editar(id_scj):
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))
        conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
        if request.method == 'POST':
            id_jornada = request.form.get('id_jornada')
            try:
                cursor.execute('UPDATE sedes_carreras_jornadas SET id_jornada=%s WHERE id_sede_carrera_jornada=%s', (id_jornada, id_scj))
                conn.commit(); flash('Mapping actualizado.', 'success')
                cursor.close(); conn.close(); return redirect(url_for('admin_sedes_carreras_jornadas'))
            except Exception as e:
                conn.rollback(); flash(f'Error: {e}', 'danger')
                cursor.close(); conn.close(); return redirect(url_for('admin_sedes_carreras_jornadas'))
        cursor.execute('''
            SELECT scj.id_sede_carrera_jornada, sc.id_sede, sc.id_carrera, ca.nombre AS carrera_nombre, j.id_jornada
            FROM sedes_carreras_jornadas scj
            JOIN sede_carrera sc ON scj.id_sede_carrera = sc.id_sede_carrera
            JOIN carreras ca ON sc.id_carrera = ca.id_carrera
            JOIN jornadas j ON scj.id_jornada = j.id_jornada
            WHERE scj.id_sede_carrera_jornada = %s
        ''', (id_scj,))
        row = cursor.fetchone()
        if not row:
            cursor.close(); conn.close(); flash('Mapping no encontrado.', 'warning'); return redirect(url_for('admin_sedes_carreras_jornadas'))
        # fetch sedes and carreras for the sede
        cursor.execute('SELECT id_sede, nombre FROM sedes ORDER BY nombre')
        sedes = cursor.fetchall()
        # get carreras for this sede
        carreras = get_carreras_for_sede(row['id_sede'])
        jornadas = get_jornadas_options()
        cursor.close(); conn.close()
        return render_template('admin_sede_carrera_jornada_form.html', sedes=sedes, carreras=carreras, jornadas=jornadas, mapping=row)

    @app.route('/admin/sedes_carreras_jornadas/<int:id_scj>/eliminar', methods=['POST'])
    def admin_scj_eliminar(id_scj):
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))
        conn = get_db_connection(); cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM sedes_carreras_jornadas WHERE id_sede_carrera_jornada=%s', (id_scj,))
            conn.commit(); flash('Mapping eliminado.', 'success')
        except Exception as e:
            conn.rollback(); flash(f'Error eliminando: {e}', 'danger')
        finally:
            cursor.close(); conn.close()
        return redirect(url_for('admin_sedes_carreras_jornadas'))

    # -------------------- Horarios CRUD (básico) --------------------
    @app.route('/admin/horarios')
    def admin_horarios():
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))
        conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT h.id_horario, h.id_asignacion, h.dia, h.hora_inicio, h.hora_fin, h.id_salon FROM horarios h ORDER BY h.id_horario DESC')
        horarios = cursor.fetchall()
        cursor.close(); conn.close()
        return render_template('admin_horarios.html', horarios=horarios)

    @app.route('/admin/horarios/nuevo', methods=['GET', 'POST'])
    def admin_horarios_nuevo():
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))
        conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
        if request.method == 'POST':
            id_asignacion = request.form.get('id_asignacion') or None
            dia = request.form.get('dia')
            hora_inicio = request.form.get('hora_inicio')
            hora_fin = request.form.get('hora_fin')
            id_salon = request.form.get('id_salon') or None
            if not dia or not hora_inicio or not hora_fin:
                flash('Día y horas son requeridos.', 'warning'); return redirect(url_for('admin_horarios_nuevo'))
            try:
                cursor.execute('INSERT INTO horarios (id_asignacion, dia, hora_inicio, hora_fin, id_salon) VALUES (%s,%s,%s,%s,%s)', (id_asignacion, dia, hora_inicio, hora_fin, id_salon))
                conn.commit(); flash('Horario creado.', 'success'); return redirect(url_for('admin_horarios'))
            except Exception as e:
                conn.rollback(); flash(f'Error: {e}', 'danger')
        cursor.execute('SELECT id_asignacion, id_curso, id_salon FROM asignacion_cursos ORDER BY id_asignacion')
        asignaciones = cursor.fetchall()
        cursor.execute('SELECT id_salon, nombre FROM salones ORDER BY nombre')
        salones = cursor.fetchall()
        cursor.close(); conn.close()
        return render_template('admin_horario_form.html', asignaciones=asignaciones, salones=salones)

    @app.route('/admin/horarios/<int:id_horario>/eliminar', methods=['POST'])
    def admin_horarios_eliminar(id_horario):
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))
        conn = get_db_connection(); cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM horarios WHERE id_horario=%s', (id_horario,))
            conn.commit(); flash('Horario eliminado.', 'success')
        except Exception as e:
            conn.rollback(); flash(f'Error eliminando: {e}', 'danger')
        finally:
            cursor.close(); conn.close()
        return redirect(url_for('admin_horarios'))

    @app.route('/personas/<int:id_persona>/cambiar-carrera', methods=['POST'])
    def change_carrera_persona(id_persona):
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))

        carrera = request.form.get('carrera')
        if not carrera:
            flash('Debe seleccionar una carrera.', 'warning')
            return redirect(url_for('admin_role_detail', id_persona=id_persona))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            id_carrera = get_carrera_id(carrera)
            if not id_carrera:
                flash('Carrera inválida.', 'warning')
                return redirect(url_for('admin_role_detail', id_persona=id_persona))

            cursor.execute('SELECT id_rol_persona, tipo_persona, carnet, id_seccion, id_sede, id_carrera FROM roles_persona WHERE id_persona=%s AND activo=1', (id_persona,))
            current = cursor.fetchone()
            if not current:
                flash('No existe un rol activo para esta persona.', 'warning')
                return redirect(url_for('admin_role_detail', id_persona=id_persona))

            if current['id_carrera'] == id_carrera:
                flash('La carrera seleccionada es la misma que la actual.', 'info')
                return redirect(url_for('admin_role_detail', id_persona=id_persona))

            cursor.execute('UPDATE roles_persona SET activo=0, fecha_fin=%s WHERE id_rol_persona=%s', (date.today(), current['id_rol_persona']))
            cursor.execute(
                'INSERT INTO roles_persona (id_persona, tipo_persona, carnet, id_carrera, id_seccion, id_sede, fecha_inicio, activo) VALUES (%s, %s, %s, %s, %s, %s, %s, 1)',
                (id_persona, current['tipo_persona'], current['carnet'], id_carrera, current['id_seccion'], current['id_sede'], date.today())
            )
            conn.commit()
            flash('Carrera actualizada correctamente y el cambio quedó registrado.', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error cambiando carrera: {e}', 'danger')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('admin_roles'))

    @app.route('/personas/<int:id_persona>/cambiar-sede', methods=['POST'])
    def change_sede_persona(id_persona):
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))

        id_sede = request.form.get('id_sede')
        if not id_sede or not is_valid_sede(id_sede):
            flash('Debe seleccionar una sede válida.', 'warning')
            return redirect(url_for('admin_role_detail', id_persona=id_persona))

        id_sede = int(id_sede)
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute('SELECT id_rol_persona, tipo_persona, carnet, id_seccion, id_sede, id_carrera FROM roles_persona WHERE id_persona=%s AND activo=1', (id_persona,))
            current = cursor.fetchone()
            if not current:
                flash('No existe un rol activo para esta persona.', 'warning')
                return redirect(url_for('admin_role_detail', id_persona=id_persona))

            if current['id_sede'] == id_sede:
                flash('La sede seleccionada es la misma que la actual.', 'info')
                return redirect(url_for('admin_role_detail', id_persona=id_persona))

            cursor.execute('UPDATE roles_persona SET activo=0, fecha_fin=%s WHERE id_rol_persona=%s', (date.today(), current['id_rol_persona']))
            cursor.execute(
                'INSERT INTO roles_persona (id_persona, tipo_persona, carnet, id_carrera, id_seccion, id_sede, fecha_inicio, activo) VALUES (%s, %s, %s, %s, %s, %s, %s, 1)',
                (id_persona, current['tipo_persona'], current['carnet'], current['id_carrera'], current['id_seccion'], id_sede, date.today())
            )
            conn.commit()
            flash('Sede actualizada correctamente y el cambio quedó registrado.', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error cambiando sede: {e}', 'danger')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('admin_roles'))

    @app.route('/personas/<int:id_persona>/cambiar-rol', methods=['POST'])
    def change_role_persona(id_persona):
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))

        carrera = request.form.get('carrera')
        seccion = request.form.get('seccion')
        id_sede = request.form.get('id_sede')

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute('SELECT id_rol_persona, tipo_persona, carnet, id_carrera, id_seccion, id_sede FROM roles_persona WHERE id_persona=%s AND activo=1', (id_persona,))
            current = cursor.fetchone()
            if not current:
                flash('No existe un rol activo para esta persona.', 'warning')
                return redirect(url_for('admin_role_detail', id_persona=id_persona))

            new_id_carrera = current['id_carrera']
            if carrera:
                new_id_carrera = get_carrera_id(carrera)
                if not new_id_carrera:
                    flash('Carrera inválida.', 'warning')
                    return redirect(url_for('admin_role_detail', id_persona=id_persona))

            new_id_seccion = current['id_seccion']
            if seccion:
                if not new_id_carrera:
                    flash('Debe seleccionar primero una carrera válida.', 'warning')
                    return redirect(url_for('admin_role_detail', id_persona=id_persona))
                new_id_seccion = get_seccion_id(seccion, new_id_carrera)
                if new_id_seccion is None:
                    flash('Sección inválida para la carrera seleccionada.', 'warning')
                    return redirect(url_for('admin_role_detail', id_persona=id_persona))

            new_id_sede = current['id_sede']
            if id_sede:
                if not is_valid_sede(id_sede):
                    flash('Sede inválida.', 'warning')
                    return redirect(url_for('admin_role_detail', id_persona=id_persona))
                new_id_sede = int(id_sede)

            if new_id_carrera == current['id_carrera'] and new_id_seccion == current['id_seccion'] and new_id_sede == current['id_sede']:
                flash('No se realizaron cambios en el rol.', 'info')
                return redirect(url_for('admin_role_detail', id_persona=id_persona))

            cursor.execute('UPDATE roles_persona SET activo=0, fecha_fin=%s WHERE id_rol_persona=%s', (date.today(), current['id_rol_persona']))
            cursor.execute(
                'INSERT INTO roles_persona (id_persona, tipo_persona, carnet, id_carrera, id_seccion, id_sede, fecha_inicio, activo) VALUES (%s, %s, %s, %s, %s, %s, %s, 1)',
                (id_persona, current['tipo_persona'], current['carnet'], new_id_carrera, new_id_seccion, new_id_sede, date.today())
            )
            conn.commit()
            flash('Rol actualizado correctamente y el cambio quedó registrado en el historial.', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error actualizando el rol: {e}', 'danger')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('admin_roles'))
