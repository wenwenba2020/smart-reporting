"""Tests for MCP data source adapter."""
import pytest
from backend.core.datasource.mcp_source import McpSource
from backend.core.models import McpSourceConfig


@pytest.mark.asyncio
async def test_mcp_source_supports():
    adapter = McpSource()
    assert adapter.supports("anything") is False


@pytest.mark.asyncio
async def test_mcp_source_placeholder_without_api_key(monkeypatch):
    """When WORKOPILOT_API_KEY is empty, fetch returns a placeholder document."""
    monkeypatch.setattr("backend.config.settings.workopilot_api_key", "")
    monkeypatch.setattr("backend.core.datasource.mcp_source.settings.workopilot_api_key", "")

    adapter = McpSource()
    config = McpSourceConfig(
        robot_id=12345,
        user_id="test_user",
        tool_prompt="Get sales data from ERP",
    )
    doc = await adapter.fetch(config)
    assert doc.source_type == "mcp"
    assert "MCP 数据源未配置" in doc.content
    assert doc.metadata.get("robot_id") == 12345
    assert doc.metadata.get("status") == "not_configured"
