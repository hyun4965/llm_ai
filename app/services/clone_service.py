import os
import uuid
import requests
import json
from dotenv import load_dotenv

load_dotenv()

# 환경 변수에서 키 가져오기
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

def clone_voice_and_save(text: str, language: str, speaker_wav: str, output_path: str):
    """
    [Starter 유료 플랜용] 
    1. 내 목소리(speaker_wav)를 일레븐랩스에 등록 (Instant Cloning)
    2. 그 목소리로 텍스트 읽기 (TTS)
    3. 슬롯 확보를 위해 목소리 삭제 (Delete)
    """
    
    # API 키 확인
    if not ELEVENLABS_API_KEY:
        raise ValueError("ELEVENLABS_API_KEY가 설정되지 않았습니다.")

    headers = {
        "xi-api-key": ELEVENLABS_API_KEY
    }

    voice_id = None
    
    try:
        # ==========================================
        # 1. 목소리 등록 (Add Voice) - 복제 시작
        # ==========================================
        print(f"📡 일레븐랩스 API로 내 목소리 등록 요청 중... ({os.path.basename(speaker_wav)})")
        
        add_url = "https://api.elevenlabs.io/v1/voices/add"
        
        # 임시 이름 생성
        temp_name = f"MyVoice_{uuid.uuid4().hex[:8]}"
        
        # 파일 전송
        with open(speaker_wav, "rb") as f:
            files = {
                'files': (os.path.basename(speaker_wav), f, 'audio/wav')
            }
            data = {
                'name': temp_name,
                'description': 'FastAPI Cloned Voice'
            }
            
            response = requests.post(add_url, headers=headers, data=data, files=files)
            
        if response.status_code != 200:
            raise Exception(f"목소리 등록 실패(결제 확인 필요): {response.text}")
            
        # 응답에서 voice_id 추출
        voice_id = response.json().get("voice_id")
        print(f"✅ 목소리 등록 완료! ID: {voice_id}")

        # ==========================================
        # 2. 오디오 생성 (Text to Speech)
        # ==========================================
        print(f"🗣️ 내 목소리로 오디오 생성 시작... (내용: {text[:15]}...)")
        
        generate_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
        
        # JSON 요청 헤더
        gen_headers = headers.copy()
        gen_headers["Content-Type"] = "application/json"
        
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2", # 한국어 지원 모델
            "voice_settings": {
                "stability": 0.5,       # 0.5가 가장 자연스러움
                "similarity_boost": 0.75 # 0.75 이상이면 목소리가 매우 비슷해짐
            }
        }
        
        # 스트리밍 요청
        gen_response = requests.post(generate_url, headers=gen_headers, json=payload, stream=True)
        
        if gen_response.status_code != 200:
            raise Exception(f"오디오 생성 실패: {gen_response.text}")

        # 파일 저장
        with open(output_path, "wb") as f:
            for chunk in gen_response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
                    
        print(f"💾 파일 저장 완료: {output_path}")
        return output_path

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        raise e

    finally:
        # ==========================================
        # 3. 목소리 삭제 (Delete Voice)
        # ==========================================
        # Starter 플랜은 슬롯이 10개이므로, 다 쓰면 꽉 찹니다. 
        # 그래서 사용 후 바로 지워주는 것이 좋습니다.
        if voice_id:
            try:
                delete_url = f"https://api.elevenlabs.io/v1/voices/{voice_id}"
                del_response = requests.delete(delete_url, headers=headers)
                print(f"🗑️ 임시 목소리 삭제 완료 (슬롯 반환)")
            except Exception as e:
                print(f"⚠️ 목소리 삭제 실패 (수동 삭제 필요): {e}")