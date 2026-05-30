import base64
import json
import os
import re
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage

import qrcode
from database import get_db_connection
from fpdf import FPDF
from flask import current_app


def _decode_dataurl_image(dataurl: str):
    if not dataurl:
        return None
    dataurl = dataurl.strip()
    m = re.match(r"data:image/[^;]+;base64,(.*)", dataurl)
    if m:
        dataurl = m.group(1)
    return base64.b64decode(dataurl)


def generate_id_card_pdf(nombre, apellido, correo, foto_bytes, carnet, id_persona, seccion="-", firma_base64=None):
    conn = None
    cursor = None
    foto_path = None
    qr_path = None
    firma_img_path = None
    try:
        year = datetime.now().year
        CARD_W = 85.6
        CARD_H = 54.0
        pdf = FPDF(orientation="L", unit="mm", format=(CARD_H, CARD_W))
        pdf.add_page()
        pdf.set_auto_page_break(False)
        pdf.set_fill_color(255, 255, 255)
        pdf.rect(0, 0, CARD_W, CARD_H, "F")

        logo_path = os.path.join("static", "img", "logo.png")
        if os.path.exists(logo_path):
            pdf.image(logo_path, x=3.6, y=0.75, w=13.2, h=13.2)

        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Times", "B", 16)
        pdf.text(19.5, 5.5, "UNIVERSIDAD")
        pdf.text(19.5, 12.5, "MARIANO GÁLVEZ")
        pdf.set_font("Times", "B", 13)
        pdf.text(67.0, 19.5, str(year))

        foto_path = os.path.join("static", f"temp_foto_{id_persona}.png")
        with open(foto_path, "wb") as f:
            f.write(foto_bytes)
        pdf.image(foto_path, x=4.5, y=16.2, w=23.4, h=25.3)

        pdf.set_font("Times", "B", 11)
        pdf.text(32.4, 20.5, nombre)
        pdf.text(32.4, 24.5, apellido)

        pdf.set_font("Helvetica", "", 8)
        pdf.text(32.4, 29, "Carnet")
        pdf.text(32.4, 32, carnet)

        pdf.text(32.4, 36, "Sección")
        pdf.text(32.4, 39, str (seccion))

        firma_bytes = _decode_dataurl_image(firma_base64)
        if not firma_bytes:
            try:
                conn = get_db_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT firma FROM personas WHERE id_persona=%s", (id_persona,))
                row = cursor.fetchone()
                if row and row.get("firma"):
                    firma_bytes = _decode_dataurl_image(row["firma"])
            except Exception:
                pass

        if firma_bytes:
            firma_img_path = os.path.join("static", f"temp_firma_{id_persona}.png")
            with open(firma_img_path, "wb") as f:
                f.write(firma_bytes)
            pdf.image(firma_img_path, x=33.7, y=36.5, w=27.3, h=6.3)
            pdf.text(38.7, 46.5, "Firma")

        qr_data = f"CARNET:{carnet};NOMBRE:{nombre} {apellido}"
        qr_img = qrcode.make(qr_data)
        qr_path = os.path.join("static", f"temp_qr_{id_persona}.png")
        qr_img.save(qr_path)
        pdf.image(qr_path, x=63.6, y=21.5, w=16.5, h=16.5)

        return pdf.output(dest="S").encode("latin1")
    except Exception as e:
        print("Error generando PDF:", e)
        return None
    finally:
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except Exception:
            pass
        for p in (foto_path, qr_path, firma_img_path):
            try:
                if p and os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass


def send_email_with_pdf(to_email, pdf_bytes, filename, subject="Tu carnet institucional"):
    smtp_server = current_app.config.get("SMTP_SERVER") or os.getenv("SMTP_SERVER")
    smtp_port = current_app.config.get("SMTP_PORT") or os.getenv("SMTP_PORT") or "587"
    try:
        smtp_port = int(smtp_port)
    except Exception:
        smtp_port = 587
    smtp_user = current_app.config.get("SMTP_USER") or os.getenv("SMTP_USER")
    smtp_pass = current_app.config.get("SMTP_PASSWORD") or os.getenv("SMTP_PASSWORD")
    sender_email = current_app.config.get("SENDER_EMAIL") or os.getenv("SENDER_EMAIL")
    use_tls_raw = current_app.config.get("SMTP_USE_TLS") or os.getenv("SMTP_USE_TLS", "true")
    use_tls = str(use_tls_raw).lower() == "true"
    missing = []
    if not smtp_server:
        missing.append("SMTP_SERVER")
    if not smtp_user:
        missing.append("SMTP_USER")
    if not smtp_pass:
        missing.append("SMTP_PASSWORD")
    if not sender_email:
        missing.append("SENDER_EMAIL")
    if missing:
        err = "Faltan variables SMTP: " + ", ".join(missing)
        print(err)
        return (False, err)
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = to_email
    msg.set_content("Adjunto encontrarás tu carnet institucional en formato PDF.")
    msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename=filename)
    context = ssl.create_default_context()
    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=15) as server:
            if use_tls:
                server.starttls(context=context)
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return (True, None)
    except Exception as e:
        err = f"Error enviando correo con PDF: {e}"
        print(err)
        return (False, err)


