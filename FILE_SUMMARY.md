# Resumen de archivos del proyecto

Este documento describe la responsabilidad principal de cada archivo y módulo del proyecto sin incluir fragmentos de código.

## Archivos principales

- `app.py`
  - Punto de entrada actual de la aplicación Flask.
  - Crea la instancia de la aplicación, carga la configuración y registra los módulos de rutas.
  - Inicia los hilos de cámara para el reconocimiento facial.

- `app_legacy.py`
  - Versión monolítica antigua de la aplicación.
  - Conserva toda la lógica original centralizada para referencia o respaldo.

- `config.py`
  - Define la configuración general de la aplicación y las variables de entorno.
  - Centraliza datos como conexión a base de datos y ajustes de Flask.

- `database.py`
  - Contiene el helper para crear conexiones a la base de datos MySQL.
  - Abstrae la lógica de conexión para usarla desde cualquier módulo.

- `pdf_utils.py`
  - Gestiona la generación de documentos PDF, como carnés y reportes de asistencia.
  - Incluye utilidades para crear archivos y enviar correos con adjuntos.

- `requirements.txt`
  - Lista las dependencias del proyecto necesarias para instalar el entorno.

- `hash.py`
  - Archivo auxiliar para funciones de hashing, si se utiliza en la aplicación.

## Paquete de helpers

- `helpers/__init__.py`
  - Exposición unificada de los helpers disponibles en el paquete.
  - Permite importar funciones de forma centralizada.

- `helpers/campus_helpers.py`
  - Contiene funciones relacionadas con carreras, sedes, secciones y cursos.
  - Incluye validaciones y consultas de datos académicos usados en el sistema.

- `helpers/user_helpers.py`
  - Contiene funciones relacionadas con el usuario y la sesión.
  - Gestiona la información del usuario conectado y genera carnés únicos.

## Paquete de rutas

- `routes/__init__.py`
  - Centraliza el registro de todas las rutas en la aplicación.
  - Permite una importación única para ensamblar la aplicación.

- `routes/auth_routes.py`
  - Maneja las rutas de inicio de sesión, cierre de sesión y redirección inicial.
  - Controla la autenticación básica de usuarios.

- `routes/admin_routes.py`
  - Implementa funcionalidades administrativas.
  - Administra datos de personas, roles, promociones y vistas de panel.

- `routes/api_routes.py`
  - Ofrece endpoints destinados a consultas AJAX y APIs internas.
  - Devuelve listas de secciones, carreras y cursos para los formularios.

- `routes/registro_routes.py`
  - Encapsula la lógica de registro de personas y captura de rostros.
  - Realiza validaciones de datos, guarda fotos y crea encodings faciales.

- `routes/cursos_routes.py`
  - Gestiona la creación y listado de cursos.
  - Maneja la asignación de cursos a catedráticos y filtros por sede/carrera.

- `routes/docente_routes.py`
  - Contiene las rutas específicas para el rol de catedrático.
  - Muestra cursos asignados, asistencia y descarga de reportes.

- `routes/reconocimiento.py`
  - Administra el reconocimiento facial por cámara.
  - Proporciona streaming MJPEG, estado de cámaras y registro de entradas.

## Otras carpetas relevantes

- `backup/`
  - Carpeta de respaldo donde se pueden guardar versiones anteriores o archivos temporales.

- `static/`
  - Contiene los recursos estáticos de la aplicación, como imágenes, estilos y scripts.

- `templates/`
  - Contiene las plantillas HTML usadas por Flask para renderizar las páginas.
