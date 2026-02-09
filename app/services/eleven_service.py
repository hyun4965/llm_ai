import requests
import os
from dotenv import load_dotenv

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
# 일레븐랩스 사이트에서 목소리 등록 후 받은 ID
VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID") 

def generate_clone_voice(text: str, output_path: str):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    
    data = {
        "text": text,
        "model_id": "eleven_turbo_v2_5",  # 한국어 목소리로 영어 발화 가능
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.8
        }
    }

    response = requests.post(url, json=data)
    
    if response.status_code == 200:
        with open(output_path, "wb") as f:
            f.write(response.content)
        return output_path
    else:
        raise Exception(f"ElevenLabs API Error: {response.text}")