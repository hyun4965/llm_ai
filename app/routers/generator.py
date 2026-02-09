from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from app.services.clone_service import clone_voice_and_save
from app.services.stt_service import transcribe_audio_file_local, convert_webm_to_wav
from app.services.processor_service import get_gpt_response
from app.dependencies import get_current_user 
import os
import shutil
import uuid
import csv

router = APIRouter()

# WSL/Linux 환경 호환 경로 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # app/
UPLOAD_DIR = os.path.join(BASE_DIR, "routers", "uploads")
STATIC_DIR = os.path.join(BASE_DIR, "static")
KNOWLEDGE_DIR = os.path.join(BASE_DIR, "assets", "knowledge")

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# 폴더가 없으면 에러 방지를 위해 생성은 안 하더라도 경로는 인식시킴
if not os.path.exists(KNOWLEDGE_DIR):
    try:
        os.makedirs(KNOWLEDGE_DIR)
    except:
        pass

def load_domain_knowledge(domain_code: str) -> str:
    """
    선택된 도메인 코드를 기반으로 TXT 또는 CSV 파일을 찾아
    GPT가 이해할 수 있는 문자열 형태로 반환합니다.
    """
    if not domain_code or domain_code == "none":
        return ""

    # 지원하는 파일 확장자 우선순위
    extensions = [".txt", ".csv"]
    target_file = None

    # 해당 도메인 이름의 파일이 있는지 탐색
    for ext in extensions:
        file_path = os.path.join(KNOWLEDGE_DIR, f"{domain_code}{ext}")
        if os.path.exists(file_path):
            target_file = file_path
            break
    
    if not target_file:
        return ""

    context_data = []
    try:
        if target_file.endswith(".txt"):
            with open(target_file, "r", encoding="utf-8") as f:
                context_data.append(f.read().strip())
                
        elif target_file.endswith(".csv"):
            with open(target_file, "r", encoding="utf-8-sig") as f: 
                reader = csv.reader(f)
                header = next(reader, None) 
                if header:
                    for row in reader:
                        if len(row) >= 2: # 열 2개 가져옴
                            context_data.append(f"{row[0]}: {row[1]}")
                            
        return "\n".join(context_data)

    except Exception as e:
        print(f"도메인 파일 읽기 실패: {e}")
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
                speaker_ref = temp_path
                
            # STT 실행 (순차 처리)
            source_text = transcribe_audio_file_local(speaker_ref)
        
        else:
            # 텍스트 모드
            if not text:
                raise HTTPException(status_code=400, detail="텍스트가 입력되지 않았습니다.")
            source_text = text
            
            # 텍스트 모드일 때 사용할 '내 목소리 샘플' 경로
            default_voice = os.path.join(STATIC_DIR, "default_sample.wav")
            
            if not os.path.exists(default_voice):
                raise HTTPException(status_code=500, detail="서버에 기준 목소리 샘플(default_sample.wav)이 없습니다.")
            
            speaker_ref = default_voice

        # 2. GPT 번역 및 역번역 (RAG: 도메인 지식 주입)
        
        # (1) 도메인 지식 로드
        knowledge_context = load_domain_knowledge(domain)
        
        # (2) 프롬프트 구성
        system_instruction = ""
        if knowledge_context:
            system_instruction = f"""
[전문 용어 사전]
{knowledge_context}

[지시사항]
위의 전문 용어 사전을 반드시 참고하여, 전문적인 문맥에 맞게 번역하세요.
"""
        
        prompt = f"""
{system_instruction}
다음 문장을 {target_lang} 언어로 원어민이 말하는 것처럼 자연스럽게 번역해줘. 
오직 번역된 문장만 출력해: 
{source_text}
"""
        # GPT 번역 실행 (순차 처리)
        translated_text = get_gpt_response(prompt)
        
        # (3) 역번역 (Cross-Check)
        back_translated_text = "대상 언어가 한국어입니다." 
        
        if target_lang != "Korean" and target_lang != "한국어":
            back_trans_prompt = f"다음 문장을 한국어로 번역해줘. 원래 의미가 잘 전달되었는지 확인하기 위해 의역보다는 직역에 가깝게 번역해줘. 오직 번역된 문장만 출력해: {translated_text}"
            back_translated_text = get_gpt_response(back_trans_prompt)
            print(f"🔄 교차 검증: {source_text} -> {translated_text} -> {back_translated_text}")

        # 3. 목소리 복제 및 TTS 생성
        out_filename = f"result_{user_id}_{request_id}.wav"
        out_path = os.path.join(UPLOAD_DIR, out_filename)
        
        # 일레븐랩스 호출 (순차 처리)
        clone_voice_and_save(translated_text, target_lang, speaker_ref, out_path)

        # 4. 결과 반환
        return {
            "status": "success",
            "source_text": source_text,           # 1. 원본
            "translated_text": translated_text,   # 2. 번역
            "back_translated_text": back_translated_text, # 3. 재번역 (검증용)
            "target_lang": target_lang,
            "audio_url": f"/uploads/{out_filename}"
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))