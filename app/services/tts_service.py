import os
import requests
from dotenv import load_dotenv

# .env 로드 (이미 main.py에서 했더라도, 중복 호출은 무해)
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY가 설정되어 있지 않습니다. .env 또는 환경변수를 확인하세요.")


def text_to_speech(text: str, output_path: str = "output.mp3"):
    url = "https://api.openai.com/v1/audio/speech"
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "tts-1",
        "input": text,
        "voice": "nova"
    }

    response = requests.post(url, headers=headers, json=data)
    print(f"TTS 응답 상태 코드: {response.status_code}")

    if response.status_code != 200:
        raise Exception(f"TTS 요청 실패: {response.status_code} - {response.text}")

    with open(output_path, "wb") as f:
        f.write(response.content)

    return output_path