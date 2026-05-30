"""
Módulo de modelos para operaciones de base de datos.
Centraliza las consultas y operaciones comunes.
"""

from database import get_db_connection
from werkzeug.security import generate_password_hash
import json


# ==================== PERSONAS ====================

def get_all_personas(filters=None):
    """Obtiene todas las personas con filtros opcionales"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = "SELECT * FROM personas"
    params = []
    
    if filters:
        conditions = []
        if filters.get('estado'):
            conditions.append("estado = %s")
            params.append(filters['estado'])
        if filters.get('search'):
            conditions.append("(nombre LIKE %s OR apellido LIKE %s OR carnet LIKE %s)")
            search = f"%{filters['search']}%"
            params.extend([search, search, search])
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY id_persona DESC"
    cursor.execute(query, params)
    personas = cursor.fetchall()
    cursor.close()
    conn.close()
    return personas


def get_persona_by_id(id_persona):
    """Obtiene una persona por ID"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM personas WHERE id_persona = %s", (id_persona,))
    persona = cursor.fetchone()
    cursor.close()
    conn.close()
    return persona


def get_persona_with_roles(id_persona):
    """Obtiene una persona con sus roles"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM personas WHERE id_persona = %s", (id_persona,))
    persona = cursor.fetchone()
    
    if persona:
        cursor.execute("""
            SELECT rp.id_rol_persona, r.id_rol, r.nombre, ac.id_asignacion, c.nombre as curso,
                   s.nombre as seccion, ca.nombre as carrera
            FROM roles_persona rp
            JOIN roles r ON rp.id_rol = r.id_rol
            LEFT JOIN asignacion_cursos ac ON rp.id_rol_persona = ac.id_rol_persona
            LEFT JOIN cursos c ON ac.id_curso = c.id_curso
            LEFT JOIN secciones s ON ac.id_seccion = s.id_seccion
            LEFT JOIN sede_carrera sc ON c.id_sede_carrera = sc.id_sede_carrera
            LEFT JOIN carreras ca ON sc.id_carrera = ca.id_carrera
            WHERE rp.id_persona = %s
        """, (id_persona,))
        persona['roles'] = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return persona


def create_persona(nombre, apellido, telefono=None, correo_personal=None, 
                   correo_institucional=None, carnet=None, foto=None, firma=None):
    """Crea una nueva persona"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO personas 
        (nombre, apellido, telefono, correo_personal, correo_institucional, carnet, foto, firma, estado)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'activo')
    """, (nombre, apellido, telefono, correo_personal, correo_institucional, carnet, foto, firma))
    
    id_persona = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    return id_persona


def update_persona(id_persona, **kwargs):
    """Actualiza datos de una persona"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    allowed_fields = ['nombre', 'apellido', 'telefono', 'correo_personal', 
                      'correo_institucional', 'carnet', 'foto', 'firma', 'estado']
    
    updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
    
    if not updates:
        cursor.close()
        conn.close()
        return False
    
    set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
    values = list(updates.values()) + [id_persona]
    
    cursor.execute(f"UPDATE personas SET {set_clause} WHERE id_persona = %s", values)
    conn.commit()
    cursor.close()
    conn.close()
    return True


def delete_persona(id_persona):
    """Elimina una persona (cascada)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM personas WHERE id_persona = %s", (id_persona,))
    conn.commit()
    cursor.close()
    conn.close()
    return True


# ==================== USUARIOS ====================

def get_all_usuarios():
    """Obtiene todos los usuarios con datos de persona"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT u.id_usuario, u.id_persona, u.username, u.ultimo_login,
               p.nombre, p.apellido, p.carnet, p.correo_institucional
        FROM usuarios u
        JOIN personas p ON u.id_persona = p.id_persona
        ORDER BY u.id_usuario DESC
    """)
    usuarios = cursor.fetchall()
    cursor.close()
    conn.close()
    return usuarios


def get_usuario_by_username(username):
    """Obtiene usuario por username"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuarios WHERE username = %s", (username,))
    usuario = cursor.fetchone()
    cursor.close()
    conn.close()
    return usuario


def create_usuario(id_persona, username, password):
    """Crea un nuevo usuario"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    hashed_password = generate_password_hash(password)
    cursor.execute("""
        INSERT INTO usuarios (id_persona, username, password)
        VALUES (%s, %s, %s)
    """, (id_persona, username, hashed_password))
    
    id_usuario = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    return id_usuario


def update_usuario_password(id_usuario, new_password):
    """Actualiza contraseña de usuario"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    hashed_password = generate_password_hash(new_password)
    cursor.execute("UPDATE usuarios SET password = %s WHERE id_usuario = %s", 
                   (hashed_password, id_usuario))
    conn.commit()
    cursor.close()
    conn.close()
    return True


# ==================== ROLES ====================

