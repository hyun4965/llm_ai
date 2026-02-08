import os
from pydub import AudioSegment
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# OpenAI 클라이언트 초기화
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

def convert_webm_to_wav(webm_path: str, wav_path: str) -> None:
    """
    webm 파일을 wav 파일로 변환 (pydub 사용)
    """
    try:
        audio = AudioSegment.from_file(webm_path) # 확장자 자동 인식
        # OpenAI Whisper API는 파일 용량 제한이 있으므로 모노/16kHz로 줄이면 좋음
        audio = audio.set_channels(1).set_frame_rate(16000)
        audio.export(wav_path, format="wav")
        print(f"🎵 변환 완료: {wav_path}")
    except Exception as e:
        print(f"❌ 오디오 변환 실패: {e}")
        # ffmpeg가 없으면 여기서 에러가 납니다.
        raise e

def transcribe_audio_file_local(file_path: str) -> str:
    """
    OpenAI API (Whisper)를 사용하여 음성을 텍스트로 변환
    """
    try:
        print(f"📝 STT 요청 중 (OpenAI Whisper)...")
        
        with open(file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file,
                language="ko" # 한국어 우선 인식 (필요 시 제거 가능)
            )
            
        result_text = transcript.text
        print(f"✅ STT 결과: {result_text}")
        return result_text

    except Exception as e:
        print(f"❌ STT 변환 실패: {e}")
        return "음성 인식에 실패했습니다."