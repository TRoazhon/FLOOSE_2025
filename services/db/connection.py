"""
Database Connection Management
SQLAlchemy engine and session configuration
"""

import os
import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from sqlalchemy.pool import QueuePool

from .models import Base, create_all_tables

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Centralized database connection manager.
    Supports PostgreSQL (primary) and SQLite (fallback for development).
    """

    _instance = None
    _engine = None
    _session_factory = None
    _scoped_session = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._engine is not None:
            return  # Already initialized

        self._initialize()

    def _initialize(self):
        """Initialize database connection based on environment"""
        database_url = self._get_database_url()

        # Engine configuration
        engine_kwargs = {
            'echo': os.environ.get('SQL_ECHO', 'false').lower() == 'true',
            'pool_pre_ping': True,  # Verify connections before use
        }

        # PostgreSQL-specific settings
        if database_url.startswith('postgresql'):
            engine_kwargs.update({
                'poolclass': QueuePool,
                'pool_size': int(os.environ.get('DB_POOL_SIZE', 5)),
                'max_overflow': int(os.environ.get('DB_MAX_OVERFLOW', 10)),
                'pool_timeout': int(os.environ.get('DB_POOL_TIMEOUT', 30)),
                'pool_recycle': int(os.environ.get('DB_POOL_RECYCLE', 1800)),
            })
        # SQLite settings
        elif database_url.startswith('sqlite'):
            engine_kwargs['connect_args'] = {'check_same_thread': False}

        self._engine = create_engine(database_url, **engine_kwargs)

        # Enable foreign keys for SQLite
        if database_url.startswith('sqlite'):
            @event.listens_for(self._engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        # Session factory
        self._session_factory = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False
        )

        # Scoped session for thread safety
        self._scoped_session = scoped_session(self._session_factory)

        logger.info(f"Database initialized: {self._mask_url(database_url)}")

    def _get_database_url(self) -> str:
        """Get database URL from environment or use default"""
        # Check for explicit DATABASE_URL
        url = os.environ.get('DATABASE_URL')
        if url:
            # Handle Heroku-style postgres:// URLs
            if url.startswith('postgres://'):
                url = url.replace('postgres://', 'postgresql://', 1)
            return url

        # Build URL from components
        db_type = os.environ.get('DB_TYPE', 'sqlite')

        if db_type == 'postgresql':
            host = os.environ.get('DB_HOST', 'localhost')
            port = os.environ.get('DB_PORT', '5432')
            name = os.environ.get('DB_NAME', 'floose')
            user = os.environ.get('DB_USER', 'floose')
            password = os.environ.get('DB_PASSWORD', '')

            if password:
                return f"postgresql://{user}:{password}@{host}:{port}/{name}"
            return f"postgresql://{user}@{host}:{port}/{name}"

        # Default: SQLite for development
        data_dir = os.environ.get('DATA_DIR', 'data')
        os.makedirs(data_dir, exist_ok=True)
        return f"sqlite:///{data_dir}/floose.db"

    def _mask_url(self, url: str) -> str:
        """Mask password in URL for logging"""
        if '@' in url and ':' in url.split('@')[0]:
            parts = url.split('@')
            credentials = parts[0].split(':')
            if len(credentials) >= 3:
                credentials[2] = '****'
            return ':'.join(credentials) + '@' + parts[1]
        return url

    @property
    def engine(self):
        """Get SQLAlchemy engine"""
        return self._engine

    def get_session(self) -> Session:
        """Get a new session (caller responsible for closing)"""
        return self._session_factory()

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions.
        Handles commit/rollback and cleanup automatically.

        Usage:
            with db.session_scope() as session:
                session.add(obj)
        """
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()

    def create_tables(self):
        """Create all tables defined in models"""
        create_all_tables(self._engine)
        logger.info("Database tables created")

    def execute_raw(self, sql: str, params: dict = None):
        """Execute raw SQL (use with caution)"""
        with self._engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            conn.commit()
            return result

    def health_check(self) -> bool:
        """Check database connectivity"""
        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    def get_stats(self) -> dict:
        """Get database statistics"""
        stats = {
            'pool_size': self._engine.pool.size() if hasattr(self._engine.pool, 'size') else 'N/A',
            'checked_out': self._engine.pool.checkedout() if hasattr(self._engine.pool, 'checkedout') else 'N/A',
            'overflow': self._engine.pool.overflow() if hasattr(self._engine.pool, 'overflow') else 'N/A',
        }

        # Get table counts
        with self.session_scope() as session:
            from .models import User, Project, Expense, BankAccount, Category, Dashboard, Widget

            stats['tables'] = {
                'users': session.query(User).count(),
                'projects': session.query(Project).count(),
                'expenses': session.query(Expense).count(),
                'accounts': session.query(BankAccount).count(),
                'categories': session.query(Category).count(),
                'dashboards': session.query(Dashboard).count(),
                'widgets': session.query(Widget).count(),
            }

        return stats

    def close(self):
        """Close all connections"""
        if self._scoped_session:
            self._scoped_session.remove()
        if self._engine:
            self._engine.dispose()
            logger.info("Database connections closed")


# Global instance
_db_manager: DatabaseManager = None


def get_db() -> DatabaseManager:
    """Get the global DatabaseManager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def init_db():
    """Initialize database and create tables"""
    db = get_db()
    db.create_tables()
    return db
