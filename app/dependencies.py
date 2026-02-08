from fastapi import HTTPException, status, Cookie
from jose import jwt, JWTError
import os

# 환경 변수 또는 하드코딩된 키
SECRET_KEY = "RANDOM_SECRET_KEY"
ALGORITHM = "HS256"
ISSUER = "simple-auth-server"

def get_current_user(access_token: str | None = Cookie(default=None, alias="ACCESS_TOKEN")):
    """
    Java 서버에서 발급한 쿠키를 검증하여 유저 정보를 반환합니다.
    """
    if access_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated (no ACCESS_TOKEN cookie)",
        )

    try:
        payload = jwt.decode(
            access_token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            issuer=ISSUER,
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id = payload.get("sub")
    username = payload.get("username")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    return {"id": user_id, "username": username}