from flask import render_template, request, redirect, url_for, session, flash, jsonify

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
    get_jornadas_for_sede_carrera,
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
            print("\n" + "="*60)
            print("DEBUG: crear_curso() - POST REQUEST RECIBIDO")
            print("="*60)
            print(f"Datos del formulario:")
            print(f"  id_catedratico: {id_catedratico}")
            print(f"  id_sede: {id_sede}")
            print(f"  carrera: {carrera}")
            print(f"  seccion: {seccion}")
            print(f"  id_curso: {id_curso}")
            print(f"  id_jornada: {id_jornada}")
            print("="*60)
            if not id_catedratico:
                print("❌ FALLO: id_catedratico está vacío")
                flash('Seleccione un catedrático válido.', 'danger')
            elif not id_sede:
                print("❌ FALLO: id_sede está vacío")
                flash('Seleccione una sede válida.', 'danger')
            elif not carrera:
                print("❌ FALLO: carrera está vacía")
                flash('Seleccione una carrera válida.', 'danger')
            elif not seccion:
                print("❌ FALLO: seccion está vacía")
                flash('Seleccione una sección válida.', 'danger')
            elif not id_curso:
                print("❌ FALLO: id_curso está vacío")
                flash('Seleccione un curso válido.', 'danger')
            elif not id_jornada:
                print("❌ FALLO: id_jornada está vacío")
                flash('Seleccione una jornada válida.', 'danger')
            else:
                print("✓ Todas las validaciones básicas pasaron")
                try:
                    cols = get_roles_persona_schema()
                    active_clause = get_active_role_clause()
                    print(f"  Buscando id_rol_persona para id_persona={id_catedratico}")
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
                        print(f"❌ FALLO: No se encontró id_rol_persona para id_persona={id_catedratico}")
                        flash('El catedrático seleccionado no es válido o no está activo.', 'danger')
                    else:
                        id_rol_persona = rol_result[0]
                        print(f"  ✓ id_rol_persona encontrado: {id_rol_persona}")
                        # Obtener id_seccion por nombre (tabla secciones no contiene id_sede_carrera)
                        cursor.execute('SELECT id_seccion FROM secciones WHERE nombre = %s LIMIT 1', (seccion,))
                        seccion_row = cursor.fetchone()
                        if not seccion_row:
                            print(f"❌ FALLO: Sección '{seccion}' no existe")
                            flash('La sección seleccionada no existe.', 'danger')
                        else:
                            id_seccion = seccion_row[0]
                            print(f"  ✓ id_seccion encontrado: {id_seccion}")
                            # resolver id_sede_carrera desde sede y carrera
                            print(f"  Buscando id_sede_carrera para id_sede={id_sede}, carrera={carrera}")
                            cursor.execute('SELECT id_sede_carrera FROM sede_carrera WHERE id_sede = %s AND id_carrera = (SELECT id_carrera FROM carreras WHERE nombre = %s) LIMIT 1', (id_sede, carrera))
                            sc_row = cursor.fetchone()
                            id_sede_carrera = sc_row[0] if sc_row else None
                            if not id_sede_carrera:
                                print(f"❌ FALLO: No se encontró id_sede_carrera")
                                flash('La combinación de sede/carrera no es válida.', 'danger')
                            else:
                                print(f"  ✓ id_sede_carrera encontrado: {id_sede_carrera}")
                                print(f"  Validando que curso {id_curso} pertenece a sede_carrera {id_sede_carrera}")
                                cursor.execute(
                                    'SELECT COUNT(*) FROM cursos WHERE id_curso = %s AND id_sede_carrera = %s',
                                    (id_curso, id_sede_carrera)
                                )
                                curso_valido = cursor.fetchone()
                                if not curso_valido or curso_valido[0] == 0:
                                    print(f"❌ FALLO: Curso {id_curso} no pertenece a sede_carrera {id_sede_carrera}")
                                    flash('El curso seleccionado no pertenece a la sede/carrera/sección seleccionada.', 'danger')
                                else:
                                    print(f"  ✓ Curso válido para esta sede/carrera")
                                    # validar que la jornada pertenece a la sede+carrera
                                    allowed = get_jornadas_for_sede_carrera(id_sede, carrera) if id_sede and carrera else []
                                    allowed_ids = [str(j['id_jornada']) for j in allowed]
                                    print(f"  Jornadas permitidas: {allowed_ids}")
                                    print(f"  Jornada seleccionada: {id_jornada}")
                                    if allowed and str(id_jornada) not in allowed_ids:
                                        print(f"❌ FALLO: Jornada {id_jornada} no es válida")
                                        flash('La jornada seleccionada no es válida para la sede y carrera indicadas.', 'danger')
                                    else:
                                        print(f"  ✓ Jornada válida")
                                        cursor.execute(
                                            'INSERT INTO asignacion_cursos (id_curso, id_rol_persona, id_seccion, id_jornada) VALUES (%s, %s, %s, %s)',
                                            (id_curso, id_rol_persona, id_seccion, id_jornada)
                                        )
                                        print(f"\n✓✓✓ INSERT EJECUTADO ✓✓✓")
                                        print(f"  id_curso: {id_curso}")
                                        print(f"  id_rol_persona: {id_rol_persona}")
                                        print(f"  id_seccion: {id_seccion}")
                                        print(f"  id_jornada: {id_jornada}")
                                        conexion.commit()
                                        print(f"✓ COMMIT EJECUTADO")
                                        print("="*60 + "\n")
                                        flash('Curso asignado al catedrático correctamente.', 'success')
                                        cursor.close()
                                        conexion.close()
                                        return redirect(url_for('listar_cursos'))
                except Exception as e:
                    print(f"\n❌❌❌ EXCEPCIÓN ❌❌❌")
                    print(f"Error: {e}")
                    print(f"Tipo: {type(e).__name__}")
                    import traceback
                    print(traceback.format_exc())
                    print("="*60 + "\n")
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
            # poblar jornadas específicas para esta sede+carrera
            try:
                jornadas_options = get_jornadas_for_sede_carrera(id_sede, carrera) or []
            except Exception:
                jornadas_options = get_jornadas_options()

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

    @app.route('/admin/cursos/crear', methods=['GET', 'POST'])
    def admin_crear_curso():
        """Crear nuevo curso en la tabla cursos"""
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))

        usuario = obtener_usuario_sesion()
        conexion = get_db_connection()
        cursor = conexion.cursor(dictionary=True)

        form_data = {}

        if request.method == 'POST':
            nombre = request.form.get('nombre', '').strip()
            codigo = request.form.get('codigo', '').strip()
            creditos = request.form.get('creditos', '0')
            id_sede_carrera = request.form.get('id_sede_carrera', '')
            id_jornada = request.form.get('id_jornada', '')

            form_data = {'nombre': nombre, 'codigo': codigo, 'creditos': creditos, 'id_sede_carrera': id_sede_carrera, 'id_jornada': id_jornada}

            if not nombre:
                flash('El nombre del curso es requerido', 'danger')
            elif not codigo:
                flash('El código del curso es requerido', 'danger')
            elif not id_sede_carrera:
                flash('Debe seleccionar una sede y carrera', 'danger')
            elif not id_jornada:
                flash('Debe seleccionar una jornada', 'danger')
            else:
                try:
                    creditos_int = int(creditos) if creditos else 0
                    cursor.execute(
                        'INSERT INTO cursos (nombre, codigo, creditos, id_sede_carrera) VALUES (%s, %s, %s, %s)',
                        (nombre, codigo, creditos_int, id_sede_carrera)
                    )
                    conexion.commit()
                    flash(f'Curso "{nombre}" creado exitosamente', 'success')
                    form_data = {}
                except Exception as e:
                    conexion.rollback()
                    flash(f'Error al crear curso: {str(e)}', 'danger')

        # Obtener sedes y carreras para el formulario
        try:
            cursor.execute('''
                SELECT sc.id_sede_carrera, CONCAT(s.nombre, ' - ', c.nombre) as display_name
                FROM sede_carrera sc
                JOIN sedes s ON sc.id_sede = s.id_sede
                JOIN carreras c ON sc.id_carrera = c.id_carrera
                ORDER BY s.nombre, c.nombre
            ''')
            sede_carrera_options = cursor.fetchall()
        except Exception:
            sede_carrera_options = []

        # Obtener jornadas con sus sedes y carreras
        try:
            cursor.execute('''
                SELECT scj.id_sede_carrera_jornada, sc.id_sede_carrera, j.id_jornada, j.nombre as jornada_nombre,
                       CONCAT(s.nombre, ' - ', c.nombre, ' - ', j.nombre) as display_name
                FROM sedes_carreras_jornadas scj
                JOIN sede_carrera sc ON scj.id_sede_carrera = sc.id_sede_carrera
                JOIN jornadas j ON scj.id_jornada = j.id_jornada
                JOIN sedes s ON sc.id_sede = s.id_sede
                JOIN carreras c ON sc.id_carrera = c.id_carrera
                ORDER BY s.nombre, c.nombre, j.nombre
            ''')
            jornada_sede_carrera_options = cursor.fetchall()
        except Exception:
            jornada_sede_carrera_options = []

        cursor.close()
        conexion.close()

        return render_template('admin/cursos_crear.html',
                             usuario=usuario,
                             sede_carrera_options=sede_carrera_options,
                             jornada_sede_carrera_options=jornada_sede_carrera_options,
                             form_data=form_data)

    @app.route('/admin/cursos/listar', methods=['GET'])
    def admin_listar_cursos():
        """Listar todos los cursos"""
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))

        usuario = obtener_usuario_sesion()
        conexion = get_db_connection()
        cursor = conexion.cursor(dictionary=True)

        try:
            cursor.execute('''
                SELECT c.id_curso, c.nombre, c.codigo, c.creditos,
                       s.nombre AS sede, ca.nombre AS carrera
                FROM cursos c
                JOIN sede_carrera sc ON c.id_sede_carrera = sc.id_sede_carrera
                JOIN sedes s ON sc.id_sede = s.id_sede
                JOIN carreras ca ON sc.id_carrera = ca.id_carrera
                ORDER BY s.nombre, ca.nombre, c.nombre
            ''')
            cursos = cursor.fetchall()
        except Exception as e:
            flash(f'Error al cargar cursos: {str(e)}', 'danger')
            cursos = []

        cursor.close()
        conexion.close()

        return render_template('admin/cursos_listar.html',
                             usuario=usuario,
                             cursos=cursos)

    @app.route('/admin/cursos/<int:id_curso>/editar', methods=['GET', 'POST'])
    def admin_editar_curso(id_curso):
        """Editar curso existente"""
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))

        usuario = obtener_usuario_sesion()
        conexion = get_db_connection()
        cursor = conexion.cursor(dictionary=True)

        if request.method == 'POST':
            nombre = request.form.get('nombre', '').strip()
            codigo = request.form.get('codigo', '').strip()
            creditos = request.form.get('creditos', '0')
            id_sede_carrera = request.form.get('id_sede_carrera', '')

            if not nombre:
                flash('El nombre del curso es requerido', 'danger')
            elif not codigo:
                flash('El código del curso es requerido', 'danger')
            elif not id_sede_carrera:
                flash('Debe seleccionar una sede y carrera', 'danger')
            else:
                try:
                    creditos_int = int(creditos) if creditos else 0
                    cursor.execute(
                        'UPDATE cursos SET nombre=%s, codigo=%s, creditos=%s, id_sede_carrera=%s WHERE id_curso=%s',
                        (nombre, codigo, creditos_int, id_sede_carrera, id_curso)
                    )
                    conexion.commit()
                    flash(f'Curso actualizado exitosamente', 'success')
                    return redirect(url_for('admin_listar_cursos'))
                except Exception as e:
                    conexion.rollback()
                    flash(f'Error al actualizar curso: {str(e)}', 'danger')

        # Obtener datos del curso
        try:
            cursor.execute('SELECT * FROM cursos WHERE id_curso = %s', (id_curso,))
            curso = cursor.fetchone()
            if not curso:
                flash('Curso no encontrado', 'danger')
                return redirect(url_for('admin_listar_cursos'))

            cursor.execute('''
                SELECT sc.id_sede_carrera, CONCAT(s.nombre, ' - ', c.nombre) as display_name
                FROM sede_carrera sc
                JOIN sedes s ON sc.id_sede = s.id_sede
                JOIN carreras c ON sc.id_carrera = c.id_carrera
                ORDER BY s.nombre, c.nombre
            ''')
            sede_carrera_options = cursor.fetchall()
        except Exception as e:
            flash(f'Error al cargar datos: {str(e)}', 'danger')
            return redirect(url_for('admin_listar_cursos'))

        cursor.close()
        conexion.close()

        return render_template('admin/cursos_editar.html',
                             usuario=usuario,
                             curso=curso,
                             sede_carrera_options=sede_carrera_options)

    @app.route('/admin/cursos/<int:id_curso>/eliminar', methods=['POST'])
    def admin_eliminar_curso(id_curso):
        """Eliminar curso"""
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))

        conexion = get_db_connection()
        cursor = conexion.cursor()

        try:
            cursor.execute('SELECT nombre FROM cursos WHERE id_curso = %s', (id_curso,))
            curso = cursor.fetchone()
            if not curso:
                flash('Curso no encontrado', 'danger')
                return redirect(url_for('admin_listar_cursos'))

            cursor.execute('DELETE FROM cursos WHERE id_curso = %s', (id_curso,))
            conexion.commit()
            flash(f'Curso eliminado exitosamente', 'success')
        except Exception as e:
            conexion.rollback()
            flash(f'Error al eliminar curso: {str(e)}', 'danger')

        cursor.close()
        conexion.close()
        return redirect(url_for('admin_listar_cursos'))

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
            # si no hay secciones asignadas, listar las secciones disponibles (tabla `secciones`)
            cursor.execute('SELECT nombre FROM secciones ORDER BY nombre')
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
            cursor.execute('SELECT id_seccion FROM secciones WHERE nombre = %s LIMIT 1', (selected_section,))
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

            # obtener id_sede desde id_sede_carrera y validar jornadas permitidas
            id_sede = None
            try:
                cursor.execute('SELECT id_sede FROM sede_carrera WHERE id_sede_carrera = %s LIMIT 1', (id_sede_carrera,))
                sc_row = cursor.fetchone()
                id_sede = sc_row[0] if sc_row else None
            except Exception:
                id_sede = None

            allowed = get_jornadas_for_sede_carrera(id_sede, carrera_curso) if id_sede and carrera_curso else []
            allowed_ids = [str(j['id_jornada']) for j in allowed]

            # obtener la jornada de la asignación (si existe)
            asignacion_jornada = None
            if id_asignacion:
                cursor.execute('SELECT id_jornada FROM asignacion_cursos WHERE id_asignacion = %s LIMIT 1', (id_asignacion,))
                ar = cursor.fetchone()
                asignacion_jornada = ar[0] if ar and ar[0] is not None else None
                # validar que la jornada de la asignación pertenece a la sede+carrera
                if asignacion_jornada and allowed and str(asignacion_jornada) not in allowed_ids:
                    flash('La jornada de la asignación no es válida para la sede y carrera del curso.', 'danger')
                    cursor.close()
                    conexion.close()
                    return redirect(url_for('listar_cursos'))

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

            enrolled_count = 0
            skipped = []
            for id_persona in estudiantes_seleccionados:
                if 'tipo_persona' in cols:
                    # traer id_rol_persona y possible id_jornada si existe en esquema
                    if 'id_jornada' in cols:
                        cursor.execute(f"""
                            SELECT id_rol_persona, id_jornada
                            FROM roles_persona
                            WHERE id_persona = %s
                              AND id_rol = (SELECT id_rol FROM roles WHERE nombre = %s){active_clause}
                            ORDER BY id_rol_persona DESC
                            LIMIT 1
                        """, (id_persona, tipo_estudiante))
                    else:
                        cursor.execute(f"""
                            SELECT id_rol_persona
                            FROM roles_persona
                            WHERE id_persona = %s
                              AND id_rol = (SELECT id_rol FROM roles WHERE nombre = %s){active_clause}
                            ORDER BY id_rol_persona DESC
                            LIMIT 1
                        """, (id_persona, tipo_estudiante))
                else:
                    if 'id_jornada' in cols:
                        cursor.execute(f"""
                            SELECT id_rol_persona, id_jornada
                            FROM roles_persona
                            WHERE id_persona = %s
                              AND id_rol = %s{active_clause}
                            ORDER BY id_rol_persona DESC
                            LIMIT 1
                        """, (id_persona, id_rol_estudiante))
                    else:
                        cursor.execute(f"""
                            SELECT id_rol_persona
                            FROM roles_persona
                            WHERE id_persona = %s
                              AND id_rol = %s{active_clause}
                            ORDER BY id_rol_persona DESC
                            LIMIT 1
                        """, (id_persona, id_rol_estudiante))
                rol = cursor.fetchone()
                if not rol or id_asignacion is None:
                    reason = 'no_role' if not rol else 'no_asignacion'
                    # obtener nombre del estudiante para feedback
                    try:
                        cursor.execute('SELECT nombre, apellido FROM personas WHERE id_persona = %s LIMIT 1', (id_persona,))
                        p_row = cursor.fetchone()
                        nombre_est = f"{p_row[0]} {p_row[1]}" if p_row else ''
                    except Exception:
                        nombre_est = ''
                    skipped.append((int(id_persona), nombre_est, reason))
                    continue
                # extraer id_rol_persona y id_jornada si se devolvieron
                if isinstance(rol, tuple) or isinstance(rol, list):
                    id_rol_persona = rol[0]
                    rol_id_jornada = rol[1] if len(rol) > 1 else None
                else:
                    id_rol_persona = rol[0]
                    rol_id_jornada = None
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
                # si la asignación tiene una jornada, asegurar que el estudiante pertenezca a la misma jornada (si el esquema la contiene)
                if asignacion_jornada and rol_id_jornada is not None and int(rol_id_jornada) != int(asignacion_jornada):
                    # no inscribir si las jornadas no coinciden -> registrar motivo
                    try:
                        cursor.execute('SELECT nombre, apellido FROM personas WHERE id_persona = %s LIMIT 1', (id_persona,))
                        p_row = cursor.fetchone()
                        nombre_est = f"{p_row[0]} {p_row[1]}" if p_row else ''
                    except Exception:
                        nombre_est = ''
                    skipped.append((int(id_persona), nombre_est, 'jornada_mismatch'))
                    continue
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM inscripciones
                    WHERE id_rol_persona = %s
                      AND id_asignacion = %s
                """, (id_rol_persona, id_asignacion))
                if cursor.fetchone()[0] == 0:
                    try:
                        cursor.execute('INSERT INTO inscripciones (id_rol_persona, id_asignacion) VALUES (%s, %s)', (id_rol_persona, id_asignacion))
                        enrolled_count += 1
                    except Exception:
                        try:
                            cursor.execute('SELECT nombre, apellido FROM personas WHERE id_persona = %s LIMIT 1', (id_persona,))
                            p_row = cursor.fetchone()
                            nombre_est = f"{p_row[0]} {p_row[1]}" if p_row else ''
                        except Exception:
                            nombre_est = ''
                        skipped.append((int(id_persona), nombre_est, 'insert_error'))
                        pass
            conexion.commit()
            # after processing, re-query estudiantes and inscritos to render results on same page
            cols = get_roles_persona_schema()
            active_clause = get_active_role_clause('r')
            rr_active_clause = get_active_role_clause('rr')
            if 'tipo_persona' in cols:
                cursor.execute(f"""
                    SELECT p.id_persona, p.carnet, p.nombre, p.apellido, COALESCE(p.correo_institucional, p.correo_personal) AS correo
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
                    SELECT p.id_persona, p.carnet, p.nombre, p.apellido, COALESCE(p.correo_institucional, p.correo_personal) AS correo
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
            if enrolled_count:
                flash(f'Estudiantes inscritos correctamente: {enrolled_count}', 'success')
            if skipped:
                flash(f'Algunos estudiantes fueron omitidos: {len(skipped)}', 'warning')
            return render_template(
                'cursos/inscribir.html',
                curso=curso,
                section_options=section_options,
                selected_section=selected_section,
                estudiantes=estudiantes,
                inscritos=inscritos,
                catedratico_info=catedratico_info,
                usuario=usuario,
                skipped=skipped
            )

        estudiantes = []
        inscritos = []
        if selected_section and section_id:
            cols = get_roles_persona_schema()
            active_clause = get_active_role_clause('r')
            rr_active_clause = get_active_role_clause('rr')
            # obtener estudiantes activos que no son catedráticos y no están ya inscritos en este curso+sección
            if 'tipo_persona' in cols:
                cursor.execute(f"""
                    SELECT p.id_persona, p.carnet, p.nombre, p.apellido, COALESCE(p.correo_institucional, p.correo_personal) AS correo
                    FROM personas p
                    JOIN roles_persona r ON p.id_persona = r.id_persona
                    WHERE r.tipo_persona = 'estudiante'{active_clause}
                      AND p.estado = 'activo'
                      AND NOT EXISTS (
                          SELECT 1 FROM roles_persona rr
                          WHERE rr.id_persona = p.id_persona
                            AND rr.tipo_persona = 'catedratico'{rr_active_clause}
                      )
                    ORDER BY p.nombre, p.apellido
                """)
            else:
                id_rol_estudiante = get_rol_id_by_name('estudiante')
                id_rol_catedratico = get_rol_id_by_name('catedratico')
                cursor.execute(f"""
                    SELECT p.id_persona, p.carnet, p.nombre, p.apellido, COALESCE(p.correo_institucional, p.correo_personal) AS correo
                    FROM personas p
                    JOIN roles_persona r ON p.id_persona = r.id_persona
                    WHERE r.id_rol = %s{active_clause}
                      AND p.estado = 'activo'
                      AND NOT EXISTS (
                          SELECT 1 FROM roles_persona rr
                          WHERE rr.id_persona = p.id_persona
                            AND rr.id_rol = %s{rr_active_clause}
                      )
                    ORDER BY p.nombre, p.apellido
                """, (id_rol_estudiante, id_rol_catedratico))
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

    # ===== NUEVAS RUTAS: INSCRIPCIÓN POR CARNET =====

    @app.route('/inscribir_estudiantes', methods=['GET'])
    def inscribir_estudiantes_por_carnet():
        """Página principal para inscribir estudiantes por carnet"""
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))

        usuario = obtener_usuario_sesion()
        return render_template('cursos/inscribir_por_carnet.html', usuario=usuario)

    @app.route('/api/estudiante/carnet/<carnet>', methods=['GET'])
    def api_estudiante_por_carnet(carnet):
        """API: Busca estudiante por carnet y retorna sus datos (sede, carrera, jornada)"""
        
        conexion = get_db_connection()
        cursor = conexion.cursor(dictionary=True)

        try:
            # Buscar la persona por carnet
            cursor.execute("""
                SELECT p.id_persona, p.carnet, p.nombre, p.apellido, p.estado
                FROM personas p
                WHERE p.carnet = %s AND p.estado = 'activo'
                LIMIT 1
            """, (carnet,))
            persona = cursor.fetchone()

            if not persona:
                return jsonify({'success': False, 'message': 'Estudiante no encontrado'}), 404

            id_persona = persona['id_persona']

            # Verificar que sea estudiante activo
            cols = get_roles_persona_schema()
            active_clause = get_active_role_clause('r')
            
            if 'tipo_persona' in cols:
                cursor.execute(f"""
                    SELECT r.id_rol_persona, r.id_jornada
                    FROM roles_persona r
                    WHERE r.id_persona = %s
                      AND r.id_rol = (SELECT id_rol FROM roles WHERE nombre = 'estudiante'){active_clause}
                    ORDER BY r.id_rol_persona DESC
                    LIMIT 1
                """, (id_persona,))
            else:
                id_rol_estudiante = get_rol_id_by_name('estudiante')
                cursor.execute(f"""
                    SELECT r.id_rol_persona, r.id_jornada
                    FROM roles_persona r
                    WHERE r.id_persona = %s
                      AND r.id_rol = %s{active_clause}
                    ORDER BY r.id_rol_persona DESC
                    LIMIT 1
                """, (id_persona, id_rol_estudiante))

            rol = cursor.fetchone()
            if not rol:
                return jsonify({'success': False, 'message': 'No tiene rol de estudiante activo'}), 400

            id_jornada = rol.get('id_jornada')

            # Obtener jornada
            jornada_nombre = 'No especificada'
            if id_jornada:
                cursor.execute('SELECT nombre FROM jornadas WHERE id_jornada = %s', (id_jornada,))
                jornada_row = cursor.fetchone()
                jornada_nombre = jornada_row['nombre'] if jornada_row else 'No especificada'

            # Obtener sede y carrera desde sedes_carreras_jornadas
            if id_jornada:
                cursor.execute("""
                    SELECT sd.id_sede, sd.nombre AS sede, ca.id_carrera, ca.nombre AS carrera
                    FROM sedes_carreras_jornadas scj
                    JOIN sede_carrera sc ON scj.id_sede_carrera = sc.id_sede_carrera
                    JOIN sedes sd ON sc.id_sede = sd.id_sede
                    JOIN carreras ca ON sc.id_carrera = ca.id_carrera
                    WHERE scj.id_jornada = %s
                    LIMIT 1
                """, (id_jornada,))
                sede_carrera = cursor.fetchone()
            else:
                sede_carrera = None

            # Si no encuentra combinación válida
            if not sede_carrera:
                return jsonify({'success': False, 'message': 'No hay combinación sede-carrera-jornada válida'}), 400

            cursor.close()
            conexion.close()

            return jsonify({
                'success': True,
                'id_persona': id_persona,
                'carnet': persona['carnet'],
                'nombre_completo': f"{persona['nombre']} {persona['apellido']}",
                'sede': sede_carrera['sede'],
                'carrera': sede_carrera['carrera'],
                'jornada': jornada_nombre,
                'id_sede': sede_carrera['id_sede'],
                'id_carrera': sede_carrera['id_carrera'],
                'id_jornada': id_jornada
            })

        except Exception as e:
            cursor.close()
            conexion.close()
            return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

    @app.route('/api/cursos-disponibles/<int:id_persona>', methods=['GET'])
    def api_cursos_disponibles(id_persona):
        """API: Retorna cursos disponibles para un estudiante"""
        
        conexion = get_db_connection()
        cursor = conexion.cursor(dictionary=True)

        try:
            # Primero obtener sede, carrera y jornada del estudiante
            cols = get_roles_persona_schema()
            active_clause = get_active_role_clause('r')
            
            if 'tipo_persona' in cols:
                cursor.execute(f"""
                    SELECT r.id_jornada
                    FROM roles_persona r
                    WHERE r.id_persona = %s
                      AND r.id_rol = (SELECT id_rol FROM roles WHERE nombre = 'estudiante'){active_clause}
                    ORDER BY r.id_rol_persona DESC
                    LIMIT 1
                """, (id_persona,))
            else:
                id_rol_estudiante = get_rol_id_by_name('estudiante')
                cursor.execute(f"""
                    SELECT r.id_jornada
                    FROM roles_persona r
                    WHERE r.id_persona = %s
                      AND r.id_rol = %s{active_clause}
                    ORDER BY r.id_rol_persona DESC
                    LIMIT 1
                """, (id_persona, id_rol_estudiante))

            rol = cursor.fetchone()
            if not rol:
                return jsonify({'success': False, 'cursos': []}), 200

            id_jornada = rol.get('id_jornada')

            # Obtener sede y carrera del estudiante
            if id_jornada:
                cursor.execute("""
                    SELECT sd.id_sede, ca.id_carrera
                    FROM sedes_carreras_jornadas scj
                    JOIN sede_carrera sc ON scj.id_sede_carrera = sc.id_sede_carrera
                    JOIN sedes sd ON sc.id_sede = sd.id_sede
                    JOIN carreras ca ON sc.id_carrera = ca.id_carrera
                    WHERE scj.id_jornada = %s
                    LIMIT 1
                """, (id_jornada,))
                sede_carrera = cursor.fetchone()
            else:
                sede_carrera = None

            if not sede_carrera:
                return jsonify({'success': True, 'cursos': []}), 200

            id_sede = sede_carrera['id_sede']
            id_carrera = sede_carrera['id_carrera']

            # Obtener cursos disponibles para esa sede y carrera
            # Si hay asignaciones, usa esas; si no, devuelve todos los cursos de la sede/carrera
            cursor.execute("""
                SELECT ac.id_asignacion, c.id_curso, c.nombre AS nombre_curso, 
                       c.codigo, COALESCE(s.nombre, 'A') AS seccion, 
                       COALESCE(p.nombre, 'SIN ASIGNAR') AS docente_nombre, 
                       COALESCE(p.apellido, '') AS docente_apellido, 
                       COALESCE(j.nombre, 'General') AS jornada,
                       COALESCE((SELECT COUNT(*) FROM inscripciones WHERE id_asignacion = ac.id_asignacion), 0) AS inscritos_count
                FROM (
                    -- Primero intenta obtener asignaciones
                    SELECT ac.id_asignacion, ac.id_curso, ac.id_seccion, ac.id_rol_persona, ac.id_jornada
                    FROM asignacion_cursos ac
                    WHERE ac.id_jornada = %s OR ac.id_jornada IS NULL
                    UNION ALL
                    -- Si no hay asignaciones para estos cursos, genera filas virtuales
                    SELECT NULL, c.id_curso, NULL, NULL, NULL
                    FROM cursos c
                    WHERE c.id_sede_carrera IN (
                        SELECT sc.id_sede_carrera
                        FROM sede_carrera sc
                        WHERE sc.id_sede = %s AND sc.id_carrera = %s
                    )
                    AND NOT EXISTS (
                        SELECT 1 FROM asignacion_cursos ac2 WHERE ac2.id_curso = c.id_curso
                    )
                ) ac
                JOIN cursos c ON ac.id_curso = c.id_curso
                LEFT JOIN secciones s ON ac.id_seccion = s.id_seccion
                LEFT JOIN roles_persona r ON ac.id_rol_persona = r.id_rol_persona
                LEFT JOIN personas p ON r.id_persona = p.id_persona
                LEFT JOIN jornadas j ON ac.id_jornada = j.id_jornada
                ORDER BY c.nombre, s.nombre
            """, (id_jornada, id_sede, id_carrera))

            cursos_disponibles = cursor.fetchall()

            # Verificar cuales ya están inscritos
            cursos_resultado = []
            for curso in cursos_disponibles:
                # Verificar si ya está inscrito
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM inscripciones i
                    JOIN roles_persona r ON i.id_rol_persona = r.id_rol_persona
                    WHERE r.id_persona = %s
                      AND i.id_asignacion = %s
                """, (id_persona, curso['id_asignacion']))
                
                inscripcion = cursor.fetchone()
                ya_inscrito = inscripcion['count'] > 0 if inscripcion else False

                cursos_resultado.append({
                    'id_asignacion': curso['id_asignacion'],
                    'id_curso': curso['id_curso'],
                    'codigo_curso': curso['codigo'],
                    'nombre_curso': curso['nombre_curso'],
                    'seccion': curso['seccion'],
                    'docente': f"{curso['docente_nombre']} {curso['docente_apellido']}",
                    'jornada': curso['jornada'],
                    'inscritos_count': curso['inscritos_count'],
                    'ya_inscrito': ya_inscrito
                })

            cursor.close()
            conexion.close()

            return jsonify({'success': True, 'cursos': cursos_resultado}), 200

        except Exception as e:
            cursor.close()
            conexion.close()
            return jsonify({'success': False, 'message': f'Error: {str(e)}', 'cursos': []}), 500

    @app.route('/inscribir_estudiantes_guardar', methods=['POST'])
    def inscribir_estudiantes_guardar():
        """Procesa inscripciones de estudiante en múltiples cursos"""
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))

        id_persona = request.form.get('id_persona')
        cursos_seleccionados = request.form.getlist('cursos')

        if not id_persona or not cursos_seleccionados:
            flash('Debe seleccionar al menos un curso', 'warning')
            return redirect(url_for('inscribir_estudiantes_por_carnet'))

        conexion = get_db_connection()
        cursor = conexion.cursor()

        try:
            # Obtener rol de estudiante
            cols = get_roles_persona_schema()
            active_clause = get_active_role_clause('r')
            
            if 'tipo_persona' in cols:
                cursor.execute(f"""
                    SELECT r.id_rol_persona
                    FROM roles_persona r
                    WHERE r.id_persona = %s
                      AND r.tipo_persona = 'estudiante'{active_clause}
                    ORDER BY r.id_rol_persona DESC
                    LIMIT 1
                """, (id_persona,))
            else:
                id_rol_estudiante = get_rol_id_by_name('estudiante')
                cursor.execute(f"""
                    SELECT r.id_rol_persona
                    FROM roles_persona r
                    WHERE r.id_persona = %s
                      AND r.id_rol = %s{active_clause}
                    ORDER BY r.id_rol_persona DESC
                    LIMIT 1
                """, (id_persona, id_rol_estudiante))

            rol_row = cursor.fetchone()
            if not rol_row:
                flash('Estudiante no válido', 'danger')
                return redirect(url_for('inscribir_estudiantes_por_carnet'))

            id_rol_persona = rol_row[0]
            enrolled_count = 0
            already_enrolled = 0

            # Procesar cada curso
            for id_asignacion in cursos_seleccionados:
                # Verificar si ya está inscrito
                cursor.execute("""
                    SELECT COUNT(*) FROM inscripciones
                    WHERE id_rol_persona = %s AND id_asignacion = %s
                """, (id_rol_persona, id_asignacion))

                if cursor.fetchone()[0] == 0:
                    try:
                        cursor.execute("""
                            INSERT INTO inscripciones (id_rol_persona, id_asignacion)
                            VALUES (%s, %s)
                        """, (id_rol_persona, id_asignacion))
                        enrolled_count += 1
                    except Exception as e:
                        print(f"Error al inscribir en asignación {id_asignacion}: {str(e)}")
                else:
                    already_enrolled += 1

            conexion.commit()
            cursor.close()
            conexion.close()

            mensaje = f'Se inscribieron {enrolled_count} curso(s)'
            if already_enrolled > 0:
                mensaje += f' ({already_enrolled} ya estaban inscritos)'
            
            flash(mensaje, 'success')
            return redirect(url_for('inscribir_estudiantes_por_carnet'))

        except Exception as e:
            conexion.rollback()
            cursor.close()
            conexion.close()
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('inscribir_estudiantes_por_carnet'))
