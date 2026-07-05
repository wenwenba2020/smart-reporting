"""API-KEY verification middleware for WorkoPilot Open API.

Provides a FastAPI Header dependency that validates the API-KEY header
against the configured workopilot_api_key setting.
"""
from fastapi import Header, HTTPException
from backend.config import settings


async def verify_workopilot_api_key(
    api_key: str = Header(..., alias="API-KEY"),
) -> str:
    """FastAPI dependency that verifies the API-KEY header.

    Returns the authenticated tenant/user identifier on success.
    Raises HTTPException(401/403) on missing or invalid keys.
    """
    if not api_key:
        raise HTTPException(status_code=401, detail="API-KEY header is required")

    if settings.workopilot_api_key and api_key != settings.workopilot_api_key:
        raise HTTPException(status_code=403, detail="Invalid API-KEY")

    return "openapi_user"
