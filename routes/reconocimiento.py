import json
import threading
import time
from datetime import date, datetime, timedelta

import cv2
import face_recognition
import numpy as np
from flask import Response, jsonify, render_template

from database import get_db_connection
from helpers import obtener_usuario_sesion

CAMERAS = {}

SCALE = 0.35
TIPO_REGISTRO = 'puerta_principal'
RECOGNITION_LEVEL = 'medio'
RECOGNITION_PROFILES = {
    'facil': {'detect_model': 'hog', 'encoding_model': 'small', 'tolerance': 0.60},
    'medio': {'detect_model': 'hog', 'encoding_model': 'large', 'tolerance': 0.50},
    'avanzado': {'detect_model': 'cnn', 'encoding_model': 'large', 'tolerance': 0.45},
}
PROFILE = RECOGNITION_PROFILES[RECOGNITION_LEVEL]
DETECT_MODEL = PROFILE['detect_model']
ENCODING_MODEL = PROFILE['encoding_model']
TOLERANCE = PROFILE['tolerance']
MIN_SECONDS_BETWEEN_LOGS = 300
RECOGNIZE_EVERY_N_FRAMES = 15
STREAM_FPS = 20
JPEG_QUALITY = 45

cam_state = {}
last_log_time = {}
camera_threads = {}
state_lock = threading.Lock()


def init_cam_state():
    for cam_id in CAMERAS.keys():
        cam_state[cam_id] = {
            'latest_jpeg': None,
            'latest_match': {
                'matched': False,
                'id_persona': None,
                'nombre': None,
                'apellido': None,
                'carnet': None,
                'correo': None,
                'dist': None,
                'timestamp': None,
                'cam_id': cam_id,
            },
            'last_log_time': last_log_time,
        }


def ensure_camera_thread(cam_id, source):
    thread = camera_threads.get(cam_id)
    if thread and thread.is_alive():
        return False
    t = threading.Thread(target=camera_loop, args=(cam_id, source), daemon=True)
    t.start()
    camera_threads[cam_id] = t
    return True


init_cam_state()


def load_known_faces():
    conn = get_db_connection()
    cursor = conn.cursor()
    # detect available columns in personas
    cursor.execute('SELECT DATABASE()')
    db_name = cursor.fetchone()[0]
    cursor.execute("SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME='personas'", (db_name,))
    cols = [r[0] for r in cursor.fetchall()]
    select_cols = ['id_persona']
    for c in ('nombre', 'apellido', 'carnet', 'correo', 'encoding_facial', 'estado'):
        if c in cols and c not in select_cols:
            select_cols.append(c)

    sql = f"SELECT {', '.join(select_cols)} FROM personas WHERE encoding_facial IS NOT NULL AND encoding_facial <> ''"
    if 'estado' in select_cols:
        sql += " AND estado = 'activo'"
    cursor.execute(sql)
    rows = [dict(zip([col.lower() for col in select_cols], row)) for row in cursor.fetchall()]
    cursor.close()
    conn.close()

    known_encodings = []
    known_people = []
    for r in rows:
        try:
            enc_list = json.loads(r.get('encoding_facial') or '[]')
            enc = np.array(enc_list, dtype=np.float32)
            if enc.shape == (128,):
                known_encodings.append(enc)
                known_people.append({
                    'id_persona': r['id_persona'],
                    'nombre': r.get('nombre'),
                    'apellido': r.get('apellido'),
                    'carnet': r.get('carnet'),
                    'correo': r.get('correo'),
                })
        except Exception as e:
            print('Encoding inválido id_persona=%s: %s' % (r.get('id_persona'), e))

    print(f'✔ Encodings cargados: {len(known_encodings)}')
    return known_encodings, known_people


KNOWN_ENCODINGS, KNOWN_PEOPLE = load_known_faces()
if not KNOWN_ENCODINGS:
    print('⚠ No hay encodings en la base de datos (personas.activo con encoding_facial).')


def registrar_entrada(id_persona, ubicacion):
    conn = get_db_connection()
    cursor = conn.cursor()
    cutoff_time = (datetime.now() - timedelta(seconds=MIN_SECONDS_BETWEEN_LOGS)).time()
    cursor.execute(
        """
            SELECT COUNT(*)
            FROM registros_entrada
            WHERE id_persona = %s
              AND ubicacion = %s
              AND fecha = %s
              AND hora >= %s
        """,
        (id_persona, ubicacion, date.today(), cutoff_time)
    )
    already_logged = cursor.fetchone()[0]
    if already_logged == 0:
        cursor.execute(
            "INSERT INTO registros_entrada (id_persona, ubicacion, fecha, hora, tipo_registro) VALUES (%s, %s, %s, %s, %s)",
            (id_persona, ubicacion, date.today(), time.strftime('%H:%M:%S'), TIPO_REGISTRO)
        )
        conn.commit()
    else:
        print(f'Entrada ya registrada recientemente para persona={id_persona} ubicacion={ubicacion}')
    cursor.close()
    conn.close()


