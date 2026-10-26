import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-this-secret-key")
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "0").lower() in {"1", "true", "yes"}
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = (
        "mysql+pymysql://"
        f"{quote_plus(os.getenv('MYSQL_USER', 'attendance_app'))}:"
        f"{quote_plus(os.getenv('MYSQL_PASSWORD', ''))}@"
        f"{os.getenv('MYSQL_HOST', '127.0.0.1')}:"
        f"{os.getenv('MYSQL_PORT', '3306')}/"
        f"{quote_plus(os.getenv('MYSQL_DATABASE', 'pazo_attendance'))}"
        "?charset=utf8mb4"
    )
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
        "pool_size": 5,
        "max_overflow": 10,
    }
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0").lower() in {"1", "true", "yes"}
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    WTF_CSRF_TIME_LIMIT = 3600
