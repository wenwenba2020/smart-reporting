from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from backend.api.auth import create_access_token, verify_credentials, decode_token

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    if not verify_credentials(req.username, req.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    token = create_access_token(subject=req.username)
    return TokenResponse(access_token=token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(req: TokenResponse):
    subject = decode_token(req.access_token)
    new_token = create_access_token(subject=subject)
    return TokenResponse(access_token=new_token)
