from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from app.services.clone_service import clone_voice_and_save
from app.services.stt_service import transcribe_audio_file_local, convert_webm_to_wav
from app.services.processor_service import get_gpt_response
from app.dependencies import get_current_user  # ✅ 분리된 Auth 모듈 사용
import os
import shutil
import uuid

router = APIRouter()

# WSL/Linux 환경 호환 경로 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # app/
UPLOAD_DIR = os.path.join(BASE_DIR, "routers", "uploads")
STATIC_DIR = os.path.join(BASE_DIR, "static")

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

@router.post("/generate-content")
async def generate_content(
    mode: str = Form(...),
    target_lang: str = Form(...),
    text: str = Form(None),
    audio: UploadFile = File(None),
    current_user: dict = Depends(get_current_user) # ✅ 인증 활성화
):
    user_id = current_user["id"]
    
    # 임시 파일 처리를 위한 고유 ID
    request_id = str(uuid.uuid4())
    speaker_ref = ""
    source_text = ""

    try:
        # 1. 입력 소스 처리 (음성 -> 텍스트 & 목소리 샘플 확보)
        if mode in ['record', 'upload']:
            if not audio:
                raise HTTPException(status_code=400, detail="오디오 파일이 없습니다.")

            # 원본 저장 (webm 또는 mp3 등)
            ext = os.path.splitext(audio.filename)[1]
            temp_filename = f"{user_id}_{request_id}{ext}"
            temp_path = os.path.join(UPLOAD_DIR, temp_filename)
            
            with open(temp_path, "wb") as f:
                shutil.copyfileobj(audio.file, f)
            
            # WebM인 경우 WAV로 변환 (STT 및 TTS 참조용)
            wav_path = os.path.join(UPLOAD_DIR, f"{user_id}_{request_id}.wav")
            if ext.lower() == ".webm":
                convert_webm_to_wav(temp_path, wav_path)
                speaker_ref = wav_path
            else:
                # 다른 포맷도 안전하게 변환하거나 그대로 사용 (여기선 그대로 사용 시도)
                speaker_ref = temp_path
                
            # STT 실행
            source_text = transcribe_audio_file_local(speaker_ref)
        
        else:
            # 텍스트 모드
            if not text:
                raise HTTPException(status_code=400, detail="텍스트가 입력되지 않았습니다.")
            source_text = text
            
            # ✅ 텍스트 모드일 때 사용할 '내 목소리 샘플' 경로
            # 사용자가 미리 올려둔 파일이 없으므로, static에 있는 default_sample.wav를 사용한다고 가정
            # 실제 서비스에서는 DB에 저장된 사용자의 대표 목소리 경로를 가져와야 함
            default_voice = os.path.join(STATIC_DIR, "default_sample.wav")
            
            if not os.path.exists(default_voice):
                # 파일이 없으면 에러 방지를 위해 임시 에러 처리 혹은 예제 생성
                raise HTTPException(status_code=500, detail="서버에 기준 목소리 샘플(default_sample.wav)이 없습니다.")
            
            speaker_ref = default_voice

        # 2. GPT 번역
        prompt = f"다음 문장을 {target_lang} 언어로 원어민이 말하는 것처럼 자연스럽게 번역해줘. 오직 번역된 문장만 출력해: {source_text}"
        translated_text = get_gpt_response(prompt)

        # 3. 목소리 복제 및 TTS 생성
        out_filename = f"result_{user_id}_{request_id}.wav"
        out_path = os.path.join(UPLOAD_DIR, out_filename)
        
        clone_voice_and_save(translated_text, target_lang, speaker_ref, out_path)

        # 4. 결과 반환 (프론트엔드 접근 URL)
        # 중요: HTML에서 접근 가능하도록 '/uploads/' 경로로 매핑해야 함
        return {
            "status": "success",
            "source_text": source_text,
            "translated_text": translated_text,
            "audio_url": f"/uploads/{out_filename}"
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))