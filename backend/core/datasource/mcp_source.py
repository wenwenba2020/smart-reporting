"""MCP data source adapter — invoke WorkoPilot MCP tools and collect results."""
import json
import uuid
import logging
from typing import Optional
from backend.core.datasource.base import DataSourceAdapter, register_adapter
from backend.core.models import SourceDocument, McpSourceConfig
from backend.workopilot.client import workopilot_client
from backend.config import settings

logger = logging.getLogger(__name__)


@register_adapter
class McpSource(DataSourceAdapter):
    """Invoke MCP tools via WorkoPilot chat and convert results to SourceDocument."""

    source_type = "mcp"

    def supports(self, filename: str) -> bool:
        return False  # not file-based; configured via API

    async def parse(
        self, file_path: str, filename: str, metadata: Optional[dict] = None
    ) -> SourceDocument:
        raise NotImplementedError("Use fetch() for configuration-based sources")

    async def fetch(self, config: McpSourceConfig) -> SourceDocument:
        """Trigger an MCP tool via WorkoPilot chat and collect the result."""

        # If WorkoPilot API key is not configured, return a placeholder
        if not settings.workopilot_api_key:
            logger.warning("WorkoPilot API key not configured — returning placeholder for MCP source")
            return SourceDocument(
                id=str(uuid.uuid4()),
                title=f"MCP: {config.tool_prompt[:50]}",
                content=f"[MCP 数据源未配置]\n\n请配置 WORKOPILOT_API_KEY 后重试。\n\n"
                        f"触发提示: {config.tool_prompt}\n"
                        f"数字员工ID: {config.robot_id}\n"
                        f"用户ID: {config.user_id}",
                source_type=self.source_type,
                metadata={"robot_id": config.robot_id, "user_id": config.user_id, "status": "not_configured"},
            )

        try:
            # 1. Create or reuse a chat session
            session_resp = await workopilot_client.create_session(
                robot_id=config.robot_id,
                user_id=config.user_id,
                user_name="",
            )
            session_data = session_resp.get("data", session_resp)
            session_id = config.session_id or session_data.get("sessionId", "")

            # 2. Send the tool-triggering prompt (non-streaming for simplicity)
            msg_resp = await workopilot_client.send_message(
                robot_id=config.robot_id,
                user_id=config.user_id,
                session_id=session_id,
                content=config.tool_prompt,
                stream=False,
            )

            msg_data = msg_resp.get("data", msg_resp)
            result_text = msg_data.get("message", "")

            # 3. Check cardData for structured tool results
            card_data_raw = msg_data.get("cardData", "")
            if card_data_raw:
                try:
                    card_data = json.loads(card_data_raw) if isinstance(card_data_raw, str) else card_data_raw
                    result_text += f"\n\n---\n{json.dumps(card_data, ensure_ascii=False, indent=2)}"
                except (json.JSONDecodeError, TypeError):
                    pass

            return SourceDocument(
                id=str(uuid.uuid4()),
                title=f"MCP Result: {config.tool_prompt[:50]}",
                content=result_text or f"[MCP 工具返回为空]\n\n提示: {config.tool_prompt}",
                source_type=self.source_type,
                metadata={
                    "robot_id": config.robot_id,
                    "user_id": config.user_id,
                    "session_id": session_id,
                    "tool_prompt": config.tool_prompt,
                },
            )

        except Exception as e:
            logger.error(f"MCP source fetch failed: {e}")
            return SourceDocument(
                id=str(uuid.uuid4()),
                title=f"MCP Error: {config.tool_prompt[:50]}",
                content=f"[MCP 调用失败]\n\n错误: {str(e)}\n\n提示: {config.tool_prompt}",
                source_type=self.source_type,
                metadata={"robot_id": config.robot_id, "user_id": config.user_id, "error": str(e)},
            )
