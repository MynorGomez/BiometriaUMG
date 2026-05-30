from flask import render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash

from database import get_db_connection
from helpers import obtener_usuario_sesion, get_role_name


def register_auth_routes(app):
    @app.route('/')
    def home():
        return redirect(url_for('login'))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM usuarios WHERE username = %s', (username,))
            user = cursor.fetchone()
            cursor.close()
            conn.close()
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id_usuario']
                role = None
                if 'rol' in user and user.get('rol'):
                    role = user.get('rol')
                else:
                    role = get_role_name(user.get('id_persona'))

                if not role:
                    flash('Cuenta sin rol asignado. Contacte al administrador.', 'error')
                    return redirect(url_for('login'))

                session['rol'] = role
                if role == 'administrativo':
                    return redirect(url_for('dashboard_admin'))
                elif role == 'catedratico':
                    return redirect(url_for('mis_cursos'))
                elif role == 'estudiante':
                    return redirect(url_for('dashboard_estudiante'))
                flash('Rol no autorizado.', 'error')
                return redirect(url_for('login'))
            flash('Usuario o contraseña incorrectos', 'error')
            return redirect(url_for('login'))
        return render_template('login.html')

    @app.route('/logout')
    def logout():
        session.clear()
        return redirect(url_for('login'))
