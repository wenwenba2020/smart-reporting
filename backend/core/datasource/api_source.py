"""REST API data source adapter — fetch data from external HTTP APIs."""
import json
import uuid
import httpx
from typing import Optional
from backend.core.datasource.base import DataSourceAdapter, register_adapter
from backend.core.models import SourceDocument, RestApiSourceConfig


@register_adapter
class RestApiSource(DataSourceAdapter):
    """Fetch data from a configured REST API endpoint and convert to SourceDocument."""

    source_type = "rest_api"

    def supports(self, filename: str) -> bool:
        return False  # not file-based; configured via API

    async def parse(
        self, file_path: str, filename: str, metadata: Optional[dict] = None
    ) -> SourceDocument:
        raise NotImplementedError("Use fetch() for configuration-based sources")

    async def fetch(self, config: RestApiSourceConfig) -> SourceDocument:
        """Execute a REST API call and convert the response to a SourceDocument."""
        headers = {**config.headers}
        auth = None

        if config.auth_type == "bearer" and config.auth_token:
            headers["Authorization"] = f"Bearer {config.auth_token}"
        elif config.auth_type == "basic":
            auth = httpx.BasicAuth(config.auth_username, config.auth_password)

        async with httpx.AsyncClient(timeout=30, auth=auth) as client:
            if config.method.upper() == "GET":
                resp = await client.get(config.url, headers=headers)
            elif config.method.upper() == "POST":
                resp = await client.post(config.url, headers=headers)
            else:
                resp = await client.request(config.method, config.url, headers=headers)

        resp.raise_for_status()

        try:
            data = resp.json()
        except json.JSONDecodeError:
            data = {"raw_text": resp.text}

        # Apply JSONPath extraction
        extracted = self._jsonpath_extract(data, config.jsonpath_expr)

        # Determine title
        title = ""
        if config.title_field and isinstance(extracted, dict):
            title = str(extracted.get(config.title_field, ""))
        if not title and isinstance(extracted, dict):
            title = extracted.get("title", extracted.get("name", config.url))
        if not title:
            title = config.url

        # Format extracted data as Markdown
        content = self._format_as_markdown(extracted)

        return SourceDocument(
            id=str(uuid.uuid4()),
            title=title,
            content=content,
            source_type=self.source_type,
            metadata={
                "url": config.url,
                "method": config.method,
                "jsonpath": config.jsonpath_expr,
                "response_status": resp.status_code,
            },
        )

    def _jsonpath_extract(self, data, expr: str):
        """Simple JSONPath extraction supporting $.key, $.key.sub, $[*], $.key[*]."""
        expr = expr.strip()
        if expr == "$":
            return data

        # Strip leading "$."
        path = expr[2:] if expr.startswith("$.") else expr
        parts = path.split(".")
        current = data

        for part in parts:
            if part.endswith("[*]") and isinstance(current, dict):
                key = part[:-3]
                current = current.get(key, [])
                if isinstance(current, list):
                    return current
            elif isinstance(current, dict):
                current = current.get(part, {})
            elif isinstance(current, list):
                # Collect field from each item
                results = []
                for item in current:
                    if isinstance(item, dict):
                        val = item.get(part)
                        if val is not None:
                            results.append(val)
                return results
            else:
                return current

        return current

    def _format_as_markdown(self, data) -> str:
        """Format extracted data as Markdown."""
        lines = []

        if isinstance(data, list):
            if data and isinstance(data[0], dict):
                # List of dicts → Markdown table
                keys = list(data[0].keys())[:10]  # limit columns
                # Header
                lines.append("| " + " | ".join(keys) + " |")
                lines.append("| " + " | ".join("---" for _ in keys) + " |")
                # Rows
                for item in data[:100]:  # limit rows
                    row_vals = [str(item.get(k, "")) for k in keys]
                    lines.append("| " + " | ".join(row_vals) + " |")
            else:
                # List of scalars → bullet list
                for item in data[:100]:
                    lines.append(f"- {item}")

        elif isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (list, dict)):
                    lines.append(f"### {key}")
                    lines.append(f"```json")
                    lines.append(json.dumps(value, ensure_ascii=False, indent=2))
                    lines.append(f"```")
                else:
                    lines.append(f"- **{key}**: {value}")

        else:
            lines.append(str(data))

        return "\n".join(lines)
