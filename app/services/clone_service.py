import os
import json
import requests
import uuid
from dotenv import load_dotenv

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_DB_FILE = "user_voice_map.json"

def _load_voice_db():
    if os.path.exists(VOICE_DB_FILE):
        with open(VOICE_DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def _save_voice_db(data):
    with open(VOICE_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_or_create_voice_id(user_id: str, speaker_wav: str) -> str:
    """
    [기존과 동일] Voice ID 조회 또는 생성
    """
    if not ELEVENLABS_API_KEY:
        raise ValueError("ELEVENLABS_API_KEY가 설정되지 않았습니다.")

    headers = {"xi-api-key": ELEVENLABS_API_KEY}
    
    db = _load_voice_db()
    if user_id in db:
        voice_id = db[user_id]
        print(f"♻️ 기존 Voice ID 재사용: {voice_id}")
        return voice_id

    print(f"🆕 새 목소리 등록 요청 중... ({os.path.basename(speaker_wav)})")
    add_url = "https://api.elevenlabs.io/v1/voices/add"
    voice_name = f"User_{user_id}_{uuid.uuid4().hex[:4]}"

    with open(speaker_wav, "rb") as f:
        files = {'files': (os.path.basename(speaker_wav), f, 'audio/wav')}
        data = {'name': voice_name, 'description': 'FastAPI Auto Clone'}
        response = requests.post(add_url, headers=headers, data=data, files=files)
    
    if response.status_code != 200:
        raise Exception(f"목소리 등록 실패: {response.text}")
    
    voice_id = response.json().get("voice_id")
    print(f"목소리 등록 완료! ID: {voice_id}")

    db[user_id] = voice_id
    _save_voice_db(db)
    
    return voice_id

def generate_speech_stream(text: str, voice_id: str):
    """
    [핵심 수정] 파일 저장이 아닌, 오디오 데이터 조각(chunk)을 실시간으로 반환(yield)
    """
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }

    # optimize_streaming_latency=3 : 지연 시간 최소화 옵션
    generate_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream?optimize_streaming_latency=3"

    payload = {
        "text": text,
        "model_id": "eleven_turbo_v2_5",  # Turbo 모델 (속도 최우선)
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }

    # stream=True 필수
    response = requests.post(generate_url, headers=headers, json=payload, stream=True)

    if response.status_code != 200:
        raise Exception(f"ElevenLabs API Error: {response.text}")

    # 청크 단위로 데이터를 즉시 반환
    for chunk in response.iter_content(chunk_size=1024):
        if chunk:
            yield chunk