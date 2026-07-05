"""WorkoPilot 数字员工 Open API 适配层"""
import json
import uuid

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.config import settings

router = APIRouter(prefix="/wp-open", tags=["workopilot"])


class ChatSendRequest(BaseModel):
    RobotId: int
    UserId: str
    UserName: str | None = None
    SessionId: str | None = None
    Content: str | None = None
    Message: str | None = None
    Files: list[str] | None = None
    Attachments: list[str] | None = None
    ContextData: dict | None = None
    Stream: bool = True


def _verify_api_key(request: Request) -> str:
    """验证 API-KEY，返回 tenant user_id。"""
    api_key = request.headers.get("API-KEY", "")
    if not api_key:
        raise HTTPException(status_code=401, detail="API Key missing")
    if settings.WORKOPILOT_API_KEY and api_key != settings.WORKOPILOT_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key or Permission Denied")
    return "openapi_user"


async def _generate_sse_stream(
    user_message: str,
    user_id: str,
    ctx: dict,
) -> str:
    """调用 PPT agent pipeline 并生成 WorkoPilot SSE 事件流。"""
    import asyncio

    from backend.models.database import async_session
    from backend.models.project import Project

    async with async_session() as db:
        project = Project(
            name=f"WP-{user_id[:8]}-{uuid.uuid4().hex[:6]}",
            user_id="admin",
        )
        db.add(project)
        await db.commit()
        project_id = project.id

    full_message = user_message
    if ctx:
        ctx_lines = [f"{k}: {v}" for k, v in ctx.items()]
        full_message = f"{user_message}\n\n[业务上下文]\n" + "\n".join(ctx_lines)

    yield _sse_event("text", {"text": "正在分析您的需求..."})

    try:
        from backend.graph.workflow import graph

        config = {"configurable": {"thread_id": project_id}}
        state = {
            "project_id": project_id,
            "user_message": full_message,
            "mode": "global",
        }

        yield _sse_event("text", {"text": "规划师正在设计大纲结构..."})

        result = await asyncio.to_thread(
            lambda: asyncio.run(graph.ainvoke(state, config=config))
        )

        async with async_session() as db:
            proj = await db.get(Project, project_id)
            total_slides = proj.total_slides if proj else 0

        base_url = settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else "http://localhost:5173"
        download_url = f"{base_url}/api/projects/{project_id}/download"
        preview_url = f"{base_url}/project-files/{project_id}/svg_output/slide_01.svg"

        card_data = json.dumps({
            "title": f"PPT 已生成（{total_slides}页）",
            "type": "ppt_generated",
            "slideCount": total_slides,
            "coverUrl": preview_url,
            "downloadUrl": download_url,
            "previewUrl": f"{base_url}/wp-preview/{project_id}",
        }, ensure_ascii=False)

        yield _sse_event("card", {
            "title": f"PPT 已生成（{total_slides}页）",
            "skillCode": "ppt_generate",
            "cardData": card_data,
        })

        yield _sse_event("done", {
            "messageId": str(uuid.uuid4()),
            "sessionId": project_id,
        })

    except Exception as e:
        yield _sse_event("error", {"message": f"PPT 生成失败: {str(e)}"})


def _sse_event(event_type: str, data: dict) -> str:
    """格式化为 WorkoPilot SSE 事件。"""
    data_str = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {data_str}\n\n"


@router.post("/chat/send")
async def chat_send(
    request: Request,
    body: ChatSendRequest,
):
    """WorkoPilot 对话发送接口。"""
    _verify_api_key(request)

    user_message = body.Content or body.Message or ""
    if not user_message:
        if not body.Stream:
            return {
                "code": 500,
                "msg": "消息内容不能为空",
                "data": None,
            }
        else:
            return StreamingResponse(
                iter([_sse_event("error", {"message": "消息内容不能为空"})]),
                media_type="text/event-stream",
            )

    ctx = {}
    for key, value in request.query_params.items():
        if key.startswith("ctx."):
            ctx[key[4:]] = value
    if body.ContextData:
        ctx.update(body.ContextData)

    if not body.Stream:
        return {
            "code": 200,
            "msg": None,
            "data": {
                "sessionId": body.SessionId or uuid.uuid4().hex,
                "message": "PPT 生成功能需要通过流式模式使用。请设置 Stream=true 获取实时进度。",
                "cardData": None,
                "attachments": [],
            },
        }

    return StreamingResponse(
        _generate_sse_stream(user_message, body.UserId, ctx),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/robot/profile")
async def get_robot_profile(
    request: Request,
    robotId: int | None = None,
):
    """获取数字员工资料。"""
    _verify_api_key(request)
    base_url = _get_base_url(request)
    return {
        "code": 200,
        "msg": None,
        "data": {
            "id": robotId or 0,
            "robotCode": "ppt-assistant",
            "robotName": "PPT 智能助理",
            "avatarUrl": "",
            "welcomeMessage": "您好！我是 PPT 智能助理，可以帮您生成企业专属 PPT。请告诉我您需要什么类型的演示文稿？",
            "businessLine": "productivity",
            "isActive": 1,
            "appMenus": [
                {
                    "id": 1,
                    "menuType": "iframe",
                    "displayMode": "fullscreen",
                    "menuKey": "ppt-editor",
                    "title": "PPT 工作台",
                    "icon": "lucide:presentation",
                    "routePath": "",
                    "componentPath": None,
                    "iframeUrl": f"{base_url}/embed",
                    "directUrl": f"{base_url}/embed?token=xxx&externalUserId={{userId}}&externalUserName={{userName}}",
                    "sort": 1,
                    "isEnabled": True,
                }
            ],
        },
        "total": 0,
        "rows": None,
    }


@router.get("/robots")
async def list_robots(request: Request):
    """列出数字员工列表。"""
    _verify_api_key(request)
    base_url = _get_base_url(request)
    return {
        "code": 200,
        "msg": None,
        "data": None,
        "total": 1,
        "rows": [
            {
                "robotId": 1,
                "robotCode": "ppt-assistant",
                "robotName": "PPT 智能助理",
                "avatarUrl": "",
                "description": "一键生成企业专属 PPT，支持方案库、知识库、案例库、模板库四大数据底座",
                "intro": "面向企业用户的智能 PPT 生成数字员工",
                "enableShare": True,
                "shareUrl": f"{base_url}/embed/chat/1?token=xxx&externalUserId={{userId}}&externalUserName={{userName}}",
                "appMenus": [
                    {
                        "id": 1,
                        "menuType": "iframe",
                        "displayMode": "fullscreen",
                        "menuKey": "ppt-editor",
                        "title": "PPT 工作台",
                        "icon": "lucide:presentation",
                        "routePath": "",
                        "componentPath": None,
                        "iframeUrl": f"{base_url}/embed",
                        "directUrl": f"{base_url}/embed?token=xxx&externalUserId={{userId}}&externalUserName={{userName}}",
                        "sort": 1,
                        "isEnabled": True,
                    }
                ],
            }
        ],
    }


def _get_base_url(request: Request) -> str:
    """获取当前服务的基础 URL。"""
    base = request.query_params.get("baseUrl", "")
    if base:
        return base.rstrip("/")
    return str(request.base_url).rstrip("/")