def get_all_roles():
    """Obtiene todos los roles"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM roles ORDER BY nombre")
    roles = cursor.fetchall()
    cursor.close()
    conn.close()
    return roles


def assign_role_to_persona(id_persona, id_rol):
    """Asigna un rol a una persona"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO roles_persona (id_persona, id_rol)
        VALUES (%s, %s)
    """, (id_persona, id_rol))
    
    id_rol_persona = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    return id_rol_persona


def remove_role_from_persona(id_rol_persona):
    """Elimina un rol de una persona"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM roles_persona WHERE id_rol_persona = %s", (id_rol_persona,))
    conn.commit()
    cursor.close()
    conn.close()
    return True


# ==================== CURSOS ====================

def get_all_cursos(id_sede=None):
    """Obtiene todos los cursos"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if id_sede:
        cursor.execute("""
            SELECT c.*, ca.nombre as carrera, s.nombre as sede
            FROM cursos c
            JOIN sede_carrera sc ON c.id_sede_carrera = sc.id_sede_carrera
            JOIN carreras ca ON sc.id_carrera = ca.id_carrera
            JOIN sedes s ON sc.id_sede = s.id_sede
            WHERE sc.id_sede = %s
            ORDER BY c.nombre
        """, (id_sede,))
    else:
        cursor.execute("""
            SELECT c.*, ca.nombre as carrera, s.nombre as sede
            FROM cursos c
            JOIN sede_carrera sc ON c.id_sede_carrera = sc.id_sede_carrera
            JOIN carreras ca ON sc.id_carrera = ca.id_carrera
            JOIN sedes s ON sc.id_sede = s.id_sede
            ORDER BY c.nombre
        """)
    
    cursos = cursor.fetchall()
    cursor.close()
    conn.close()
    return cursos


def get_curso_by_id(id_curso):
    """Obtiene un curso por ID"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT c.*, ca.nombre as carrera, s.nombre as sede
        FROM cursos c
        JOIN sede_carrera sc ON c.id_sede_carrera = sc.id_sede_carrera
        JOIN carreras ca ON sc.id_carrera = ca.id_carrera
        JOIN sedes s ON sc.id_sede = s.id_sede
        WHERE c.id_curso = %s
    """, (id_curso,))
    curso = cursor.fetchone()
    cursor.close()
    conn.close()
    return curso


# ==================== ASISTENCIAS ====================

def get_asistencias_by_curso(id_curso, fecha=None):
    """Obtiene asistencias de un curso"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if fecha:
        cursor.execute("""
            SELECT a.*, p.nombre, p.apellido, p.carnet
            FROM asistencias a
            JOIN inscripciones i ON a.id_inscripcion = i.id_inscripcion
            JOIN roles_persona rp ON i.id_rol_persona = rp.id_rol_persona
            JOIN personas p ON rp.id_persona = p.id_persona
            JOIN asignacion_cursos ac ON i.id_asignacion = ac.id_asignacion
            WHERE ac.id_curso = %s AND a.fecha = %s
            ORDER BY p.apellido, p.nombre
        """, (id_curso, fecha))
    else:
        cursor.execute("""
            SELECT a.*, p.nombre, p.apellido, p.carnet
            FROM asistencias a
            JOIN inscripciones i ON a.id_inscripcion = i.id_inscripcion
            JOIN roles_persona rp ON i.id_rol_persona = rp.id_rol_persona
            JOIN personas p ON rp.id_persona = p.id_persona
            JOIN asignacion_cursos ac ON i.id_asignacion = ac.id_asignacion
            WHERE ac.id_curso = %s
            ORDER BY a.fecha DESC, p.apellido, p.nombre
        """, (id_curso,))
    
    asistencias = cursor.fetchall()
    cursor.close()
    conn.close()
    return asistencias


def register_asistencia(id_inscripcion, fecha, hora_entrada, estado='presente', 
                       metodo_registro='facial', observaciones=None):
    """Registra una asistencia"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO asistencias 
        (id_inscripcion, fecha, hora_entrada, estado, metodo_registro, observaciones)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (id_inscripcion, fecha, hora_entrada, estado, metodo_registro, observaciones))
    
    id_asistencia = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    return id_asistencia


def get_asistencia_stats_by_curso(id_curso):
    """Obtiene estadísticas de asistencia por curso"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT 
            p.id_persona,
            p.nombre,
            p.apellido,
            COUNT(a.id_asistencia) as total_clases,
            SUM(CASE WHEN a.estado = 'presente' THEN 1 ELSE 0 END) as presentes,
            SUM(CASE WHEN a.estado = 'ausente' THEN 1 ELSE 0 END) as ausentes,
            SUM(CASE WHEN a.estado = 'tarde' THEN 1 ELSE 0 END) as tardes,
            ROUND(100 * SUM(CASE WHEN a.estado = 'presente' THEN 1 ELSE 0 END) / COUNT(a.id_asistencia), 2) as porcentaje
        FROM personas p
        JOIN roles_persona rp ON p.id_persona = rp.id_persona
        JOIN inscripciones i ON rp.id_rol_persona = i.id_rol_persona
        JOIN asignacion_cursos ac ON i.id_asignacion = ac.id_asignacion
        LEFT JOIN asistencias a ON i.id_inscripcion = a.id_inscripcion
        WHERE ac.id_curso = %s
        GROUP BY p.id_persona
        ORDER BY p.apellido, p.nombre
    """, (id_curso,))
    
    stats = cursor.fetchall()
    cursor.close()
    conn.close()
    return stats


# ==================== SALONES ====================

def get_all_salones(id_sede=None):
    """Obtiene todos los salones"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if id_sede:
        cursor.execute("""
            SELECT s.*, se.nombre as sede_nombre, ca.nombre as carrera_nombre, j.nombre as jornada_nombre
            FROM salones s
            JOIN sedes se ON s.id_sede = se.id_sede
            LEFT JOIN carreras ca ON s.id_carrera = ca.id_carrera
            LEFT JOIN jornadas j ON s.id_jornada = j.id_jornada
            WHERE s.id_sede = %s
            ORDER BY s.nombre
        """, (id_sede,))
    else:
        cursor.execute("""
            SELECT s.*, se.nombre as sede_nombre, ca.nombre as carrera_nombre, j.nombre as jornada_nombre
            FROM salones s
            JOIN sedes se ON s.id_sede = se.id_sede
            LEFT JOIN carreras ca ON s.id_carrera = ca.id_carrera
            LEFT JOIN jornadas j ON s.id_jornada = j.id_jornada
            ORDER BY s.nombre
        """)
    
    salones = cursor.fetchall()
    cursor.close()
    conn.close()
    return salones


