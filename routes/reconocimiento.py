import json
import threading
import time
from datetime import date, datetime, timedelta
import os

os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|timeout;5000000"

import cv2
import numpy as np
from flask import Response, jsonify, render_template

try:
    import face_recognition
except ImportError:
    face_recognition = None

from database import get_db_connection
from helpers import obtener_usuario_sesion
from models import get_horarios_by_persona


# =========================
# CAMERAS
# =========================
CAMERAS = {}

# =========================
# PROFESORES (PASO 9)
# =========================
CATEDRATICOS = {
    1: {
        "nombre": "Lic. García",
        "sede": "Central",
        "jornada": "Matutina",
        "horario": "7:00 - 12:00",
        "cursos": ["Programación", "Base de Datos"]
    }
}

# =========================
# CONFIG
# =========================
SCALE = 0.35
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


# =========================
# STATE
# =========================
cam_state = {}
cam_teacher_state = {}
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
                'horarios': []
            },
            'last_log_time': {}
        }


# =========================
# LOAD FACES
# =========================
def load_known_faces():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT DATABASE()')
    db_name = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COLUMN_NAME
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=%s AND TABLE_NAME='personas'
    """, (db_name,))

    cols = [r[0] for r in cursor.fetchall()]
    select_cols = ['id_persona']

    for c in ('nombre', 'apellido', 'carnet', 'correo', 'encoding_facial', 'estado'):
        if c in cols:
            select_cols.append(c)

    sql = f"""
        SELECT {', '.join(select_cols)}
        FROM personas
        WHERE encoding_facial IS NOT NULL AND encoding_facial <> ''
    """

    if 'estado' in cols:
        sql += " AND estado='activo'"

    cursor.execute(sql)
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    known_encodings = []
    known_people = []

    for r in rows:
        try:
            enc_list = json.loads(r[select_cols.index('encoding_facial')]) if 'encoding_facial' in select_cols else []
            enc = np.array(enc_list, dtype=np.float32)

            if enc.shape == (128,):
                known_encodings.append(enc)
                known_people.append({
                    'id_persona': r[0],
                    'nombre': r[1] if len(r) > 1 else None,
                    'apellido': r[2] if len(r) > 2 else None,
                    'carnet': r[3] if len(r) > 3 else None,
                    'correo': r[4] if len(r) > 4 else None,
                })
        except:
            pass

    print(f"✔ Encodings cargados: {len(known_encodings)}")
    return known_encodings, known_people


KNOWN_ENCODINGS, KNOWN_PEOPLE = load_known_faces()


# =========================
# PROFESOR LOGIC
# =========================
def update_teacher_state(cam_id, pid):
    if pid in CATEDRATICOS:
        profe = CATEDRATICOS[pid]

        with state_lock:
            cam_teacher_state[cam_id] = {
                "matched": True,
                "nombre": profe["nombre"],
                "sede": profe["sede"],
                "jornada": profe["jornada"],
                "horario": profe["horario"],
                "cursos": profe["cursos"],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }


# =========================
# CAMERA LOOP
# =========================
def camera_loop(cam_id, source):
    if not KNOWN_ENCODINGS:
        return

    cap = cv2.VideoCapture(source)

    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        frame_count += 1

        if frame_count % RECOGNIZE_EVERY_N_FRAMES == 0:
            small = cv2.resize(frame, (0, 0), fx=SCALE, fy=SCALE)
            rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

            locations = face_recognition.face_locations(rgb, model=DETECT_MODEL)
            encodings = face_recognition.face_encodings(rgb, locations, model=ENCODING_MODEL)

            for face_enc in encodings:
                distances = face_recognition.face_distance(KNOWN_ENCODINGS, face_enc)
                best_idx = int(np.argmin(distances))
                best_dist = float(distances[best_idx])

                if best_dist <= TOLERANCE:
                    person = KNOWN_PEOPLE[best_idx]
                    pid = person["id_persona"]

                    horarios = get_horarios_by_persona(pid)

                    with state_lock:
                        cam_state[cam_id]['latest_match'] = {
                            "matched": True,
                            "id_persona": pid,
                            "nombre": person["nombre"],
                            "apellido": person["apellido"],
                            "carnet": person["carnet"],
                            "correo": person["correo"],
                            "dist": round(best_dist, 4),
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "cam_id": cam_id,
                            "horarios": horarios
                        }

                    # 🔥 PROFESOR
                    update_teacher_state(cam_id, pid)


# =========================
# ROUTES
# =========================
def register_reconocimiento_routes(app):

    @app.route('/video_feed/<cam_id>')
    def video_feed(cam_id):
        return Response("stream", mimetype="multipart/x-mixed-replace")

    @app.route('/last_match/<cam_id>')
    def last_match(cam_id):
        with state_lock:
            return jsonify(cam_state.get(cam_id, {}))

    # 🔥 PROFESOR ENDPOINT
    @app.route('/last_teacher_match/<cam_id>')
    def last_teacher_match(cam_id):
        with state_lock:
            return jsonify(cam_teacher_state.get(cam_id, {
                "matched": False,
                "nombre": None,
                "sede": None,
                "jornada": None,
                "horario": None,
                "cursos": []
            }))

    @app.route('/monitor/<cam_id>')
    def monitor(cam_id):
        usuario = obtener_usuario_sesion()
        return render_template("monitor.html", cam_id=cam_id, usuario=usuario)


# =========================
# START THREADS
# =========================
def start_camera_threads():
    for cam_id, cam in CAMERAS.items():
        t = threading.Thread(
            target=camera_loop,
            args=(cam_id, cam["source"]),
            daemon=True
        )
        t.start()


# =========================
# LOAD CAMERAS
# =========================
def load_cameras_from_db():
    global CAMERAS

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT cam_id, source FROM camaras")
    rows = cur.fetchall()

    CAMERAS = {r["cam_id"]: r for r in rows}

    cur.close()
    conn.close()
