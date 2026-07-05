from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.models.database import create_all_tables, async_session, engine
from backend.models.migrations import backfill_project_stages, ensure_stage_column, ensure_phase4_tables, seed_scenarios_on_startup


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_all_tables()
    await ensure_phase4_tables(engine)
    await ensure_stage_column(engine)
    async with async_session() as db:
        await backfill_project_stages(db)
    await seed_scenarios_on_startup()
    yield


app = FastAPI(
    title="PPT 智能助手",
    version="0.1.0",
    lifespan=lifespan,
)

from backend.config import settings as _settings  # noqa: E402

app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
from backend.api.routes.health import router as health_router  # noqa: E402
from backend.api.routes.auth import router as auth_router  # noqa: E402
from backend.api.routes.projects import router as projects_router  # noqa: E402

from backend.api.routes.generate import router as generate_router  # noqa: E402

from backend.api.routes.download import router as download_router  # noqa: E402

from backend.api.routes.upload import router as upload_router  # noqa: E402

from backend.api.routes.slide_library import router as slide_library_router  # noqa: E402
from backend.api.routes.knowledge import router as knowledge_router  # noqa: E402
from backend.api.routes.scenarios import router as scenarios_router  # noqa: E402
from backend.api.routes.workopilot import router as workopilot_router  # noqa: E402
from backend.api.routes.embed import router as embed_router  # noqa: E402
from backend.api.routes.report_templates import router as report_templates_router  # noqa: E402
from backend.api.routes.data_sources import router as data_sources_router  # noqa: E402
from backend.api.routes.smart_fill import router as smart_fill_router  # noqa: E402
from backend.api.routes.reports import router as reports_router  # noqa: E402

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(generate_router)
app.include_router(download_router)
app.include_router(upload_router)
app.include_router(slide_library_router)
app.include_router(knowledge_router)
app.include_router(scenarios_router)
app.include_router(workopilot_router)
app.include_router(embed_router)
app.include_router(report_templates_router)
app.include_router(data_sources_router)
app.include_router(smart_fill_router)
app.include_router(reports_router)

# Static files
_fonts_dir = Path(_settings.FONTS_DIR)
if _fonts_dir.exists():
    app.mount("/fonts", StaticFiles(directory=str(_fonts_dir)), name="fonts")

# Serve project SVG files
_projects_dir = Path(_settings.LOCAL_STORAGE_PATH)
_projects_dir.mkdir(parents=True, exist_ok=True)
app.mount("/project-files", StaticFiles(directory=str(_projects_dir)), name="project-files")
