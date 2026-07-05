import hmac
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from backend.config import settings

ALGORITHM = "HS256"
# auto_error=False so we can return 401 instead of FastAPI's default 403
security = HTTPBearer(auto_error=False)


def verify_credentials(username: str, password: str) -> bool:
    # constant-time comparison to avoid timing side-channel
    user_ok = hmac.compare_digest(username, settings.ADMIN_USERNAME)
    pass_ok = hmac.compare_digest(password, settings.ADMIN_PASSWORD)
    return user_ok and pass_ok


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_EXPIRE_DAYS)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        sub: str | None = payload.get("sub")
        if sub is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return sub
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return decode_token(credentials.credentials)
