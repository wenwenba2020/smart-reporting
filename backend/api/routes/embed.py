"""iframe 嵌入模式的免登端点"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse

from backend.api.auth import create_access_token

router = APIRouter(prefix="/embed", tags=["embed"])


EMBED_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PPT 智能助理</title>
<style>
  body {{ margin: 0; padding: 0; overflow: hidden; }}
  iframe {{ width: 100vw; height: 100vh; border: none; }}
</style>
</head>
<body>
  <iframe src="{frontend_url}?token={token}&embed=1" allow="clipboard-write"></iframe>
</body>
</html>"""


@router.get("")
async def embed_entry(
    request: Request,
    token: str | None = None,
    externalUserId: str | None = None,
    externalUserName: str | None = None,
):
    """iframe 嵌入入口：自动登录并跳转到前端。"""
    if externalUserId and not token:
        token = create_access_token(
            data={"sub": "admin"},
        )

    if not token:
        raise HTTPException(status_code=401, detail="Missing authentication")

    from backend.config import settings
    frontend_url = settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else "http://localhost:5173"

    html = EMBED_HTML.format(frontend_url=frontend_url, token=token)
    return HTMLResponse(content=html)


@router.get("/auto-login")
async def auto_login(
    externalUserId: str,
    externalUserName: str | None = None,
):
    """自动登录：用 externalUserId 换取 JWT token。"""
    token = create_access_token(data={"sub": "admin"})
    return {"token": token, "token_type": "bearer"}
