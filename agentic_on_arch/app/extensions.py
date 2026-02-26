"""Extension initialization — DB engine, session factory.

Engine is created lazily to avoid connection errors when PostgreSQL is not available.
This allows the app to start and serve LLM-only endpoints without a database.
"""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings
from app.utils.logger import logger

_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        try:
            _engine = create_async_engine(
                settings.DATABASE_URL,
                echo=settings.DEBUG,
                pool_size=10,
                max_overflow=20,
            )
            logger.info("Database engine created")
        except Exception as e:
            logger.warning(f"Database engine creation failed: {e}")
            raise
    return _engine


def get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


# Keep backward compat — but lazy now
class _LazySessionFactory:
    def __call__(self):
        return get_session_factory()()

async_session_factory = _LazySessionFactory()
