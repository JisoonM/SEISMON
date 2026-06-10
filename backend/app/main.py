import logging
import asyncio
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text

from app.config import get_settings
from app.database import engine
from app.rate_limit import limiter
from app.redis_client import create_redis_client
from app.routers import earthquakes, websocket

settings = get_settings()
logger = logging.getLogger(__name__)


async def check_database() -> bool:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await check_database()
        logger.info("database startup check ok")
    except Exception:
        logger.exception("database startup check failed")
    redis = create_redis_client()
    try:
        await redis.ping()
        logger.info("redis startup check ok")
    except Exception:
        logger.exception("redis startup check failed")
    finally:
        await redis.aclose()
    app.state.redis_listener_task = asyncio.create_task(websocket.redis_listener())
    app.state.heartbeat_task = asyncio.create_task(websocket.heartbeat_loop())
    try:
        yield
    finally:
        for task_name in ("redis_listener_task", "heartbeat_task"):
            task = getattr(app.state, task_name, None)
            if task is not None:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):  # noqa: ANN001
    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    logger.info(
        "request completed",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


app.include_router(earthquakes.router, prefix="/api/v1", tags=["earthquakes"])
app.include_router(earthquakes.provinces_router, prefix="/api/v1", tags=["provinces"])
app.include_router(websocket.router, tags=["websocket"])
app.mount("/socket.io", websocket.socket_app)


@app.get("/health", summary="Health check", description="Return backend, database, and Redis health state.")
async def health(redis=Depends(create_redis_client)):  # noqa: ANN001
    try:
        db_status = "ok" if await check_database() else "error"
    except Exception as exc:
        logger.warning("database health check failed: %s", exc)
        db_status = "error"

    try:
        await redis.ping()
        redis_status = "ok"
    except Exception as exc:
        logger.warning("redis health check failed: %s", exc)
        redis_status = "error"
    finally:
        if hasattr(redis, "aclose"):
            try:
                await redis.aclose()
            except Exception as exc:
                logger.warning("redis health client cleanup failed: %s", exc)
    return {
        "status": "ok" if db_status == "ok" and redis_status == "ok" else "degraded",
        "db": db_status,
        "redis": redis_status,
        "timestamp": datetime.now(UTC).isoformat(),
    }