def create_salon(nombre, capacidad, id_sede, id_carrera=None, id_jornada=None):
    """Crea un nuevo salón"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO salones (nombre, capacidad, id_sede, id_carrera, id_jornada)
        VALUES (%s, %s, %s, %s, %s)
    """, (nombre, capacidad, id_sede, id_carrera, id_jornada))
    
    id_salon = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    return id_salon


# ==================== HORARIOS ====================

def get_horarios_by_curso(id_curso):
    """Obtiene horarios de un curso"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT h.*, s.nombre as salon, j.nombre as jornada
        FROM horarios h
        JOIN salones s ON h.id_salon = s.id_salon
        JOIN jornadas j ON h.id_jornada = j.id_jornada
        JOIN asignacion_cursos ac ON h.id_asignacion = ac.id_asignacion
        WHERE ac.id_curso = %s
        ORDER BY h.dia_semana, h.hora_inicio
    """, (id_curso,))
    
    horarios = cursor.fetchall()
    cursor.close()
    conn.close()
    return horarios


def get_horarios_by_persona(id_persona):
    """Obtiene horarios de una persona (estudiante/docente)"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT 
            c.nombre as curso,
            s.nombre as salon,
            j.nombre as jornada,
            h.dia_semana,
            h.hora_inicio,
            h.hora_fin,
            ca.nombre as carrera,
            sec.nombre as seccion
        FROM horarios h
        JOIN asignacion_cursos ac ON h.id_asignacion = ac.id_asignacion
        JOIN cursos c ON ac.id_curso = c.id_curso
        JOIN salones s ON h.id_salon = s.id_salon
        JOIN jornadas j ON h.id_jornada = j.id_jornada
        JOIN secciones sec ON ac.id_seccion = sec.id_seccion
        JOIN sede_carrera sc ON c.id_sede_carrera = sc.id_sede_carrera
        JOIN carreras ca ON sc.id_carrera = ca.id_carrera
        JOIN roles_persona rp ON ac.id_rol_persona = rp.id_rol_persona
        WHERE rp.id_persona = %s
        ORDER BY FIELD(h.dia_semana, 'lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado'), h.hora_inicio
    """, (id_persona,))
    
    horarios = cursor.fetchall()
    cursor.close()
    conn.close()
    return horarios


# ==================== SEDES ====================

def get_all_sedes():
    """Obtiene todas las sedes"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM sedes ORDER BY nombre")
    sedes = cursor.fetchall()
    cursor.close()
    conn.close()
    return sedes


# ==================== ESTADÍSTICAS ====================

def get_dashboard_stats():
    """Obtiene estadísticas para el dashboard"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    stats = {}
    
    cursor.execute("SELECT COUNT(*) as total FROM personas WHERE estado = 'activo'")
    stats['total_personas'] = cursor.fetchone()['total']
    
    cursor.execute("""
        SELECT COUNT(DISTINCT rp.id_persona) as total
        FROM roles_persona rp
        JOIN roles r ON rp.id_rol = r.id_rol
        WHERE r.nombre = 'estudiante'
    """)
    stats['total_estudiantes'] = cursor.fetchone()['total']
    
    cursor.execute("""
        SELECT COUNT(DISTINCT rp.id_persona) as total
        FROM roles_persona rp
        JOIN roles r ON rp.id_rol = r.id_rol
        WHERE r.nombre = 'catedratico'
    """)
    stats['total_docentes'] = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as total FROM cursos")
    stats['total_cursos'] = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as total FROM salones")
    stats['total_salones'] = cursor.fetchone()['total']
    
    cursor.execute("""
        SELECT COUNT(*) as total FROM asistencias 
        WHERE DATE(fecha) = CURDATE()
    """)
    stats['asistencias_hoy'] = cursor.fetchone()['total']
    
    cursor.close()
    conn.close()
    return stats
