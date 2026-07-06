"""Tests for database source adapter."""
import pytest
from pathlib import Path
from backend.core.datasource.database_source import DatabaseSource
from backend.core.models import DatabaseSourceConfig


@pytest.mark.asyncio
async def test_database_source_supports():
    adapter = DatabaseSource()
    assert adapter.supports("anything") is False


@pytest.mark.asyncio
async def test_database_source_sqlite():
    """Test with an in-memory SQLite database."""
    import sqlite3
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE sales (id INTEGER, region TEXT, amount REAL)")
    conn.execute("INSERT INTO sales VALUES (1, '华南', 1000.0), (2, '华北', 1500.0)")
    conn.commit()

    # Export the in-memory DB to a file for SQLAlchemy access
    file_db = sqlite3.connect("data/test_sales.db")
    conn.backup(file_db)
    file_db.close()
    conn.close()

    adapter = DatabaseSource()
    config = DatabaseSourceConfig(
        connection_string="sqlite:///data/test_sales.db",
        query="SELECT * FROM sales",
        db_type="sqlite",
    )
    doc = await adapter.fetch(config)
    assert doc.source_type == "database"
    assert "华南" in doc.content
    assert "1000.0" in doc.content
    assert "华北" in doc.content


@pytest.mark.asyncio
async def test_database_source_write_blocked():
    """Write operations should be blocked."""
    adapter = DatabaseSource()
    config = DatabaseSourceConfig(
        connection_string="sqlite:///:memory:",
        query="INSERT INTO t VALUES (1)",
        db_type="sqlite",
    )
    with pytest.raises(ValueError, match="not allowed"):
        await adapter.fetch(config)


@pytest.mark.asyncio
async def test_database_source_select_only():
    """Only SELECT-like queries allowed."""
    adapter = DatabaseSource()
    config = DatabaseSourceConfig(
        connection_string="sqlite:///:memory:",
        query="DROP TABLE xyz",
        db_type="sqlite",
    )
    with pytest.raises(ValueError, match="not allowed"):
        await adapter.fetch(config)
