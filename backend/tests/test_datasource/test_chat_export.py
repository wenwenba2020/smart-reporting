import pytest
import tempfile
import os

from backend.core.datasource.chat_export import ChatExportAdapter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_temp(content: str, suffix: str = ".txt") -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

WECHAT_SAMPLE = """2024-01-15 09:30:00 张三
大家早上好，今天的项目评审会议几点开始？

2024-01-15 09:31:05 李四
早上好！十点在3号会议室。

2024-01-15 09:32:10 王五
收到，我准备了上周的数据报表。

2024-01-15 09:33:00 张三
很好，请把营收数据重点标注一下。

2024-01-16 14:00:00 李四
会议纪要已经发到群里了，大家查看一下。

2024-01-16 14:05:30 张三
看到了，总结得很到位。"""

WECOM_SAMPLE = """张三  2024-06-10 10:00:00
今天的客户方案定稿了吗？

李四  2024-06-10 10:05:12
已经发到审批流程了，预计下午出结果。

王五  2024-06-10 10:06:00
我在跟进技术方案的细节，稍后同步。

张三  2024-06-11 09:00:00
审批通过了，可以开始执行了。"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_export_wechat():
    adapter = ChatExportAdapter()
    path = _write_temp(WECHAT_SAMPLE, suffix="_微信聊天记录.txt")
    try:
        doc = await adapter.parse(path, "微信聊天记录.txt")
        assert doc.source_type == "chat_export"
        assert "张三" in doc.content
        assert "李四" in doc.content
        assert "王五" in doc.content
        assert "Total Messages" in doc.content
        assert "Total Messages**: 6" in doc.content
        assert "2024-01-15" in doc.content
        assert "2024-01-16" in doc.content
        assert doc.metadata["chat_format"] == "wechat"
    finally:
        os.unlink(path)


@pytest.mark.asyncio
async def test_chat_export_wecom():
    adapter = ChatExportAdapter()
    path = _write_temp(WECOM_SAMPLE, suffix="_企业微信导出.txt")
    try:
        doc = await adapter.parse(path, "企业微信导出.txt")
        assert doc.source_type == "chat_export"
        assert "张三" in doc.content
        assert "李四" in doc.content
        assert "王五" in doc.content
        assert "Total Messages" in doc.content
        assert doc.metadata["chat_format"] == "wecom"
        # Should have date headings
        assert "2024-06-10" in doc.content
        assert "2024-06-11" in doc.content
    finally:
        os.unlink(path)


@pytest.mark.asyncio
async def test_chat_export_fallback_colon_format():
    """Name: message style fallback."""
    adapter = ChatExportAdapter()
    content = """张三: 大家好
李四: 你好
张三: 今天天气不错"""
    path = _write_temp(content, suffix="_chat.txt")
    try:
        doc = await adapter.parse(path, "chat.txt")
        assert doc.source_type == "chat_export"
        assert "张三" in doc.content
        assert "李四" in doc.content
        assert "大家好" in doc.content
    finally:
        os.unlink(path)


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("微信聊天记录.txt", True),
        ("wechat_export.txt", True),
        ("企业微信导出.txt", True),
        ("wecom_chat.log", True),
        ("钉钉消息.txt", True),
        ("dingtalk_export.csv", True),
        ("飞书聊天记录.txt", True),
        ("feishu_chat.txt", True),
        ("聊天备份.txt", True),
        ("chat_history.txt", True),
        ("report.docx", False),
        ("data.csv", False),
        ("notes.txt", False),
    ],
)
def test_chat_export_supports(filename, expected):
    adapter = ChatExportAdapter()
    assert adapter.supports(filename) is expected


@pytest.mark.asyncio
async def test_chat_export_participants_list():
    adapter = ChatExportAdapter()
    path = _write_temp(WECHAT_SAMPLE, suffix="_wechat.txt")
    try:
        doc = await adapter.parse(path, "wechat.txt")
        assert "Participants" in doc.content
        # All 3 participants should be listed
        assert "张三" in doc.content
        assert "李四" in doc.content
        assert "王五" in doc.content
    finally:
        os.unlink(path)


@pytest.mark.asyncio
async def test_chat_export_date_grouping():
    """Verify messages are grouped under date headings."""
    adapter = ChatExportAdapter()
    path = _write_temp(WECHAT_SAMPLE, suffix="_wechat.txt")
    try:
        doc = await adapter.parse(path, "wechat.txt")
        content = doc.content
        # Date headings should appear
        assert "## 2024-01-15" in content
        assert "## 2024-01-16" in content
        # Day 1 has 4 messages, day 2 has 2 (per the footer)
        assert "2024-01-15 (4 messages)" in content
        assert "2024-01-16 (2 messages)" in content
    finally:
        os.unlink(path)
