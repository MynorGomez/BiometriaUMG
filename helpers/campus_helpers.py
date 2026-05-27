from database import get_db_connection


def _get_selection_options(table_name, default_options, where_clause=None, params=None):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = f"SELECT DISTINCT nombre FROM {table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"
        query += " ORDER BY nombre"
        cursor.execute(query, params or ())
        rows = cursor.fetchall()
        return [row[0] for row in rows] if rows else (default_options or [])
    except Exception:
        return default_options or []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_carrera_options():
    return _get_selection_options("carreras", [])


def get_seccion_options(id_sede=None, carrera=None):
    if not carrera:
        return []

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT nombre FROM secciones ORDER BY nombre")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [r[0] for r in rows] if rows else []


def is_valid_carrera(carrera):
    return len(_get_selection_options("carreras", [], "nombre = %s", (carrera,))) == 1


def is_valid_seccion(seccion, carrera=None, id_sede=None):
    if not (seccion and carrera):
        return False
    return seccion in get_seccion_options(id_sede, carrera)


def is_valid_carrera_in_sede(id_sede, carrera):
    try:
        id_sede = int(id_sede)
    except Exception:
        return False
    id_carrera = get_carrera_id(carrera)
    if not id_carrera:
        return False
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM sede_carrera WHERE id_sede = %s AND id_carrera = %s", (id_sede, id_carrera))
    valid = cursor.fetchone()[0] == 1
    cursor.close()
    conn.close()
    return valid


def get_carreras_for_sede(id_sede):
    try:
        id_sede = int(id_sede)
    except Exception:
        return []
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT c.nombre FROM carreras c JOIN sede_carrera sc ON c.id_carrera = sc.id_carrera WHERE sc.id_sede = %s ORDER BY c.nombre", (id_sede,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [r[0] for r in rows] if rows else []


def get_cursos_for_sede_carrera(id_sede, carrera):
    if not id_sede or not carrera:
        return []
    try:
        id_sede = int(id_sede)
    except Exception:
        return []
    if not is_valid_carrera_in_sede(id_sede, carrera):
        return []
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT c.id_curso, c.nombre "
        "FROM cursos c "
        "JOIN sede_carrera sc ON c.id_sede_carrera = sc.id_sede_carrera "
        "JOIN carreras ca ON sc.id_carrera = ca.id_carrera "
        "WHERE sc.id_sede = %s AND ca.nombre = %s "
        "ORDER BY c.nombre",
        (id_sede, carrera)
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows if rows else []


def get_carrera_id(carrera):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id_carrera FROM carreras WHERE nombre = %s", (carrera,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row[0] if row else None


def get_sede_carrera_id(id_sede, carrera):
    try:
        id_sede = int(id_sede)
    except Exception:
        return None
    id_carrera = get_carrera_id(carrera)
    if not id_carrera:
        return None
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id_sede_carrera FROM sede_carrera WHERE id_sede = %s AND id_carrera = %s", (id_sede, id_carrera))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row[0] if row else None


def get_seccion_id(seccion, id_carrera=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id_seccion FROM secciones WHERE nombre = %s", (seccion,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row[0] if row else None


def get_sede_options():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id_sede, nombre FROM sedes ORDER BY nombre")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows or []


def is_valid_sede(id_sede):
    if not id_sede:
        return False
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM sedes WHERE id_sede = %s", (id_sede,))
    valid = cursor.fetchone()[0] == 1
    cursor.close()
    conn.close()
    return valid


def get_jornadas_options():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id_jornada, nombre FROM jornadas ORDER BY nombre")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows or []
