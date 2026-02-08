from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status, Cookie
from jose import jwt, JWTError
import shutil
import os

# ✅ 로컬 Whisper용 STT 함수로 교체 (transcribe_audio_file_local)
from app.services.stt_service import transcribe_audio_file_local, convert_webm_to_wav

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

    if user_id is None or username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # 필요하면 여기서 DB 조회 후 실제 User 객체를 리턴해도 됨
    return {"id": user_id, "username": username}

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/")
async def stt(
    current_user: dict = Depends(get_current_user),
    audio: UploadFile = File(...)):
    webm_path = os.path.join(UPLOAD_DIR, audio.filename)

    with open(webm_path, "wb") as buffer:
        shutil.copyfileobj(audio.file, buffer)

    try:
        # webm → wav 변환
        wav_path = webm_path.replace(".webm", ".wav")
        convert_webm_to_wav(webm_path, wav_path)

        # Whisper STT (로컬 버전 사용)
        text = transcribe_audio_file_local(wav_path)

        os.remove(webm_path)
        os.remove(wav_path)
        return {
            "text": text,
            "user": current_user  # 디버깅용으로 유저 정보 확인
        }
    except Exception as e:
        return {"error": str(e)}