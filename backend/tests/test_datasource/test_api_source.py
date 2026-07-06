"""Tests for REST API data source adapter."""
import json
import pytest
from pathlib import Path
from backend.core.datasource.api_source import RestApiSource
from backend.core.models import RestApiSourceConfig


@pytest.mark.asyncio
async def test_rest_api_source_supports():
    adapter = RestApiSource()
    assert adapter.supports("anything.json") is False
    assert adapter.supports("anything.txt") is False


@pytest.mark.asyncio
async def test_jsonpath_root_extraction():
    adapter = RestApiSource()
    data = {"title": "Test", "items": [1, 2, 3]}
    result = adapter._jsonpath_extract(data, "$")
    assert result == data


@pytest.mark.asyncio
async def test_jsonpath_field_extraction():
    adapter = RestApiSource()
    data = {"title": "My Report", "value": 42}
    result = adapter._jsonpath_extract(data, "$.title")
    assert result == "My Report"


@pytest.mark.asyncio
async def test_jsonpath_nested_extraction():
    adapter = RestApiSource()
    data = {"data": {"results": {"count": 10}}}
    result = adapter._jsonpath_extract(data, "$.data.results")
    assert result == {"count": 10}


@pytest.mark.asyncio
async def test_jsonpath_array_extraction():
    adapter = RestApiSource()
    data = {"items": [{"name": "A"}, {"name": "B"}, {"name": "C"}]}
    result = adapter._jsonpath_extract(data, "$.items[*]")
    assert isinstance(result, list)
    assert len(result) == 3


@pytest.mark.asyncio
async def test_format_list_of_dicts_as_table():
    adapter = RestApiSource()
    data = [{"name": "Alice", "score": 95}, {"name": "Bob", "score": 87}]
    md = adapter._format_as_markdown(data)
    assert "| name" in md
    assert "| Alice" in md


@pytest.mark.asyncio
async def test_format_dict_as_keyvalue():
    adapter = RestApiSource()
    data = {"title": "Report", "author": "Test"}
    md = adapter._format_as_markdown(data)
    assert "**title**" in md
    assert "Report" in md


@pytest.mark.asyncio
async def test_format_scalar():
    adapter = RestApiSource()
    md = adapter._format_as_markdown("simple text")
    assert "simple text" in md
