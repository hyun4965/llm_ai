from fastapi import APIRouter, Form, Depends, HTTPException, Cookie
from jose import jwt, JWTError
from app.services.tts_service import text_to_speech
import os

router = APIRouter()

# Java 서버와 반드시 맞춰야 하는 설정
SECRET_KEY = "RANDOM_SECRET_KEY"   # Java JwtUtil.SECRET 과 동일
ALGORITHM = "HS256"
ISSUER = "simple-auth-server"         # Java JwtUtil.ISSUER 와 동일


def get_current_user(
    access_token: str | None = Cookie(default=None, alias="ACCESS_TOKEN")
):
    """
    8080 Java 서버에서 발급한 ACCESS_TOKEN(JWT) 쿠키를 읽어
    현재 로그인 유저 정보를 반환하는 의존성.
    """
    if access_token is None:
        raise HTTPException(
            status_code=401,
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
            status_code=401,
            detail="Invalid or expired token",
        )

    user_id = payload.get("sub")
    username = payload.get("username")

    if user_id is None or username is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid token payload",
        )

    # 필요하면 여기서 DB 조회 후 실제 User 객체를 리턴해도 됨
    return {"id": user_id, "username": username}


# 출력 파일 저장할 uploads 폴더 경로
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/")
async def tts_endpoint(
    current_user: dict = Depends(get_current_user),   # 인증 추가
    text: str = Form(...)
):
    try:
        file_name = "openai_tts_output.mp3"
        output_path = os.path.join(UPLOAD_DIR, file_name)

        # 실제 TTS 생성 처리
        file_path = text_to_speech(text, output_path)  # 내부 저장용 절대경로

        # 클라이언트용 웹 경로 반환
        return {
            "message": "TTS 처리 완료 (OpenAI TTS)",
            "file_path": f"/uploads/{file_name}",  # 웹 경로만 전달
            "user": current_user  # 디버깅용으로 유저 정보 확인
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))