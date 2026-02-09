from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import StreamingResponse
import urllib.parse  # 한글 헤더 인코딩용

# 서비스 모듈들
from app.services.clone_service import get_or_create_voice_id, generate_speech_stream
from app.services.stt_service import transcribe_audio_file_local, convert_webm_to_wav
from app.services.processor_service import get_gpt_response
from app.dependencies import get_current_user 
import os
import shutil
import uuid
import csv

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "routers", "uploads")
STATIC_DIR = os.path.join(BASE_DIR, "static")
KNOWLEDGE_DIR = os.path.join(BASE_DIR, "assets", "knowledge")

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

def load_domain_knowledge(domain_code: str) -> str:
    if not domain_code or domain_code == "none": return ""
    # (기존 파일 읽기 로직 유지)
    return "" 

@router.post("/generate-content")
async def generate_content(
    mode: str = Form(...),
    target_lang: str = Form(...),
    domain: str = Form("none"),
    text: str = Form(None),
    audio: UploadFile = File(None),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    request_id = str(uuid.uuid4())
    speaker_ref = ""
    source_text = ""

    try:
        # 1. 입력 처리 및 STT
        if mode in ['record', 'upload']:
            if not audio:
                raise HTTPException(status_code=400, detail="오디오 파일이 없습니다.")

            ext = os.path.splitext(audio.filename)[1]
            temp_filename = f"{user_id}_{request_id}{ext}"
            temp_path = os.path.join(UPLOAD_DIR, temp_filename)
            
            with open(temp_path, "wb") as f:
                shutil.copyfileobj(audio.file, f)
            
            wav_path = os.path.join(UPLOAD_DIR, f"{user_id}_{request_id}.wav")
            if ext.lower() == ".webm":
                convert_webm_to_wav(temp_path, wav_path)
                speaker_ref = wav_path
            else:
                speaker_ref = temp_path
                
            source_text = transcribe_audio_file_local(speaker_ref if ext.lower() == ".webm" else temp_path)
        
        else:
            if not text: raise HTTPException(status_code=400, detail="텍스트 입력 필요")
            source_text = text
            default_voice = os.path.join(STATIC_DIR, "default_sample.wav")
            if not os.path.exists(default_voice):
                raise HTTPException(status_code=500, detail="default_sample.wav 없음")
            speaker_ref = default_voice

        knowledge_context = load_domain_knowledge(domain)
        system_instruction = ""
        if knowledge_context:
            system_instruction = f"[전문 용어 사전]\n{knowledge_context}\n\n[지시사항]\n전문 용어를 참고하여 번역하세요."
        
        prompt = f"""
{system_instruction}
다음 문장을 {target_lang} 언어로 원어민처럼 자연스럽게 번역해줘. 
오직 번역된 문장만 출력해: 
{source_text}
"""
        translated_text = get_gpt_response(prompt)
        
        # 역번역
        back_translated_text = ""
        if target_lang not in ["Korean", "한국어"]:
            # 검증을 위해 다시 한국어로 직역 요청
            back_prompt = f"다음 문장을 한국어로 번역해줘. 원래 의미가 잘 전달되었는지 확인하기 위해 의역보다는 직역에 가깝게 번역해줘. 오직 번역된 문장만 출력해: {translated_text}"
            back_translated_text = get_gpt_response(back_prompt)
        else:
            back_translated_text = "(대상 언어가 한국어입니다)"

        # 3. Voice ID 확보
        voice_ref_path = wav_path if mode in ['record', 'upload'] and ext.lower() == ".webm" else speaker_ref
        voice_id = get_or_create_voice_id(user_id, voice_ref_path)

        # 4. 스트리밍 응답 반환
        audio_stream = generate_speech_stream(translated_text, voice_id)

        # 헤더에 데이터 담기 (한글 인코딩 필수)
        safe_source_text = urllib.parse.quote(source_text)
        safe_translated_text = urllib.parse.quote(translated_text)
        # 역번역 텍스트 헤더 추가
        safe_back_text = urllib.parse.quote(back_translated_text)

        return StreamingResponse(
            audio_stream, 
            media_type="audio/mpeg",
            headers={
                "X-Source-Text": safe_source_text,
                "X-Translated-Text": safe_translated_text,
                "X-Back-Translated-Text": safe_back_text,  # 헤더 추가
                "X-Status": "success"
            }
        )

    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))