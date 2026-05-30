import mysql.connector
from flask import current_app
from config import Config


def get_db_connection():
    config = current_app.config if current_app else None
    return mysql.connector.connect(
        host=(config.get("MYSQL_HOST") if config else Config.MYSQL_HOST) or "localhost",
        user=(config.get("MYSQL_USER") if config else Config.MYSQL_USER) or "root",
        password=(config.get("MYSQL_PASSWORD") if config else Config.MYSQL_PASSWORD) or "",
        database=(config.get("MYSQL_DATABASE") if config else Config.MYSQL_DATABASE) or ""
    )
