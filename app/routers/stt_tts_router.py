from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status, Cookie
from jose import jwt, JWTError
import os
import shutil
import logging

# ✅ 로컬 Whisper용 STT 함수로 교체
from app.services.stt_service import transcribe_audio_file_local, convert_webm_to_wav
from app.services.processor_service import get_gpt_response
from app.services.tts_service import text_to_speech

logger = logging.getLogger(__name__)

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

# 업로드 디렉토리 설정
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/")
async def stt_to_tts(
    current_user: dict = Depends(get_current_user),   
    audio: UploadFile = File(...)):
    try:
        logger.info("STT → GPT → TTS 요청 시작")
        # 1. 업로드된 파일 저장
        webm_path = os.path.join(UPLOAD_DIR, audio.filename)
        logger.info(f"업로드된 파일 경로: {webm_path}")
        with open(webm_path, "wb") as buffer:
            shutil.copyfileobj(audio.file, buffer)

        # 2. webm → wav 변환
        wav_path = webm_path.replace(".webm", ".wav")
        convert_webm_to_wav(webm_path, wav_path)
        logger.info(f"webm → wav 변환 완료: {wav_path}")

        # 3. STT 처리 (로컬 Whisper 사용)
        stt_text = transcribe_audio_file_local(wav_path)
        logger.info(f"STT 변환 결과: {stt_text}")

        # 4. GPT 처리
        gpt_response = get_gpt_response(stt_text)
        logger.info(f"GPT 응답 텍스트: {gpt_response}")

        # 5. TTS 처리
        tts_output_path = os.path.join(UPLOAD_DIR, "response.mp3")
        text_to_speech(gpt_response, tts_output_path)
        logger.info(f"TTS 출력 파일 생성 완료: {tts_output_path}")

        # HTTP URL로 반환
        tts_file_url = f"/uploads/response.mp3"
        logger.info(f"클라이언트에 반환된 TTS 파일 경로: {tts_file_url}")
        return {
            "message": "STT → GPT → TTS 처리 완료",
            "stt_text": stt_text,
            "gpt_response": gpt_response,
            "tts_file_path": tts_file_url,
            "user": current_user  # 디버깅용으로 유저 정보 확인
        }
    except Exception as e:
        logger.error(f"에러 발생: {e}")
        raise HTTPException(status_code=500, detail=str(e))