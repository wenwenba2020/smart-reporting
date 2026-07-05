import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.routes.health import router as health_router
from backend.config import settings
from backend.storage.database import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle for the FastAPI application."""
    # Startup
    Path("data").mkdir(parents=True, exist_ok=True)
    Path(settings.local_storage_path).mkdir(parents=True, exist_ok=True)
    await init_db()
    logger.info("Smart Reporting API started — database and storage ready")
    yield
    # Shutdown
    logger.info("Smart Reporting API shutting down")


app = FastAPI(
    title="Smart Reporting API",
    description="Enterprise Smart Report Platform — configurable data sources, intelligent fill, multi-format output",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health_router, prefix="/api/v1")

# Static file mount for uploaded files
Path(settings.local_storage_path).mkdir(parents=True, exist_ok=True)
app.mount("/static/files", StaticFiles(directory=settings.local_storage_path), name="static_files")
