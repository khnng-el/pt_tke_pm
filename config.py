import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DEFAULT_SQLITE_PATH = os.path.join(BASE_DIR, "hotel_management.db")

load_dotenv(os.path.join(BASE_DIR, ".env"))

# Cấu hình DB linh hoạt:
# - Ưu tiên DATABASE_URL nếu có
# - Nếu DB_BACKEND=mysql thì dùng biến môi trường MySQL
# - Mặc định dùng MySQL, chỉ fallback sang SQLite khi bạn đặt DB_BACKEND=sqlite
# - DB_AUTO_CREATE=0 để app chỉ đọc schema/data đã có, không tự tạo bảng
DB_BACKEND = os.getenv("DB_BACKEND", "mysql").strip().lower()
DATABASE_URL = os.getenv("DATABASE_URL")
DB_AUTO_CREATE = os.getenv("DB_AUTO_CREATE", "0").strip().lower() in ("1", "true", "yes")

MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DB = os.getenv("MYSQL_DB", "hotel_management")


def _build_database_uri() -> str:
    if DATABASE_URL:
        return DATABASE_URL

    if DB_BACKEND == "mysql":
        credentials = MYSQL_USER
        if MYSQL_PASSWORD:
            credentials = f"{credentials}:{MYSQL_PASSWORD}"
        return (
            f"mysql+pymysql://{credentials}@{MYSQL_HOST}:{MYSQL_PORT}/"
            f"{MYSQL_DB}?charset=utf8mb4"
        )

    return f"sqlite:///{DEFAULT_SQLITE_PATH}"


DATABASE_URI = _build_database_uri()
USE_SQLITE = DATABASE_URI.startswith("sqlite")

engine_kwargs = {"echo": False, "future": True}
if USE_SQLITE:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_recycle"] = 3600

engine = create_engine(DATABASE_URI, **engine_kwargs)

db_session = scoped_session(
    sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
)

Base = declarative_base()
Base.query = db_session.query_property()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = DATABASE_URI
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = 604800


def init_db():
    if DB_AUTO_CREATE:
        Base.metadata.create_all(bind=engine)


def get_db():
    return db_session


__all__ = [
    "DATABASE_URI",
    "DB_BACKEND",
    "DB_AUTO_CREATE",
    "USE_SQLITE",
    "Base",
    "engine",
    "get_db",
    "init_db",
]
