"""Rutas para gestión de personas y usuarios - CRUD Completo"""

from flask import render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date
import models
from helpers import obtener_usuario_sesion, get_carrera_options, get_sede_options


def register_personas_crud_routes(app):
    """Registra rutas CRUD para gestión de personas"""
    
    # ==================== PERSONAS ====================
    
    @app.route('/admin/personas')
    def personas_list():
        """Lista de todas las personas"""
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))
        
        usuario = obtener_usuario_sesion()
        search = request.args.get('search', '').strip()
        estado = request.args.get('estado', 'activo')
        
        filters = {'estado': estado}
        if search:
            filters['search'] = search
        
        personas = models.get_all_personas(filters)
        
        # Enriquecer cada persona con sus roles
        for p in personas:
            p_detail = models.get_persona_with_roles(p['id_persona'])
            if p_detail:
                p['roles'] = p_detail.get('roles', [])
        
        return render_template(
            'admin/personas_list.html',
            personas=personas,
            usuario=usuario,
            search=search,
            estado=estado
        )
    
    @app.route('/admin/personas/<int:id_persona>')
    def persona_detail(id_persona):
        """Detalles de una persona"""
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))
        
        usuario = obtener_usuario_sesion()
        persona = models.get_persona_with_roles(id_persona)
        
        if not persona:
            flash('Persona no encontrada', 'warning')
            return redirect(url_for('personas_list'))
        
        # Obtener usuario asociado
        from database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT u.id_usuario, u.username, u.ultimo_login
            FROM usuarios u
            WHERE u.id_persona = %s
        """, (id_persona,))
        user_account = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return render_template(
            'admin/persona_detail.html',
            persona=persona,
            user_account=user_account,
            usuario=usuario,
            roles_list=models.get_all_roles(),
            sedes=models.get_all_sedes()
        )
    
    @app.route('/admin/personas/<int:id_persona>/edit', methods=['GET', 'POST'])
    def persona_edit(id_persona):
        """Editar datos de una persona"""
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))
        
        persona = models.get_persona_by_id(id_persona)
        if not persona:
            flash('Persona no encontrada', 'warning')
            return redirect(url_for('personas_list'))
        
        if request.method == 'POST':
            try:
                nombre = request.form.get('nombre', '').strip()
                apellido = request.form.get('apellido', '').strip()
                telefono = request.form.get('telefono', '').strip()
                correo_personal = request.form.get('correo_personal', '').strip()
                correo_institucional = request.form.get('correo_institucional', '').strip()
                dpi = request.form.get('dpi', '').strip()
                estado = request.form.get('estado', 'activo')
                
                if not nombre or not apellido:
                    flash('Nombre y apellido son obligatorios', 'warning')
                    return redirect(url_for('persona_edit', id_persona=id_persona))
                
                models.update_persona(
                    id_persona,
                    nombre=nombre,
                    apellido=apellido,
                    telefono=telefono,
                    correo_personal=correo_personal,
                    correo_institucional=correo_institucional,
                    dpi=dpi,
                    estado=estado
                )
                
                flash('Persona actualizada exitosamente', 'success')
                return redirect(url_for('persona_detail', id_persona=id_persona))
            except Exception as e:
                flash(f'Error actualizando persona: {str(e)}', 'danger')
                return redirect(url_for('persona_edit', id_persona=id_persona))
        
        usuario = obtener_usuario_sesion()
        return render_template(
            'admin/persona_edit.html',
            persona=persona,
            usuario=usuario
        )
    
    @app.route('/admin/personas/<int:id_persona>/delete', methods=['POST'])
    def persona_delete(id_persona):
        """Eliminar una persona"""
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))
        
        try:
            models.delete_persona(id_persona)
            flash('Persona eliminada exitosamente', 'success')
        except Exception as e:
            flash(f'Error eliminando persona: {str(e)}', 'danger')
        
        return redirect(url_for('personas_list'))
    
    @app.route('/admin/personas/<int:id_persona>/role/add', methods=['POST'])
    def persona_add_role(id_persona):
        """Agregar rol a una persona"""
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))
        
        try:
            id_rol = request.form.get('id_rol')
            if not id_rol:
                flash('Debe seleccionar un rol', 'warning')
                return redirect(url_for('persona_detail', id_persona=id_persona))
            
            models.assign_role_to_persona(id_persona, id_rol)
            flash('Rol asignado exitosamente', 'success')
        except Exception as e:
            flash(f'Error asignando rol: {str(e)}', 'danger')
        
        return redirect(url_for('persona_detail', id_persona=id_persona))
    
    @app.route('/admin/personas/<int:id_persona>/role/<int:id_rol_persona>/remove', methods=['POST'])
    def persona_remove_role(id_persona, id_rol_persona):
        """Remover rol de una persona"""
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))
        
        try:
            models.remove_role_from_persona(id_rol_persona)
            flash('Rol removido exitosamente', 'success')
        except Exception as e:
            flash(f'Error removiendo rol: {str(e)}', 'danger')
        
        return redirect(url_for('persona_detail', id_persona=id_persona))
    
    # ==================== USUARIOS ====================
    
    @app.route('/admin/usuarios')
    def usuarios_list():
        """Lista de todos los usuarios"""
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))
        
        usuario = obtener_usuario_sesion()
        usuarios = models.get_all_usuarios()
        
        return render_template(
            'admin/usuarios_list.html',
            usuarios=usuarios,
            usuario=usuario
        )
    
    @app.route('/admin/usuarios/crear', methods=['GET', 'POST'])
    def usuario_create():
        """Crear nuevo usuario"""
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))
        
        if request.method == 'POST':
            try:
                id_persona = request.form.get('id_persona')
                username = request.form.get('username', '').strip()
                password = request.form.get('password', '').strip()
                
                if not all([id_persona, username, password]):
                    flash('Todos los campos son obligatorios', 'warning')
                    return redirect(url_for('usuario_create'))
                
                # Verificar que la persona exista
                persona = models.get_persona_by_id(id_persona)
                if not persona:
                    flash('Persona no encontrada', 'warning')
                    return redirect(url_for('usuario_create'))
                
                # Verificar que el username sea único
                existing = models.get_usuario_by_username(username)
                if existing:
                    flash('El username ya existe', 'warning')
                    return redirect(url_for('usuario_create'))
                
                models.create_usuario(id_persona, username, password)
                flash('Usuario creado exitosamente', 'success')
                return redirect(url_for('usuarios_list'))
            except Exception as e:
                flash(f'Error creando usuario: {str(e)}', 'danger')
                return redirect(url_for('usuario_create'))
        
        usuario = obtener_usuario_sesion()
        # Obtener personas sin usuario
        from database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT p.id_persona, p.nombre, p.apellido, p.carnet
            FROM personas p
            WHERE p.id_persona NOT IN (SELECT DISTINCT id_persona FROM usuarios)
            AND p.estado = 'activo'
            ORDER BY p.nombre, p.apellido
        """)
        personas_sin_usuario = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return render_template(
            'admin/usuario_create.html',
            usuario=usuario,
            personas_sin_usuario=personas_sin_usuario
        )
    
    @app.route('/admin/usuarios/<int:id_usuario>/cambiar-password', methods=['POST'])
    def usuario_change_password(id_usuario):
        """Cambiar contraseña de usuario"""
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))
        
        try:
            new_password = request.form.get('new_password', '').strip()
            
            if not new_password or len(new_password) < 4:
                flash('La contraseña debe tener al menos 4 caracteres', 'warning')
            else:
                models.update_usuario_password(id_usuario, new_password)
                flash('Contraseña actualizada exitosamente', 'success')
        except Exception as e:
            flash(f'Error actualizando contraseña: {str(e)}', 'danger')
        
        return redirect(url_for('usuarios_list'))
    
    # ==================== CURSOS ====================
    
    @app.route('/admin/cursos')
    def cursos_list():
        """Lista de todos los cursos"""
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))
        
        usuario = obtener_usuario_sesion()
        cursos = models.get_all_cursos()
        
        return render_template(
            'admin/cursos_list.html',
            cursos=cursos,
            usuario=usuario
        )
    
    @app.route('/admin/cursos/<int:id_curso>')
    def curso_detail(id_curso):
        """Detalles de un curso"""
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))
        
        usuario = obtener_usuario_sesion()
        curso = models.get_curso_by_id(id_curso)
        
        if not curso:
            flash('Curso no encontrado', 'warning')
            return redirect(url_for('cursos_list'))
        
        # Obtener asistencias
        asistencias = models.get_asistencias_by_curso(id_curso)
        stats = models.get_asistencia_stats_by_curso(id_curso)
        horarios = models.get_horarios_by_curso(id_curso)
        
        return render_template(
            'admin/curso_detail.html',
            curso=curso,
            asistencias=asistencias,
            stats=stats,
            horarios=horarios,
            usuario=usuario
        )
    
    # ==================== SALONES ====================
    
    @app.route('/admin/salones')
    def salones_list():
        """Lista de todos los salones"""
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))
        
        usuario = obtener_usuario_sesion()
        salones = models.get_all_salones()
        
        return render_template(
            'admin/salones_list.html',
            salones=salones,
            usuario=usuario,
            sedes=models.get_all_sedes()
        )
    
    @app.route('/admin/salones/crear', methods=['GET', 'POST'])
    def salon_create():
        """Crear nuevo salón"""
        if session.get('rol') != 'administrativo':
            return redirect(url_for('login'))
        
        if request.method == 'POST':
            try:
                nombre = request.form.get('nombre', '').strip()
                capacidad = request.form.get('capacidad', 40)
                id_sede = request.form.get('id_sede')
                
                if not nombre or not id_sede:
                    flash('Nombre y sede son obligatorios', 'warning')
                    return redirect(url_for('salon_create'))
                
                capacidad = int(capacidad) if capacidad else 40
                models.create_salon(nombre, capacidad, id_sede)
                flash('Salón creado exitosamente', 'success')
                return redirect(url_for('salones_list'))
            except Exception as e:
                flash(f'Error creando salón: {str(e)}', 'danger')
                return redirect(url_for('salon_create'))
        
        usuario = obtener_usuario_sesion()
        return render_template(
            'admin/salon_create.html',
            usuario=usuario,
            sedes=models.get_all_sedes()
        )
