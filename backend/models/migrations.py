"""启动时轻量迁移 — 加列 + 为老项目回填 stage 字段"""
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine

from backend.config import settings
from backend.models.database import Base
from backend.models.project import Project


async def ensure_stage_column(engine: AsyncEngine) -> None:
    """SQLite 老库没有 stage 列时补一列。幂等。

    Base.metadata.create_all 只建缺失的表，不会给已存在的表加列，
    所以老项目升级到 MVP-2 后启动会报 "no such column: projects.stage"。
    """
    async with engine.begin() as conn:
        cols = await conn.execute(text("PRAGMA table_info(projects)"))
        existing = {row[1] for row in cols.fetchall()}
        if "stage" not in existing:
            await conn.execute(
                text("ALTER TABLE projects ADD COLUMN stage VARCHAR NOT NULL DEFAULT 'idle'")
            )


async def backfill_project_stages(db: AsyncSession) -> None:
    """对 stage='idle' 的项目按磁盘状态推断 stage。幂等。

    - 有 svg_output/ 且覆盖所有 OUTLINE 页 → 'completed'
    - 只有 OUTLINE.md          → 'awaiting_content_review'
    - 都没有                    → 'idle'（不变）
    """
    result = await db.execute(select(Project).where(Project.stage == "idle"))
    projects = result.scalars().all()

    base = Path(settings.LOCAL_STORAGE_PATH)
    changed = False
    for p in projects:
        proj_dir = base / p.id
        outline = proj_dir / "OUTLINE.md"
        svg_dir = proj_dir / "svg_output"

        if not outline.exists():
            continue  # stay 'idle'

        if svg_dir.is_dir():
            svg_files = list(svg_dir.glob("slide_*.svg"))
            expected = _expected_slide_count(outline)
            if expected > 0 and len(svg_files) >= expected:
                p.stage = "completed"
                changed = True
                continue

        p.stage = "awaiting_content_review"
        changed = True

    if changed:
        await db.commit()


def _expected_slide_count(outline_path: Path) -> int:
    """Read total_slides from OUTLINE.md frontmatter. Return 0 if unparseable."""
    try:
        text = outline_path.read_text(encoding="utf-8")
        return sum(1 for line in text.splitlines() if line.strip().startswith("- slide_id:"))
    except Exception:
        return 0


async def ensure_phase4_tables(engine: AsyncEngine) -> None:
    """Phase 4 新表自动创建（幂等）。导入 knowledge 和 scenario 模型以注册。"""
    from backend.models import knowledge, scenario  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def seed_scenarios_on_startup() -> None:
    """应用启动时自动注入预设场景方案（幂等）。"""
    from backend.models.database import async_session
    from backend.models.scenario import seed_preset_scenarios

    async with async_session() as db:
        await seed_preset_scenarios(db, "admin")
