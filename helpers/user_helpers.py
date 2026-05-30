import base64
import random
import re
from datetime import datetime

from flask import session
from database import get_db_connection


def limpiar_nombre(texto):
    return re.sub(r"[^\w\-]", "_", texto)


def get_roles_persona_schema():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT DATABASE()')
        db_name = cursor.fetchone()[0]
        cursor.execute(
            "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA=%s AND TABLE_NAME='roles_persona'",
            (db_name,)
        )
        return {row[0] for row in cursor.fetchall()}
    except Exception:
        return set()
    finally:
        cursor.close()
        conn.close()


def get_active_role_clause(column='rp'):
    cols = get_roles_persona_schema()
    if 'activo' in cols:
        return f' AND {column}.activo = 1'
    return ''


def get_role_name(id_persona):
    cols = get_roles_persona_schema()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if 'id_rol' in cols:
            cursor.execute(
                f"SELECT r.nombre FROM roles_persona rp JOIN roles r ON rp.id_rol = r.id_rol "
                f"WHERE rp.id_persona=%s{get_active_role_clause('rp')} LIMIT 1",
                (id_persona,)
            )
            row = cursor.fetchone()
            if row:
                return row[0]
        if 'tipo_persona' in cols:
            cursor.execute(
                f"SELECT tipo_persona FROM roles_persona WHERE id_persona=%s{get_active_role_clause('roles_persona')} LIMIT 1",
                (id_persona,)
            )
            row = cursor.fetchone()
            if row:
                return row[0]
        return None
    finally:
        cursor.close()
        conn.close()


def get_rol_id_by_name(nombre, conn=None):
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id_rol FROM roles WHERE LOWER(nombre)=LOWER(%s) LIMIT 1", (nombre,))
        row = cursor.fetchone()
        return row[0] if row else None
    finally:
        cursor.close()
        if close_conn:
            conn.close()


def obtener_usuario_sesion():
    if not session.get("user_id"):
        return None
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT p.id_persona, p.nombre, p.apellido, p.foto
        FROM usuarios u
        JOIN personas p ON u.id_persona = p.id_persona
        WHERE u.id_usuario = %s
    """, (session.get("user_id"),))
    usuario = cursor.fetchone()
    cursor.close()
    conn.close()

    if usuario and usuario.get("foto"):
        if isinstance(usuario["foto"], (bytes, bytearray)):
            usuario["foto"] = base64.b64encode(usuario["foto"]).decode("utf-8")
    elif usuario:
        usuario["foto"] = None

    return usuario


def generar_carnet_unico():
    yy = datetime.now().strftime("%y")
    prefijo = f"7691-{yy}-"
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        while True:
            numero_random = random.randint(10000, 99999)
            carnet = f"{prefijo}{numero_random}"
            cursor.execute("SELECT id_persona FROM personas WHERE carnet = %s", (carnet,))
            if cursor.fetchone() is None:
                return carnet
    finally:
        cursor.close()
        conn.close()
