#### 다음 실습 코드는 학습 목적으로만 사용 바랍니다. 문의 : audit@korea.ac.kr 임성열 Ph.D.
#### 실습 코드는 완성된 상용 버전이 아니라 교육용으로 제작되었으며, 상용 서비스로 이용하려면 배포 목적에 따라서 보완이 필요합니다.

from fastapi import FastAPI, Depends, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path
from dotenv import load_dotenv

# 라우터 및 의존성 임포트
from app.dependencies import get_current_user
from app.routers.generator import router as generator_router
# 필요한 경우 다른 라우터도 임포트 (stt_router 등)

# 환경 변수 로드
load_dotenv()

# 경로 설정 (pathlib 사용 권장)
APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
UPLOAD_DIR = APP_DIR / "routers" / "uploads"

# 디렉토리 생성
STATIC_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI()

# CORS 설정 (프론트엔드와 포트가 다를 경우 필요)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"], # Java Spring 서버 주소
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. 정적 파일 마운트 (Uploads 폴더 접근 허용)
# 결과 오디오 파일에 접근하기 위해 필요합니다.
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# 2. 라우터 등록
app.include_router(generator_router, prefix="/api")

# 3. HTML 페이지 라우팅 (보안 적용)
def _must_exist(p: Path):
    if not p.exists():
        return False
    return True

@app.get("/select.html", include_in_schema=False)
async def select_page(current_user: dict = Depends(get_current_user)):
    if _must_exist(STATIC_DIR / "select.html"):
        return FileResponse(STATIC_DIR / "select.html")
    return Response(status_code=404)

@app.get("/process.html", include_in_schema=False)
async def process_page(current_user: dict = Depends(get_current_user)):
    if _must_exist(STATIC_DIR / "process.html"):
        return FileResponse(STATIC_DIR / "process.html")
    return Response(status_code=404)

@app.get("/result.html", include_in_schema=False)
async def result_page(current_user: dict = Depends(get_current_user)):
    if _must_exist(STATIC_DIR / "result.html"):
        return FileResponse(STATIC_DIR / "result.html")
    return Response(status_code=404)

# 루트 접속 시 리다이렉트 (선택 사항)
@app.get("/")
async def root(current_user: dict = Depends(get_current_user)):
    return FileResponse(STATIC_DIR / "select.html")

# 실행
if __name__ == "__main__":
    import uvicorn
    # WSL에서는 0.0.0.0으로 열어야 호스트 윈도우에서 접속하기 편함
    uvicorn.run("app.main:app", host="0.0.0.0", port=8008, reload=True)
# 1. 인증을 거치지 않고 직접 접근하는 차단 적용됨 : 아래 2개가 모두 막혀야 정상
# http://localhost:8008/index.html  → 401
# http://localhost:8008/static/index.html → 404 (미들웨어 차단)    
    
# python -m uvicorn app.main:app --port 8008
# 단계별 동작 테스트 Java 인증 후에..
# http://localhost:8008/index.html -> 음성 인식 녹화 테스트
# http://localhost:8008/stt-tts.html -> 음성 인식 녹화 -> STT 변환 데모
# http://localhost:8008/TTS-Demo.html -> 텍스트를 입력 -> TTS 음성으로 변환
