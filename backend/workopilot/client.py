"""WorkoPilot Open API client wrapping httpx."""
import httpx
from backend.config import settings


class WorkoPilotClient:
    """Async HTTP client for WorkoPilot Open API."""

    def __init__(self):
        self.base_url = settings.workopilot_base_url
        self.api_key = settings.workopilot_api_key
        self._headers = {
            "API-KEY": self.api_key,
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        """Make an HTTP request to the WorkoPilot API."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.request(
                method,
                f"{self.base_url}{path}",
                headers=self._headers,
                **kwargs,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_robot_profile(self, robot_id: int) -> dict:
        """Fetch the profile of a digital employee robot."""
        return await self._request(
            "GET", f"/api/ai/open/robot/profile?robotId={robot_id}"
        )

    async def list_robots(self) -> dict:
        """List all available digital employee robots."""
        return await self._request("GET", "/api/ai/open/robots")

    async def create_session(
        self,
        robot_id: int,
        user_id: str,
        user_name: str = "",
        context_data: dict = None,
    ) -> dict:
        """Create a chat session for a robot and user."""
        return await self._request(
            "POST",
            "/api/ai/open/chat/session",
            json={
                "robotId": robot_id,
                "userId": user_id,
                "userName": user_name,
                "contextData": context_data or {},
            },
        )

    async def send_message(
        self,
        robot_id: int,
        user_id: str,
        session_id: str,
        content: str,
        stream: bool = False,
    ) -> dict:
        """Send a message to a robot session."""
        return await self._request(
            "POST",
            "/api/ai/open/chat/send",
            json={
                "robotId": robot_id,
                "userId": user_id,
                "sessionId": session_id,
                "content": content,
                "stream": stream,
            },
        )

    async def extract_attachment(
        self, file_url: str, category_code: str
    ) -> dict:
        """Extract structured data from a file attachment."""
        return await self._request(
            "POST",
            "/api/attachment/extract",
            json={
                "fileUrl": file_url,
                "categoryCode": category_code,
            },
        )


# Module-level convenience singleton
workopilot_client = WorkoPilotClient()