def resolve_asignacion_for_camera(cam_id, ts=None):
    """Resolver una asignacion activa para la cámara en el timestamp dado.
    Devuelve (id_asignacion, id_salon) o (None, None).
    Lógica:
    - busca mappings en `camera_mappings` para la cámara
    - intenta encontrar una asignacion por `horarios` (día + hora)
    - fallback: busca en `asignacion_cursos` por id_salon e id_jornada
    """
    try:
        if ts is None:
            ts = datetime.now()
        hora = ts.strftime('%H:%M:%S')
        dia = ts.strftime('%a').upper()[:3]
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # ensure camera mappings filtered by camera id and (optionally) camera's sede
        cursor.execute("SELECT id_salon, id_sede_carrera, id_seccion, id_jornada FROM camera_mappings WHERE cam_id = %s AND activo = 1", (cam_id,))
        maps = cursor.fetchall()
        for m in maps:
            id_salon = m.get('id_salon')
            id_seccion = m.get('id_seccion')
            id_jornada = m.get('id_jornada')
            # 1) Buscar asignacion por horarios
            if id_salon:
                cursor.execute(
                    """
                    SELECT a.id_asignacion FROM asignacion_cursos a
                    JOIN horarios h ON h.id_asignacion = a.id_asignacion
                    WHERE h.id_salon = %s
                      AND h.dia = %s
                      AND %s BETWEEN h.hora_inicio AND h.hora_fin
                    LIMIT 1
                    """,
                    (id_salon, dia, hora)
                )
                row = cursor.fetchone()
                if row:
                    cursor.close()
                    conn.close()
                    return row['id_asignacion'], id_salon
            # 2) Fallback por asignacion_cursos con sección
            if id_seccion:
                cursor.execute(
                    "SELECT id_asignacion FROM asignacion_cursos WHERE id_seccion = %s AND (id_jornada = %s OR id_jornada IS NULL) LIMIT 1",
                    (id_seccion, id_jornada)
                )
                row = cursor.fetchone()
                if row:
                    cursor.close()
                    conn.close()
                    return row['id_asignacion'], id_salon
            # 3) Fallback por asignacion_cursos (salon + jornada)
            if id_salon:
                cursor.execute(
                    "SELECT id_asignacion FROM asignacion_cursos WHERE id_salon = %s AND (id_jornada = %s OR id_jornada IS NULL) LIMIT 1",
                    (id_salon, id_jornada)
                )
                row = cursor.fetchone()
                if row:
                    cursor.close()
                    conn.close()
                    return row['id_asignacion'], id_salon
        cursor.close()
        conn.close()
    except Exception as e:
        print('Error resolving asignacion for camera', cam_id, e)
    return None, None


def registrar_asistencia(id_persona, id_asignacion):
    """Registra una asistencia para la persona en la asignacion dada.
    Crea inscripcion si no existe y luego inserta en `asistencias`.
    """
    if not id_asignacion:
        return False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Obtener rol_persona (estudiante)
        # roles_persona in your schema may not have tipo_persona; try both selection strategies
        cursor.execute("SELECT id_rol_persona FROM roles_persona WHERE id_persona = %s AND activo = 1 LIMIT 1", (id_persona,))
        res = cursor.fetchone()
        if not res:
            cursor.close()
            conn.close()
            return False
        id_rol_persona = res[0]
        # Buscar inscripcion existente
        cursor.execute("SELECT id_inscripcion FROM inscripciones WHERE id_rol_persona = %s AND id_asignacion = %s LIMIT 1", (id_rol_persona, id_asignacion))
        row = cursor.fetchone()
        if row:
            id_inscripcion = row[0]
        else:
            # crear inscripcion automática (fecha actual)
            cursor.execute("INSERT INTO inscripciones (id_rol_persona, id_asignacion, fecha_inscripcion) VALUES (%s, %s, %s)", (id_rol_persona, id_asignacion, date.today()))
            id_inscripcion = cursor.lastrowid
            conn.commit()

        # Evitar duplicar asistencias en un intervalo corto (ej. 10 minutos)
        cutoff = datetime.now() - timedelta(minutes=10)
        cursor.execute("SELECT COUNT(*) FROM asistencias WHERE id_inscripcion = %s AND fecha >= %s", (id_inscripcion, cutoff))
        exists_recent = cursor.fetchone()[0]
        if exists_recent and exists_recent > 0:
            cursor.close()
            conn.close()
            return False

        # Insertar asistencia
        cursor.execute("INSERT INTO asistencias (id_inscripcion, estado, fecha) VALUES (%s, %s, %s)", (id_inscripcion, 'presente', datetime.now()))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print('Error registrando asistencia:', e)
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass
        return False


