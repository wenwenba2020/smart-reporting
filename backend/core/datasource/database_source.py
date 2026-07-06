"""Database direct connection data source adapter."""
import uuid
from typing import Optional
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from backend.core.datasource.base import DataSourceAdapter, register_adapter
from backend.core.models import SourceDocument, DatabaseSourceConfig

# SQL keywords indicating write operations — blocked for safety
_WRITE_KEYWORDS = {"INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER", "CREATE", "REPLACE", "MERGE", "GRANT", "REVOKE"}


@register_adapter
class DatabaseSource(DataSourceAdapter):
    """Execute SQL queries against databases and return results as SourceDocument."""

    source_type = "database"

    def supports(self, filename: str) -> bool:
        return False

    async def parse(self, file_path: str, filename: str, metadata: Optional[dict] = None) -> SourceDocument:
        raise NotImplementedError("Use fetch() for configuration-based sources")

    async def fetch(self, config: DatabaseSourceConfig) -> SourceDocument:
        # Safety: block write operations
        query_upper = config.query.strip().upper()
        first_word = query_upper.split()[0] if query_upper else ""
        if first_word in _WRITE_KEYWORDS:
            raise ValueError(f"Write operation '{first_word}' is not allowed. Only SELECT queries are permitted.")

        if not query_upper.startswith("SELECT") and not query_upper.startswith("WITH") and not query_upper.startswith("SHOW") and not query_upper.startswith("DESCRIBE") and not query_upper.startswith("EXPLAIN"):
            raise ValueError("Only read-only queries (SELECT/WITH/SHOW/DESCRIBE/EXPLAIN) are allowed.")

        try:
            engine = create_engine(config.connection_string, connect_args={"timeout": 10} if config.db_type == "sqlite" else {})
            with engine.connect() as conn:
                result = conn.execute(text(config.query))
                rows = result.fetchall()
                columns = list(result.keys())

            engine.dispose()

            # Format as Markdown table
            lines = [f"## Query Results\n"]
            lines.append(f"- **Rows**: {len(rows)}")
            lines.append(f"- **Columns**: {', '.join(columns)}\n")

            if rows:
                lines.append("| " + " | ".join(columns) + " |")
                lines.append("| " + " | ".join("---" for _ in columns) + " |")
                for row in rows[:200]:  # limit to 200 rows
                    row_vals = [str(v) if v is not None else "" for v in row]
                    lines.append("| " + " | ".join(row_vals) + " |")

            title = f"DB Query: {config.query[:60]}..."
            return SourceDocument(
                id=str(uuid.uuid4()),
                title=title,
                content="\n".join(lines),
                source_type=self.source_type,
                metadata={
                    "db_type": config.db_type,
                    "query": config.query,
                    "row_count": len(rows),
                    "column_count": len(columns),
                },
            )

        except SQLAlchemyError as e:
            raise ValueError(f"Database error: {e}") from e
