"""
Database Configuration
SQLAlchemy setup ve session yönetimi
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from typing import Generator

from app.core.config import settings


# SQLAlchemy Engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Connection health check
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG  # SQL logları (debug modda)
)

# Session Factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency.
    FastAPI dependency injection için kullanılır.

    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Database tablolarını oluşturur.
    Development için kullanılır, production'da alembic kullan.
    """
    Base.metadata.create_all(bind=engine)