def generar_pdf_asistencia(curso, docente, estudiantes, fecha_hoy):
    carpeta_reportes = os.path.join("static", "reportes")
    os.makedirs(carpeta_reportes, exist_ok=True)

    nombre_archivo = f"asistencia_curso_{curso['id_curso']}_{fecha_hoy}.pdf"
    ruta_pdf = os.path.join(carpeta_reportes, nombre_archivo)

    total = len(estudiantes)
    presentes = sum(1 for e in estudiantes if e["presente"])
    ausentes = total - presentes

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    logo_path = os.path.join("static", "img", "logo.png")
    if os.path.exists(logo_path):
        pdf.image(logo_path, 10, 10, 25)

    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "UNIVERSIDAD MARIANO GALVEZ", ln=True, align="C")
    pdf.cell(0, 10, "DE GUATEMALA", ln=True, align="C")
    pdf.set_font("Times", "", 13)
    pdf.cell(0, 8, "REPORTE FINAL DE ASISTENCIA", ln=True, align="C")
    pdf.ln(12)

    pdf.set_font("Arial", "B", 10)
    pdf.cell(35, 8, "Curso:")
    pdf.set_font("Arial", "", 10)
    pdf.cell(75, 8, str(curso.get("nombre_curso", "-")))

    pdf.set_font("Arial", "B", 10)
    pdf.cell(25, 8, "Carrera:")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 8, str(curso.get("carrera", "-")), ln=True)

    pdf.set_font("Arial", "B", 10)
    pdf.cell(35, 8, "Seccion:")
    pdf.set_font("Arial", "", 10)
    pdf.cell(75, 8, str(curso.get("seccion", "-")))

    pdf.set_font("Arial", "B", 10)
    pdf.cell(25, 8, "Fecha:")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 8, str(fecha_hoy), ln=True)

    pdf.set_font("Arial", "B", 10)
    pdf.cell(35, 8, "Catedratico:")
    pdf.set_font("Arial", "", 10)
    pdf.cell(75, 8, f"{docente.get('nombre', '')} {docente.get('apellido', '')}")

    pdf.set_font("Arial", "B", 10)
    pdf.cell(25, 8, "Correo:")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 8, str(docente.get("correo", "-")), ln=True)

    pdf.set_font("Arial", "B", 10)
    pdf.cell(35, 8, "Sede:")
    pdf.set_font("Arial", "", 10)
    pdf.cell(75, 8, str(curso.get("sede", "-")))

    pdf.set_font("Arial", "B", 10)
    pdf.cell(25, 8, "Salon:")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 8, str(curso.get("salon", "-")), ln=True)

    pdf.set_font("Arial", "B", 10)
    pdf.cell(35, 8, "Jornada:")
    pdf.set_font("Arial", "", 10)
    pdf.cell(75, 8, str(curso.get("jornada", "-")))

    pdf.set_font("Arial", "B", 10)
    pdf.cell(25, 8, "Horario:")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 8, str(curso.get("horario", "-")), ln=True)

    pdf.ln(8)

    pdf.set_font("Arial", "B", 10)
    pdf.cell(63, 8, "Total estudiantes", 1, 0, "C")
    pdf.cell(63, 8, "Presentes", 1, 0, "C")
    pdf.cell(63, 8, "Ausentes", 1, 1, "C")

    pdf.set_font("Arial", "", 10)
    pdf.cell(63, 8, str(total), 1, 0, "C")
    pdf.cell(63, 8, str(presentes), 1, 0, "C")
    pdf.cell(63, 8, str(ausentes), 1, 1, "C")

    pdf.ln(10)

    pdf.set_fill_color(52, 73, 94)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(10, 10, "No", 1, 0, "C", True)
    pdf.cell(30, 10, "Carnet", 1, 0, "C", True)
    pdf.cell(55, 10, "Nombre", 1, 0, "C", True)
    pdf.cell(60, 10, "Correo", 1, 0, "C", True)
    pdf.cell(35, 10, "Estado", 1, 1, "C", True)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "", 9)

    for i, est in enumerate(estudiantes, start=1):
        estado = "PRESENTE" if est["presente"] else "AUSENTE"
        nombre = str(est.get("nombre_completo", "-"))[:28]
        correo = str(est.get("correo", "-"))[:32] if est.get("correo") else ""

        pdf.cell(10, 10, str(i), 1, 0, "C")
        pdf.cell(30, 10, str(est.get("carnet", "-")), 1, 0, "C")
        pdf.cell(55, 10, nombre, 1, 0, "L")
        pdf.cell(60, 10, correo, 1, 0, "L")
        pdf.cell(35, 10, estado, 1, 1, "C")

    pdf.output(ruta_pdf)
    return ruta_pdf, nombre_archivo


def enviar_pdf_por_correo(destinatario, ruta_pdf, curso):
    remitente = "16mynorgomez@gmail.com"
    password = "yuef jvmk gisp trtb"

    msg = EmailMessage()
    msg["Subject"] = f"Reporte de asistencia - {curso['nombre_curso']}"
    msg["From"] = remitente
    msg["To"] = destinatario
    msg.set_content(
        f"Adjunto se envia el reporte oficial de asistencia del curso {curso['nombre_curso']}."
    )

    with open(ruta_pdf, "rb") as f:
        pdf_data = f.read()

    msg.add_attachment(
        pdf_data,
        maintype="application",
        subtype="pdf",
        filename=os.path.basename(ruta_pdf)
    )

    contexto = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=contexto) as smtp:
        smtp.login(remitente, password)
        smtp.send_message(msg)
