"""
Database connection pool and query utilities
"""
import asyncpg
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Global connection pool
_pool: Optional[asyncpg.Pool] = None

async def get_pool() -> asyncpg.Pool:
    """Get or create database connection pool"""
    global _pool

    if _pool is None:
        try:
            _pool = await asyncpg.create_pool(
                host="172.20.0.11",
                port=5432,
                user="postgres",
                password="hackathon_db_pass",
                database="superops",
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            logger.info("Database connection pool created")
        except Exception as e:
            logger.error(f"Failed to create database pool: {e}")
            raise

    return _pool

async def close_pool():
    """Close database connection pool"""
    global _pool

    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed")
