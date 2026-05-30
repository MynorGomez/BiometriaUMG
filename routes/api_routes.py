from flask import jsonify, request

from database import get_db_connection
from helpers import get_carrera_options, get_seccion_options, is_valid_carrera_in_sede, is_valid_sede


def register_api_routes(app):
    @app.route('/api/secciones')
    def api_secciones():
        id_sede = request.args.get('sede')
        carrera = request.args.get('carrera', '')
        options = get_seccion_options(id_sede, carrera) if carrera else []
        return jsonify({'options': options})

    @app.route('/api/carreras')
    def api_carreras():
        id_sede = request.args.get('sede')
        if not id_sede:
            options = get_carrera_options()
            return jsonify({'options': options})
        try:
            id_sede = int(id_sede)
        except Exception:
            return jsonify({'options': []})

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT c.nombre FROM carreras c JOIN sede_carrera sc ON c.id_carrera = sc.id_carrera WHERE sc.id_sede = %s ORDER BY c.nombre",
            (id_sede,)
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        options = [r[0] for r in rows] if rows else []
        return jsonify({'options': options})

    @app.route('/api/cursos')
    def api_cursos():
        id_sede = request.args.get('sede')
        carrera = request.args.get('carrera', '')
        if not id_sede or not carrera:
            return jsonify({'options': []})
        try:
            id_sede = int(id_sede)
        except Exception:
            return jsonify({'options': []})
        if not is_valid_sede(id_sede) or not is_valid_carrera_in_sede(id_sede, carrera):
            return jsonify({'options': []})

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
        options = [{'id': r[0], 'nombre': r[1]} for r in rows] if rows else []
        return jsonify({'options': options})
