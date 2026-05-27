"""Rutas para dashboard de estudiante"""

from flask import render_template, request, redirect, url_for, session, flash
from datetime import date
import models
from helpers import obtener_usuario_sesion
from database import get_db_connection


def register_student_routes(app):
    """Registra rutas para estudiantes"""
    
    @app.route('/estudiante')
    def dashboard_estudiante():
        """Dashboard principal del estudiante"""
        if session.get('rol') != 'estudiante':
            return redirect(url_for('login'))
        
        usuario = obtener_usuario_sesion()
        if not usuario:
            flash('Debe iniciar sesión', 'danger')
            return redirect(url_for('login'))
        
        id_persona = usuario['id_persona']
        
        # Obtener cursos en los que está inscrito
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT DISTINCT 
                c.id_curso,
                c.nombre as curso,
                ca.nombre as carrera,
                s.nombre as seccion,
                rp.id_rol_persona
            FROM cursos c
            JOIN asignacion_cursos ac ON c.id_curso = ac.id_curso
            JOIN roles_persona rp ON ac.id_rol_persona = rp.id_rol_persona
            JOIN roles r ON rp.id_rol = r.id_rol
            JOIN secciones s ON ac.id_seccion = s.id_seccion
            JOIN sede_carrera sc ON c.id_sede_carrera = sc.id_sede_carrera
            JOIN carreras ca ON sc.id_carrera = ca.id_carrera
            WHERE rp.id_persona = %s
            AND r.nombre = 'estudiante'
            ORDER BY c.nombre
        """, (id_persona,))
        
        cursos = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return render_template(
            'estudiante/dashboard.html',
            usuario=usuario,
            cursos=cursos
        )
    
    @app.route('/estudiante/horarios')
    def estudiante_horarios():
        """Ver horarios del estudiante"""
        if session.get('rol') != 'estudiante':
            return redirect(url_for('login'))
        
        usuario = obtener_usuario_sesion()
        if not usuario:
            flash('Debe iniciar sesión', 'danger')
            return redirect(url_for('login'))
        
        horarios = models.get_horarios_by_persona(usuario['id_persona'])
        
        # Organizar por día
        dias_semana = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado']
        horarios_organizados = {dia: [] for dia in dias_semana}
        
        for h in horarios:
            dia = h['dia_semana'].lower()
            if dia in horarios_organizados:
                horarios_organizados[dia].append(h)
        
        # Ordenar por hora
        for dia in horarios_organizados:
            horarios_organizados[dia].sort(key=lambda x: x['hora_inicio'])
        
        return render_template(
            'estudiante/horarios.html',
            usuario=usuario,
            horarios_organizados=horarios_organizados,
            dias_semana=dias_semana
        )
    
    @app.route('/estudiante/asistencia')
    def estudiante_asistencia():
        """Ver asistencia del estudiante"""
        if session.get('rol') != 'estudiante':
            return redirect(url_for('login'))
        
        usuario = obtener_usuario_sesion()
        if not usuario:
            flash('Debe iniciar sesión', 'danger')
            return redirect(url_for('login'))
        
        id_persona = usuario['id_persona']
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener cursos del estudiante
        cursor.execute("""
            SELECT DISTINCT 
                c.id_curso,
                c.nombre as curso,
                ca.nombre as carrera,
                s.nombre as seccion,
                i.id_inscripcion
            FROM cursos c
            JOIN asignacion_cursos ac ON c.id_curso = ac.id_curso
            JOIN inscripciones i ON ac.id_asignacion = i.id_asignacion
            JOIN roles_persona rp ON i.id_rol_persona = rp.id_rol_persona
            JOIN roles r ON rp.id_rol = r.id_rol
            JOIN secciones s ON ac.id_seccion = s.id_seccion
            JOIN sede_carrera sc ON c.id_sede_carrera = sc.id_sede_carrera
            JOIN carreras ca ON sc.id_carrera = ca.id_carrera
            WHERE rp.id_persona = %s
            AND r.nombre = 'estudiante'
            ORDER BY c.nombre
        """, (id_persona,))
        
        cursos = cursor.fetchall()
        
        # Para cada curso, obtener asistencias
        for curso in cursos:
            cursor.execute("""
                SELECT a.*, 
                    CASE WHEN a.estado = 'presente' THEN 'Presente'
                         WHEN a.estado = 'ausente' THEN 'Ausente'
                         WHEN a.estado = 'tarde' THEN 'Tarde'
                    END as estado_label
                FROM asistencias a
                WHERE a.id_inscripcion = %s
                ORDER BY a.fecha DESC
            """, (curso['id_inscripcion'],))
            
            curso['asistencias'] = cursor.fetchall()
            
            # Calcular estadísticas
            total = len(curso['asistencias'])
            if total > 0:
                presentes = sum(1 for a in curso['asistencias'] if a['estado'] == 'presente')
                ausentes = sum(1 for a in curso['asistencias'] if a['estado'] == 'ausente')
                tardes = sum(1 for a in curso['asistencias'] if a['estado'] == 'tarde')
                
                curso['stats'] = {
                    'total': total,
                    'presentes': presentes,
                    'ausentes': ausentes,
                    'tardes': tardes,
                    'porcentaje': round((presentes / total * 100), 2)
                }
            else:
                curso['stats'] = {'total': 0, 'presentes': 0, 'ausentes': 0, 'tardes': 0, 'porcentaje': 0}
        
        cursor.close()
        conn.close()
        
        return render_template(
            'estudiante/asistencia.html',
            usuario=usuario,
            cursos=cursos
        )
    
    @app.route('/estudiante/curso/<int:id_curso>/detalle')
    def estudiante_curso_detalle(id_curso):
        """Detalles de un curso para el estudiante"""
        if session.get('rol') != 'estudiante':
            return redirect(url_for('login'))
        
        usuario = obtener_usuario_sesion()
        if not usuario:
            flash('Debe iniciar sesión', 'danger')
            return redirect(url_for('login'))
        
        curso = models.get_curso_by_id(id_curso)
        if not curso:
            flash('Curso no encontrado', 'warning')
            return redirect(url_for('dashboard_estudiante'))
        
        # Obtener horarios del curso
        horarios = models.get_horarios_by_curso(id_curso)
        
        # Obtener asistencia del estudiante en este curso
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT a.*, 
                CASE WHEN a.estado = 'presente' THEN 'Presente'
                     WHEN a.estado = 'ausente' THEN 'Ausente'
                     WHEN a.estado = 'tarde' THEN 'Tarde'
                END as estado_label
            FROM asistencias a
            JOIN inscripciones i ON a.id_inscripcion = i.id_inscripcion
            JOIN asignacion_cursos ac ON i.id_asignacion = ac.id_asignacion
            JOIN roles_persona rp ON i.id_rol_persona = rp.id_rol_persona
            WHERE ac.id_curso = %s
            AND rp.id_persona = %s
            ORDER BY a.fecha DESC
        """, (id_curso, usuario['id_persona']))
        
        asistencias = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Calcular estadísticas
        total = len(asistencias)
        if total > 0:
            presentes = sum(1 for a in asistencias if a['estado'] == 'presente')
            stats = {
                'total': total,
                'presentes': presentes,
                'ausentes': sum(1 for a in asistencias if a['estado'] == 'ausente'),
                'tardes': sum(1 for a in asistencias if a['estado'] == 'tarde'),
                'porcentaje': round((presentes / total * 100), 2)
            }
        else:
            stats = {'total': 0, 'presentes': 0, 'ausentes': 0, 'tardes': 0, 'porcentaje': 0}
        
        return render_template(
            'estudiante/curso_detalle.html',
            usuario=usuario,
            curso=curso,
            horarios=horarios,
            asistencias=asistencias,
            stats=stats
        )
