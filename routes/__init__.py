"""Rutas modulares para la aplicación de biometría."""

from .admin_routes import register_admin_routes
from .auth_routes import register_auth_routes
from .api_routes import register_api_routes
from .cursos_routes import register_cursos_routes
from .docente_routes import register_docente_routes
from .registro_routes import register_registro_routes
from .reconocimiento import register_reconocimiento_routes


def register_routes(app):
    register_auth_routes(app)
    register_admin_routes(app)
    register_api_routes(app)
    register_registro_routes(app)
    register_cursos_routes(app)
    register_docente_routes(app)
    register_reconocimiento_routes(app)
