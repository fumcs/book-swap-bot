import os
import logging
from urllib.parse import urlparse, parse_qs, urlunparse
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlmodel import SQLModel

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data.db")

# Convert PostgreSQL URL to use asyncpg driver and handle SSL parameters
if DATABASE_URL.startswith("postgresql://"):
    # Parse the URL to handle sslmode parameter
    parsed = urlparse(DATABASE_URL)
    query_params = parse_qs(parsed.query)
    
    # Remove sslmode from query parameters (asyncpg doesn't support it)
    if 'sslmode' in query_params:
        query_params.pop('sslmode')
    
    # Rebuild query string
    new_query = "&".join([f"{k}={v[0]}" for k, v in query_params.items()])
    
    # Rebuild URL with asyncpg driver
    new_parsed = parsed._replace(
        scheme="postgresql+asyncpg",
        query=new_query
    )
    DATABASE_URL = urlunparse(new_parsed)

# Create async engine
engine_kwargs = {
    "echo": os.getenv("SQL_ECHO", "false").lower() == "true",
    "future": True
}

# Add SSL config for PostgreSQL
if "postgresql" in DATABASE_URL:
    engine_kwargs["connect_args"] = {"ssl": "prefer"}

engine = create_async_engine(DATABASE_URL, **engine_kwargs)

# Create session maker
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    """Initialize database tables"""
    try:
        async with engine.begin() as conn:
            # Import models to ensure they're registered
            from models import User, Book, BookRequest
            await conn.run_sync(SQLModel.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise

def get_session_context():
    """Get database session as context manager"""
    return async_session()
