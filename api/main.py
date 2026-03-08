from contextlib import asynccontextmanager

from fastapi import FastAPI

from db import init_async_db, close_async_db, ping_async_db
from api.dependencies import close_all_clients
from shared.config import settings
from shared.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — initializing async DB engine")
    init_async_db(
        settings.postgres_async_url,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_POOL_MAX_OVERFLOW,
        echo=settings.DATABASE_ECHO,
    )
    if not await ping_async_db():
        logger.warning("Postgres is not reachable at startup")
    yield
    logger.info("Shutting down — closing clients and DB engine")
    await close_all_clients()
    await close_async_db()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    db_ok = await ping_async_db()
    return {"status": "ok" if db_ok else "degraded", "database": db_ok}
