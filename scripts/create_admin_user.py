#!/usr/bin/env python3
import sys
import os
from datetime import date

# Ensure project root is on sys.path so imports like `database` work
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from werkzeug.security import generate_password_hash
from database import get_db_connection


def main(username, password, nombre='Admin', apellido='Usuario', correo=None):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id_usuario FROM usuarios WHERE username=%s", (username,))
        if cur.fetchone():
            print(f"Usuario '{username}' ya existe.")
            return
        # detect columns available in personas table
        cur.execute('SELECT DATABASE()')
        db_name = cur.fetchone()[0]
        cur.execute("SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME='personas'", (db_name,))
        cols = [r[0] for r in cur.fetchall()]

        insert_cols = []
        insert_vals = []
        if 'nombre' in cols:
            insert_cols.append('nombre'); insert_vals.append(nombre)
        if 'apellido' in cols:
            insert_cols.append('apellido'); insert_vals.append(apellido)
        if 'telefono' in cols:
            insert_cols.append('telefono'); insert_vals.append(None)
        if 'correo' in cols and correo:
            insert_cols.append('correo'); insert_vals.append(correo)
        if 'carnet' in cols:
            insert_cols.append('carnet'); insert_vals.append(None)
        if 'foto' in cols:
            insert_cols.append('foto'); insert_vals.append(None)
        if 'firma' in cols:
            insert_cols.append('firma'); insert_vals.append(None)
        if 'estado' in cols:
            insert_cols.append('estado'); insert_vals.append('activo')

        if not insert_cols:
            raise RuntimeError('No hay columnas conocidas para insertar en personas')

        placeholders = ','.join(['%s'] * len(insert_cols))
        sql = f"INSERT INTO personas ({','.join(insert_cols)}) VALUES ({placeholders})"
        cur.execute(sql, tuple(insert_vals))
        id_persona = cur.lastrowid
        if not id_persona:
            # fallback: try to find inserted row by correo or nombre+apellido
            if 'correo' in cols and correo:
                cur.execute('SELECT id_persona FROM personas WHERE correo=%s ORDER BY id_persona DESC LIMIT 1', (correo,))
                row = cur.fetchone()
                id_persona = row[0] if row else None
            if not id_persona:
                cur.execute('SELECT id_persona FROM personas WHERE nombre=%s AND apellido=%s ORDER BY id_persona DESC LIMIT 1', (nombre, apellido))
                row = cur.fetchone()
                id_persona = row[0] if row else None

        if not id_persona:
            raise RuntimeError('No se pudo obtener id_persona tras insertar persona')

        # Insert role administrativo adaptively depending on table schema
        cur.execute("SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME='roles_persona'", (db_name,))
        rp_cols = [r[0] for r in cur.fetchall()]
        if 'id_rol' in rp_cols:
            # lookup id_rol for 'administrativo'
            cur.execute("SELECT id_rol FROM roles WHERE nombre=%s LIMIT 1", ('administrativo',))
            row = cur.fetchone()
            id_rol = row[0] if row else None
            if not id_rol:
                # try lowercase or create
                cur.execute("SELECT id_rol FROM roles WHERE LOWER(nombre)=LOWER(%s) LIMIT 1", ('administrativo',))
                row = cur.fetchone()
                id_rol = row[0] if row else None
            if not id_rol:
                # insert role
                cur.execute("INSERT INTO roles (nombre) VALUES (%s)", ('administrativo',))
                id_rol = cur.lastrowid
            insert_cols = ['id_persona','id_rol']
            insert_vals = [id_persona, id_rol]
            if 'fecha_inicio' in rp_cols:
                insert_cols.append('fecha_inicio'); insert_vals.append(date.today())
            if 'activo' in rp_cols:
                insert_cols.append('activo'); insert_vals.append(1)
            sql = f"INSERT INTO roles_persona ({','.join(insert_cols)}) VALUES ({','.join(['%s']*len(insert_vals))})"
            cur.execute(sql, tuple(insert_vals))
        elif 'tipo_persona' in rp_cols:
            # older schema: use tipo_persona
            cols = ['id_persona','tipo_persona']
            vals = [id_persona, 'administrativo']
            if 'fecha_inicio' in rp_cols:
                cols.append('fecha_inicio'); vals.append(date.today())
            if 'activo' in rp_cols:
                cols.append('activo'); vals.append(1)
            sql = f"INSERT INTO roles_persona ({','.join(cols)}) VALUES ({','.join(['%s']*len(vals))})"
            cur.execute(sql, tuple(vals))
        else:
            # fallback: try minimal insert if possible
            try:
                cur.execute('INSERT INTO roles_persona (id_persona) VALUES (%s)', (id_persona,))
            except Exception:
                pass

        # Create usuario with hashed password (adapt columns)
        pwd_hash = generate_password_hash(password)
        cur.execute("SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME='usuarios'", (db_name,))
        ucols = [r[0] for r in cur.fetchall()]
        if 'rol' in ucols:
            cur.execute('INSERT INTO usuarios (id_persona, username, password, rol) VALUES (%s,%s,%s,%s)', (id_persona, username, pwd_hash, 'administrativo'))
        else:
            cur.execute('INSERT INTO usuarios (id_persona, username, password) VALUES (%s,%s,%s)', (id_persona, username, pwd_hash))

        conn.commit()
        print('Usuario administrador creado:', username)
        print('Accede con ese usuario en la interfaz de login.')
    except Exception as e:
        conn.rollback()
        print('Error creando admin:', e)
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Uso: python scripts/create_admin_user.py <username> <password> [nombre] [apellido] [correo]')
        sys.exit(1)
    args = sys.argv[1:]
    username = args[0]
    password = args[1]
    nombre = args[2] if len(args) > 2 else 'Admin'
    apellido = args[3] if len(args) > 3 else 'Usuario'
    correo = args[4] if len(args) > 4 else None
    main(username, password, nombre, apellido, correo)