def open_camera(source):
    if isinstance(source, int):
        cap = cv2.VideoCapture(source, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def camera_loop(cam_id, source):
    known_encodings, known_people = KNOWN_ENCODINGS, KNOWN_PEOPLE
    if not known_encodings:
        print(f'[{cam_id}] No hay encodings para reconocimiento.')
        return

    print(f'[{cam_id}] Intentando abrir: {source}')
    cap = open_camera(source)
    if not cap.isOpened():
        print(f'[{cam_id}] ❌ No se pudo abrir la cámara: {source}')
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
    cap.set(cv2.CAP_PROP_FPS, STREAM_FPS)

    frame_count = 0
    last_boxes = []
    last_labels = []
    frame_interval = 1.0 / STREAM_FPS
    next_frame_time = time.time()

    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            time.sleep(0.05)
            continue
        frame_count += 1
        do_recognize = (frame_count % RECOGNIZE_EVERY_N_FRAMES == 0)
        if do_recognize:
            small = cv2.resize(frame, (0, 0), fx=SCALE, fy=SCALE)
            rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb, model=DETECT_MODEL)
            face_encodings = face_recognition.face_encodings(rgb, face_locations, model=ENCODING_MODEL)
            last_boxes = []
            last_labels = []
            frame_match = None
            for (top, right, bottom, left), face_enc in zip(face_locations, face_encodings):
                distances = face_recognition.face_distance(known_encodings, face_enc)
                best_idx = int(np.argmin(distances))
                best_distance = float(distances[best_idx])
                if best_distance <= TOLERANCE:
                    person = known_people[best_idx]
                    pid = person['id_persona']
                    now_ts = time.time()
                    with state_lock:
                        last_ts = cam_state[cam_id]['last_log_time'].get(pid, 0)
                    if now_ts - last_ts >= MIN_SECONDS_BETWEEN_LOGS:
                        try:
                            ubicacion_real = CAMERAS[cam_id]['ubicacion']
                            registrar_entrada(pid, ubicacion=ubicacion_real)
                            # actualizar timestamp y registrar asistencia vinculada a asignacion (si existe)
                            with state_lock:
                                cam_state[cam_id]['last_log_time'][pid] = now_ts
                            try:
                                id_asignacion, id_salon = resolve_asignacion_for_camera(cam_id, datetime.now())
                                if id_asignacion:
                                    registrar_asistencia(pid, id_asignacion)
                            except Exception as e:
                                print(f'[{cam_id}] Error registrando asistencia automática:', e)
                        except Exception as e:
                            print(f'[{cam_id}] Error registrando entrada:', e)
                    frame_match = {
                        'matched': True,
                        'id_persona': pid,
                        'nombre': person['nombre'],
                        'apellido': person['apellido'],
                        'carnet': person['carnet'],
                        'correo': person['correo'],
                        'dist': round(best_distance, 4),
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'cam_id': cam_id,
                    }
                    label = f"{person['nombre']} {person['apellido']} ({person['carnet']})"
                    color = (0, 255, 0)
                else:
                    label = f"NO REGISTRADO (dist={best_distance:.2f})"
                    color = (0, 0, 255)
                inv = 1.0 / SCALE
                top2, right2, bottom2, left2 = int(top*inv), int(right*inv), int(bottom*inv), int(left*inv)
                last_boxes.append((top2, right2, bottom2, left2, color))
                last_labels.append((label, left2, top2, color))
            if frame_match:
                with state_lock:
                    cam_state[cam_id]['latest_match'] = frame_match
        for (top2, right2, bottom2, left2, color) in last_boxes:
            cv2.rectangle(frame, (left2, top2), (right2, bottom2), color, 2)
        for (label, left2, top2, color) in last_labels:
            cv2.putText(frame, label, (left2, max(20, top2 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 3)
            cv2.putText(frame, label, (left2, max(20, top2 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        ok, jpg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
        if ok:
            with state_lock:
                cam_state[cam_id]['latest_jpeg'] = jpg.tobytes()
        now = time.time()
        sleep_time = next_frame_time - now
        if sleep_time > 0:
            time.sleep(sleep_time)
        next_frame_time = max(next_frame_time + frame_interval, now + frame_interval)


def mjpeg_generator(cam_id):
    while True:
        with state_lock:
            frame = cam_state[cam_id]['latest_jpeg']
        if frame is None:
            time.sleep(0.05)
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(1.0 / STREAM_FPS)


def register_reconocimiento_routes(app):
    @app.route('/video_feed/<cam_id>')
    def video_feed(cam_id):
        if cam_id not in CAMERAS:
            try:
                load_cameras_from_db()
            except Exception:
                pass
        if cam_id not in CAMERAS:
            return 'Cámara no existe', 404
        return Response(mjpeg_generator(cam_id), mimetype='multipart/x-mixed-replace; boundary=frame')

    @app.route('/last_match/<cam_id>')
    def last_match(cam_id):
        if cam_id not in CAMERAS:
            try:
                load_cameras_from_db()
            except Exception:
                pass
        if cam_id not in CAMERAS:
            return jsonify({'error': 'Cámara no existe'}), 404
        with state_lock:
            return jsonify(cam_state[cam_id]['latest_match'])

    @app.route('/monitor/<cam_id>')
    def monitor(cam_id):
        if cam_id not in CAMERAS:
            try:
                load_cameras_from_db()
            except Exception:
                pass
        if cam_id not in CAMERAS:
            return 'Cámara no existe', 404
        usuario = obtener_usuario_sesion()
        return render_template('monitor.html', cam_id=cam_id, nombre_cam=CAMERAS[cam_id].get('nombre'), usuario=usuario)

    @app.route('/cameras_status')
    def cameras_status():
        out = {}
        with state_lock:
            for cam_id in CAMERAS.keys():
                out[cam_id] = {
                    'source': CAMERAS[cam_id],
                    'has_frame': cam_state.get(cam_id, {}).get('latest_jpeg') is not None,
                    'last_match_ts': cam_state.get(cam_id, {}).get('latest_match', {}).get('timestamp'),
                }
        return jsonify(out)

    @app.route('/api/cameras')
    def api_cameras():
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute('SELECT cam_id, nombre, source, id_sede, descripcion FROM camaras ORDER BY cam_id')
        rows = cur.fetchall()
        cur.close(); conn.close()
        return jsonify(rows)

    @app.route('/api/refresh_cameras')
    def api_refresh_cameras():
        # reload CAMERAS from DB and ensure camera threads exist
        try:
            load_cameras_from_db()
            return jsonify({'ok': True})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 500

    @app.route('/api/restart_camera/<cam_id>')
    def api_restart_camera(cam_id):
        if cam_id not in CAMERAS:
            try:
                load_cameras_from_db()
            except Exception:
                pass
        if cam_id not in CAMERAS:
            return jsonify({'ok': False, 'error': 'Cámara no existe'}), 404
        try:
            restarted = ensure_camera_thread(cam_id, CAMERAS[cam_id].get('source'))
            return jsonify({'ok': True, 'restarted': restarted})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 500


def start_camera_threads():
    # load cameras from DB before starting threads
    try:
        load_cameras_from_db()
    except Exception:
        pass
    for cam_id, cam_data in CAMERAS.items():
        ensure_camera_thread(cam_id, cam_data.get('source'))


def load_cameras_from_db():
    global CAMERAS
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute('SELECT cam_id, nombre, source, id_sede, descripcion FROM camaras')
    rows = cur.fetchall()
    cur.close(); conn.close()
    cams = {}
    for r in rows:
        cams[r['cam_id']] = {
            'nombre': r.get('nombre'),
            'ubicacion': r.get('nombre'),
            'source': r.get('source'),
            'id_sede': r.get('id_sede'),
            'descripcion': r.get('descripcion')
        }
    CAMERAS = cams
    # re-init cam_state for new cameras
    with state_lock:
        for cam_id in list(cam_state.keys()):
            if cam_id not in CAMERAS:
                cam_state.pop(cam_id, None)
        for cam_id in CAMERAS.keys():
            if cam_id not in cam_state:
                cam_state[cam_id] = {
                    'latest_jpeg': None,
                    'latest_match': {
                        'matched': False,
                        'id_persona': None,
                        'nombre': None,
                        'apellido': None,
                        'carnet': None,
                        'correo': None,
                        'dist': None,
                        'timestamp': None,
                        'cam_id': cam_id,
                    },
                    'last_log_time': last_log_time,
                }
    for cam_id, cam_data in CAMERAS.items():
        ensure_camera_thread(cam_id, cam_data.get('source'))
