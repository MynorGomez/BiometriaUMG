from flask import render_template, request, redirect, url_for, session, flash

from database import get_db_connection
from helpers import (
    obtener_usuario_sesion,
    get_sede_options,
    get_carreras_for_sede,
    get_cursos_for_sede_carrera,
    get_seccion_options,
    get_carrera_id,
    get_seccion_id,
    get_roles_persona_schema,
    get_rol_id_by_name,
    get_active_role_clause,
    get_jornadas_options,
)


def register_cursos_routes(app):
    @app.route('/cursos/nuevo', methods=['GET', 'POST'])
    def crear_curso():
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))

        usuario = obtener_usuario_sesion()
        conexion = get_db_connection()
        cursor = conexion.cursor()

        form_data = {}
        id_catedratico = request.form.get('id_catedratico', '')
        id_sede = request.form.get('id_sede', '')
        carrera = request.form.get('carrera', '')
        seccion = request.form.get('seccion', '')
        id_curso = request.form.get('id_curso', '')
        id_jornada = request.form.get('id_jornada', '')

        if request.method == 'POST':
            form_data = request.form.to_dict(flat=True)
            if not id_catedratico:
                flash('Seleccione un catedrático válido.', 'danger')
            elif not id_sede:
                flash('Seleccione una sede válida.', 'danger')
            elif not carrera:
                flash('Seleccione una carrera válida.', 'danger')
            elif not seccion:
                flash('Seleccione una sección válida.', 'danger')
            elif not id_curso:
                flash('Seleccione un curso válido.', 'danger')
            elif not id_jornada:
                flash('Seleccione una jornada válida.', 'danger')
            else:
                try:
                    cols = get_roles_persona_schema()
                    active_clause = get_active_role_clause()
                    if 'tipo_persona' in cols:
                        cursor.execute(
                            f'SELECT id_rol_persona FROM roles_persona WHERE id_persona = %s AND tipo_persona = %s{active_clause}',
                            (id_catedratico, 'catedratico')
                        )
                    else:
                        id_rol_catedratico = get_rol_id_by_name('catedratico')
                        if id_rol_catedratico is not None:
                            cursor.execute(
                                f'SELECT id_rol_persona FROM roles_persona WHERE id_persona = %s AND id_rol = %s{active_clause}',
                                (id_catedratico, id_rol_catedratico)
                            )
                        else:
                            rol_result = None
                            raise ValueError('No existe el rol de catedrático en la base de datos.')
                    rol_result = cursor.fetchone()
                    if not rol_result:
                        flash('El catedrático seleccionado no es válido o no está activo.', 'danger')
                    else:
                        id_rol_persona = rol_result[0]
                        cursor.execute(
                            'SELECT s.id_seccion, s.id_sede_carrera FROM secciones s JOIN sede_carrera sc ON s.id_sede_carrera = sc.id_sede_carrera WHERE s.nombre = %s AND s.id_carrera = (SELECT id_carrera FROM carreras WHERE nombre = %s) AND sc.id_sede = %s LIMIT 1',
                            (seccion, carrera, id_sede)
                        )
                        seccion_row = cursor.fetchone()
                        if not seccion_row:
                            flash('La sección seleccionada no es válida para la sede/carrera seleccionada.', 'danger')
                        else:
                            id_seccion = seccion_row[0]
                            id_sede_carrera = seccion_row[1]
                            cursor.execute(
                                'SELECT COUNT(*) FROM cursos WHERE id_curso = %s AND id_sede_carrera = %s',
                                (id_curso, id_sede_carrera)
                            )
                            curso_valido = cursor.fetchone()
                            if not curso_valido or curso_valido[0] == 0:
                                flash('El curso seleccionado no pertenece a la sede/carrera/sección seleccionada.', 'danger')
                            else:
                                cursor.execute(
                                    'INSERT INTO asignacion_cursos (id_curso, id_rol_persona, id_sede_carrera, id_seccion, id_jornada) VALUES (%s, %s, %s, %s, %s)',
                                    (id_curso, id_rol_persona, id_sede_carrera, id_seccion, id_jornada)
                                )
                                conexion.commit()
                                flash('Curso asignado al catedrático correctamente.', 'success')
                                cursor.close()
                                conexion.close()
                                return redirect(url_for('listar_cursos'))
                except Exception as e:
                    conexion.rollback()
                    flash(f'Error asignando curso: {e}', 'danger')

        cols = get_roles_persona_schema()
        active_clause = get_active_role_clause('r')
        if 'tipo_persona' in cols:
            cursor.execute(f"""
                SELECT p.id_persona, p.nombre, p.apellido
                FROM personas p
                JOIN roles_persona r ON p.id_persona = r.id_persona
                WHERE r.tipo_persona = 'catedratico'{active_clause}
                  AND p.estado = 'activo'
                ORDER BY p.nombre, p.apellido
            """)
        else:
            id_rol_catedratico = get_rol_id_by_name('catedratico')
            if id_rol_catedratico is not None:
                cursor.execute(f"""
                    SELECT p.id_persona, p.nombre, p.apellido
                    FROM personas p
                    JOIN roles_persona r ON p.id_persona = r.id_persona
                    WHERE r.id_rol = %s{active_clause}
                      AND p.estado = 'activo'
                    ORDER BY p.nombre, p.apellido
                """, (id_rol_catedratico,))
            else:
                catedraticos = []
                cursor.close()
                conexion.close()
                return render_template(
                    'cursos/nuevo.html',
                    usuario=usuario,
                    catedraticos=catedraticos,
                    sede_options=sede_options,
                    carrera_options=carrera_options,
                    curso_options=curso_options,
                    seccion_options=seccion_options,
                    form_data=form_data
                )
        catedraticos = cursor.fetchall()
        sede_options = get_sede_options()
        jornadas_options = get_jornadas_options()
        carrera_options = []
        curso_options = []
        seccion_options = []

        if id_sede:
            try:
                carrera_options = get_carreras_for_sede(id_sede)
            except Exception:
                carrera_options = []

        if id_sede and carrera:
            curso_options = get_cursos_for_sede_carrera(id_sede, carrera)
            seccion_options = get_seccion_options(id_sede, carrera)

        cursor.close()
        conexion.close()

        return render_template(
            'cursos/nuevo.html',
            usuario=usuario,
            catedraticos=catedraticos,
            sede_options=sede_options,
            jornadas_options=jornadas_options,
            carrera_options=carrera_options,
            curso_options=curso_options,
            seccion_options=seccion_options,
            form_data=form_data
        )

    @app.route('/cursos')
    def listar_cursos():
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))

        usuario = obtener_usuario_sesion()
        id_sede = request.args.get('id_sede', '')
        carrera = request.args.get('carrera', '')
        conn = get_db_connection()
        cursor = conn.cursor()
        cursos = []
        carrera_options = []
        curso_options = []

        if id_sede:
            try:
                id_sede_int = int(id_sede)
                carrera_options = get_carreras_for_sede(id_sede_int)
            except Exception:
                pass

        if id_sede and carrera:
            try:
                id_sede_int = int(id_sede)
                curso_options = get_cursos_for_sede_carrera(id_sede_int, carrera)
                cursor.execute(
                    'SELECT c.id_curso, c.nombre, ca.nombre AS carrera, sd.nombre AS sede '
                    'FROM cursos c '
                    'JOIN sede_carrera sc ON c.id_sede_carrera = sc.id_sede_carrera '
                    'JOIN carreras ca ON sc.id_carrera = ca.id_carrera '
                    'JOIN sedes sd ON sc.id_sede = sd.id_sede '
                    'WHERE sc.id_sede = %s AND ca.nombre = %s '
                    'ORDER BY c.nombre',
                    (id_sede_int, carrera)
                )
                cursos = cursor.fetchall()
            except Exception:
                pass

        cursor.close()
        conn.close()

        return render_template('cursos/listar.html',
                               usuario=usuario,
                               sede_options=get_sede_options(),
                               carrera_options=carrera_options,
                               curso_options=curso_options,
                               cursos=cursos,
                               id_sede=id_sede,
                               carrera=carrera)

    @app.route('/cursos/<int:id_curso>/inscribir', methods=['GET', 'POST'])
    def inscribir_estudiantes(id_curso):
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))

        usuario = obtener_usuario_sesion()
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT c.id_curso, c.nombre, ca.nombre AS carrera, sd.nombre AS sede,
                   sc.id_carrera, sc.id_sede_carrera
            FROM cursos c
            JOIN sede_carrera sc ON c.id_sede_carrera = sc.id_sede_carrera
            JOIN carreras ca ON sc.id_carrera = ca.id_carrera
            JOIN sedes sd ON sc.id_sede = sd.id_sede
            WHERE c.id_curso = %s
        """, (id_curso,))
        curso = cursor.fetchone()
        if not curso:
            cursor.close()
            conexion.close()
            flash('Curso no encontrado.', 'danger')
            return redirect(url_for('listar_cursos'))

        curso_id, curso_nombre, carrera_curso, sede_curso, carrera_id, id_sede_carrera = curso
        cursor.execute("""
            SELECT DISTINCT s.nombre
            FROM asignacion_cursos ac
            JOIN secciones s ON ac.id_seccion = s.id_seccion
            WHERE ac.id_curso = %s
            ORDER BY s.nombre
        """, (id_curso,))
        section_options = [row[0] for row in cursor.fetchall()]

        if not section_options:
            cursor.execute("""
                SELECT DISTINCT s.nombre
                FROM secciones s
                JOIN cursos c ON c.id_sede_carrera = s.id_sede_carrera
                WHERE c.id_curso = %s
                ORDER BY s.nombre
            """, (id_curso,))
            section_options = [row[0] for row in cursor.fetchall()]

        if request.method == 'POST':
            selected_section = request.form.get('seccion', '')
        else:
            selected_section = request.args.get('seccion', '')

        if selected_section not in section_options:
            selected_section = ''
        if not selected_section and len(section_options) == 1:
            selected_section = section_options[0]

        catedratico_info = None
        section_id = None
        if selected_section:
            cursor.execute('SELECT s.id_seccion FROM secciones s WHERE s.nombre = %s AND s.id_sede_carrera = %s LIMIT 1', (selected_section, id_sede_carrera))
            section_row = cursor.fetchone()
            section_id = section_row[0] if section_row else None
            if section_id:
                cursor.execute("""
                    SELECT p.id_persona, p.nombre, p.apellido, ac.id_jornada, j.nombre
                    FROM asignacion_cursos ac
                    JOIN roles_persona r ON ac.id_rol_persona = r.id_rol_persona
                    JOIN personas p ON r.id_persona = p.id_persona
                    LEFT JOIN jornadas j ON ac.id_jornada = j.id_jornada
                    WHERE ac.id_curso = %s
                      AND ac.id_seccion = %s
                    ORDER BY ac.id_asignacion DESC
                    LIMIT 1
                """, (id_curso, section_id))
                prof_row = cursor.fetchone()
                if prof_row:
                    catedratico_info = {
                        'id_persona': prof_row[0],
                        'nombre': f"{prof_row[1]} {prof_row[2]}",
                        'jornada': prof_row[4] if prof_row[4] else 'No especificada'
                    }
        if request.method == 'POST':
            id_asignacion = None
            if selected_section and section_id:
                cursor.execute('SELECT ac.id_asignacion FROM asignacion_cursos ac WHERE ac.id_curso = %s AND ac.id_seccion = %s LIMIT 1', (id_curso, section_id))
                asignacion_row = cursor.fetchone()
                id_asignacion = asignacion_row[0] if asignacion_row else None

            estudiantes_seleccionados = request.form.getlist('estudiantes')
            cols = get_roles_persona_schema()
            active_clause = get_active_role_clause()
            tipo_estudiante = 'estudiante'
            tipo_catedratico = 'catedratico'
            id_rol_estudiante = None
            id_rol_catedratico = None
            if 'tipo_persona' not in cols:
                id_rol_estudiante = get_rol_id_by_name(tipo_estudiante)
                id_rol_catedratico = get_rol_id_by_name(tipo_catedratico)

            for id_persona in estudiantes_seleccionados:
                if 'tipo_persona' in cols:
                    cursor.execute(f"""
                        SELECT id_rol_persona
                        FROM roles_persona
                        WHERE id_persona = %s
                          AND tipo_persona = %s{active_clause}
                        ORDER BY fecha_inicio DESC
                        LIMIT 1
                    """, (id_persona, tipo_estudiante))
                else:
                    cursor.execute(f"""
                        SELECT id_rol_persona
                        FROM roles_persona
                        WHERE id_persona = %s
                          AND id_rol = %s{active_clause}
                        ORDER BY fecha_inicio DESC
                        LIMIT 1
                    """, (id_persona, id_rol_estudiante))
                rol = cursor.fetchone()
                if not rol or id_asignacion is None:
                    continue
                rr_active_clause = get_active_role_clause('rr')
                if 'tipo_persona' in cols:
                    cursor.execute(f"""
                        SELECT COUNT(*)
                        FROM roles_persona rr
                        WHERE rr.id_persona = %s
                          AND rr.tipo_persona = %s{rr_active_clause}
                    """, (id_persona, tipo_catedratico))
                else:
                    cursor.execute(f"""
                        SELECT COUNT(*)
                        FROM roles_persona rr
                        WHERE rr.id_persona = %s
                          AND rr.id_rol = %s{rr_active_clause}
                    """, (id_persona, id_rol_catedratico))
                if cursor.fetchone()[0] > 0:
                    continue
                id_rol_persona = rol[0]
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM inscripciones
                    WHERE id_rol_persona = %s
                      AND id_asignacion = %s
                """, (id_rol_persona, id_asignacion))
                if cursor.fetchone()[0] == 0:
                    try:
                        cursor.execute('INSERT INTO inscripciones (id_rol_persona, id_asignacion) VALUES (%s, %s)', (id_rol_persona, id_asignacion))
                    except Exception:
                        pass
            conexion.commit()
            cursor.close()
            conexion.close()
            flash('Estudiantes inscritos correctamente.', 'success')
            return redirect(url_for('listar_cursos'))

        estudiantes = []
        inscritos = []
        if selected_section and section_id:
            cols = get_roles_persona_schema()
            active_clause = get_active_role_clause('r')
            rr_active_clause = get_active_role_clause('rr')
            if 'tipo_persona' in cols:
                cursor.execute(f"""
                    SELECT p.id_persona, p.carnet, p.nombre, p.apellido, p.correo
                    FROM personas p
                    JOIN roles_persona r ON p.id_persona = r.id_persona
                    WHERE r.tipo_persona = 'estudiante'{active_clause}
                      AND r.id_carrera = %s
                      AND r.id_seccion = %s
                      AND p.estado = 'activo'
                      AND NOT EXISTS (
                          SELECT 1 FROM roles_persona rr
                          WHERE rr.id_persona = p.id_persona
                            AND rr.tipo_persona = 'catedratico'{rr_active_clause}
                      )
                    ORDER BY p.nombre, p.apellido
                """, (carrera_id, section_id))
            else:
                id_rol_estudiante = get_rol_id_by_name('estudiante')
                id_rol_catedratico = get_rol_id_by_name('catedratico')
                cursor.execute(f"""
                    SELECT p.id_persona, p.carnet, p.nombre, p.apellido, p.correo
                    FROM personas p
                    JOIN roles_persona r ON p.id_persona = r.id_persona
                    WHERE r.id_rol = %s{active_clause}
                      AND r.id_carrera = %s
                      AND r.id_seccion = %s
                      AND p.estado = 'activo'
                      AND NOT EXISTS (
                          SELECT 1 FROM roles_persona rr
                          WHERE rr.id_persona = p.id_persona
                            AND rr.id_rol = %s{rr_active_clause}
                      )
                    ORDER BY p.nombre, p.apellido
                """, (id_rol_estudiante, carrera_id, section_id, id_rol_catedratico))
            estudiantes = cursor.fetchall()
            cursor.execute("""
                SELECT p.id_persona
                FROM inscripciones i
                JOIN roles_persona r ON i.id_rol_persona = r.id_rol_persona
                JOIN personas p ON r.id_persona = p.id_persona
                JOIN asignacion_cursos ac ON i.id_asignacion = ac.id_asignacion
                WHERE ac.id_curso = %s
                  AND ac.id_seccion = %s
            """, (id_curso, section_id))
            inscritos = [fila[0] for fila in cursor.fetchall()]

        cursor.close()
        conexion.close()
        return render_template(
            'cursos/inscribir.html',
            curso=curso,
            section_options=section_options,
            selected_section=selected_section,
            estudiantes=estudiantes,
            inscritos=inscritos,
            catedratico_info=catedratico_info,
            usuario=usuario
        )
