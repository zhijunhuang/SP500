import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Support DATABASE_URL environment variable override
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Fallback to config/db.py values
    from ..config.db import dbname, host, port, user, password
    DATABASE_URL = f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{dbname}?charset=utf8mb4"


class Base(DeclarativeBase):
    pass


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    # 延迟导入 models，避免循环引用
    from .. import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

