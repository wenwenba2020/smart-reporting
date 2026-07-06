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
    # Startup — ensure data directories exist
    Path("data").mkdir(parents=True, exist_ok=True)
    Path("data/exports").mkdir(parents=True, exist_ok=True)
    Path("data/files").mkdir(parents=True, exist_ok=True)
    Path(settings.local_storage_path).mkdir(parents=True, exist_ok=True)
    await init_db()

    # Security: warn about default secrets
    if not settings.jwt_secret:
        import secrets
        logger.warning("JWT_SECRET is empty — auto-generating a random key for this session. "
                       "Set JWT_SECRET in .env for production use.")
        settings.jwt_secret = secrets.token_hex(32)
    elif settings.jwt_secret == "change-me-in-production":
        logger.critical("JWT_SECRET is the default placeholder 'change-me-in-production'! "
                        "Set a secure random value in .env immediately.")
    if not settings.openrouter_api_key or "placeholder" in settings.openrouter_api_key:
        logger.warning("OPENROUTER_API_KEY is not configured — LLM features will use fallback mode")

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

# ---------------------------------------------------------------------------
# API Routers
# ---------------------------------------------------------------------------

# Health check
app.include_router(health_router, prefix="/api/v1")

# Data sources — file upload, parse, manage
from backend.api.routes.datasources import router as datasources_router  # noqa: E402
app.include_router(datasources_router, prefix="/api/v1")

# Enterprise PPT deck library — upload, search, manage
from backend.api.routes.enterprise_ppt import router as enterprise_ppt_router  # noqa: E402
app.include_router(enterprise_ppt_router, prefix="/api/v1")

# Report templates — list and detail
from backend.api.routes.templates import router as templates_router  # noqa: E402
app.include_router(templates_router, prefix="/api/v1")

# Reports — intent, generate (SSE), manage, chat-command, confirm
from backend.api.routes.reports import router as reports_router  # noqa: E402
app.include_router(reports_router, prefix="/api/v1")

# Export — multi-format export and file download
from backend.api.routes.export import router as export_router  # noqa: E402
app.include_router(export_router, prefix="/api/v1")

# PPT template — recommend and select template decks
from backend.api.routes.ppt_template import router as ppt_template_router  # noqa: E402
app.include_router(ppt_template_router, prefix="/api/v1")

# WorkoPilot AI service bridge
from backend.workopilot.ai_service_bridge import router as workopilot_router  # noqa: E402
app.include_router(workopilot_router, prefix="/api/v1")

# ---------------------------------------------------------------------------
# Static file mounts
# ---------------------------------------------------------------------------

# Serve uploaded files
Path(settings.local_storage_path).mkdir(parents=True, exist_ok=True)
app.mount("/static/files", StaticFiles(directory=settings.local_storage_path), name="static_files")
