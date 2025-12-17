"""
Database Base Configuration
SQLAlchemy setup and session management
"""

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from ..config import database

# Create engine
engine = create_engine(
    database.DATABASE_URL,
    echo=database.ECHO_SQL,
    connect_args={"check_same_thread": False} if "sqlite" in database.DATABASE_URL else {},
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


@contextmanager
def get_db():
    """Context manager for database sessions"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """Initialize all database tables"""
    Base.metadata.create_all(bind=engine)
